"""Application-owned bounded publication of canonical Bedrock source objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

from opslens.knowledge_retrieval.application.bedrock_publication import (
    BedrockPublicationPlan,
)

CONTENT_TEXT_PLAIN = "text/plain; charset=utf-8"
CONTENT_APPLICATION_JSON = "application/json"
MAX_PUBLICATION_OBJECTS = 32


class S3PublicationValidationError(ValueError):
    """Raised when remote publication evidence does not match the deterministic plan."""


def _require_nonblank(value: object, *, field: str) -> str:
    """Require one exact non-empty string through a runtime boundary."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise S3PublicationValidationError(f"{field} must be one trimmed non-empty string")
    return value


def _require_sha256(value: object, *, field: str) -> str:
    """Require one lowercase SHA-256 digest without importing provider semantics."""
    normalized = _require_nonblank(value, field=field)
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise S3PublicationValidationError(
            f"{field} must be a lowercase 64-hex SHA-256 digest"
        )
    return normalized


def _require_positive_int(value: object, *, field: str) -> int:
    """Require one positive non-boolean integer."""
    if type(value) is not int or value <= 0:
        raise S3PublicationValidationError(f"{field} must be a positive integer")
    return value


def _require_bytes(value: object, *, field: str) -> bytes:
    """Require non-empty immutable bytes for one outbound object body."""
    if not isinstance(value, bytes) or not value:
        raise S3PublicationValidationError(f"{field} must contain non-empty bytes")
    return value


def _require_payloads(value: object) -> tuple[PublicationPayload, ...]:
    """Require one bounded tuple of publication payloads."""
    if not isinstance(value, tuple):
        raise S3PublicationValidationError("payloads must be a tuple")
    items = cast(tuple[object, ...], value)
    if not 1 <= len(items) <= MAX_PUBLICATION_OBJECTS:
        raise S3PublicationValidationError(
            f"payloads must contain between 1 and {MAX_PUBLICATION_OBJECTS} objects"
        )
    if any(not isinstance(item, PublicationPayload) for item in items):
        raise S3PublicationValidationError(
            "payloads must contain only PublicationPayload values"
        )
    return cast(tuple[PublicationPayload, ...], items)


def _require_remote_objects(value: object) -> tuple[RemoteObjectEvidence, ...]:
    """Require one bounded tuple of verified remote object evidence."""
    if not isinstance(value, tuple):
        raise S3PublicationValidationError("objects must be a tuple")
    items = cast(tuple[object, ...], value)
    if not 1 <= len(items) <= MAX_PUBLICATION_OBJECTS:
        raise S3PublicationValidationError(
            f"objects must contain between 1 and {MAX_PUBLICATION_OBJECTS} entries"
        )
    if any(not isinstance(item, RemoteObjectEvidence) for item in items):
        raise S3PublicationValidationError(
            "objects must contain only RemoteObjectEvidence values"
        )
    return cast(tuple[RemoteObjectEvidence, ...], items)


@dataclass(frozen=True, slots=True)
class PublicationPayload:
    """One exact object body authorized for remote publication."""

    key: str
    body: bytes
    content_type: str
    checksum_sha256: str

    def __post_init__(self) -> None:
        """Validate exact key/body/checksum semantics before the object-store port."""
        key = _require_nonblank(self.key, field="key")
        body = _require_bytes(self.body, field="body")
        content_type = _require_nonblank(self.content_type, field="content_type")
        checksum_sha256 = _require_sha256(
            self.checksum_sha256,
            field="checksum_sha256",
        )
        from hashlib import sha256

        if sha256(body).hexdigest() != checksum_sha256:
            raise S3PublicationValidationError(
                "checksum_sha256 must match the exact publication body"
            )
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "body", body)
        object.__setattr__(self, "content_type", content_type)
        object.__setattr__(self, "checksum_sha256", checksum_sha256)


@dataclass(frozen=True, slots=True)
class RemoteObjectEvidence:
    """Provider-neutral verification evidence for one published object."""

    key: str
    byte_count: int
    checksum_sha256: str
    content_type: str

    def __post_init__(self) -> None:
        """Validate one object-state observation returned by the storage adapter."""
        object.__setattr__(self, "key", _require_nonblank(self.key, field="key"))
        object.__setattr__(
            self,
            "byte_count",
            _require_positive_int(self.byte_count, field="byte_count"),
        )
        object.__setattr__(
            self,
            "checksum_sha256",
            _require_sha256(self.checksum_sha256, field="checksum_sha256"),
        )
        object.__setattr__(
            self,
            "content_type",
            _require_nonblank(self.content_type, field="content_type"),
        )


