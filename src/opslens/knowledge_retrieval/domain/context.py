"""Provider-independent contracts for deterministic retrieval-context assembly."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import Self, cast
from urllib.parse import urlparse

from opslens.knowledge_retrieval.domain.errors import KnowledgeRetrievalValidationError
from opslens.knowledge_retrieval.domain.models import (
    DEFAULT_RETRIEVAL_TOP_K,
    MAX_RETRIEVAL_TOP_K,
    KnowledgeSourceType,
    RetrievedChunk,
)

DEFAULT_CONTEXT_MAX_CHUNKS = DEFAULT_RETRIEVAL_TOP_K
MAX_CONTEXT_CHUNKS = MAX_RETRIEVAL_TOP_K
MAX_CONTEXT_UTF8_BYTES = 16_384
DEFAULT_CONTEXT_MAX_UTF8_BYTES = MAX_CONTEXT_UTF8_BYTES

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _normalize_required_text(value: object, label: str) -> str:
    """Return one trimmed non-empty string or fail closed."""
    if not isinstance(value, str):
        raise KnowledgeRetrievalValidationError(f"{label} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise KnowledgeRetrievalValidationError(f"{label} cannot be blank.")
    return normalized


def _normalize_optional_text(value: object, label: str) -> str | None:
    """Normalize an optional string while rejecting explicit blank values."""
    if value is None:
        return None
    return _normalize_required_text(value, label)


def _validate_sha256(value: object, label: str) -> str:
    """Require one lowercase hexadecimal SHA-256 digest."""
    normalized = _normalize_required_text(value, label)
    if _SHA256_PATTERN.fullmatch(normalized) is None:
        raise KnowledgeRetrievalValidationError(
            f"{label} must be a 64-character lowercase hexadecimal SHA-256 digest."
        )
    return normalized


def _validate_https_uri(value: object, label: str) -> str:
    """Require an absolute HTTPS provenance URI."""
    normalized = _normalize_required_text(value, label)
    parsed = urlparse(normalized)
    if parsed.scheme != "https" or not parsed.netloc:
        raise KnowledgeRetrievalValidationError(f"{label} must be an absolute HTTPS URI.")
    return normalized


def _normalize_text_tuple(value: object, label: str) -> tuple[str, ...]:
    """Normalize one tuple of unique non-empty strings."""
    if not isinstance(value, tuple):
        raise KnowledgeRetrievalValidationError(f"{label} must be a tuple.")
    values = cast(tuple[object, ...], value)
    normalized = tuple(_normalize_required_text(item, label) for item in values)
    if len(set(normalized)) != len(normalized):
        raise KnowledgeRetrievalValidationError(f"{label} cannot contain duplicates.")
    return normalized


def _sha256_text(text: str) -> str:
    """Return the exact UTF-8 SHA-256 digest for one text payload."""
    return sha256(text.encode("utf-8")).hexdigest()


class ContextAssemblyStopReason(StrEnum):
    """Deterministic reasons why context assembly stopped selecting a rank prefix."""

    EXHAUSTED_RETRIEVAL = "exhausted_retrieval"
    MAX_CHUNKS = "max_chunks"
    MAX_UTF8_BYTES = "max_utf8_bytes"


@dataclass(frozen=True, slots=True)
class ContextAssemblyLimits:
    """Model-independent denial-of-wallet limits applied before synthesis."""

    max_chunks: int = DEFAULT_CONTEXT_MAX_CHUNKS
    max_utf8_bytes: int = DEFAULT_CONTEXT_MAX_UTF8_BYTES

    def __post_init__(self) -> None:
        """Reject unbounded context breadth or byte budgets."""
        if type(self.max_chunks) is not int or not 1 <= self.max_chunks <= MAX_CONTEXT_CHUNKS:
            raise KnowledgeRetrievalValidationError(
                f"max_chunks must be an integer from 1 to {MAX_CONTEXT_CHUNKS}."
            )
        if (
            type(self.max_utf8_bytes) is not int
            or not 1 <= self.max_utf8_bytes <= MAX_CONTEXT_UTF8_BYTES
        ):
            raise KnowledgeRetrievalValidationError(
                f"max_utf8_bytes must be an integer from 1 to {MAX_CONTEXT_UTF8_BYTES}."
            )


@dataclass(frozen=True, slots=True)
class ContextEvidenceBlock:
    """One whole admitted retrieval chunk projected for later synthesis context."""

    retrieval_rank: int
    chunk_id: str
    document_id: str
    source_id: str
    source_type: KnowledgeSourceType
    canonical_uri: str
    document_content_sha256: str
    chunk_content_sha256: str
    text: str
    utf8_byte_count: int
    title: str | None = None
    section_path: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate exact content identity and canonical provenance without provider scores."""
        if (
            type(self.retrieval_rank) is not int
            or not 1 <= self.retrieval_rank <= MAX_CONTEXT_CHUNKS
        ):
            raise KnowledgeRetrievalValidationError(
                f"retrieval_rank must be an integer from 1 to {MAX_CONTEXT_CHUNKS}."
            )
        object.__setattr__(self, "chunk_id", _normalize_required_text(self.chunk_id, "chunk_id"))
        object.__setattr__(
            self,
            "document_id",
            _normalize_required_text(self.document_id, "document_id"),
        )
        object.__setattr__(self, "source_id", _normalize_required_text(self.source_id, "source_id"))
        if not isinstance(self.source_type, KnowledgeSourceType):
            raise KnowledgeRetrievalValidationError("source_type has an unsupported value.")
        object.__setattr__(
            self,
            "canonical_uri",
            _validate_https_uri(self.canonical_uri, "canonical_uri"),
        )
        object.__setattr__(
            self,
            "document_content_sha256",
            _validate_sha256(self.document_content_sha256, "document_content_sha256"),
        )
        object.__setattr__(self, "text", _normalize_required_text(self.text, "text"))
        chunk_digest = _validate_sha256(self.chunk_content_sha256, "chunk_content_sha256")
        if chunk_digest != _sha256_text(self.text):
            raise KnowledgeRetrievalValidationError(
                "chunk_content_sha256 must match the exact UTF-8 context block text."
            )
        object.__setattr__(self, "chunk_content_sha256", chunk_digest)
        expected_bytes = len(self.text.encode("utf-8"))
        if type(self.utf8_byte_count) is not int or self.utf8_byte_count != expected_bytes:
            raise KnowledgeRetrievalValidationError(
                "utf8_byte_count must match the exact UTF-8 context block bytes."
            )
        object.__setattr__(self, "title", _normalize_optional_text(self.title, "title"))
        object.__setattr__(
            self,
            "section_path",
            _normalize_text_tuple(self.section_path, "section_path"),
        )

    @classmethod
    def from_chunk(cls, chunk: RetrievedChunk) -> Self:
        """Project one admitted chunk without provider score evidence."""
        if not isinstance(chunk, RetrievedChunk):
            raise KnowledgeRetrievalValidationError("chunk must be a RetrievedChunk value.")
        return cls(
            retrieval_rank=chunk.rank,
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            source_id=chunk.source_id,
            source_type=chunk.source_type,
            canonical_uri=chunk.canonical_uri,
            document_content_sha256=chunk.document_content_sha256,
            chunk_content_sha256=chunk.chunk_content_sha256,
            text=chunk.text,
            utf8_byte_count=len(chunk.text.encode("utf-8")),
            title=chunk.title,
            section_path=chunk.section_path,
        )


