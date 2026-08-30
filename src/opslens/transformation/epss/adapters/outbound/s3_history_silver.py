"""Amazon S3 adapter for immutable historical EPSS Silver persistence."""

from collections.abc import Mapping
from typing import Protocol, TypedDict, cast

from botocore.exceptions import ClientError

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.epss.history.models import (
    HistoricalEpssSilverArtifactV1,
    HistoricalEpssSilverStoredObjectV1,
)
from opslens.transformation.epss.history.persistence import (
    HistoricalEpssSilverAlreadyExistsError,
)


class HistoricalEpssSilverConcurrentWriteError(RuntimeError):
    """Raised when S3 reports a concurrent conditional-write conflict."""


class HistoricalEpssSilverWriteEvidenceError(RuntimeError):
    """Raised when a successful write lacks exact S3 version evidence."""


class _S3ResponseMetadata(TypedDict, total=False):
    """Represent S3 HTTP metadata used for error classification."""

    HTTPStatusCode: int


class _S3ClientErrorResponse(TypedDict, total=False):
    """Represent the subset of one S3 client error used by this adapter."""

    ResponseMetadata: _S3ResponseMetadata


class S3HistoricalEpssSilverPutResponse(TypedDict, total=False):
    """Represent successful PutObject evidence required by historical Silver."""

    VersionId: str
    ETag: str


class S3HistoricalEpssSilverPutClient(Protocol):
    """Define the minimal conditional S3 PutObject capability."""

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: Mapping[str, str],
        IfNoneMatch: str,
    ) -> S3HistoricalEpssSilverPutResponse:
        """Conditionally create one immutable historical Silver object."""
        ...


class S3HistoricalEpssSilverRepository:
    """Persist deterministic historical EPSS Silver Parquet in Amazon S3."""

    CONTENT_TYPE = "application/vnd.apache.parquet"

    def __init__(
        self,
        *,
        client: S3HistoricalEpssSilverPutClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize explicit infrastructure dependencies."""
        normalized_bucket = bucket_name.strip()

        if not normalized_bucket:
            raise ValueError("Historical EPSS Silver S3 bucket name cannot be empty.")

        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry

    def put_if_absent(
        self,
        *,
        key: str,
        artifact: HistoricalEpssSilverArtifactV1,
    ) -> HistoricalEpssSilverStoredObjectV1:
        """Create exact deterministic Parquet only when the Silver key is absent."""
        normalized_key = key.strip()

        if not normalized_key:
            raise ValueError("Historical EPSS Silver S3 object key cannot be empty.")

        fields = {
            "bucket": self._bucket_name,
            "object_key": normalized_key,
            "row_count": artifact.row_count,
            "size_bytes": artifact.size_bytes,
            "schema_version": artifact.schema_version,
            "parquet_sha256": artifact.parquet_sha256,
        }

        self._telemetry.info(
            "Persisting historical EPSS Silver Parquet artifact",
            fields=fields,
        )

        try:
            with self._telemetry.span("epss.history.silver.s3.put_parquet"):
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
        except HistoricalEpssSilverWriteEvidenceError:
            self._telemetry.metric(
                name="EpssHistorySilverWriteEvidenceMismatch",
                value=1.0,
                unit="Count",
            )
            self._telemetry.exception(
                "Historical EPSS Silver write lacks exact S3 version evidence",
                fields=fields,
            )
            raise

        stored = HistoricalEpssSilverStoredObjectV1(
            key=normalized_key,
            version_id=version_id,
            parquet_sha256=artifact.parquet_sha256,
            size_bytes=artifact.size_bytes,
            row_count=artifact.row_count,
            schema_version=artifact.schema_version,
        )

        self._telemetry.metric(
            name="EpssHistorySilverCreated",
            value=1.0,
            unit="Count",
        )
        self._telemetry.metric(
            name="EpssHistorySilverWriteBytes",
            value=float(artifact.size_bytes),
            unit="Bytes",
        )
        self._telemetry.info(
            "Historical EPSS Silver Parquet artifact created",
            fields={
                **fields,
                "version_id": version_id,
            },
        )

        return stored

    @staticmethod
    def _build_metadata(
        artifact: HistoricalEpssSilverArtifactV1,
    ) -> Mapping[str, str]:
        """Build bounded informational metadata for the exact Parquet object."""
        return {
            "dataset": "epss_scores",
            "schema_version": str(artifact.schema_version),
            "parquet_sha256": artifact.parquet_sha256,
            "row_count": str(artifact.row_count),
        }

    @staticmethod
    def _require_version_id(
        response: S3HistoricalEpssSilverPutResponse,
    ) -> str:
        """Require exact S3 VersionId evidence after successful creation."""
        version_id = response.get("VersionId")

        if not isinstance(version_id, str) or not version_id.strip():
            raise HistoricalEpssSilverWriteEvidenceError(
                "Successful historical EPSS Silver PutObject response requires VersionId."
            )

        return version_id

    def _handle_client_error(
        self,
        *,
        error: ClientError,
        object_key: str,
    ) -> None:
        """Classify conditional-write failures without accepting unverified replay."""
        status_code = self._extract_http_status(error)
        fields = {
            "bucket": self._bucket_name,
            "object_key": object_key,
            "http_status": status_code,
        }

        if status_code == 412:
            self._telemetry.metric(
                name="EpssHistorySilverAlreadyExists",
                value=1.0,
                unit="Count",
            )
            self._telemetry.info(
                "Historical EPSS Silver deterministic key already exists",
                fields=fields,
            )
            raise HistoricalEpssSilverAlreadyExistsError(
                "Historical EPSS Silver key already exists and requires exact replay verification."
            ) from error

        if status_code == 409:
            self._telemetry.metric(
                name="EpssHistorySilverConcurrentWrite",
                value=1.0,
                unit="Count",
            )
            self._telemetry.exception(
                "Concurrent historical EPSS Silver conditional write conflict",
                fields=fields,
            )
            raise HistoricalEpssSilverConcurrentWriteError(
                "Concurrent historical EPSS Silver conditional write conflict."
            ) from error

        self._telemetry.metric(
            name="EpssHistorySilverWriteFailure",
            value=1.0,
            unit="Count",
        )
        self._telemetry.exception(
            "Failed to persist historical EPSS Silver Parquet artifact",
            fields=fields,
        )
        raise error

    @staticmethod
    def _extract_http_status(error: ClientError) -> int | None:
        """Extract one S3 HTTP status from Botocore error evidence."""
        response = cast(_S3ClientErrorResponse, error.response)
        metadata = response.get("ResponseMetadata", {})
        status_code = metadata.get("HTTPStatusCode")
        return status_code if isinstance(status_code, int) else None
