"""Application services for deterministic hybrid evidence assembly."""

from __future__ import annotations

from opslens.hybrid_retrieval.domain.evidence import (
    HybridEvidenceEnvelope,
    SemanticEvidenceChunk,
    StructuredEvidenceRow,
)
from opslens.hybrid_retrieval.domain.errors import HybridRetrievalValidationError
from opslens.hybrid_retrieval.domain.models import HybridRouteDecision
from opslens.knowledge_retrieval.domain import RetrievalEvidence, RetrievedChunk


def _admit_retrieval_evidence(value: object) -> RetrievalEvidence:
    """Reject values that bypass the Phase 7 retrieval evidence contract."""
    if not isinstance(value, RetrievalEvidence):
        raise HybridRetrievalValidationError(
            "retrieval evidence must be an admitted RetrievalEvidence."
        )
    return value


def _admit_authority_decision(value: object) -> HybridRouteDecision:
    """Reject values that bypass the Gate 8.1 routing authority contract."""
    if not isinstance(value, HybridRouteDecision):
        raise HybridRetrievalValidationError(
            "authority_decision must be an admitted HybridRouteDecision."
        )
    return value


def _project_retrieved_chunk(*, retrieval_id: str, chunk: RetrievedChunk) -> SemanticEvidenceChunk:
    """Project one already-admitted Phase 7 chunk without changing its provenance."""
    return SemanticEvidenceChunk(
        retrieval_id=retrieval_id,
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        source_id=chunk.source_id,
        source_type=chunk.source_type.value,
        canonical_uri=chunk.canonical_uri,
        document_content_sha256=chunk.document_content_sha256,
        chunk_content_sha256=chunk.chunk_content_sha256,
        text=chunk.text,
        rank=chunk.rank,
        relevance_score=chunk.relevance_score,
        title=chunk.title,
        section_path=chunk.section_path,
    )


def project_semantic_retrieval_evidence(
    evidence: RetrievalEvidence,
) -> tuple[SemanticEvidenceChunk, ...]:
    """Project one admitted retrieval operation into provider-independent semantic evidence."""
    admitted_evidence = _admit_retrieval_evidence(evidence)
    return tuple(
        _project_retrieved_chunk(
            retrieval_id=admitted_evidence.retrieval_id,
            chunk=chunk,
        )
        for chunk in admitted_evidence.chunks
    )


def assemble_hybrid_evidence(
    *,
    authority_decision: HybridRouteDecision,
    structured_evidence: tuple[StructuredEvidenceRow, ...] = (),
    semantic_evidence: tuple[SemanticEvidenceChunk, ...] = (),
) -> HybridEvidenceEnvelope:
    """Assemble only evidence that exactly satisfies one deterministic authority decision."""
    admitted_decision = _admit_authority_decision(authority_decision)
    return HybridEvidenceEnvelope(
        authority_decision=admitted_decision,
        structured_evidence=structured_evidence,
        semantic_evidence=semantic_evidence,
    )
