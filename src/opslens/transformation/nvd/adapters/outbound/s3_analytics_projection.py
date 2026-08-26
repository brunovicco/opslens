"""Amazon S3 adapter for exact-version NVD analytics projection."""

from collections.abc import Mapping
from hashlib import sha256
from typing import Protocol, TypedDict, cast

from botocore.exceptions import ClientError

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.nvd.application.analytics_projection_key_factory import (
    NvdAnalyticsProjectionKeyFactoryV1,
    NvdAnalyticsProjectionKeyV1,
    NvdAnalyticsProjectionRequestV1,
)
from opslens.transformation.nvd.application.analytics_projection_models import (
    NvdAnalyticsExactObjectRefV1,
)
from opslens.transformation.nvd.serialization.schema import (
    NVD_CVE_VERSIONS_SCHEMA_NAME,
    NVD_CVE_VERSIONS_SCHEMA_VERSION,
)

NVD_ANALYTICS_MAX_PARQUET_BYTES = 128 * 1024 * 1024


class NvdAnalyticsProjectionAlreadyExistsError(RuntimeError):
    """Raised when the deterministic destination already has a current object."""


class NvdAnalyticsProjectionConcurrentWriteError(RuntimeError):
    """Raised when S3 reports a concurrent conditional-copy conflict."""


class NvdAnalyticsProjectionEvidenceMismatchError(RuntimeError):
    """Raised when S3 persistence evidence does not match projection authority."""


class NvdAnalyticsProjectionS3Error(RuntimeError):
    """Raised for provider failures not classified as conditional conflicts."""


class _ReadableBody(Protocol):
    """Define the bounded response-body operations used by this adapter."""

    def read(
        self,
        amt: int | None = None,
    ) -> bytes:
        """Read response bytes."""
        ...

    def close(self) -> None:
        """Close the response stream."""
        ...


class S3NvdAnalyticsProjectionClient(Protocol):
    """Define the minimal S3 capabilities required by analytics projection."""

    def copy_object(
        self,
        *,
        Bucket: str,
        Key: str,
        CopySource: Mapping[str, str],
        IfNoneMatch: str,
        MetadataDirective: str,
        ContentType: str,
        Metadata: Mapping[str, str],
    ) -> Mapping[str, object]:
        """Conditionally copy one exact source object version."""
        ...

    def head_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> Mapping[str, object]:
        """Read current destination metadata without prefix discovery."""
        ...

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> Mapping[str, object]:
        """Read one exact projected object version."""
        ...


class _S3ResponseMetadata(TypedDict, total=False):
    """Represent HTTP metadata inspected from Botocore errors."""

    HTTPStatusCode: int


class _S3ClientErrorResponse(TypedDict, total=False):
    """Represent the Botocore error response fields inspected here."""

    ResponseMetadata: _S3ResponseMetadata


