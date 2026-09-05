"""Trusted source-registry contracts for the Phase 7 canonical corpus."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import cast
from urllib.parse import quote, urlparse

from opslens.knowledge_retrieval.domain.errors import KnowledgeRetrievalValidationError
from opslens.knowledge_retrieval.domain.models import KnowledgeSourceType

SOURCE_REGISTRY_ID = "knowledge-source-registry:v1"
RAW_GITHUB_HOST = "raw.githubusercontent.com"
_GITHUB_REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", re.ASCII)
_FULL_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$", re.ASCII)
_CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x1f\x7f]", re.ASCII)


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


def _require_repository(value: object) -> str:
    normalized = _require_nonblank(value, field="upstream_repository")
    if _GITHUB_REPOSITORY_PATTERN.fullmatch(normalized) is None:
        raise KnowledgeRetrievalValidationError(
            "upstream_repository must use the exact owner/repository form"
        )
    return normalized


def _require_commit_sha(value: object) -> str:
    normalized = _require_nonblank(value, field="upstream_commit_sha")
    if _FULL_GIT_SHA_PATTERN.fullmatch(normalized) is None:
        raise KnowledgeRetrievalValidationError(
            "upstream_commit_sha must be one full lowercase 40-hex Git SHA"
        )
    return normalized


def _require_upstream_path(value: object) -> str:
    normalized = _require_nonblank(value, field="upstream_path")
    if (
        normalized.startswith("/")
        or _CONTROL_CHARACTER_PATTERN.search(normalized) is not None
    ):
        raise KnowledgeRetrievalValidationError(
            "upstream_path must be one clean repository-relative path"
        )
    segments = normalized.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise KnowledgeRetrievalValidationError(
            "upstream_path must not contain empty or traversal segments"
        )
    return normalized


def _require_unique_strings(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise KnowledgeRetrievalValidationError(f"{field} must be a tuple")
    items = cast(tuple[object, ...], value)
    normalized = tuple(_require_nonblank(item, field=field) for item in items)
    if len(set(normalized)) != len(normalized):
        raise KnowledgeRetrievalValidationError(f"{field} must not contain duplicates")
    return normalized


def _require_source_type(value: object) -> KnowledgeSourceType:
    if not isinstance(value, KnowledgeSourceType):
        raise KnowledgeRetrievalValidationError(
            "source_type must be a supported KnowledgeSourceType"
        )
    return value


def _require_entries(value: object) -> tuple[KnowledgeSourceDescriptor, ...]:
    if not isinstance(value, tuple):
        raise KnowledgeRetrievalValidationError("entries must be a tuple")
    items = cast(tuple[object, ...], value)
    if not items:
        raise KnowledgeRetrievalValidationError("entries must not be empty")
    if any(not isinstance(item, KnowledgeSourceDescriptor) for item in items):
        raise KnowledgeRetrievalValidationError(
            "entries must contain only KnowledgeSourceDescriptor values"
        )
    return cast(tuple[KnowledgeSourceDescriptor, ...], items)


@dataclass(frozen=True, slots=True)
class KnowledgeSourceDescriptor:
    """Pre-acquisition authorization for one pinned canonical knowledge source."""

    document_id: str
    source_id: str
    source_type: KnowledgeSourceType
    canonical_uri: str
    upstream_repository: str
    upstream_commit_sha: str
    upstream_path: str
    expected_chunk_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """Normalize and fail closed on malformed pinned source authorization."""
        document_id = _require_nonblank(self.document_id, field="document_id")
        source_id = _require_nonblank(self.source_id, field="source_id")
        source_type = _require_source_type(self.source_type)
        canonical_uri = _require_https_uri(self.canonical_uri, field="canonical_uri")
        upstream_repository = _require_repository(self.upstream_repository)
        upstream_commit_sha = _require_commit_sha(self.upstream_commit_sha)
        upstream_path = _require_upstream_path(self.upstream_path)
        expected_chunk_ids = _require_unique_strings(
            self.expected_chunk_ids,
            field="expected_chunk_ids",
        )
        if not expected_chunk_ids:
            raise KnowledgeRetrievalValidationError(
                "expected_chunk_ids must contain at least one chunk"
            )

        object.__setattr__(self, "document_id", document_id)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "source_type", source_type)
        object.__setattr__(self, "canonical_uri", canonical_uri)
        object.__setattr__(self, "upstream_repository", upstream_repository)
        object.__setattr__(self, "upstream_commit_sha", upstream_commit_sha)
        object.__setattr__(self, "upstream_path", upstream_path)
        object.__setattr__(self, "expected_chunk_ids", expected_chunk_ids)

    @property
    def acquisition_host(self) -> str:
        """Return the only v1 host authorized for pinned source bytes."""
        return RAW_GITHUB_HOST

    @property
    def acquisition_path(self) -> str:
        """Derive the exact raw GitHub request target from pinned source coordinates."""
        owner, repository = self.upstream_repository.split("/", maxsplit=1)
        encoded_path = "/".join(
            quote(segment, safe="-._~") for segment in self.upstream_path.split("/")
        )
        return (
            f"/{quote(owner, safe='-._~')}/{quote(repository, safe='-._~')}"
            f"/{self.upstream_commit_sha}/{encoded_path}"
        )

    @property
    def acquisition_uri(self) -> str:
        """Return the immutable raw-source URI used by the corpus acquisition adapter."""
        return f"https://{self.acquisition_host}{self.acquisition_path}"


@dataclass(frozen=True, slots=True)
class KnowledgeSourceRegistry:
    """Frozen v1 allowlist of trusted pinned inputs for corpus acquisition."""

    registry_id: str
    entries: tuple[KnowledgeSourceDescriptor, ...]

    def __post_init__(self) -> None:
        """Validate registry identity and reject competing source authority."""
        registry_id = _require_nonblank(self.registry_id, field="registry_id")
        if registry_id != SOURCE_REGISTRY_ID:
            raise KnowledgeRetrievalValidationError(
                f"registry_id must equal {SOURCE_REGISTRY_ID!r}"
            )
        entries = _require_entries(self.entries)

        document_ids = [entry.document_id for entry in entries]
        source_ids = [entry.source_id for entry in entries]
        canonical_uris = [entry.canonical_uri for entry in entries]
        acquisition_uris = [entry.acquisition_uri for entry in entries]
        chunk_ids = [
            chunk_id
            for entry in entries
            for chunk_id in entry.expected_chunk_ids
        ]

        for field, values in (
            ("document_id", document_ids),
            ("source_id", source_ids),
            ("canonical_uri", canonical_uris),
            ("acquisition_uri", acquisition_uris),
            ("expected_chunk_ids", chunk_ids),
        ):
            if len(set(values)) != len(values):
                raise KnowledgeRetrievalValidationError(
                    f"registry {field} values must be unique"
                )

        object.__setattr__(self, "registry_id", registry_id)
        object.__setattr__(self, "entries", entries)
