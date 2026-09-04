"""Typed, provider-independent contracts for OpsLens knowledge retrieval."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from hashlib import sha256
from typing import Self
from urllib.parse import urlparse

from opslens.knowledge_retrieval.domain.errors import KnowledgeRetrievalValidationError

MAX_RETRIEVAL_QUERY_CHARS = 1_000
DEFAULT_RETRIEVAL_TOP_K = 5
MAX_RETRIEVAL_TOP_K = 10

CANONICAL_METADATA_FIELDS = frozenset(
    {
        "source_id",
        "source_type",
        "canonical_uri",
        "document_id",
        "content_sha256",
        "title",
        "published_at",
        "updated_at",
        "vulnerability_ids",
        "ecosystem",
        "package_name",
        "section_path",
    }
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_CITATION_ID_PATTERN = re.compile(r"^C[1-9][0-9]*$")


class KnowledgeSourceType(StrEnum):
    """Allowlisted explanatory/remediation source classes for the initial corpus."""

    MAINTAINER_DOCUMENTATION = "maintainer_documentation"
    VENDOR_ADVISORY = "vendor_advisory"
    SECURITY_GUIDANCE = "security_guidance"
    STANDARDS_GUIDANCE = "standards_guidance"


class RetrievalBackend(StrEnum):
    """Backends that may produce typed retrieval evidence."""

    OFFLINE_GOLDEN = "offline_golden"
    BEDROCK_KNOWLEDGE_BASE = "bedrock_knowledge_base"


def _require_runtime_instance(value: object, expected_type: type[object], label: str) -> None:
    """Reject untrusted runtime values that do not match a frozen contract type."""
    if not isinstance(value, expected_type):
        raise KnowledgeRetrievalValidationError(f"{label} has an unsupported value.")


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


def _sha256_text(text: str) -> str:
    """Return the canonical UTF-8 SHA-256 digest for one text payload."""
    return sha256(text.encode("utf-8")).hexdigest()


def _validate_https_uri(value: object, label: str) -> str:
    """Require an absolute HTTPS provenance URI."""
    normalized = _normalize_required_text(value, label)
    parsed = urlparse(normalized)
    if parsed.scheme != "https" or not parsed.netloc:
        raise KnowledgeRetrievalValidationError(f"{label} must be an absolute HTTPS URI.")
    return normalized


def _normalize_text_tuple(value: object, label: str) -> tuple[str, ...]:
    """Normalize one tuple of unique non-empty strings."""
    if type(value) is not tuple:
        raise KnowledgeRetrievalValidationError(f"{label} must be a tuple.")
    normalized = tuple(_normalize_required_text(item, label) for item in value)
    if len(set(normalized)) != len(normalized):
        raise KnowledgeRetrievalValidationError(f"{label} cannot contain duplicates.")
    return normalized


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    """One canonical explanatory/remediation source snapshot with exact content identity."""

    document_id: str
    source_id: str
    source_type: KnowledgeSourceType
    title: str
    canonical_uri: str
    content_sha256: str
    text: str
    published_at: date | None = None
    updated_at: date | None = None
    vulnerability_ids: tuple[str, ...] = ()
    ecosystem: str | None = None
    package_name: str | None = None

    def __post_init__(self) -> None:
        """Validate source identity, provenance, metadata, and exact content identity."""
        object.__setattr__(
            self,
            "document_id",
            _normalize_required_text(self.document_id, "document_id"),
        )
        object.__setattr__(self, "source_id", _normalize_required_text(self.source_id, "source_id"))
        _require_runtime_instance(self.source_type, KnowledgeSourceType, "source_type")
        object.__setattr__(self, "title", _normalize_required_text(self.title, "title"))
        object.__setattr__(
            self,
            "canonical_uri",
            _validate_https_uri(self.canonical_uri, "canonical_uri"),
        )
        object.__setattr__(self, "text", _normalize_required_text(self.text, "text"))
        digest = _validate_sha256(self.content_sha256, "content_sha256")
        if digest != _sha256_text(self.text):
            raise KnowledgeRetrievalValidationError(
                "content_sha256 must match the canonical UTF-8 document text."
            )
        object.__setattr__(self, "content_sha256", digest)
        object.__setattr__(
            self,
            "vulnerability_ids",
            _normalize_text_tuple(self.vulnerability_ids, "vulnerability_ids"),
        )
        object.__setattr__(
            self,
            "ecosystem",
            _normalize_optional_text(self.ecosystem, "ecosystem"),
        )
        object.__setattr__(
            self,
            "package_name",
            _normalize_optional_text(self.package_name, "package_name"),
        )
        if self.published_at is not None and type(self.published_at) is not date:
            raise KnowledgeRetrievalValidationError("published_at must be an explicit date.")
        if self.updated_at is not None and type(self.updated_at) is not date:
            raise KnowledgeRetrievalValidationError("updated_at must be an explicit date.")
        if (
            self.published_at is not None
            and self.updated_at is not None
            and self.updated_at < self.published_at
        ):
            raise KnowledgeRetrievalValidationError(
                "updated_at cannot precede published_at."
            )

    @classmethod
    def from_text(
        cls,
        *,
        document_id: str,
        source_id: str,
        source_type: KnowledgeSourceType,
        title: str,
        canonical_uri: str,
        text: str,
        published_at: date | None = None,
        updated_at: date | None = None,
        vulnerability_ids: tuple[str, ...] = (),
        ecosystem: str | None = None,
        package_name: str | None = None,
    ) -> Self:
        """Create one document while deriving exact content identity deterministically."""
        normalized_text = _normalize_required_text(text, "text")
        return cls(
            document_id=document_id,
            source_id=source_id,
            source_type=source_type,
            title=title,
            canonical_uri=canonical_uri,
            content_sha256=_sha256_text(normalized_text),
            text=normalized_text,
            published_at=published_at,
            updated_at=updated_at,
            vulnerability_ids=vulnerability_ids,
            ecosystem=ecosystem,
            package_name=package_name,
        )


@dataclass(frozen=True, slots=True)
class RetrievalRequest:
    """Bounded semantic retrieval request with typed optional scope."""

    query: str
    top_k: int = DEFAULT_RETRIEVAL_TOP_K
    source_types: tuple[KnowledgeSourceType, ...] = ()
    vulnerability_ids: tuple[str, ...] = ()
    ecosystem: str | None = None
    package_name: str | None = None

    def __post_init__(self) -> None:
        """Normalize the query and reject unbounded or arbitrary retrieval authority."""
        normalized_query = _normalize_required_text(self.query, "query")
        if len(normalized_query) > MAX_RETRIEVAL_QUERY_CHARS:
            raise KnowledgeRetrievalValidationError(
                f"query cannot exceed {MAX_RETRIEVAL_QUERY_CHARS} characters."
            )
        object.__setattr__(self, "query", normalized_query)

        if type(self.top_k) is not int or not 1 <= self.top_k <= MAX_RETRIEVAL_TOP_K:
            raise KnowledgeRetrievalValidationError(
                f"top_k must be an integer from 1 to {MAX_RETRIEVAL_TOP_K}."
            )
        if type(self.source_types) is not tuple or any(
            not isinstance(source_type, KnowledgeSourceType)
            for source_type in self.source_types
        ):
            raise KnowledgeRetrievalValidationError(
                "source_types must contain only allowlisted source types."
            )
        if len(set(self.source_types)) != len(self.source_types):
            raise KnowledgeRetrievalValidationError("source_types cannot contain duplicates.")
        object.__setattr__(
            self,
            "vulnerability_ids",
            _normalize_text_tuple(self.vulnerability_ids, "vulnerability_ids"),
        )
        object.__setattr__(
            self,
            "ecosystem",
            _normalize_optional_text(self.ecosystem, "ecosystem"),
        )
        object.__setattr__(
            self,
            "package_name",
            _normalize_optional_text(self.package_name, "package_name"),
        )


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """One ranked knowledge chunk with explicit source and content provenance."""

    chunk_id: str
    document_id: str
    source_id: str
    source_type: KnowledgeSourceType
    canonical_uri: str
    document_content_sha256: str
    chunk_content_sha256: str
    text: str
    rank: int
    relevance_score: float | None = None
    title: str | None = None
    section_path: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Reject malformed provenance, content identity, rank, or score evidence."""
        object.__setattr__(self, "chunk_id", _normalize_required_text(self.chunk_id, "chunk_id"))
        object.__setattr__(
            self,
            "document_id",
            _normalize_required_text(self.document_id, "document_id"),
        )
        object.__setattr__(self, "source_id", _normalize_required_text(self.source_id, "source_id"))
        _require_runtime_instance(self.source_type, KnowledgeSourceType, "source_type")
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
                "chunk_content_sha256 must match the canonical UTF-8 chunk text."
            )
        object.__setattr__(self, "chunk_content_sha256", chunk_digest)
        if type(self.rank) is not int or not 1 <= self.rank <= MAX_RETRIEVAL_TOP_K:
            raise KnowledgeRetrievalValidationError(
                f"rank must be an integer from 1 to {MAX_RETRIEVAL_TOP_K}."
            )
        if self.relevance_score is not None:
            if isinstance(self.relevance_score, bool) or not isinstance(
                self.relevance_score, (int, float)
            ):
                raise KnowledgeRetrievalValidationError("relevance_score must be numeric.")
            normalized_score = float(self.relevance_score)
            if not math.isfinite(normalized_score):
                raise KnowledgeRetrievalValidationError("relevance_score must be finite.")
            object.__setattr__(self, "relevance_score", normalized_score)
        object.__setattr__(self, "title", _normalize_optional_text(self.title, "title"))
        object.__setattr__(
            self,
            "section_path",
            _normalize_text_tuple(self.section_path, "section_path"),
        )

    @classmethod
    def from_text(
        cls,
        *,
        chunk_id: str,
        document_id: str,
        source_id: str,
        source_type: KnowledgeSourceType,
        canonical_uri: str,
        document_content_sha256: str,
        text: str,
        rank: int,
        relevance_score: float | None = None,
        title: str | None = None,
        section_path: tuple[str, ...] = (),
    ) -> Self:
        """Create one chunk while deriving exact chunk content identity deterministically."""
        normalized_text = _normalize_required_text(text, "text")
        return cls(
            chunk_id=chunk_id,
            document_id=document_id,
            source_id=source_id,
            source_type=source_type,
            canonical_uri=canonical_uri,
            document_content_sha256=document_content_sha256,
            chunk_content_sha256=_sha256_text(normalized_text),
            text=normalized_text,
            rank=rank,
            relevance_score=relevance_score,
            title=title,
            section_path=section_path,
        )


