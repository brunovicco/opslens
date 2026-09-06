"""Deterministic citation catalog contracts over already-admitted synthesis context."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Self, cast

from opslens.knowledge_retrieval.domain.context import (
    MAX_CONTEXT_CHUNKS,
    AssembledContext,
    ContextEvidenceBlock,
)
from opslens.knowledge_retrieval.domain.errors import KnowledgeRetrievalValidationError
from opslens.knowledge_retrieval.domain.models import Citation

CITATION_CATALOG_ID = "knowledge-citation-catalog:v1"

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _is_runtime_instance(value: object, expected_type: type[object]) -> bool:
    """Check untrusted runtime values without weakening public annotations."""
    return isinstance(value, expected_type)


def _normalize_required_text(value: object, label: str) -> str:
    """Return one trimmed non-empty string or fail closed."""
    if not isinstance(value, str):
        raise KnowledgeRetrievalValidationError(f"{label} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise KnowledgeRetrievalValidationError(f"{label} cannot be blank.")
    return normalized


def _validate_sha256(value: object, label: str) -> str:
    """Require one lowercase hexadecimal SHA-256 digest."""
    normalized = _normalize_required_text(value, label)
    if _SHA256_PATTERN.fullmatch(normalized) is None:
        raise KnowledgeRetrievalValidationError(
            f"{label} must be a 64-character lowercase hexadecimal SHA-256 digest."
        )
    return normalized


def _canonical_json_bytes(payload: object) -> bytes:
    """Serialize deterministic content-free citation identity evidence."""
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _projected_citation_payload(
    *,
    citation: Citation,
    retrieval_rank: int,
    document_content_sha256: str,
    chunk_content_sha256: str,
) -> dict[str, object]:
    """Project one canonical citation identity without source text."""
    return {
        "canonical_uri": citation.canonical_uri,
        "chunk_content_sha256": chunk_content_sha256,
        "chunk_id": citation.chunk_id,
        "citation_id": citation.citation_id,
        "document_content_sha256": document_content_sha256,
        "document_id": citation.document_id,
        "retrieval_rank": retrieval_rank,
        "section_path": list(citation.section_path),
        "source_id": citation.source_id,
        "title": citation.title,
    }


@dataclass(frozen=True, slots=True)
class ProjectedCitation:
    """One canonical citation projected from a selected context block."""

    citation: Citation
    retrieval_rank: int
    document_content_sha256: str
    chunk_content_sha256: str
    citation_sha256: str

    def __post_init__(self) -> None:
        """Bind citation provenance to selected-rank and content-addressed evidence."""
        if not _is_runtime_instance(self.citation, Citation):
            raise KnowledgeRetrievalValidationError("citation must be a Citation value.")
        if (
            type(self.retrieval_rank) is not int
            or not 1 <= self.retrieval_rank <= MAX_CONTEXT_CHUNKS
        ):
            raise KnowledgeRetrievalValidationError(
                f"retrieval_rank must be an integer from 1 to {MAX_CONTEXT_CHUNKS}."
            )
        if self.citation.citation_id != f"C{self.retrieval_rank}":
            raise KnowledgeRetrievalValidationError(
                "citation_id must match the deterministic selected retrieval rank."
            )

        document_digest = _validate_sha256(
            self.document_content_sha256,
            "document_content_sha256",
        )
        chunk_digest = _validate_sha256(
            self.chunk_content_sha256,
            "chunk_content_sha256",
        )
        object.__setattr__(self, "document_content_sha256", document_digest)
        object.__setattr__(self, "chunk_content_sha256", chunk_digest)

        citation_digest = _validate_sha256(self.citation_sha256, "citation_sha256")
        expected = sha256(
            _canonical_json_bytes(
                _projected_citation_payload(
                    citation=self.citation,
                    retrieval_rank=self.retrieval_rank,
                    document_content_sha256=document_digest,
                    chunk_content_sha256=chunk_digest,
                )
            )
        ).hexdigest()
        if citation_digest != expected:
            raise KnowledgeRetrievalValidationError(
                "citation_sha256 must match deterministic projected citation evidence."
            )
        object.__setattr__(self, "citation_sha256", citation_digest)

    @classmethod
    def from_context_block(cls, block: ContextEvidenceBlock) -> Self:
        """Project one citation from an already-admitted whole context block."""
        if not _is_runtime_instance(block, ContextEvidenceBlock):
            raise KnowledgeRetrievalValidationError(
                "block must be a ContextEvidenceBlock value."
            )
        citation = Citation(
            citation_id=f"C{block.retrieval_rank}",
            chunk_id=block.chunk_id,
            document_id=block.document_id,
            source_id=block.source_id,
            canonical_uri=block.canonical_uri,
            title=block.title,
            section_path=block.section_path,
        )
        payload = _projected_citation_payload(
            citation=citation,
            retrieval_rank=block.retrieval_rank,
            document_content_sha256=block.document_content_sha256,
            chunk_content_sha256=block.chunk_content_sha256,
        )
        return cls(
            citation=citation,
            retrieval_rank=block.retrieval_rank,
            document_content_sha256=block.document_content_sha256,
            chunk_content_sha256=block.chunk_content_sha256,
            citation_sha256=sha256(_canonical_json_bytes(payload)).hexdigest(),
        )


def _normalize_projected_citations(value: object) -> tuple[ProjectedCitation, ...]:
    """Require one non-empty bounded tuple of projected citation values."""
    if not isinstance(value, tuple):
        raise KnowledgeRetrievalValidationError("citations must be a tuple.")
    values = cast(tuple[object, ...], value)
    if not values or len(values) > MAX_CONTEXT_CHUNKS:
        raise KnowledgeRetrievalValidationError(
            f"citations must contain between 1 and {MAX_CONTEXT_CHUNKS} entries."
        )
    if any(not _is_runtime_instance(item, ProjectedCitation) for item in values):
        raise KnowledgeRetrievalValidationError(
            "citations must contain only ProjectedCitation values."
        )
    return cast(tuple[ProjectedCitation, ...], values)


def _catalog_payload(
    *,
    context_sha256: str,
    citations: tuple[ProjectedCitation, ...],
) -> dict[str, object]:
    """Build the canonical content-free identity for one citation catalog."""
    return {
        "catalog_id": CITATION_CATALOG_ID,
        "citations": [
            {
                **_projected_citation_payload(
                    citation=item.citation,
                    retrieval_rank=item.retrieval_rank,
                    document_content_sha256=item.document_content_sha256,
                    chunk_content_sha256=item.chunk_content_sha256,
                ),
                "citation_sha256": item.citation_sha256,
            }
            for item in citations
        ],
        "context_sha256": context_sha256,
    }


@dataclass(frozen=True, slots=True)
class CitationCatalog:
    """Content-addressed citation authority derived only from admitted context."""

    context_sha256: str
    citations: tuple[ProjectedCitation, ...]
    catalog_sha256: str

    def __post_init__(self) -> None:
        """Require deterministic rank order, unique identities, and exact catalog hash."""
        context_sha256 = _validate_sha256(self.context_sha256, "context_sha256")
        object.__setattr__(self, "context_sha256", context_sha256)
        citations = _normalize_projected_citations(self.citations)
        object.__setattr__(self, "citations", citations)

        expected_ranks = tuple(range(1, len(citations) + 1))
        actual_ranks = tuple(item.retrieval_rank for item in citations)
        if actual_ranks != expected_ranks:
            raise KnowledgeRetrievalValidationError(
                "citation ranks must form one contiguous selected-context prefix from 1."
            )
        expected_ids = tuple(f"C{rank}" for rank in expected_ranks)
        actual_ids = tuple(item.citation.citation_id for item in citations)
        if actual_ids != expected_ids:
            raise KnowledgeRetrievalValidationError(
                "citation IDs must be deterministic C1..Cn in selected context order."
            )
        chunk_ids = tuple(item.citation.chunk_id for item in citations)
        if len(set(chunk_ids)) != len(chunk_ids):
            raise KnowledgeRetrievalValidationError(
                "citation catalog cannot contain duplicate chunk identities."
            )

        catalog_sha256 = _validate_sha256(self.catalog_sha256, "catalog_sha256")
        expected = sha256(
            _canonical_json_bytes(
                _catalog_payload(
                    context_sha256=context_sha256,
                    citations=citations,
                )
            )
        ).hexdigest()
        if catalog_sha256 != expected:
            raise KnowledgeRetrievalValidationError(
                "catalog_sha256 must match deterministic citation-catalog evidence."
            )
        object.__setattr__(self, "catalog_sha256", catalog_sha256)

    @classmethod
    def create(cls, context: AssembledContext) -> Self:
        """Create the only v1 citation catalog allowed for one assembled context."""
        if not _is_runtime_instance(context, AssembledContext):
            raise KnowledgeRetrievalValidationError(
                "context must be an AssembledContext value."
            )
        citations = tuple(
            ProjectedCitation.from_context_block(block) for block in context.blocks
        )
        digest = sha256(
            _canonical_json_bytes(
                _catalog_payload(
                    context_sha256=context.context_sha256,
                    citations=citations,
                )
            )
        ).hexdigest()
        return cls(
            context_sha256=context.context_sha256,
            citations=citations,
            catalog_sha256=digest,
        )