def _normalize_blocks(value: object) -> tuple[ContextEvidenceBlock, ...]:
    """Validate one tuple containing only context evidence blocks."""
    if not isinstance(value, tuple):
        raise KnowledgeRetrievalValidationError("blocks must be a tuple.")
    values = cast(tuple[object, ...], value)
    if any(not isinstance(block, ContextEvidenceBlock) for block in values):
        raise KnowledgeRetrievalValidationError(
            "blocks must contain only ContextEvidenceBlock values."
        )
    return cast(tuple[ContextEvidenceBlock, ...], values)


def _context_fingerprint_payload(
    *,
    retrieval_id: str,
    query_sha256: str,
    limits: ContextAssemblyLimits,
    blocks: tuple[ContextEvidenceBlock, ...],
    retrieved_chunk_count: int,
    stop_reason: ContextAssemblyStopReason,
) -> bytes:
    """Build the canonical content-free payload used to identify assembled context."""
    payload = {
        "blocks": [
            {
                "canonical_uri": block.canonical_uri,
                "chunk_content_sha256": block.chunk_content_sha256,
                "chunk_id": block.chunk_id,
                "document_content_sha256": block.document_content_sha256,
                "document_id": block.document_id,
                "retrieval_rank": block.retrieval_rank,
                "section_path": list(block.section_path),
                "source_id": block.source_id,
                "source_type": block.source_type.value,
                "title": block.title,
                "utf8_byte_count": block.utf8_byte_count,
            }
            for block in blocks
        ],
        "limits": {
            "max_chunks": limits.max_chunks,
            "max_utf8_bytes": limits.max_utf8_bytes,
        },
        "query_sha256": query_sha256,
        "retrieval_id": retrieval_id,
        "retrieved_chunk_count": retrieved_chunk_count,
        "stop_reason": stop_reason.value,
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class AssembledContext:
    """Deterministic rank-prefix context admitted for a later synthesis request."""

    retrieval_id: str
    query_sha256: str
    limits: ContextAssemblyLimits
    blocks: tuple[ContextEvidenceBlock, ...]
    retrieved_chunk_count: int
    total_utf8_bytes: int
    stop_reason: ContextAssemblyStopReason
    context_sha256: str

    def __post_init__(self) -> None:
        """Require internally consistent bounds, ranks, counts, and exact context identity."""
        retrieval_id = _normalize_required_text(self.retrieval_id, "retrieval_id")
        object.__setattr__(self, "retrieval_id", retrieval_id)
        query_sha256 = _validate_sha256(self.query_sha256, "query_sha256")
        object.__setattr__(self, "query_sha256", query_sha256)
        if not isinstance(self.limits, ContextAssemblyLimits):
            raise KnowledgeRetrievalValidationError("limits must be a ContextAssemblyLimits value.")
        blocks = _normalize_blocks(self.blocks)
        if not blocks:
            raise KnowledgeRetrievalValidationError(
                "assembled context must contain at least one block."
            )
        object.__setattr__(self, "blocks", blocks)
        if len(blocks) > self.limits.max_chunks:
            raise KnowledgeRetrievalValidationError(
                "assembled context cannot contain more blocks than limits.max_chunks."
            )
        expected_ranks = tuple(range(1, len(blocks) + 1))
        actual_ranks = tuple(block.retrieval_rank for block in blocks)
        if actual_ranks != expected_ranks:
            raise KnowledgeRetrievalValidationError(
                "context blocks must preserve one contiguous retrieval-rank prefix from 1."
            )
        if type(self.retrieved_chunk_count) is not int or not (
            len(blocks) <= self.retrieved_chunk_count <= MAX_CONTEXT_CHUNKS
        ):
            raise KnowledgeRetrievalValidationError(
                "retrieved_chunk_count must cover selected blocks within retrieval bounds."
            )
        expected_bytes = sum(block.utf8_byte_count for block in blocks)
        if type(self.total_utf8_bytes) is not int or self.total_utf8_bytes != expected_bytes:
            raise KnowledgeRetrievalValidationError(
                "total_utf8_bytes must equal the exact sum of selected block bytes."
            )
        if self.total_utf8_bytes > self.limits.max_utf8_bytes:
            raise KnowledgeRetrievalValidationError(
                "assembled context cannot exceed limits.max_utf8_bytes."
            )
        if not isinstance(self.stop_reason, ContextAssemblyStopReason):
            raise KnowledgeRetrievalValidationError(
                "stop_reason must be a ContextAssemblyStopReason value."
            )
        if self.stop_reason is ContextAssemblyStopReason.EXHAUSTED_RETRIEVAL:
            if len(blocks) != self.retrieved_chunk_count:
                raise KnowledgeRetrievalValidationError(
                    "exhausted_retrieval requires all retrieved chunks to be selected."
                )
        elif self.stop_reason is ContextAssemblyStopReason.MAX_CHUNKS:
            if not (
                len(blocks) == self.limits.max_chunks
                and len(blocks) < self.retrieved_chunk_count
            ):
                raise KnowledgeRetrievalValidationError(
                    "max_chunks requires the chunk limit to stop a non-empty remainder."
                )
        elif not (
            len(blocks) < self.limits.max_chunks
            and len(blocks) < self.retrieved_chunk_count
        ):
            raise KnowledgeRetrievalValidationError(
                "max_utf8_bytes requires a remaining retrieval suffix before max_chunks."
            )

        context_sha256 = _validate_sha256(self.context_sha256, "context_sha256")
        expected_context_sha256 = sha256(
            _context_fingerprint_payload(
                retrieval_id=retrieval_id,
                query_sha256=query_sha256,
                limits=self.limits,
                blocks=blocks,
                retrieved_chunk_count=self.retrieved_chunk_count,
                stop_reason=self.stop_reason,
            )
        ).hexdigest()
        if context_sha256 != expected_context_sha256:
            raise KnowledgeRetrievalValidationError(
                "context_sha256 must match deterministic assembled-context evidence."
            )
        object.__setattr__(self, "context_sha256", context_sha256)

    @classmethod
    def create(
        cls,
        *,
        retrieval_id: str,
        query: str,
        limits: ContextAssemblyLimits,
        blocks: tuple[ContextEvidenceBlock, ...],
        retrieved_chunk_count: int,
        stop_reason: ContextAssemblyStopReason,
    ) -> Self:
        """Create exact assembled-context identity without copying the raw query into evidence."""
        normalized_retrieval_id = _normalize_required_text(retrieval_id, "retrieval_id")
        normalized_query = _normalize_required_text(query, "query")
        query_sha256 = _sha256_text(normalized_query)
        typed_blocks = _normalize_blocks(blocks)
        fingerprint = sha256(
            _context_fingerprint_payload(
                retrieval_id=normalized_retrieval_id,
                query_sha256=query_sha256,
                limits=limits,
                blocks=typed_blocks,
                retrieved_chunk_count=retrieved_chunk_count,
                stop_reason=stop_reason,
            )
        ).hexdigest()
        return cls(
            retrieval_id=normalized_retrieval_id,
            query_sha256=query_sha256,
            limits=limits,
            blocks=typed_blocks,
            retrieved_chunk_count=retrieved_chunk_count,
            total_utf8_bytes=sum(block.utf8_byte_count for block in typed_blocks),
            stop_reason=stop_reason,
            context_sha256=fingerprint,
        )
