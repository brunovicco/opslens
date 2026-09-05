"""Bounded checksummed S3 object-store adapter for Gate 7.3 corpus publication."""

from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass
from typing import Protocol, cast

from opslens.knowledge_retrieval.application.s3_publication import (
    MAX_PUBLICATION_OBJECTS,
    PublicationPayload,
    RemoteObjectEvidence,
)

MAX_LIST_KEYS = MAX_PUBLICATION_OBJECTS + 1
_BUCKET_PATTERN = re.compile(r"^(?!-)[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", re.ASCII)
_ACCOUNT_PATTERN = re.compile(r"^[0-9]{12}$", re.ASCII)


class S3PublicationClient(Protocol):
    """Minimal dynamic client surface used by the S3 publication adapter."""

    def put_object(self, **kwargs: object) -> object:
        """Put one object with caller-supplied integrity metadata."""
        ...

    def head_object(self, **kwargs: object) -> object:
        """Inspect one exact object and return stored checksum metadata."""
        ...

    def list_objects_v2(self, **kwargs: object) -> object:
        """List one bounded prefix without implicit pagination."""
        ...


class S3PublicationStoreError(RuntimeError):
    """Raised when S3 publication transport or response evidence is invalid."""


def _require_trimmed_string(value: object, *, field: str) -> str:
    """Require one trimmed non-empty provider response string."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise S3PublicationStoreError(f"{field} must be one trimmed non-empty string")
    return value


def _require_nonnegative_int(value: object, *, field: str) -> int:
    """Require one non-negative non-boolean provider response integer."""
    if type(value) is not int or value < 0:
        raise S3PublicationStoreError(f"{field} must be a non-negative integer")
    return value


def _require_bool(value: object, *, field: str) -> bool:
    """Require one exact boolean provider response field."""
    if type(value) is not bool:
        raise S3PublicationStoreError(f"{field} must be a boolean")
    return value


def _require_mapping(value: object, *, field: str) -> dict[str, object]:
    """Require one string-keyed mapping from the dynamic SDK boundary."""
    if not isinstance(value, dict):
        raise S3PublicationStoreError(f"{field} must be an object")
    raw = cast(dict[object, object], value)
    if any(not isinstance(key, str) for key in raw):
        raise S3PublicationStoreError(f"{field} keys must be strings")
    return cast(dict[str, object], raw)


def _require_list(value: object, *, field: str) -> list[object]:
    """Require one provider response list."""
    if not isinstance(value, list):
        raise S3PublicationStoreError(f"{field} must be a list")
    return cast(list[object], value)


def _sha256_hex_to_base64(digest: str) -> str:
    """Encode one validated hex SHA-256 digest for the S3 checksum header."""
    try:
        raw = bytes.fromhex(digest)
    except ValueError as exc:
        raise S3PublicationStoreError("checksum_sha256 must contain hexadecimal bytes") from exc
    if len(raw) != 32:
        raise S3PublicationStoreError("checksum_sha256 must contain exactly 32 bytes")
    return base64.b64encode(raw).decode("ascii")


def _sha256_base64_to_hex(value: object) -> str:
    """Decode one S3 ChecksumSHA256 response into the provider-neutral hex digest."""
    encoded = _require_trimmed_string(value, field="ChecksumSHA256")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise S3PublicationStoreError("ChecksumSHA256 must contain valid Base64") from exc
    if len(raw) != 32:
        raise S3PublicationStoreError("ChecksumSHA256 must decode to exactly 32 bytes")
    return raw.hex()


@dataclass(frozen=True, slots=True)
class S3PublicationTarget:
    """Fixed bucket ownership boundary for one publication run."""

    bucket_name: str
    expected_bucket_owner: str

    def __post_init__(self) -> None:
        """Reject ambiguous bucket/owner configuration before SDK calls."""
        bucket_name = _require_trimmed_string(self.bucket_name, field="bucket_name")
        if _BUCKET_PATTERN.fullmatch(bucket_name) is None:
            raise S3PublicationStoreError("bucket_name must be a valid general-purpose S3 name")
        expected_bucket_owner = _require_trimmed_string(
            self.expected_bucket_owner,
            field="expected_bucket_owner",
        )
        if _ACCOUNT_PATTERN.fullmatch(expected_bucket_owner) is None:
            raise S3PublicationStoreError(
                "expected_bucket_owner must be one 12-digit AWS account id"
            )
        object.__setattr__(self, "bucket_name", bucket_name)
        object.__setattr__(self, "expected_bucket_owner", expected_bucket_owner)


class BoundedS3PublicationStore:
    """Write and inspect a small fixed S3 prefix with SHA-256 integrity checks."""

    def __init__(self, client: S3PublicationClient, target: S3PublicationTarget) -> None:
        """Bind one injected SDK client to one exact bucket ownership boundary."""
        self._client = client
        self._target = target

    def put(self, payload: PublicationPayload) -> None:
        """Upload one single-part object with a precomputed SHA-256 and explicit SSE-S3."""
        try:
            self._client.put_object(
                Bucket=self._target.bucket_name,
                Key=payload.key,
                Body=payload.body,
                ContentLength=len(payload.body),
                ContentType=payload.content_type,
                ChecksumSHA256=_sha256_hex_to_base64(payload.checksum_sha256),
                ServerSideEncryption="AES256",
                ExpectedBucketOwner=self._target.expected_bucket_owner,
            )
        except S3PublicationStoreError:
            raise
        except Exception as exc:
            raise S3PublicationStoreError(
                f"S3 PutObject failed for publication key {payload.key!r}"
            ) from exc

    def list_keys(self, prefix: str) -> tuple[str, ...]:
        """List one tiny publication prefix and fail closed instead of paginating."""
        normalized_prefix = _require_trimmed_string(prefix, field="prefix")
        try:
            response = self._client.list_objects_v2(
                Bucket=self._target.bucket_name,
                Prefix=normalized_prefix,
                MaxKeys=MAX_LIST_KEYS,
                ExpectedBucketOwner=self._target.expected_bucket_owner,
            )
        except Exception as exc:
            raise S3PublicationStoreError(
                f"S3 ListObjectsV2 failed for publication prefix {normalized_prefix!r}"
            ) from exc

        parsed = _require_mapping(response, field="ListObjectsV2 response")
        if _require_bool(parsed.get("IsTruncated"), field="IsTruncated"):
            raise S3PublicationStoreError(
                "publication prefix exceeds the bounded object-list budget"
            )
        raw_contents = parsed.get("Contents")
        if raw_contents is None:
            return ()
        contents = _require_list(raw_contents, field="Contents")
        keys: list[str] = []
        for index, raw_item in enumerate(contents):
            item = _require_mapping(raw_item, field=f"Contents[{index}]")
            keys.append(_require_trimmed_string(item.get("Key"), field=f"Contents[{index}].Key"))
        if len(keys) > MAX_PUBLICATION_OBJECTS:
            raise S3PublicationStoreError(
                "publication prefix contains more objects than the local safety budget"
            )
        return tuple(keys)

    def inspect(self, key: str) -> RemoteObjectEvidence:
        """Read exact S3 size/type/SHA-256 evidence without downloading object content."""
        normalized_key = _require_trimmed_string(key, field="key")
        try:
            response = self._client.head_object(
                Bucket=self._target.bucket_name,
                Key=normalized_key,
                ExpectedBucketOwner=self._target.expected_bucket_owner,
                ChecksumMode="ENABLED",
            )
        except Exception as exc:
            raise S3PublicationStoreError(
                f"S3 HeadObject failed for publication key {normalized_key!r}"
            ) from exc

        parsed = _require_mapping(response, field="HeadObject response")
        return RemoteObjectEvidence(
            key=normalized_key,
            byte_count=_require_nonnegative_int(
                parsed.get("ContentLength"),
                field="ContentLength",
            ),
            checksum_sha256=_sha256_base64_to_hex(parsed.get("ChecksumSHA256")),
            content_type=_require_trimmed_string(
                parsed.get("ContentType"),
                field="ContentType",
            ),
        )
