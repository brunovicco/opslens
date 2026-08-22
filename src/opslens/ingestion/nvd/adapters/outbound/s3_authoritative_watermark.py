"""Amazon S3 adapter for authoritative NVD incremental watermark state."""

import hashlib
from collections.abc import Mapping
from typing import Protocol, TypedDict, cast

from botocore.exceptions import ClientError

from opslens.ingestion.nvd.application.authoritative_watermark import (
    NvdAuthoritativeWatermarkParserV1,
    NvdAuthoritativeWatermarkSerializerV1,
    NvdAuthoritativeWatermarkV1,
)
from opslens.ingestion.nvd.application.authoritative_watermark_store import (
    NvdAuthoritativeWatermarkAlreadyExistsError,
    NvdAuthoritativeWatermarkConflictError,
    NvdAuthoritativeWatermarkEvidenceError,
    NvdAuthoritativeWatermarkNotFoundError,
    NvdAuthoritativeWatermarkPreconditionFailedError,
    NvdPersistedAuthoritativeWatermarkV1,
)
from opslens.shared.observability.ports import OperationalTelemetry


class _ReadableBody(Protocol):
    """Define the bounded StreamingBody operations used by the adapter."""

    def read(
        self,
        amt: int | None = None,
    ) -> bytes:
        """Read response bytes."""
        ...

    def close(self) -> None:
        """Close the response stream."""
        ...


class _S3ResponseMetadata(TypedDict, total=False):
    """Represent HTTP metadata returned by Botocore errors."""

    HTTPStatusCode: int


class _S3ClientErrorResponse(TypedDict, total=False):
    """Represent Botocore error fields inspected by this adapter."""

    ResponseMetadata: _S3ResponseMetadata


class S3NvdAuthoritativeWatermarkClient(Protocol):
    """Define the minimum S3 surface required for authoritative state."""

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> Mapping[str, object]:
        """Read the current object."""
        ...

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: Mapping[str, str],
        IfNoneMatch: str | None = None,
        IfMatch: str | None = None,
    ) -> Mapping[str, object]:
        """Perform one conditional object write."""
        ...


