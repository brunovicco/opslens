"""Deterministic canonical-corpus contracts for Phase 7 knowledge retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Self, cast

from opslens.knowledge_retrieval.domain.errors import KnowledgeRetrievalValidationError
from opslens.knowledge_retrieval.domain.models import KnowledgeDocument
from opslens.knowledge_retrieval.domain.source_registry import SOURCE_REGISTRY_ID

CORPUS_SPEC_ID = "knowledge-corpus-spec:v1"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)


def _require_nonblank(value: object, *, field: str) -> str:
    """Return one trimmed non-empty string from an untrusted value."""
    if not isinstance(value, str):
        raise KnowledgeRetrievalValidationError(f"{field} must be a string")
    normalized = value.strip()
    if not normalized:
        raise KnowledgeRetrievalValidationError(f"{field} must not be blank")
    return normalized


def _require_marker(value: object, *, field: str) -> str:
    """Preserve one exact LF-only marker while rejecting ambiguous outer whitespace."""
    if not isinstance(value, str):
        raise KnowledgeRetrievalValidationError(f"{field} must be a string")
    if not value or not value.strip():
        raise KnowledgeRetrievalValidationError(f"{field} must not be blank")
    if value != value.strip():
        raise KnowledgeRetrievalValidationError(
            f"{field} must not contain leading or trailing whitespace"
        )
    if "\r" in value or "\x00" in value:
        raise KnowledgeRetrievalValidationError(
            f"{field} must use LF-only text without NUL bytes"
        )
    return value


def _require_text_tuple(value: object, *, field: str) -> tuple[str, ...]:
    """Require one tuple of unique non-empty strings."""
    if not isinstance(value, tuple):
        raise KnowledgeRetrievalValidationError(f"{field} must be a tuple")
    items = cast(tuple[object, ...], value)
    normalized = tuple(_require_nonblank(item, field=field) for item in items)
    if len(set(normalized)) != len(normalized):
        raise KnowledgeRetrievalValidationError(f"{field} must not contain duplicates")
    return normalized


def _require_selection_specs(value: object) -> tuple[ChunkSelectionSpec, ...]:
    """Require a non-empty tuple of typed chunk selectors."""
    if not isinstance(value, tuple):
        raise KnowledgeRetrievalValidationError("selections must be a tuple")
    items = cast(tuple[object, ...], value)
    if not items:
        raise KnowledgeRetrievalValidationError("selections must not be empty")
    if any(not isinstance(item, ChunkSelectionSpec) for item in items):
        raise KnowledgeRetrievalValidationError(
            "selections must contain only ChunkSelectionSpec values"
        )
    return cast(tuple[ChunkSelectionSpec, ...], items)


def _require_document_specs(value: object) -> tuple[DocumentMaterializationSpec, ...]:
    """Require a non-empty tuple of typed document materialization specs."""
    if not isinstance(value, tuple):
        raise KnowledgeRetrievalValidationError("documents must be a tuple")
    items = cast(tuple[object, ...], value)
    if not items:
        raise KnowledgeRetrievalValidationError("documents must not be empty")
    if any(not isinstance(item, DocumentMaterializationSpec) for item in items):
        raise KnowledgeRetrievalValidationError(
            "documents must contain only DocumentMaterializationSpec values"
        )
    return cast(tuple[DocumentMaterializationSpec, ...], items)


def _require_sha256(value: object, *, field: str) -> str:
    """Require one lowercase SHA-256 digest."""
    normalized = _require_nonblank(value, field=field)
    if _SHA256_PATTERN.fullmatch(normalized) is None:
        raise KnowledgeRetrievalValidationError(
            f"{field} must be a 64-character lowercase hexadecimal SHA-256 digest"
        )
    return normalized


def _require_document(value: object) -> KnowledgeDocument:
    """Require one already validated canonical KnowledgeDocument."""
    if not isinstance(value, KnowledgeDocument):
        raise KnowledgeRetrievalValidationError("document must be a KnowledgeDocument")
    return value


def _require_chunks(value: object) -> tuple[CanonicalKnowledgeChunk, ...]:
    """Require one non-empty tuple of canonical chunks."""
    if not isinstance(value, tuple):
        raise KnowledgeRetrievalValidationError("chunks must be a tuple")
    items = cast(tuple[object, ...], value)
    if not items:
        raise KnowledgeRetrievalValidationError("chunks must not be empty")
    if any(not isinstance(item, CanonicalKnowledgeChunk) for item in items):
        raise KnowledgeRetrievalValidationError(
            "chunks must contain only CanonicalKnowledgeChunk values"
        )
    return cast(tuple[CanonicalKnowledgeChunk, ...], items)


@dataclass(frozen=True, slots=True)
class ChunkSelectionSpec:
    """Exact start-inclusive/end-exclusive source-text selector for one canonical chunk."""

    chunk_id: str
    section_path: tuple[str, ...]
    start_marker: str
    end_marker: str

    def __post_init__(self) -> None:
        """Validate one exact deterministic selector."""
        chunk_id = _require_nonblank(self.chunk_id, field="chunk_id")
        section_path = _require_text_tuple(self.section_path, field="section_path")
        if not section_path:
            raise KnowledgeRetrievalValidationError(
                "section_path must contain at least one section label"
            )
        start_marker = _require_marker(self.start_marker, field="start_marker")
        end_marker = _require_marker(self.end_marker, field="end_marker")
        if start_marker == end_marker:
            raise KnowledgeRetrievalValidationError(
                "start_marker and end_marker must be different"
            )

        object.__setattr__(self, "chunk_id", chunk_id)
        object.__setattr__(self, "section_path", section_path)
        object.__setattr__(self, "start_marker", start_marker)
        object.__setattr__(self, "end_marker", end_marker)


@dataclass(frozen=True, slots=True)
class DocumentMaterializationSpec:
    """Curated transformation contract for one source-registry document."""

    document_id: str
    title: str
    selections: tuple[ChunkSelectionSpec, ...]

    def __post_init__(self) -> None:
        """Validate document identity and deterministic chunk authority."""
        document_id = _require_nonblank(self.document_id, field="document_id")
        title = _require_nonblank(self.title, field="title")
        selections = _require_selection_specs(self.selections)
        chunk_ids = [selection.chunk_id for selection in selections]
        if len(set(chunk_ids)) != len(chunk_ids):
            raise KnowledgeRetrievalValidationError(
                "document chunk_id values must be unique"
            )

        object.__setattr__(self, "document_id", document_id)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "selections", selections)


@dataclass(frozen=True, slots=True)
class KnowledgeCorpusSpec:
    """Frozen v1 mapping from pinned source documents to curated canonical chunks."""

    spec_id: str
    source_registry_id: str
    documents: tuple[DocumentMaterializationSpec, ...]

    def __post_init__(self) -> None:
        """Reject competing document/chunk authority or incompatible registry identity."""
        spec_id = _require_nonblank(self.spec_id, field="spec_id")
        if spec_id != CORPUS_SPEC_ID:
            raise KnowledgeRetrievalValidationError(
                f"spec_id must equal {CORPUS_SPEC_ID!r}"
            )
        source_registry_id = _require_nonblank(
            self.source_registry_id,
            field="source_registry_id",
        )
        if source_registry_id != SOURCE_REGISTRY_ID:
            raise KnowledgeRetrievalValidationError(
                f"source_registry_id must equal {SOURCE_REGISTRY_ID!r}"
            )
        documents = _require_document_specs(self.documents)
        document_ids = [document.document_id for document in documents]
        chunk_ids = [
            selection.chunk_id
            for document in documents
            for selection in document.selections
        ]
        if len(set(document_ids)) != len(document_ids):
            raise KnowledgeRetrievalValidationError(
                "corpus document_id values must be unique"
            )
        if len(set(chunk_ids)) != len(chunk_ids):
            raise KnowledgeRetrievalValidationError(
                "corpus chunk_id values must be unique"
            )

        object.__setattr__(self, "spec_id", spec_id)
        object.__setattr__(self, "source_registry_id", source_registry_id)
        object.__setattr__(self, "documents", documents)


@dataclass(frozen=True, slots=True)
class CanonicalKnowledgeChunk:
    """One deterministic corpus chunk before retrieval-time ranking exists."""

    chunk_id: str
    document_id: str
    document_content_sha256: str
    chunk_content_sha256: str
    text: str
    section_path: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate canonical parent/content identity and section provenance."""
        chunk_id = _require_nonblank(self.chunk_id, field="chunk_id")
        document_id = _require_nonblank(self.document_id, field="document_id")
        document_content_sha256 = _require_sha256(
            self.document_content_sha256,
            field="document_content_sha256",
        )
        text = _require_nonblank(self.text, field="text")
        chunk_content_sha256 = _require_sha256(
            self.chunk_content_sha256,
            field="chunk_content_sha256",
        )
        expected_digest = sha256(text.encode("utf-8")).hexdigest()
        if chunk_content_sha256 != expected_digest:
            raise KnowledgeRetrievalValidationError(
                "chunk_content_sha256 must match canonical UTF-8 chunk text"
            )
        section_path = _require_text_tuple(self.section_path, field="section_path")
        if not section_path:
            raise KnowledgeRetrievalValidationError(
                "section_path must contain at least one section label"
            )

        object.__setattr__(self, "chunk_id", chunk_id)
        object.__setattr__(self, "document_id", document_id)
        object.__setattr__(
            self,
            "document_content_sha256",
            document_content_sha256,
        )
        object.__setattr__(self, "chunk_content_sha256", chunk_content_sha256)
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "section_path", section_path)

    @classmethod
    def from_text(
        cls,
        *,
        chunk_id: str,
        document_id: str,
        document_content_sha256: str,
        text: str,
        section_path: tuple[str, ...],
    ) -> Self:
        """Derive exact chunk identity from canonical UTF-8 text."""
        normalized_text = _require_nonblank(text, field="text")
        return cls(
            chunk_id=chunk_id,
            document_id=document_id,
            document_content_sha256=document_content_sha256,
            chunk_content_sha256=sha256(normalized_text.encode("utf-8")).hexdigest(),
            text=normalized_text,
            section_path=section_path,
        )