@dataclass(frozen=True, slots=True)
class RetrievalEvidence:
    """Complete bounded retrieval operation evidence before any synthesis step."""

    retrieval_id: str
    request: RetrievalRequest
    chunks: tuple[RetrievedChunk, ...]
    backend: RetrievalBackend
    backend_reference: str | None = None

    def __post_init__(self) -> None:
        """Require internally consistent ranks, identities, and retrieval bounds."""
        object.__setattr__(
            self,
            "retrieval_id",
            _normalize_required_text(self.retrieval_id, "retrieval_id"),
        )
        _require_runtime_instance(self.request, RetrievalRequest, "request")
        if type(self.chunks) is not tuple or any(
            not isinstance(chunk, RetrievedChunk) for chunk in self.chunks
        ):
            raise KnowledgeRetrievalValidationError(
                "chunks must contain only RetrievedChunk values."
            )
        _require_runtime_instance(self.backend, RetrievalBackend, "backend")
        object.__setattr__(
            self,
            "backend_reference",
            _normalize_optional_text(self.backend_reference, "backend_reference"),
        )
        if len(self.chunks) > self.request.top_k:
            raise KnowledgeRetrievalValidationError(
                "retrieval cannot return more chunks than request.top_k."
            )
        expected_ranks = tuple(range(1, len(self.chunks) + 1))
        actual_ranks = tuple(chunk.rank for chunk in self.chunks)
        if actual_ranks != expected_ranks:
            raise KnowledgeRetrievalValidationError(
                "retrieved chunk ranks must be contiguous and ordered from 1."
            )
        chunk_ids = tuple(chunk.chunk_id for chunk in self.chunks)
        if len(set(chunk_ids)) != len(chunk_ids):
            raise KnowledgeRetrievalValidationError("retrieved chunk IDs must be unique.")


