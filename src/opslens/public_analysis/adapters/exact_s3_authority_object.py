"""Read one explicitly versioned S3 authority object without mutable discovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypedDict


class ExactS3AuthorityObjectError(RuntimeError):
    """Reject invalid coordinates or contradictory exact-version S3 evidence."""


class S3AuthorityObjectBody(Protocol):
    """Minimal readable/closable body capability returned by S3 GetObject."""

    def read(self) -> bytes:
        """Read the complete admitted object body."""
        ...

    def close(self) -> None:
        """Release the underlying response-body resources."""
        ...


class ExactS3GetObjectResponse(TypedDict, total=False):
    """Subset of S3 GetObject evidence required by this boundary."""

    Body: S3AuthorityObjectBody
    VersionId: str
    ContentLength: int


class ExactS3AuthorityObjectClient(Protocol):
    """Only the exact-version S3 capability permitted by this adapter."""

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> ExactS3GetObjectResponse:
        """Read one exact S3 object version."""
        ...


@dataclass(frozen=True, slots=True)
class ExactS3AuthorityObject:
    """Bytes proven to originate from one explicitly requested S3 object version."""

    object_key: str
    version_id: str
    payload: bytes


class ExactS3AuthorityObjectReader:
    """Perform exactly one bounded GetObject against admitted immutable coordinates."""

    def __init__(
        self,
        *,
        client: ExactS3AuthorityObjectClient,
        bucket_name: str,
        max_bytes: int,
    ) -> None:
        """Bind one explicit bucket and source-specific maximum object size."""
        normalized_bucket = bucket_name.strip()
        if not normalized_bucket:
            raise ValueError("S3 authority bucket name cannot be empty")
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("max_bytes must be a positive integer")
        self._client = client
        self._bucket_name = normalized_bucket
        self._max_bytes = max_bytes

    def read(self, *, object_key: str, version_id: str) -> ExactS3AuthorityObject:
        """Read and verify one exact object version with no discovery, retry, or fallback."""
        key = self._require_coordinate(object_key, name="object_key")
        version = self._require_coordinate(version_id, name="version_id")
        response = self._client.get_object(
            Bucket=self._bucket_name,
            Key=key,
            VersionId=version,
        )

        returned_version = response.get("VersionId")
        if returned_version != version:
            raise ExactS3AuthorityObjectError(
                "S3 GetObject response VersionId does not match the requested version"
            )

        content_length = response.get("ContentLength")
        if type(content_length) is not int or content_length < 0:
            raise ExactS3AuthorityObjectError(
                "S3 GetObject response requires a non-negative ContentLength"
            )
        if content_length > self._max_bytes:
            raise ExactS3AuthorityObjectError(
                "S3 authority object exceeds the configured byte limit"
            )

        body = response.get("Body")
        if body is None:
            raise ExactS3AuthorityObjectError("S3 GetObject response is missing Body")

        try:
            payload = body.read()
        finally:
            body.close()

        if type(payload) is not bytes:
            raise ExactS3AuthorityObjectError("S3 authority object body must return bytes")
        if len(payload) != content_length:
            raise ExactS3AuthorityObjectError(
                "S3 authority object byte length does not match ContentLength"
            )

        return ExactS3AuthorityObject(
            object_key=key,
            version_id=version,
            payload=payload,
        )

    @staticmethod
    def _require_coordinate(value: str, *, name: str) -> str:
        """Reject empty or non-string physical coordinates before provider I/O."""
        if type(value) is not str or not value.strip():
            raise ExactS3AuthorityObjectError(f"{name} must be a non-empty string")
        return value.strip()


__all__ = [
    "ExactS3AuthorityObject",
    "ExactS3AuthorityObjectClient",
    "ExactS3AuthorityObjectError",
    "ExactS3AuthorityObjectReader",
    "ExactS3GetObjectResponse",
    "S3AuthorityObjectBody",
]
