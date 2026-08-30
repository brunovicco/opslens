"""Amazon S3 exact replay verification for historical EPSS completion manifests."""

from hashlib import sha256
from typing import Protocol, TypedDict

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.epss.history.completion import (
    HistoricalEpssCompletionArtifactV1,
    HistoricalEpssCompletionStoredObjectV1,
)


class HistoricalEpssCompletionReplayMismatchError(ValueError):
    """Raised when persisted completion bytes differ from deterministic evidence."""


class S3ObjectBody(Protocol):
    """Define the readable response-body capability used by exact replay."""

    def read(self) -> bytes:
        """Read complete object bytes."""
        ...

    def close(self) -> None:
        """Release response-body resources."""
        ...


class S3HeadCompletionResponse(TypedDict, total=False):
    """Represent HeadObject fields required for completion replay."""

    ContentLength: int
    VersionId: str


class S3GetCompletionResponse(TypedDict, total=False):
    """Represent exact GetObject fields required for completion replay."""

    Body: S3ObjectBody
    ContentLength: int
    VersionId: str


class S3HistoricalEpssCompletionReplayClient(Protocol):
    """Define minimal S3 capabilities required for completion replay."""

    def head_object(self, *, Bucket: str, Key: str) -> S3HeadCompletionResponse:
        """Read current completion metadata."""
        ...

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> S3GetCompletionResponse:
        """Read one exact completion object version."""
        ...


class S3HistoricalEpssCompletionReplayVerifier:
    """Verify exact immutable completion-manifest replay."""

    def __init__(
        self,
        *,
        client: S3HistoricalEpssCompletionReplayClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize exact replay dependencies."""
        normalized_bucket = bucket_name.strip()
        if not normalized_bucket:
            raise ValueError("Historical EPSS completion replay bucket cannot be empty.")
        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry

    def verify_current(
        self,
        *,
        artifact: HistoricalEpssCompletionArtifactV1,
    ) -> HistoricalEpssCompletionStoredObjectV1:
        """Verify current completion key using the exact discovered S3 version."""
        fields = {
            "bucket": self._bucket_name,
            "object_key": artifact.key,
            "expected_sha256": artifact.sha256,
            "expected_size_bytes": artifact.size_bytes,
        }

        try:
            with self._telemetry.span("epss.history.completion.s3.head_current"):
                head = self._client.head_object(
                    Bucket=self._bucket_name,
                    Key=artifact.key,
                )

            version_id = self._require_version_id(head.get("VersionId"), context="HeadObject")
            head_size = self._require_size(head.get("ContentLength"), context="HeadObject")
            if head_size != artifact.size_bytes:
                raise HistoricalEpssCompletionReplayMismatchError(
                    "Historical EPSS completion current size does not match artifact."
                )

            with self._telemetry.span("epss.history.completion.s3.get_exact_version"):
                response = self._client.get_object(
                    Bucket=self._bucket_name,
                    Key=artifact.key,
                    VersionId=version_id,
                )
                body = response.get("Body")
                if body is None:
                    raise HistoricalEpssCompletionReplayMismatchError(
                        "Historical EPSS completion exact GetObject is missing Body."
                    )
                try:
                    payload = body.read()
                finally:
                    body.close()

            response_version = self._require_version_id(
                response.get("VersionId"),
                context="GetObject",
            )
            if response_version != version_id:
                raise HistoricalEpssCompletionReplayMismatchError(
                    "Historical EPSS completion GetObject VersionId changed during replay."
                )

            response_size = self._require_size(
                response.get("ContentLength"),
                context="GetObject",
            )
            if response_size != artifact.size_bytes or len(payload) != artifact.size_bytes:
                raise HistoricalEpssCompletionReplayMismatchError(
                    "Historical EPSS completion exact payload size does not match artifact."
                )

            persisted_sha256 = sha256(payload).hexdigest()
            if persisted_sha256 != artifact.sha256:
                raise HistoricalEpssCompletionReplayMismatchError(
                    "Historical EPSS completion exact payload SHA-256 does not match artifact."
                )
            if payload != artifact.raw_bytes:
                raise HistoricalEpssCompletionReplayMismatchError(
                    "Historical EPSS completion exact payload bytes do not match artifact."
                )

        except HistoricalEpssCompletionReplayMismatchError:
            self._telemetry.metric(
                name="EpssHistoryCompletionReplayMismatch",
                value=1.0,
                unit="Count",
            )
            self._telemetry.exception(
                "Historical EPSS completion replay does not match",
                fields=fields,
            )
            raise

        self._telemetry.metric(
            name="EpssHistoryCompletionReplayVerified",
            value=1.0,
            unit="Count",
        )
        self._telemetry.info(
            "Historical EPSS completion replay verified",
            fields={**fields, "version_id": version_id},
        )
        return HistoricalEpssCompletionStoredObjectV1(
            key=artifact.key,
            version_id=version_id,
            sha256=persisted_sha256,
            size_bytes=len(payload),
        )

    @staticmethod
    def _require_version_id(value: object, *, context: str) -> str:
        """Require a non-empty S3 VersionId."""
        if not isinstance(value, str) or not value.strip():
            raise HistoricalEpssCompletionReplayMismatchError(
                f"Historical EPSS completion {context} requires VersionId."
            )
        return value

    @staticmethod
    def _require_size(value: object, *, context: str) -> int:
        """Require positive S3 ContentLength evidence."""
        if type(value) is not int or value <= 0:
            raise HistoricalEpssCompletionReplayMismatchError(
                f"Historical EPSS completion {context} requires positive ContentLength."
            )
        return value
