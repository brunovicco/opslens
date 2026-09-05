"""Content-addressed manifest contracts for the reproducible Phase 7 corpus."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import cast
from urllib.parse import urlparse

from opslens.knowledge_retrieval.domain.corpus import CORPUS_SPEC_ID
from opslens.knowledge_retrieval.domain.errors import KnowledgeRetrievalValidationError
from opslens.knowledge_retrieval.domain.models import KnowledgeSourceType
from opslens.knowledge_retrieval.domain.source_registry import SOURCE_REGISTRY_ID

CORPUS_MANIFEST_ID = "knowledge-corpus-manifest:v1"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$", re.ASCII)


def _require_nonblank(value: object, *, field: str) -> str:
    """Require one trimmed non-empty string."""
    if not isinstance(value, str):
        raise KnowledgeRetrievalValidationError(f"{field} must be a string")
    if not value or value != value.strip():
        raise KnowledgeRetrievalValidationError(
            f"{field} must be one trimmed non-empty string"
        )
    return value


def _require_sha256(value: object, *, field: str) -> str:
    """Require one lowercase SHA-256 digest."""
    normalized = _require_nonblank(value, field=field)
    if _SHA256_PATTERN.fullmatch(normalized) is None:
        raise KnowledgeRetrievalValidationError(
            f"{field} must be a lowercase 64-hex SHA-256 digest"
        )
    return normalized


def _require_git_sha(value: object) -> str:
    """Require one immutable full lowercase Git commit SHA."""
    normalized = _require_nonblank(value, field="upstream_commit_sha")
    if _GIT_SHA_PATTERN.fullmatch(normalized) is None:
        raise KnowledgeRetrievalValidationError(
            "upstream_commit_sha must be a full lowercase 40-hex Git SHA"
        )
    return normalized


def _require_positive_int(value: object, *, field: str) -> int:
    """Require a positive non-boolean integer."""
    if type(value) is not int or value <= 0:
        raise KnowledgeRetrievalValidationError(f"{field} must be a positive integer")
    return value


def _require_https_uri(value: object, *, field: str) -> str:
    """Require one absolute HTTPS URI without userinfo."""
    normalized = _require_nonblank(value, field=field)
    parsed = urlparse(normalized)
    if parsed.scheme != "https" or not parsed.hostname:
        raise KnowledgeRetrievalValidationError(f"{field} must be an absolute HTTPS URI")
    if parsed.username is not None or parsed.password is not None:
        raise KnowledgeRetrievalValidationError(f"{field} must not contain user info")
    return normalized


def _require_source_type(value: object) -> KnowledgeSourceType:
    """Require one admitted knowledge source type."""
    if not isinstance(value, KnowledgeSourceType):
        raise KnowledgeRetrievalValidationError(
            "source_type must be a supported KnowledgeSourceType"
        )
    return value


def _require_string_tuple(value: object, *, field: str) -> tuple[str, ...]:
    """Require a non-empty tuple of unique trimmed strings."""
    if not isinstance(value, tuple):
        raise KnowledgeRetrievalValidationError(f"{field} must be a tuple")
    items = cast(tuple[object, ...], value)
    normalized = tuple(_require_nonblank(item, field=field) for item in items)
    if not normalized:
        raise KnowledgeRetrievalValidationError(f"{field} must not be empty")
    if len(set(normalized)) != len(normalized):
        raise KnowledgeRetrievalValidationError(f"{field} must not contain duplicates")
    return normalized


def _require_chunk_entries(value: object) -> tuple[CorpusChunkManifestEntry, ...]:
    """Require a non-empty tuple of manifest chunk entries."""
    if not isinstance(value, tuple):
        raise KnowledgeRetrievalValidationError("chunks must be a tuple")
    items = cast(tuple[object, ...], value)
    if not items:
        raise KnowledgeRetrievalValidationError("chunks must not be empty")
    if any(not isinstance(item, CorpusChunkManifestEntry) for item in items):
        raise KnowledgeRetrievalValidationError(
            "chunks must contain only CorpusChunkManifestEntry values"
        )
    return cast(tuple[CorpusChunkManifestEntry, ...], items)


def _require_document_entries(value: object) -> tuple[CorpusDocumentManifestEntry, ...]:
    """Require a non-empty tuple of manifest document entries."""
    if not isinstance(value, tuple):
        raise KnowledgeRetrievalValidationError("documents must be a tuple")
    items = cast(tuple[object, ...], value)
    if not items:
        raise KnowledgeRetrievalValidationError("documents must not be empty")
    if any(not isinstance(item, CorpusDocumentManifestEntry) for item in items):
        raise KnowledgeRetrievalValidationError(
            "documents must contain only CorpusDocumentManifestEntry values"
        )
    return cast(tuple[CorpusDocumentManifestEntry, ...], items)


@dataclass(frozen=True, slots=True)
class CorpusChunkManifestEntry:
    """Hash-only canonical chunk evidence without third-party text content."""

    chunk_id: str
    section_path: tuple[str, ...]
    content_utf8_byte_count: int
    chunk_content_sha256: str

    def __post_init__(self) -> None:
        """Validate one canonical chunk evidence record."""
        object.__setattr__(
            self,
            "chunk_id",
            _require_nonblank(self.chunk_id, field="chunk_id"),
        )
        object.__setattr__(
            self,
            "section_path",
            _require_string_tuple(self.section_path, field="section_path"),
        )
        object.__setattr__(
            self,
            "content_utf8_byte_count",
            _require_positive_int(
                self.content_utf8_byte_count,
                field="content_utf8_byte_count",
            ),
        )
        object.__setattr__(
            self,
            "chunk_content_sha256",
            _require_sha256(
                self.chunk_content_sha256,
                field="chunk_content_sha256",
            ),
        )


@dataclass(frozen=True, slots=True)
class CorpusDocumentManifestEntry:
    """Reproducible source/document identity without vendoring source text."""

    document_id: str
    source_id: str
    source_type: KnowledgeSourceType
    canonical_uri: str
    acquisition_uri: str
    upstream_repository: str
    upstream_commit_sha: str
    upstream_path: str
    source_byte_count: int
    source_bytes_sha256: str
    title: str
    content_utf8_byte_count: int
    content_sha256: str
    chunks: tuple[CorpusChunkManifestEntry, ...]

    def __post_init__(self) -> None:
        """Validate source pin, content identity, and unique chunk evidence."""
        document_id = _require_nonblank(self.document_id, field="document_id")
        source_id = _require_nonblank(self.source_id, field="source_id")
        source_type = _require_source_type(self.source_type)
        canonical_uri = _require_https_uri(self.canonical_uri, field="canonical_uri")
        acquisition_uri = _require_https_uri(self.acquisition_uri, field="acquisition_uri")
        upstream_repository = _require_nonblank(
            self.upstream_repository,
            field="upstream_repository",
        )
        upstream_commit_sha = _require_git_sha(self.upstream_commit_sha)
        upstream_path = _require_nonblank(self.upstream_path, field="upstream_path")
        source_byte_count = _require_positive_int(
            self.source_byte_count,
            field="source_byte_count",
        )
        source_bytes_sha256 = _require_sha256(
            self.source_bytes_sha256,
            field="source_bytes_sha256",
        )
        title = _require_nonblank(self.title, field="title")
        content_utf8_byte_count = _require_positive_int(
            self.content_utf8_byte_count,
            field="content_utf8_byte_count",
        )
        content_sha256 = _require_sha256(self.content_sha256, field="content_sha256")
        chunks = _require_chunk_entries(self.chunks)
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        if len(set(chunk_ids)) != len(chunk_ids):
            raise KnowledgeRetrievalValidationError(
                "manifest chunk_id values must be unique within a document"
            )

        object.__setattr__(self, "document_id", document_id)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "source_type", source_type)
        object.__setattr__(self, "canonical_uri", canonical_uri)
        object.__setattr__(self, "acquisition_uri", acquisition_uri)
        object.__setattr__(self, "upstream_repository", upstream_repository)
        object.__setattr__(self, "upstream_commit_sha", upstream_commit_sha)
        object.__setattr__(self, "upstream_path", upstream_path)
        object.__setattr__(self, "source_byte_count", source_byte_count)
        object.__setattr__(self, "source_bytes_sha256", source_bytes_sha256)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "content_utf8_byte_count", content_utf8_byte_count)
        object.__setattr__(self, "content_sha256", content_sha256)
        object.__setattr__(self, "chunks", chunks)


@dataclass(frozen=True, slots=True)
class KnowledgeCorpusManifest:
    """Deterministic content-addressed evidence for one complete corpus replay."""

    manifest_id: str
    source_registry_id: str
    corpus_spec_id: str
    documents: tuple[CorpusDocumentManifestEntry, ...]

    def __post_init__(self) -> None:
        """Validate manifest version and reject competing document/chunk identities."""
        manifest_id = _require_nonblank(self.manifest_id, field="manifest_id")
        if manifest_id != CORPUS_MANIFEST_ID:
            raise KnowledgeRetrievalValidationError(
                f"manifest_id must equal {CORPUS_MANIFEST_ID!r}"
            )
        source_registry_id = _require_nonblank(
            self.source_registry_id,
            field="source_registry_id",
        )
        if source_registry_id != SOURCE_REGISTRY_ID:
            raise KnowledgeRetrievalValidationError(
                f"source_registry_id must equal {SOURCE_REGISTRY_ID!r}"
            )
        corpus_spec_id = _require_nonblank(self.corpus_spec_id, field="corpus_spec_id")
        if corpus_spec_id != CORPUS_SPEC_ID:
            raise KnowledgeRetrievalValidationError(
                f"corpus_spec_id must equal {CORPUS_SPEC_ID!r}"
            )
        documents = _require_document_entries(self.documents)
        document_ids = [document.document_id for document in documents]
        source_ids = [document.source_id for document in documents]
        chunk_ids = [
            chunk.chunk_id
            for document in documents
            for chunk in document.chunks
        ]
        for field, values in (
            ("document_id", document_ids),
            ("source_id", source_ids),
            ("chunk_id", chunk_ids),
        ):
            if len(set(values)) != len(values):
                raise KnowledgeRetrievalValidationError(
                    f"manifest {field} values must be globally unique"
                )

        object.__setattr__(self, "manifest_id", manifest_id)
        object.__setattr__(self, "source_registry_id", source_registry_id)
        object.__setattr__(self, "corpus_spec_id", corpus_spec_id)
        object.__setattr__(self, "documents", documents)
