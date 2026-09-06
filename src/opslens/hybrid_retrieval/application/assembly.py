"""Application services for deterministic hybrid evidence assembly."""

from __future__ import annotations

from typing import cast

from opslens.hybrid_retrieval.domain.evidence import (
    HybridEvidenceEnvelope,
    SemanticEvidenceChunk,
    StructuredEvidenceRow,
)
from opslens.hybrid_retrieval.domain.errors import HybridRetrievalValidationError
from opslens.hybrid_retrieval.domain.models import HybridRouteDecision
from opslens.knowledge_retrieval.domain import RetrievalEvidence, RetrievedChunk


def _require_runtime_instance(
    value: object,
    expected_type: type[object],
    label: str,
) -> None:
    """Validate untrusted application inputs without weakening public annotations."""
    if not isinstance(value, expected_type):
        raise HybridRetrievalValidationError(f"{label} has an unsupported value.")


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
    _require_runtime_instance(evidence, RetrievalEvidence, "retrieval evidence")
    typed_evidence = cast(RetrievalEvidence, evidence)
    return tuple(
        _project_retrieved_chunk(
            retrieval_id=typed_evidence.retrieval_id,
            chunk=chunk,
        )
        for chunk in typed_evidence.chunks
    )


def assemble_hybrid_evidence(
    *,
    authority_decision: HybridRouteDecision,
    structured_evidence: tuple[StructuredEvidenceRow, ...] = (),
    semantic_evidence: tuple[SemanticEvidenceChunk, ...] = (),
) -> HybridEvidenceEnvelope:
    """Assemble only evidence that exactly satisfies one deterministic authority decision."""
    _require_runtime_instance(authority_decision, HybridRouteDecision, "authority_decision")
    return HybridEvidenceEnvelope(
        authority_decision=authority_decision,
        structured_evidence=structured_evidence,
        semantic_evidence=semantic_evidence,
    )