@dataclass(frozen=True, slots=True)
class Citation:
    """Deterministic citation projected from one already-admitted retrieved chunk."""

    citation_id: str
    chunk_id: str
    document_id: str
    source_id: str
    canonical_uri: str
    title: str | None = None
    section_path: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate citation identity and explicit provenance fields."""
        normalized_citation_id = _normalize_required_text(self.citation_id, "citation_id")
        if _CITATION_ID_PATTERN.fullmatch(normalized_citation_id) is None:
            raise KnowledgeRetrievalValidationError(
                "citation_id must use the deterministic C1, C2, ... form."
            )
        object.__setattr__(self, "citation_id", normalized_citation_id)
        object.__setattr__(self, "chunk_id", _normalize_required_text(self.chunk_id, "chunk_id"))
        object.__setattr__(
            self,
            "document_id",
            _normalize_required_text(self.document_id, "document_id"),
        )
        object.__setattr__(self, "source_id", _normalize_required_text(self.source_id, "source_id"))
        object.__setattr__(
            self,
            "canonical_uri",
            _validate_https_uri(self.canonical_uri, "canonical_uri"),
        )
        object.__setattr__(self, "title", _normalize_optional_text(self.title, "title"))
        object.__setattr__(
            self,
            "section_path",
            _normalize_text_tuple(self.section_path, "section_path"),
        )

    @classmethod
    def from_chunk(cls, *, citation_id: str, chunk: RetrievedChunk) -> Self:
        """Create a citation only by projecting provenance from admitted evidence."""
        _require_runtime_instance(chunk, RetrievedChunk, "chunk")
        return cls(
            citation_id=citation_id,
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            source_id=chunk.source_id,
            canonical_uri=chunk.canonical_uri,
            title=chunk.title,
            section_path=chunk.section_path,
        )
