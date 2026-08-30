"""Amazon S3 adapter for exact historical EPSS Bronze object versions."""

from typing import Protocol, TypedDict

from opslens.transformation.epss.history.models import (
    HistoricalEpssBronzeObjectPayloadV1,
)

EPSS_HISTORY_MAX_MANIFEST_BYTES = 256 * 1024
EPSS_HISTORY_MAX_SOURCE_BYTES = 16 * 1024 * 1024


class HistoricalEpssS3EvidenceMismatchError(ValueError):
    """Raised when S3 transport evidence disagrees with the requested version."""


class S3ObjectBody(Protocol):
    """Define the readable S3 response-body capability used by this adapter."""

    def read(self) -> bytes:
        """Read the complete response payload."""
        ...

    def close(self) -> None:
        """Release response-body resources."""
        ...


class S3VersionedGetResponse(TypedDict, total=False):
    """Represent exact-version GetObject fields required by EPSS history."""

    Body: S3ObjectBody
    ContentLength: int
    VersionId: str


class S3VersionedGetClient(Protocol):
    """Define the exact S3 GetObjectVersion capability."""

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> S3VersionedGetResponse:
        """Read one explicit S3 object version."""
        ...


class S3VersionedHistoricalEpssBronzeObjectReader:
    """Read exact historical EPSS Bronze versions from one data bucket."""

    def __init__(self, *, client: S3VersionedGetClient, bucket_name: str) -> None:
        """Initialize the reader with one exact-version S3 client and bucket."""
        normalized_bucket = bucket_name.strip()
        if not normalized_bucket:
            raise ValueError("Historical EPSS S3 bucket name cannot be empty.")
        self._client = client
        self._bucket_name = normalized_bucket

    def get(
        self,
        *,
        key: str,
        version_id: str,
        max_bytes: int,
    ) -> HistoricalEpssBronzeObjectPayloadV1:
        """Read and verify one exact S3 object version within a size envelope."""
        normalized_key = key.strip()
        normalized_version = version_id.strip()
        if not normalized_key:
            raise ValueError("Historical EPSS object key cannot be empty.")
        if not normalized_version:
            raise ValueError("Historical EPSS object VersionId cannot be empty.")
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("Historical EPSS maximum object size must be positive.")

        response = self._client.get_object(
            Bucket=self._bucket_name,
            Key=normalized_key,
            VersionId=normalized_version,
        )
        body = response.get("Body")
        if body is None:
            raise HistoricalEpssS3EvidenceMismatchError(
                "Versioned S3 response is missing Body."
            )

        try:
            response_version = response.get("VersionId")
            if response_version != normalized_version:
                raise HistoricalEpssS3EvidenceMismatchError(
                    "S3 response VersionId does not match the requested historical EPSS version."
                )

            content_length = response.get("ContentLength")
            if type(content_length) is not int or content_length <= 0:
                raise HistoricalEpssS3EvidenceMismatchError(
                    "Versioned S3 response ContentLength must be positive."
                )
            if content_length > max_bytes:
                raise HistoricalEpssS3EvidenceMismatchError(
                    "Versioned S3 response exceeds the historical EPSS size limit."
                )

            raw_bytes = body.read()
        finally:
            body.close()

        if len(raw_bytes) != content_length:
            raise HistoricalEpssS3EvidenceMismatchError(
                "Historical EPSS S3 payload length does not match ContentLength."
            )
        if len(raw_bytes) > max_bytes:
            raise HistoricalEpssS3EvidenceMismatchError(
                "Historical EPSS S3 payload exceeds the configured size limit."
            )

        return HistoricalEpssBronzeObjectPayloadV1(
            key=normalized_key,
            version_id=normalized_version,
            raw_bytes=raw_bytes,
        )