class S3NvdAnalyticsProjectionRepositoryV1:
    """Materialize exact Silver Parquet versions into the analytics namespace."""

    CONTENT_TYPE = "application/vnd.apache.parquet"

    def __init__(
        self,
        *,
        client: S3NvdAnalyticsProjectionClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
        max_parquet_bytes: int = NVD_ANALYTICS_MAX_PARQUET_BYTES,
    ) -> None:
        """Initialize exact CopyObject and verification dependencies."""
        normalized_bucket = bucket_name.strip()
        if not normalized_bucket:
            raise ValueError(
                "NVD analytics S3 bucket name cannot be empty."
            )

        if type(max_parquet_bytes) is not int or max_parquet_bytes <= 0:
            raise ValueError(
                "NVD analytics max_parquet_bytes must be a positive integer."
            )

        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry
        self._max_parquet_bytes = max_parquet_bytes
        self._key_factory = NvdAnalyticsProjectionKeyFactoryV1()

    def copy_if_absent(
        self,
        *,
        request: NvdAnalyticsProjectionRequestV1,
        destination: NvdAnalyticsProjectionKeyV1,
    ) -> NvdAnalyticsExactObjectRefV1:
        """Copy one exact Silver version and verify the new destination exactly."""
        self._require_deterministic_destination(
            request=request,
            destination=destination,
        )
        self._require_bounded_source(request)

        source = request.silver_parquet
        metadata = self._build_metadata(request)
        fields = {
            "bucket": self._bucket_name,
            "source_key": source.key,
            "source_version_id": source.version_id,
            "destination_key": destination.object_key,
            "source_kind": request.source_kind.value,
            "source_batch_id": request.source_batch_id,
            "size_bytes": source.size_bytes,
        }

        self._telemetry.info(
            "Copying exact NVD Silver Parquet into analytics",
            fields=fields,
        )

        try:
            with self._telemetry.span(
                "nvd.analytics.s3.copy_exact_version"
            ):
                response = self._client.copy_object(
                    Bucket=self._bucket_name,
                    Key=destination.object_key,
                    CopySource={
                        "Bucket": self._bucket_name,
                        "Key": source.key,
                        "VersionId": source.version_id,
                    },
                    IfNoneMatch="*",
                    MetadataDirective="REPLACE",
                    ContentType=self.CONTENT_TYPE,
                    Metadata=metadata,
                )
        except ClientError as exc:
            self._handle_copy_error(
                error=exc,
                fields=fields,
            )
            raise AssertionError(
                "Unreachable after analytics CopyObject error handling."
            ) from exc

        copy_source_version = response.get(
            "CopySourceVersionId"
        )
        if copy_source_version != source.version_id:
            self._record_evidence_mismatch(
                "NVD analytics CopySourceVersionId does not match exact source authority.",
                fields=fields,
            )

        destination_version = response.get("VersionId")
        if (
            not isinstance(destination_version, str)
            or not destination_version.strip()
        ):
            self._record_evidence_mismatch(
                "Successful NVD analytics CopyObject requires destination VersionId.",
                fields=fields,
            )

        projected = self._verify_exact_destination(
            request=request,
            destination=destination,
            destination_version_id=cast(str, destination_version),
        )

        self._telemetry.metric(
            name="NvdAnalyticsProjectionBytes",
            value=float(projected.size_bytes),
            unit="Bytes",
        )
        self._telemetry.info(
            "Exact NVD analytics projection verified",
            fields={
                **fields,
                "destination_version_id": projected.version_id,
                "destination_sha256": projected.sha256,
            },
        )

        return projected

    def verify_current(
        self,
        *,
        request: NvdAnalyticsProjectionRequestV1,
        destination: NvdAnalyticsProjectionKeyV1,
    ) -> NvdAnalyticsExactObjectRefV1:
        """Verify the current deterministic destination after a replay collision."""
        self._require_deterministic_destination(
            request=request,
            destination=destination,
        )
        self._require_bounded_source(request)

        try:
            with self._telemetry.span(
                "nvd.analytics.s3.head_current_destination"
            ):
                response = self._client.head_object(
                    Bucket=self._bucket_name,
                    Key=destination.object_key,
                )
        except ClientError as exc:
            self._raise_provider_error(
                error=exc,
                message=(
                    "Failed to read current NVD analytics destination."
                ),
                fields={
                    "bucket": self._bucket_name,
                    "destination_key": destination.object_key,
                },
            )

        version_id = response.get("VersionId")
        if not isinstance(version_id, str) or not version_id.strip():
            self._record_evidence_mismatch(
                "Current NVD analytics destination requires exact VersionId.",
                fields={
                    "bucket": self._bucket_name,
                    "destination_key": destination.object_key,
                },
            )

        return self._verify_exact_destination(
            request=request,
            destination=destination,
            destination_version_id=cast(str, version_id),
        )

    def _verify_exact_destination(
        self,
        *,
        request: NvdAnalyticsProjectionRequestV1,
        destination: NvdAnalyticsProjectionKeyV1,
        destination_version_id: str,
    ) -> NvdAnalyticsExactObjectRefV1:
        """Verify bytes and lineage on one exact destination VersionId."""
        fields = {
            "bucket": self._bucket_name,
            "destination_key": destination.object_key,
            "destination_version_id": destination_version_id,
        }

        try:
            with self._telemetry.span(
                "nvd.analytics.s3.verify_exact_destination"
            ):
                response = self._client.get_object(
                    Bucket=self._bucket_name,
                    Key=destination.object_key,
                    VersionId=destination_version_id,
                )
        except ClientError as exc:
            self._raise_provider_error(
                error=exc,
                message=(
                    "Failed to read exact NVD analytics destination version."
                ),
                fields=fields,
            )

        body_value = response.get("Body")
        if (
            body_value is None
            or not hasattr(body_value, "read")
            or not hasattr(body_value, "close")
        ):
            self._record_evidence_mismatch(
                "NVD analytics destination GetObject Body is invalid.",
                fields=fields,
            )

        body = cast(_ReadableBody, body_value)

        try:
            returned_version = response.get("VersionId")
            if returned_version != destination_version_id:
                self._record_evidence_mismatch(
                    "NVD analytics destination VersionId does not match request.",
                    fields=fields,
                )

            content_length = response.get("ContentLength")
            if (
                type(content_length) is not int
                or content_length <= 0
                or content_length != request.silver_parquet.size_bytes
                or content_length > self._max_parquet_bytes
            ):
                self._record_evidence_mismatch(
                    "NVD analytics destination ContentLength is invalid.",
                    fields=fields,
                )

            if response.get("ContentType") != self.CONTENT_TYPE:
                self._record_evidence_mismatch(
                    "NVD analytics destination ContentType is invalid.",
                    fields=fields,
                )

            metadata_value = response.get("Metadata")
            if not isinstance(metadata_value, Mapping):
                self._record_evidence_mismatch(
                    "NVD analytics destination Metadata is invalid.",
                    fields=fields,
                )

            metadata = cast(Mapping[object, object], metadata_value)
            expected_metadata = self._build_metadata(request)
            if dict(metadata) != dict(expected_metadata):
                self._record_evidence_mismatch(
                    "NVD analytics destination lineage metadata does not match authority.",
                    fields=fields,
                )

            exact_length = cast(int, content_length)
            payload = body.read(exact_length + 1)

            if len(payload) != exact_length:
                self._record_evidence_mismatch(
                    "NVD analytics destination bytes do not match ContentLength.",
                    fields=fields,
                )

            actual_sha256 = sha256(payload).hexdigest()
            if actual_sha256 != request.silver_parquet.sha256:
                self._record_evidence_mismatch(
                    "NVD analytics destination SHA-256 does not match exact source.",
                    fields=fields,
                )

            if not (
                payload.startswith(b"PAR1")
                and payload.endswith(b"PAR1")
            ):
                self._record_evidence_mismatch(
                    "NVD analytics destination lacks Parquet magic bytes.",
                    fields=fields,
                )
        finally:
            body.close()

        return NvdAnalyticsExactObjectRefV1(
            key=destination.object_key,
            version_id=destination_version_id,
            sha256=actual_sha256,
            size_bytes=len(payload),
        )

    def _require_deterministic_destination(
        self,
        *,
        request: NvdAnalyticsProjectionRequestV1,
        destination: NvdAnalyticsProjectionKeyV1,
    ) -> None:
        """Reject destinations not produced by the permanent key contract."""
        expected = self._key_factory.build(request)
        if destination != expected:
            raise ValueError(
                "NVD analytics destination does not match deterministic key contract."
            )

    def _require_bounded_source(
        self,
        request: NvdAnalyticsProjectionRequestV1,
    ) -> None:
        """Reject a source too large for exact destination verification."""
        if request.silver_parquet.size_bytes > self._max_parquet_bytes:
            raise ValueError(
                "NVD analytics source Parquet exceeds verification byte bound."
            )

    @staticmethod
    def _build_metadata(
        request: NvdAnalyticsProjectionRequestV1,
    ) -> Mapping[str, str]:
        """Build the exact bounded lineage metadata contract."""
        source = request.silver_parquet
        return {
            "dataset": NVD_CVE_VERSIONS_SCHEMA_NAME,
            "schema_version": str(
                NVD_CVE_VERSIONS_SCHEMA_VERSION
            ),
            "source_kind": request.source_kind.value,
            "source_batch_id": request.source_batch_id,
            "row_count": str(request.row_count),
            "parquet_sha256": source.sha256,
            "authority_source_key": source.key,
            "authority_source_version_id": source.version_id,
            "authority_source_sha256": source.sha256,
            "authority_state": request.authority_state,
        }

    def _handle_copy_error(
        self,
        *,
        error: ClientError,
        fields: Mapping[str, object],
    ) -> None:
        """Classify S3 conditional-copy failures without guessing success."""
        status_code = self._extract_http_status(error)
        error_fields = {
            **fields,
            "http_status": status_code,
        }

        if status_code == 412:
            self._telemetry.metric(
                name="NvdAnalyticsProjectionAlreadyProjected",
                value=1.0,
                unit="Count",
            )
            self._telemetry.info(
                "NVD analytics deterministic destination already exists",
                fields=error_fields,
            )
            raise NvdAnalyticsProjectionAlreadyExistsError(
                "NVD analytics destination already exists and requires exact replay verification."
            ) from error

        if status_code == 409:
            self._telemetry.metric(
                name="NvdAnalyticsProjectionConflict",
                value=1.0,
                unit="Count",
            )
            self._telemetry.exception(
                "Concurrent NVD analytics conditional copy conflict",
                fields=error_fields,
            )
            raise NvdAnalyticsProjectionConcurrentWriteError(
                "Concurrent NVD analytics conditional copy conflict."
            ) from error

        self._raise_provider_error(
            error=error,
            message="Failed to copy exact NVD Silver version into analytics.",
            fields=error_fields,
        )

    def _record_evidence_mismatch(
        self,
        message: str,
        *,
        fields: Mapping[str, object],
    ) -> None:
        """Emit fail-closed evidence telemetry and raise the boundary error."""
        self._telemetry.metric(
            name="NvdAnalyticsProjectionEvidenceMismatch",
            value=1.0,
            unit="Count",
        )
        self._telemetry.exception(
            message,
            fields=fields,
        )
        raise NvdAnalyticsProjectionEvidenceMismatchError(
            message
        )

    def _raise_provider_error(
        self,
        *,
        error: ClientError,
        message: str,
        fields: Mapping[str, object],
    ) -> None:
        """Map one unclassified S3 provider failure at the adapter boundary."""
        self._telemetry.metric(
            name="NvdAnalyticsProjectionFailure",
            value=1.0,
            unit="Count",
        )
        self._telemetry.exception(
            message,
            fields={
                **fields,
                "http_status": self._extract_http_status(error),
            },
        )
        raise NvdAnalyticsProjectionS3Error(message) from error

    @staticmethod
    def _extract_http_status(
        error: ClientError,
    ) -> int | None:
        """Return the Botocore HTTP status when present."""
        response = cast(
            _S3ClientErrorResponse,
            error.response,
        )
        metadata = response.get("ResponseMetadata")
        if metadata is None:
            return None

        status = metadata.get("HTTPStatusCode")
        return status if type(status) is int else None