@dataclass(frozen=True, slots=True)
class MaterializedKnowledgeDocument:
    """One content-addressed canonical document with its exact source-byte evidence."""

    source_byte_count: int
    source_bytes_sha256: str
    document: KnowledgeDocument
    chunks: tuple[CanonicalKnowledgeChunk, ...]

    def __post_init__(self) -> None:
        """Require consistent source, document, and chunk identities."""
        if type(self.source_byte_count) is not int or self.source_byte_count <= 0:
            raise KnowledgeRetrievalValidationError(
                "source_byte_count must be a positive integer"
            )
        source_bytes_sha256 = _require_sha256(
            self.source_bytes_sha256,
            field="source_bytes_sha256",
        )
        document = _require_document(self.document)
        chunks = _require_chunks(self.chunks)
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        if len(set(chunk_ids)) != len(chunk_ids):
            raise KnowledgeRetrievalValidationError(
                "materialized chunk_id values must be unique"
            )
        for chunk in chunks:
            if chunk.document_id != document.document_id:
                raise KnowledgeRetrievalValidationError(
                    "canonical chunk document_id must match its parent document"
                )
            if chunk.document_content_sha256 != document.content_sha256:
                raise KnowledgeRetrievalValidationError(
                    "canonical chunk document digest must match its parent document"
                )
            if chunk.text not in document.text:
                raise KnowledgeRetrievalValidationError(
                    "canonical chunk text must be contained in its parent document"
                )

        object.__setattr__(self, "source_bytes_sha256", source_bytes_sha256)
        object.__setattr__(self, "document", document)
        object.__setattr__(self, "chunks", chunks)
