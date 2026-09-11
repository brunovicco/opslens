"""Read one explicitly versioned S3 authority object without mutable discovery."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, TypedDict, cast


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
    Metadata: Mapping[str, str]


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
    """Evidence returned by one explicitly requested immutable S3 object version."""

    object_key: str
    version_id: str
    payload: bytes
    metadata: tuple[tuple[str, str], ...] = ()

    def metadata_value(self, key: str) -> str | None:
        """Return one exact user-metadata value without exposing mutable state."""
        for metadata_key, value in self.metadata:
            if metadata_key == key:
                return value
        return None


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

        metadata = self._freeze_metadata(response.get("Metadata"))
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
            metadata=metadata,
        )

    @staticmethod
    def _freeze_metadata(
        value: Mapping[str, str] | None,
    ) -> tuple[tuple[str, str], ...]:
        """Validate and freeze exact S3 user metadata in deterministic key order."""
        if value is None:
            return ()
        if not isinstance(value, Mapping):
            raise ExactS3AuthorityObjectError("S3 GetObject Metadata must be a mapping")

        metadata = cast(Mapping[object, object], value)
        frozen: list[tuple[str, str]] = []
        seen: set[str] = set()
        for raw_key, raw_value in metadata.items():
            if type(raw_key) is not str or not raw_key:
                raise ExactS3AuthorityObjectError(
                    "S3 user metadata keys must be non-empty strings"
                )
            if type(raw_value) is not str or not raw_value:
                raise ExactS3AuthorityObjectError(
                    "S3 user metadata values must be non-empty strings"
                )
            normalized_key = raw_key.lower()
            if normalized_key in seen:
                raise ExactS3AuthorityObjectError(
                    "S3 user metadata contains duplicate case-insensitive keys"
                )
            seen.add(normalized_key)
            frozen.append((raw_key, raw_value))

        return tuple(sorted(frozen, key=lambda item: item[0]))

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
