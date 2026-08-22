"""Amazon S3 adapter for immutable NVD Silver Parquet persistence."""

from collections.abc import Mapping
from typing import Protocol, TypedDict, cast

from botocore.exceptions import ClientError

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.nvd.application.errors import (
    NvdSilverParquetAlreadyExistsError,
)
from opslens.transformation.nvd.completion.manifest import (
    NvdSilverStoredObjectV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverParquetArtifactV1,
)


class NvdSilverParquetConcurrentWriteError(RuntimeError):
    """Raised when S3 reports a concurrent conditional-write conflict."""


class NvdSilverParquetWriteEvidenceError(RuntimeError):
    """Raised when a successful S3 write lacks required persistence evidence."""


class _S3ResponseMetadata(TypedDict, total=False):
    """Represent the S3 HTTP metadata used for error classification."""

    HTTPStatusCode: int


class _S3ClientErrorResponse(TypedDict, total=False):
    """Represent the subset of an S3 ClientError response we require."""

    ResponseMetadata: _S3ResponseMetadata


class S3PutObjectResponse(TypedDict, total=False):
    """Represent the subset of a successful PutObject response we require."""

    VersionId: str
    ETag: str


class S3PutNvdSilverObjectClient(Protocol):
    """Define the minimal S3 PutObject capability required by NVD Silver."""

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: Mapping[str, str],
        IfNoneMatch: str,
    ) -> S3PutObjectResponse:
        """Conditionally create one immutable Silver Parquet object."""
        ...


class S3NvdSilverParquetRepository:
    """Persist deterministic NVD Silver Parquet artifacts in Amazon S3."""

    CONTENT_TYPE = "application/vnd.apache.parquet"

    def __init__(
        self,
        *,
        client: S3PutNvdSilverObjectClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize the repository with explicit infrastructure dependencies."""
        normalized_bucket = bucket_name.strip()

        if not normalized_bucket:
            raise ValueError("S3 NVD Silver bucket name cannot be empty.")

        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry

    def put_if_absent(
        self,
        *,
        key: str,
        artifact: NvdSilverParquetArtifactV1,
    ) -> NvdSilverStoredObjectV1:
        """Persist one Parquet artifact only when its deterministic key is absent."""
        normalized_key = key.strip()

        if not normalized_key:
            raise ValueError("S3 NVD Silver object key cannot be empty.")

        fields = {
            "bucket": self._bucket_name,
            "object_key": normalized_key,
            "source_kind": artifact.source_kind.value,
            "source_batch_id": artifact.source_batch_id,
            "row_count": artifact.row_count,
            "size_bytes": artifact.size_bytes,
            "parquet_sha256": artifact.parquet_sha256,
        }

        self._telemetry.info(
            "Persisting NVD Silver Parquet artifact",
            fields=fields,
        )

        try:
            with self._telemetry.span("nvd.silver.s3.put_parquet"):
                response = self._client.put_object(
                    Bucket=self._bucket_name,
                    Key=normalized_key,
                    Body=artifact.parquet_bytes,
                    ContentType=self.CONTENT_TYPE,
                    Metadata=self._build_metadata(artifact),
                    IfNoneMatch="*",
                )
        except ClientError as exc:
            self._handle_client_error(
                error=exc,
                object_key=normalized_key,
            )
            raise AssertionError("Unreachable after S3 client-error handling.") from exc

        try:
            version_id = self._require_version_id(response)
        except NvdSilverParquetWriteEvidenceError:
            self._telemetry.metric(
                name="NvdSilverParquetWriteEvidenceMismatch",
                value=1.0,
                unit="Count",
            )
            self._telemetry.exception(
                "NVD Silver Parquet write lacks exact S3 version evidence",
                fields=fields,
            )
            raise

        stored = NvdSilverStoredObjectV1(
            key=normalized_key,
            version_id=version_id,
            sha256=artifact.parquet_sha256,
            size_bytes=artifact.size_bytes,
            row_count=artifact.row_count,
        )

        self._telemetry.metric(
            name="NvdSilverParquetCreated",
            value=1.0,
            unit="Count",
        )
        self._telemetry.metric(
            name="NvdSilverParquetWriteBytes",
            value=float(artifact.size_bytes),
            unit="Bytes",
        )
        self._telemetry.info(
            "NVD Silver Parquet artifact created",
            fields={
                **fields,
                "version_id": version_id,
            },
        )

        return stored

    @staticmethod
    def _build_metadata(
        artifact: NvdSilverParquetArtifactV1,
    ) -> Mapping[str, str]:
        """Build bounded informational metadata for the persisted artifact."""
        return {
            "dataset": "nvd_cve_versions",
            "schema_version": str(artifact.schema_version),
            "source_kind": artifact.source_kind.value,
            "source_batch_id": artifact.source_batch_id,
            "parquet_sha256": artifact.parquet_sha256,
            "row_count": str(artifact.row_count),
        }

    @staticmethod
    def _require_version_id(
        response: S3PutObjectResponse,
    ) -> str:
        """Require an exact S3 VersionId from a successful write."""
        version_id = response.get("VersionId")

        if not isinstance(version_id, str) or not version_id.strip():
            raise NvdSilverParquetWriteEvidenceError(
                "Successful NVD Silver PutObject response requires VersionId."
            )

        return version_id

    def _handle_client_error(
        self,
        *,
        error: ClientError,
        object_key: str,
    ) -> None:
        """Classify conditional-write failures without accepting them as COMPLETE."""
        status_code = self._extract_http_status(error)

        fields = {
            "bucket": self._bucket_name,
            "object_key": object_key,
            "http_status": status_code,
        }

        if status_code == 412:
            self._telemetry.metric(
                name="NvdSilverParquetAlreadyExists",
                value=1.0,
                unit="Count",
            )
            self._telemetry.info(
                "NVD Silver Parquet deterministic key already exists",
                fields=fields,
            )

            raise NvdSilverParquetAlreadyExistsError(
                "NVD Silver Parquet key already exists and requires exact replay verification."
            ) from error

        if status_code == 409:
            self._telemetry.metric(
                name="NvdSilverParquetConcurrentWrite",
                value=1.0,
                unit="Count",
            )
            self._telemetry.exception(
                "Concurrent NVD Silver Parquet conditional write conflict",
                fields=fields,
            )

            raise NvdSilverParquetConcurrentWriteError(
                "Concurrent NVD Silver Parquet conditional write conflict."
            ) from error

        self._telemetry.metric(
            name="NvdSilverParquetWriteFailure",
            value=1.0,
            unit="Count",
        )
        self._telemetry.exception(
            "Failed to persist NVD Silver Parquet artifact",
            fields=fields,
        )

        raise error

    @staticmethod
    def _extract_http_status(
        error: ClientError,
    ) -> int | None:
        """Extract the S3 HTTP status from one Botocore ClientError."""
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