class S3NvdAuthoritativeWatermarkStore:
    """Persist one authoritative NVD watermark using S3 CAS semantics."""

    CONTENT_TYPE = "application/json"
    MAX_PAYLOAD_BYTES = 64 * 1024

    def __init__(
        self,
        *,
        client: S3NvdAuthoritativeWatermarkClient,
        bucket_name: str,
        object_key: str,
        telemetry: OperationalTelemetry,
        serializer: NvdAuthoritativeWatermarkSerializerV1 | None = None,
        parser: NvdAuthoritativeWatermarkParserV1 | None = None,
    ) -> None:
        """Initialize explicit storage dependencies."""
        normalized_bucket = bucket_name.strip()
        normalized_key = object_key.strip()

        if not normalized_bucket:
            raise ValueError(
                "Authoritative NVD watermark bucket cannot be empty."
            )

        if not normalized_key:
            raise ValueError(
                "Authoritative NVD watermark object key cannot be empty."
            )

        self._client = client
        self._bucket_name = normalized_bucket
        self._object_key = normalized_key
        self._telemetry = telemetry
        self._serializer = (
            serializer
            if serializer is not None
            else NvdAuthoritativeWatermarkSerializerV1()
        )
        self._parser = (
            parser
            if parser is not None
            else NvdAuthoritativeWatermarkParserV1(
                serializer=self._serializer
            )
        )

    def load(
        self,
    ) -> NvdPersistedAuthoritativeWatermarkV1:
        """Load and verify the current authoritative S3 object."""
        try:
            with self._telemetry.span("nvd.watermark.s3.get_object"):
                response = self._client.get_object(
                    Bucket=self._bucket_name,
                    Key=self._object_key,
                )
        except ClientError as exc:
            status_code = self._extract_http_status(exc)

            if status_code == 404:
                raise NvdAuthoritativeWatermarkNotFoundError(
                    "Authoritative NVD watermark does not exist."
                ) from exc

            self._record_failure(
                operation="load",
                http_status=status_code,
            )
            raise

        payload = self._read_payload(response)

        try:
            watermark = self._parser.parse(payload)
        except ValueError as exc:
            raise NvdAuthoritativeWatermarkEvidenceError(
                "Persisted authoritative NVD watermark is invalid."
            ) from exc

        sha256 = hashlib.sha256(payload).hexdigest()

        self._verify_object_response(
            response=response,
            watermark=watermark,
            payload=payload,
            sha256=sha256,
        )

        persisted = NvdPersistedAuthoritativeWatermarkV1(
            watermark=watermark,
            version_id=self._require_string(
                response.get("VersionId"),
                "VersionId",
            ),
            etag=self._require_string(
                response.get("ETag"),
                "ETag",
            ),
            sha256=sha256,
            size_bytes=len(payload),
        )

        self._telemetry.metric(
            name="NvdAuthoritativeWatermarkRead",
            value=1.0,
            unit="Count",
        )
        self._telemetry.info(
            "Loaded authoritative NVD watermark",
            fields={
                "bucket": self._bucket_name,
                "object_key": self._object_key,
                "version_id": persisted.version_id,
                "etag": persisted.etag,
                "committed_through_at": (
                    watermark.canonical_committed_through_at
                ),
            },
        )

        return persisted

    def initialize(
        self,
        *,
        watermark: NvdAuthoritativeWatermarkV1,
    ) -> NvdPersistedAuthoritativeWatermarkV1:
        """Create initial state using If-None-Match."""
        payload, sha256, metadata = self._prepare_write(watermark)

        try:
            with self._telemetry.span("nvd.watermark.s3.initialize"):
                response = self._client.put_object(
                    Bucket=self._bucket_name,
                    Key=self._object_key,
                    Body=payload,
                    ContentType=self.CONTENT_TYPE,
                    Metadata=metadata,
                    IfNoneMatch="*",
                )
        except ClientError as exc:
            status_code = self._extract_http_status(exc)

            if status_code == 412:
                raise NvdAuthoritativeWatermarkAlreadyExistsError(
                    "Authoritative NVD watermark already exists."
                ) from exc

            if status_code == 409:
                raise NvdAuthoritativeWatermarkConflictError(
                    "Authoritative NVD watermark initialization conflicted."
                ) from exc

            self._record_failure(
                operation="initialize",
                http_status=status_code,
            )
            raise

        return self._write_result(
            response=response,
            watermark=watermark,
            payload=payload,
            sha256=sha256,
            metric_name="NvdAuthoritativeWatermarkInitialized",
            message="Initialized authoritative NVD watermark",
        )

    def compare_and_swap(
        self,
        *,
        watermark: NvdAuthoritativeWatermarkV1,
        expected_etag: str,
    ) -> NvdPersistedAuthoritativeWatermarkV1:
        """Advance state only when its previously-read ETag still matches."""
        normalized_etag = expected_etag.strip()

        if not normalized_etag:
            raise ValueError(
                "Expected authoritative NVD watermark ETag cannot be empty."
            )

        payload, sha256, metadata = self._prepare_write(watermark)

        try:
            with self._telemetry.span("nvd.watermark.s3.compare_and_swap"):
                response = self._client.put_object(
                    Bucket=self._bucket_name,
                    Key=self._object_key,
                    Body=payload,
                    ContentType=self.CONTENT_TYPE,
                    Metadata=metadata,
                    IfMatch=normalized_etag,
                )
        except ClientError as exc:
            status_code = self._extract_http_status(exc)

            if status_code == 412:
                raise NvdAuthoritativeWatermarkPreconditionFailedError(
                    "Authoritative NVD watermark ETag changed."
                ) from exc

            if status_code == 409:
                raise NvdAuthoritativeWatermarkConflictError(
                    "Authoritative NVD watermark CAS conflicted."
                ) from exc

            if status_code == 404:
                raise NvdAuthoritativeWatermarkNotFoundError(
                    "Authoritative NVD watermark disappeared during CAS."
                ) from exc

            self._record_failure(
                operation="compare_and_swap",
                http_status=status_code,
            )
            raise

        return self._write_result(
            response=response,
            watermark=watermark,
            payload=payload,
            sha256=sha256,
            metric_name="NvdAuthoritativeWatermarkAdvanced",
            message="Advanced authoritative NVD watermark",
        )

    def _prepare_write(
        self,
        watermark: NvdAuthoritativeWatermarkV1,
    ) -> tuple[bytes, str, dict[str, str]]:
        """Build exact bytes and integrity metadata."""
        payload = self._serializer.serialize(watermark)

        if len(payload) > self.MAX_PAYLOAD_BYTES:
            raise NvdAuthoritativeWatermarkEvidenceError(
                "Authoritative NVD watermark exceeds maximum payload size."
            )

        sha256 = hashlib.sha256(payload).hexdigest()

        return (
            payload,
            sha256,
            {
                "source": watermark.SOURCE,
                "source_interface": watermark.SOURCE_INTERFACE,
                "artifact_kind": "authoritative-watermark",
                "watermark_version": watermark.WATERMARK_VERSION,
                "state": watermark.STATE,
                "committed_through_at": (
                    watermark.canonical_committed_through_at
                ),
                "commit_basis": watermark.commit_basis.KIND,
                "object_sha256": sha256,
            },
        )

    def _read_payload(
        self,
        response: Mapping[str, object],
    ) -> bytes:
        """Read the small control object with a hard upper bound."""
        content_length = response.get("ContentLength")

        if (
            type(content_length) is not int
            or content_length <= 0
            or content_length > self.MAX_PAYLOAD_BYTES
        ):
            raise NvdAuthoritativeWatermarkEvidenceError(
                "Authoritative NVD watermark ContentLength is invalid."
            )

        body_value = response.get("Body")

        if body_value is None:
            raise NvdAuthoritativeWatermarkEvidenceError(
                "Authoritative NVD watermark response has no body."
            )

        body = cast(_ReadableBody, body_value)

        try:
            payload = body.read(self.MAX_PAYLOAD_BYTES + 1)
        finally:
            body.close()

        if len(payload) != content_length:
            raise NvdAuthoritativeWatermarkEvidenceError(
                "Authoritative NVD watermark byte length is inconsistent."
            )

        if len(payload) > self.MAX_PAYLOAD_BYTES:
            raise NvdAuthoritativeWatermarkEvidenceError(
                "Authoritative NVD watermark body exceeds maximum size."
            )

        return payload

    def _verify_object_response(
        self,
        *,
        response: Mapping[str, object],
        watermark: NvdAuthoritativeWatermarkV1,
        payload: bytes,
        sha256: str,
    ) -> None:
        """Verify S3 envelope metadata against exact parsed bytes."""
        if response.get("ContentType") != self.CONTENT_TYPE:
            raise NvdAuthoritativeWatermarkEvidenceError(
                "Authoritative NVD watermark ContentType is invalid."
            )

        metadata_value = response.get("Metadata")

        if not isinstance(metadata_value, Mapping):
            raise NvdAuthoritativeWatermarkEvidenceError(
                "Authoritative NVD watermark metadata is invalid."
            )

        metadata = cast(Mapping[object, object], metadata_value)

        expected = self._prepare_write(watermark)[2]

        for key, expected_value in expected.items():
            if metadata.get(key) != expected_value:
                raise NvdAuthoritativeWatermarkEvidenceError(
                    "Authoritative NVD watermark metadata does not "
                    f"match exact evidence for {key!r}."
                )

        if hashlib.sha256(payload).hexdigest() != sha256:
            raise NvdAuthoritativeWatermarkEvidenceError(
                "Authoritative NVD watermark SHA-256 is inconsistent."
            )

    def _write_result(
        self,
        *,
        response: Mapping[str, object],
        watermark: NvdAuthoritativeWatermarkV1,
        payload: bytes,
        sha256: str,
        metric_name: str,
        message: str,
    ) -> NvdPersistedAuthoritativeWatermarkV1:
        """Build exact persisted identity from a successful conditional PUT."""
        persisted = NvdPersistedAuthoritativeWatermarkV1(
            watermark=watermark,
            version_id=self._require_string(
                response.get("VersionId"),
                "VersionId",
            ),
            etag=self._require_string(
                response.get("ETag"),
                "ETag",
            ),
            sha256=sha256,
            size_bytes=len(payload),
        )

        self._telemetry.metric(
            name=metric_name,
            value=1.0,
            unit="Count",
        )
        self._telemetry.info(
            message,
            fields={
                "bucket": self._bucket_name,
                "object_key": self._object_key,
                "version_id": persisted.version_id,
                "etag": persisted.etag,
                "committed_through_at": (
                    watermark.canonical_committed_through_at
                ),
            },
        )

        return persisted

    def _record_failure(
        self,
        *,
        operation: str,
        http_status: int | None,
    ) -> None:
        """Record unexpected S3 persistence failure."""
        self._telemetry.metric(
            name="NvdAuthoritativeWatermarkStorageFailure",
            value=1.0,
            unit="Count",
        )
        self._telemetry.exception(
            "Authoritative NVD watermark S3 operation failed",
            fields={
                "bucket": self._bucket_name,
                "object_key": self._object_key,
                "operation": operation,
                "http_status": http_status,
            },
        )

    @staticmethod
    def _require_string(
        value: object,
        label: str,
    ) -> str:
        """Require one non-empty S3 response string."""
        if not isinstance(value, str) or not value.strip():
            raise NvdAuthoritativeWatermarkEvidenceError(
                f"Authoritative NVD watermark has no valid S3 {label}."
            )

        return value

    @staticmethod
    def _extract_http_status(
        error: ClientError,
    ) -> int | None:
        """Extract HTTP status from one Botocore error."""
        response = cast(
            _S3ClientErrorResponse,
            error.response,
        )
        metadata = response.get(
            "ResponseMetadata",
            {},
        )
        status_code = metadata.get("HTTPStatusCode")

        return status_code if isinstance(status_code, int) else None
