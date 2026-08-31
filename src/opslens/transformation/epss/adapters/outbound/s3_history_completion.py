"""Amazon S3 adapter for immutable historical EPSS completion manifests."""

from collections.abc import Mapping
from typing import Protocol, TypedDict, cast

from botocore.exceptions import ClientError

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.epss.history.completion import (
    HistoricalEpssCompletionAlreadyExistsError,
    HistoricalEpssCompletionArtifactV1,
    HistoricalEpssCompletionStoredObjectV1,
)


class HistoricalEpssCompletionConcurrentWriteError(RuntimeError):
    """Raised when S3 reports a concurrent conditional completion write."""


class HistoricalEpssCompletionWriteEvidenceError(RuntimeError):
    """Raised when successful completion persistence lacks VersionId evidence."""


class _S3ResponseMetadata(TypedDict, total=False):
    """Represent S3 HTTP metadata used for completion error classification."""

    HTTPStatusCode: int


class _S3ClientErrorResponse(TypedDict, total=False):
    """Represent the subset of one S3 client error used by this adapter."""

    ResponseMetadata: _S3ResponseMetadata


class S3HistoricalEpssCompletionPutResponse(TypedDict, total=False):
    """Represent successful PutObject evidence required by completion."""

    VersionId: str
    ETag: str


class S3HistoricalEpssCompletionPutClient(Protocol):
    """Define the minimal conditional PutObject capability for completion."""

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: Mapping[str, str],
        IfNoneMatch: str,
    ) -> S3HistoricalEpssCompletionPutResponse:
        """Conditionally create one immutable completion manifest."""
        ...


class S3HistoricalEpssCompletionRepository:
    """Persist historical EPSS completion evidence in Amazon S3."""

    CONTENT_TYPE = "application/json"

    def __init__(
        self,
        *,
        client: S3HistoricalEpssCompletionPutClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize explicit infrastructure dependencies."""
        normalized_bucket = bucket_name.strip()
        if not normalized_bucket:
            raise ValueError("Historical EPSS completion S3 bucket name cannot be empty.")
        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry

    def put_if_absent(
        self,
        *,
        artifact: HistoricalEpssCompletionArtifactV1,
    ) -> HistoricalEpssCompletionStoredObjectV1:
        """Create completion evidence only when the deterministic key is absent."""
        fields = {
            "bucket": self._bucket_name,
            "object_key": artifact.key,
            "size_bytes": artifact.size_bytes,
            "manifest_sha256": artifact.sha256,
            "snapshot_date": artifact.manifest.snapshot_date.isoformat(),
        }

        try:
            with self._telemetry.span("epss.history.completion.s3.put_manifest"):
                response = self._client.put_object(
                    Bucket=self._bucket_name,
                    Key=artifact.key,
                    Body=artifact.raw_bytes,
                    ContentType=self.CONTENT_TYPE,
                    Metadata={
                        "dataset": "epss_history_completion",
                        "schema_version": "1",
                        "manifest_sha256": artifact.sha256,
                    },
                    IfNoneMatch="*",
                )
        except ClientError as exc:
            self._handle_client_error(error=exc, object_key=artifact.key)
            raise AssertionError("Unreachable after completion client-error handling.") from exc

        version_id = response.get("VersionId")
        if not isinstance(version_id, str) or not version_id.strip():
            self._telemetry.metric(
                name="EpssHistoryCompletionWriteEvidenceMismatch",
                value=1.0,
                unit="Count",
            )
            raise HistoricalEpssCompletionWriteEvidenceError(
                "Successful historical EPSS completion PutObject requires VersionId."
            )

        stored = HistoricalEpssCompletionStoredObjectV1(
            key=artifact.key,
            version_id=version_id,
            sha256=artifact.sha256,
            size_bytes=artifact.size_bytes,
        )
        self._telemetry.metric(
            name="EpssHistoryCompletionCreated",
            value=1.0,
            unit="Count",
        )
        self._telemetry.info(
            "Historical EPSS completion manifest created",
            fields={**fields, "version_id": version_id},
        )
        return stored

    def _handle_client_error(self, *, error: ClientError, object_key: str) -> None:
        """Classify conditional completion failures without assuming success."""
        status_code = self._extract_http_status(error)
        fields = {
            "bucket": self._bucket_name,
            "object_key": object_key,
            "http_status": status_code,
        }

        if status_code == 412:
            self._telemetry.metric(
                name="EpssHistoryCompletionAlreadyExists",
                value=1.0,
                unit="Count",
            )
            raise HistoricalEpssCompletionAlreadyExistsError(
                "Historical EPSS completion exists and requires exact replay verification."
            ) from error

        if status_code == 409:
            self._telemetry.metric(
                name="EpssHistoryCompletionConcurrentWrite",
                value=1.0,
                unit="Count",
            )
            raise HistoricalEpssCompletionConcurrentWriteError(
                "Concurrent historical EPSS completion conditional write conflict."
            ) from error

        self._telemetry.exception(
            "Failed to persist historical EPSS completion manifest",
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