@dataclass(frozen=True, slots=True)
class S3PublicationEvidence:
    """Complete hash-only evidence that one publication prefix exactly matches the plan."""

    prefix: str
    source_manifest_sha256: str
    payload_count: int
    total_byte_count: int
    objects: tuple[RemoteObjectEvidence, ...]

    def __post_init__(self) -> None:
        """Reject incomplete, duplicate, or internally inconsistent publication evidence."""
        prefix = _require_nonblank(self.prefix, field="prefix")
        source_manifest_sha256 = _require_sha256(
            self.source_manifest_sha256,
            field="source_manifest_sha256",
        )
        payload_count = _require_positive_int(self.payload_count, field="payload_count")
        total_byte_count = _require_positive_int(
            self.total_byte_count,
            field="total_byte_count",
        )
        objects = _require_remote_objects(self.objects)
        if payload_count != len(objects):
            raise S3PublicationValidationError(
                "payload_count must equal the number of verified remote objects"
            )
        if total_byte_count != sum(item.byte_count for item in objects):
            raise S3PublicationValidationError(
                "total_byte_count must equal the sum of verified remote object bytes"
            )
        keys = [item.key for item in objects]
        if len(set(keys)) != len(keys):
            raise S3PublicationValidationError("verified remote object keys must be unique")

        object.__setattr__(self, "prefix", prefix)
        object.__setattr__(self, "source_manifest_sha256", source_manifest_sha256)
        object.__setattr__(self, "payload_count", payload_count)
        object.__setattr__(self, "total_byte_count", total_byte_count)
        object.__setattr__(self, "objects", objects)


class PublicationObjectStore(Protocol):
    """Minimal provider-neutral object-store authority for Gate 7.3 publication."""

    def put(self, payload: PublicationPayload) -> None:
        """Store one exact checksummed object body."""
        ...

    def list_keys(self, prefix: str) -> tuple[str, ...]:
        """Return every object key admitted under one bounded publication prefix."""
        ...

    def inspect(self, key: str) -> RemoteObjectEvidence:
        """Return checksum/size/type evidence for one exact object key."""
        ...


def build_publication_payloads(plan: BedrockPublicationPlan) -> tuple[PublicationPayload, ...]:
    """Expand one nine-chunk plan into alternating content and metadata S3 payloads."""
    payloads: list[PublicationPayload] = []
    for item in plan.objects:
        payloads.append(
            PublicationPayload(
                key=item.content_key,
                body=item.content_text.encode("utf-8"),
                content_type=CONTENT_TEXT_PLAIN,
                checksum_sha256=item.content_sha256,
            )
        )
        payloads.append(
            PublicationPayload(
                key=item.metadata_key,
                body=item.metadata_json.encode("utf-8"),
                content_type=CONTENT_APPLICATION_JSON,
                checksum_sha256=item.metadata_sha256,
            )
        )
    return _require_payloads(tuple(payloads))


def publish_bedrock_plan(
    plan: BedrockPublicationPlan,
    store: PublicationObjectStore,
) -> S3PublicationEvidence:
    """Publish serially, then require exact prefix membership and exact object evidence."""
    payloads = build_publication_payloads(plan)
    for payload in payloads:
        store.put(payload)

    expected_keys = tuple(payload.key for payload in payloads)
    actual_keys = store.list_keys(f"{plan.prefix}/")
    expected_set = set(expected_keys)
    actual_set = set(actual_keys)
    if len(actual_keys) != len(actual_set):
        raise S3PublicationValidationError("remote publication listing contains duplicate keys")
    if actual_set != expected_set:
        missing = sorted(expected_set - actual_set)
        unexpected = sorted(actual_set - expected_set)
        raise S3PublicationValidationError(
            "remote publication prefix must contain exactly the planned objects; "
            f"missing={missing}, unexpected={unexpected}"
        )

    payload_by_key = {payload.key: payload for payload in payloads}
    verified: list[RemoteObjectEvidence] = []
    for key in expected_keys:
        expected = payload_by_key[key]
        actual = store.inspect(key)
        if actual.key != expected.key:
            raise S3PublicationValidationError("remote object key does not match the request")
        if actual.byte_count != len(expected.body):
            raise S3PublicationValidationError(
                f"remote object {key!r} byte count does not match the publication plan"
            )
        if actual.checksum_sha256 != expected.checksum_sha256:
            raise S3PublicationValidationError(
                f"remote object {key!r} SHA-256 does not match the publication plan"
            )
        if actual.content_type != expected.content_type:
            raise S3PublicationValidationError(
                f"remote object {key!r} content type does not match the publication plan"
            )
        verified.append(actual)

    return S3PublicationEvidence(
        prefix=plan.prefix,
        source_manifest_sha256=plan.source_manifest_sha256,
        payload_count=len(payloads),
        total_byte_count=sum(len(payload.body) for payload in payloads),
        objects=tuple(verified),
    )
