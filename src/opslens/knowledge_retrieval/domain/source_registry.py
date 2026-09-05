"""Trusted source-registry contracts for the Phase 7 canonical corpus."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from opslens.knowledge_retrieval.domain.errors import KnowledgeRetrievalValidationError
from opslens.knowledge_retrieval.domain.models import KnowledgeSourceType

SOURCE_REGISTRY_ID = "knowledge-source-registry:v1"


def _require_nonblank(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise KnowledgeRetrievalValidationError(f"{field} must be a string")
    normalized = value.strip()
    if not normalized:
        raise KnowledgeRetrievalValidationError(f"{field} must not be blank")
    return normalized


def _require_https_uri(value: object, *, field: str) -> str:
    normalized = _require_nonblank(value, field=field)
    parsed = urlparse(normalized)
    if parsed.scheme != "https" or not parsed.hostname:
        raise KnowledgeRetrievalValidationError(f"{field} must be an absolute HTTPS URI")
    if parsed.username is not None or parsed.password is not None:
        raise KnowledgeRetrievalValidationError(f"{field} must not contain user info")
    return normalized


def _require_host(value: object, *, field: str) -> str:
    normalized = _require_nonblank(value, field=field).lower()
    if ":" in normalized or "/" in normalized or "@" in normalized:
        raise KnowledgeRetrievalValidationError(f"{field} must be a hostname only")
    return normalized


def _require_unique_strings(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise KnowledgeRetrievalValidationError(f"{field} must be a tuple")
    normalized = tuple(_require_nonblank(item, field=field) for item in value)
    if len(set(normalized)) != len(normalized):
        raise KnowledgeRetrievalValidationError(f"{field} must not contain duplicates")
    return normalized


@dataclass(frozen=True, slots=True)
class KnowledgeSourceDescriptor:
    """Pre-acquisition authorization for one canonical knowledge document."""

    document_id: str
    source_id: str
    source_type: KnowledgeSourceType
    canonical_uri: str
    allowed_host: str
    expected_chunk_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        document_id = _require_nonblank(self.document_id, field="document_id")
        source_id = _require_nonblank(self.source_id, field="source_id")
        canonical_uri = _require_https_uri(self.canonical_uri, field="canonical_uri")
        allowed_host = _require_host(self.allowed_host, field="allowed_host")
        expected_chunk_ids = _require_unique_strings(
            self.expected_chunk_ids,
            field="expected_chunk_ids",
        )

        if not isinstance(self.source_type, KnowledgeSourceType):
            raise KnowledgeRetrievalValidationError(
                "source_type must be a supported KnowledgeSourceType"
            )

        canonical_host = urlparse(canonical_uri).hostname
        if canonical_host is None or canonical_host.lower() != allowed_host:
            raise KnowledgeRetrievalValidationError(
                "canonical_uri hostname must exactly match allowed_host"
            )

        if not expected_chunk_ids:
            raise KnowledgeRetrievalValidationError(
                "expected_chunk_ids must contain at least one chunk"
            )

        object.__setattr__(self, "document_id", document_id)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "canonical_uri", canonical_uri)
        object.__setattr__(self, "allowed_host", allowed_host)
        object.__setattr__(self, "expected_chunk_ids", expected_chunk_ids)


@dataclass(frozen=True, slots=True)
class KnowledgeSourceRegistry:
    """Frozen v1 allowlist of trusted inputs for later corpus acquisition."""

    registry_id: str
    entries: tuple[KnowledgeSourceDescriptor, ...]

    def __post_init__(self) -> None:
        registry_id = _require_nonblank(self.registry_id, field="registry_id")
        if registry_id != SOURCE_REGISTRY_ID:
            raise KnowledgeRetrievalValidationError(
                f"registry_id must equal {SOURCE_REGISTRY_ID!r}"
            )
        if not isinstance(self.entries, tuple):
            raise KnowledgeRetrievalValidationError("entries must be a tuple")
        if not self.entries:
            raise KnowledgeRetrievalValidationError("entries must not be empty")
        if any(not isinstance(entry, KnowledgeSourceDescriptor) for entry in self.entries):
            raise KnowledgeRetrievalValidationError(
                "entries must contain only KnowledgeSourceDescriptor values"
            )

        document_ids = [entry.document_id for entry in self.entries]
        source_ids = [entry.source_id for entry in self.entries]
        canonical_uris = [entry.canonical_uri for entry in self.entries]
        chunk_ids = [
            chunk_id
            for entry in self.entries
            for chunk_id in entry.expected_chunk_ids
        ]

        for field, values in (
            ("document_id", document_ids),
            ("source_id", source_ids),
            ("canonical_uri", canonical_uris),
            ("expected_chunk_ids", chunk_ids),
        ):
            if len(set(values)) != len(values):
                raise KnowledgeRetrievalValidationError(
                    f"registry {field} values must be unique"
                )

        object.__setattr__(self, "registry_id", registry_id)
