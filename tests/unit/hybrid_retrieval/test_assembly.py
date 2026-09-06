"""Unit tests for deterministic Phase 8 Gate 8.2 evidence assembly."""

from __future__ import annotations

from hashlib import sha256
from typing import cast

import pytest

from opslens.hybrid_retrieval.application import (
    assemble_hybrid_evidence,
    project_semantic_retrieval_evidence,
    route_evidence_request,
)
from opslens.hybrid_retrieval.domain import (
    CompletenessSemantics,
    EvidenceClass,
    EvidenceNeed,
    HybridRetrievalValidationError,
    HybridRouteDecision,
    HybridRoutingRequest,
    SemanticEvidenceChunk,
    StructuredEvidenceAuthority,
    StructuredEvidenceField,
    StructuredEvidenceRow,
)
from opslens.knowledge_retrieval.domain import (
    KnowledgeSourceType,
    RetrievalBackend,
    RetrievalEvidence,
    RetrievalRequest,
    RetrievedChunk,
)


def _route(*needs: EvidenceNeed) -> HybridRouteDecision:
    """Build the authoritative Gate 8.1 route for one test evidence-needs set."""
    return route_evidence_request(HybridRoutingRequest(evidence_needs=needs))


def _structured_row(
    *,
    need: EvidenceNeed,
    row_key: str,
) -> StructuredEvidenceRow:
    """Build one valid structured row using the authority frozen for its need."""
    if need is EvidenceNeed.RISK_PRIORITY:
        authority = StructuredEvidenceAuthority.RISK_POLICY
        fields = (
            StructuredEvidenceField(name="priority_tier", value="P1"),
            StructuredEvidenceField(name="priority_score", value=65),
        )
    else:
        authority = StructuredEvidenceAuthority.REPOSITORY_ANALYSIS
        fields = (
            StructuredEvidenceField(name="cve", value="CVE-2026-0001"),
            StructuredEvidenceField(name="affected", value=True),
        )
    return StructuredEvidenceRow(
        evidence_need=need,
        authority=authority,
        source_artifact_id=f"{authority.value}:test",
        source_artifact_sha256=("a" if need is EvidenceNeed.VULNERABILITY_FACTS else "b")
        * 64,
        row_key=row_key,
        fields=fields,
    )


def _retrieval_evidence(*, retrieval_id: str = "retrieval-1") -> RetrievalEvidence:
    """Build one two-chunk admitted retrieval operation with canonical ranks."""
    first = RetrievedChunk.from_text(
        chunk_id="chunk-1",
        document_id="doc-1",
        source_id="source-1",
        source_type=KnowledgeSourceType.VENDOR_ADVISORY,
        canonical_uri="https://example.com/advisory",
        document_content_sha256="c" * 64,
        text="Upgrade to the fixed release.",
        rank=1,
        relevance_score=0.92,
    )
    second = RetrievedChunk.from_text(
        chunk_id="chunk-2",
        document_id="doc-2",
        source_id="source-2",
        source_type=KnowledgeSourceType.MAINTAINER_DOCUMENTATION,
        canonical_uri="https://example.com/release-notes",
        document_content_sha256="d" * 64,
        text="Rotate credentials after the upgrade when exposure is suspected.",
        rank=2,
        relevance_score=0.81,
    )
    return RetrievalEvidence(
        retrieval_id=retrieval_id,
        request=RetrievalRequest(
            query="How should this vulnerability be remediated?",
            top_k=2,
        ),
        chunks=(first, second),
        backend=RetrievalBackend.OFFLINE_GOLDEN,
    )


def _semantic_chunk(*, retrieval_id: str, chunk_id: str, rank: int) -> SemanticEvidenceChunk:
    """Build one direct semantic evidence chunk for negative assembly tests."""
    text = f"Remediation evidence for {chunk_id}."
    return SemanticEvidenceChunk(
        retrieval_id=retrieval_id,
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        source_id=f"source-{chunk_id}",
        source_type="vendor_advisory",
        canonical_uri=f"https://example.com/{chunk_id}",
        document_content_sha256="e" * 64,
        chunk_content_sha256=sha256(text.encode("utf-8")).hexdigest(),
        text=text,
        rank=rank,
    )


def test_structured_only_envelope_is_complete() -> None:
    """One admitted structured row may satisfy one structured-only authority decision."""
    decision = _route(EvidenceNeed.VULNERABILITY_FACTS)
    row = _structured_row(need=EvidenceNeed.VULNERABILITY_FACTS, row_key="finding-1")

    envelope = assemble_hybrid_evidence(
        authority_decision=decision,
        structured_evidence=(row,),
    )

    assert envelope.completeness is CompletenessSemantics.ALL_REQUIRED
    assert envelope.satisfied_evidence_needs == (EvidenceNeed.VULNERABILITY_FACTS,)
    assert envelope.semantic_evidence == ()
    assert envelope.envelope_id.startswith("hybrid-evidence:v1:")


def test_structured_route_with_two_needs_requires_need_level_coverage() -> None:
    """Class presence alone must not hide one missing structured evidence need."""
    decision = _route(EvidenceNeed.VULNERABILITY_FACTS, EvidenceNeed.RISK_PRIORITY)
    vulnerability = _structured_row(
        need=EvidenceNeed.VULNERABILITY_FACTS,
        row_key="finding-1",
    )

    with pytest.raises(HybridRetrievalValidationError, match="exactly every authorized"):
        assemble_hybrid_evidence(
            authority_decision=decision,
            structured_evidence=(vulnerability,),
        )


def test_structured_route_with_two_needs_accepts_both_authorities() -> None:
    """Distinct structured authorities may jointly satisfy distinct requested needs."""
    decision = _route(EvidenceNeed.VULNERABILITY_FACTS, EvidenceNeed.RISK_PRIORITY)
    vulnerability = _structured_row(
        need=EvidenceNeed.VULNERABILITY_FACTS,
        row_key="finding-1",
    )
    risk = _structured_row(need=EvidenceNeed.RISK_PRIORITY, row_key="risk-1")

    envelope = assemble_hybrid_evidence(
        authority_decision=decision,
        structured_evidence=(risk, vulnerability),
    )

    assert envelope.satisfied_evidence_needs == decision.evidence_needs
    assert tuple(item.evidence_need for item in envelope.structured_evidence) == (
        EvidenceNeed.RISK_PRIORITY,
        EvidenceNeed.VULNERABILITY_FACTS,
    )


def test_semantic_only_envelope_uses_already_admitted_chunks() -> None:
    """Semantic-only assembly must preserve the admitted retrieval operation and ranks."""
    decision = _route(EvidenceNeed.REMEDIATION_GUIDANCE)
    semantic = project_semantic_retrieval_evidence(_retrieval_evidence())

    envelope = assemble_hybrid_evidence(
        authority_decision=decision,
        semantic_evidence=semantic,
    )

    assert tuple(item.rank for item in envelope.semantic_evidence) == (1, 2)
    assert envelope.satisfied_evidence_needs == (EvidenceNeed.REMEDIATION_GUIDANCE,)


def test_true_hybrid_envelope_requires_both_evidence_classes() -> None:
    """A true hybrid route must admit both structured truth and semantic guidance."""
    decision = _route(
        EvidenceNeed.VULNERABILITY_FACTS,
        EvidenceNeed.REMEDIATION_GUIDANCE,
    )
    structured = _structured_row(
        need=EvidenceNeed.VULNERABILITY_FACTS,
        row_key="finding-1",
    )
    semantic = project_semantic_retrieval_evidence(_retrieval_evidence())

    envelope = assemble_hybrid_evidence(
        authority_decision=decision,
        structured_evidence=(structured,),
        semantic_evidence=semantic,
    )

    assert envelope.satisfied_evidence_needs == decision.evidence_needs
    assert tuple(item.evidence_class for item in envelope.provenance_by_class) == (
        EvidenceClass.STRUCTURED,
        EvidenceClass.SEMANTIC,
    )


def test_hybrid_envelope_fails_closed_when_semantic_evidence_is_missing() -> None:
    """Structured evidence cannot silently substitute for required semantic guidance."""
    decision = _route(
        EvidenceNeed.VULNERABILITY_FACTS,
        EvidenceNeed.REMEDIATION_GUIDANCE,
    )
    structured = _structured_row(
        need=EvidenceNeed.VULNERABILITY_FACTS,
        row_key="finding-1",
    )

    with pytest.raises(HybridRetrievalValidationError, match="semantic evidence is missing"):
        assemble_hybrid_evidence(
            authority_decision=decision,
            structured_evidence=(structured,),
        )


def test_hybrid_envelope_fails_closed_when_structured_evidence_is_missing() -> None:
    """Semantic similarity cannot silently substitute for required structured truth."""
    decision = _route(
        EvidenceNeed.VULNERABILITY_FACTS,
        EvidenceNeed.REMEDIATION_GUIDANCE,
    )
    semantic = project_semantic_retrieval_evidence(_retrieval_evidence())

    with pytest.raises(HybridRetrievalValidationError, match="structured evidence is missing"):
        assemble_hybrid_evidence(
            authority_decision=decision,
            semantic_evidence=semantic,
        )


def test_structured_route_rejects_unrequested_semantic_evidence() -> None:
    """Extra semantic evidence must not broaden a structured-only route."""
    decision = _route(EvidenceNeed.VULNERABILITY_FACTS)
    structured = _structured_row(
        need=EvidenceNeed.VULNERABILITY_FACTS,
        row_key="finding-1",
    )
    semantic = project_semantic_retrieval_evidence(_retrieval_evidence())

    with pytest.raises(HybridRetrievalValidationError, match="not authorized"):
        assemble_hybrid_evidence(
            authority_decision=decision,
            structured_evidence=(structured,),
            semantic_evidence=semantic,
        )


def test_semantic_route_rejects_unrequested_structured_evidence() -> None:
    """Extra structured evidence must not broaden a semantic-only route."""
    decision = _route(EvidenceNeed.REMEDIATION_GUIDANCE)
    structured = _structured_row(
        need=EvidenceNeed.VULNERABILITY_FACTS,
        row_key="finding-1",
    )
    semantic = project_semantic_retrieval_evidence(_retrieval_evidence())

    with pytest.raises(HybridRetrievalValidationError, match="not authorized"):
        assemble_hybrid_evidence(
            authority_decision=decision,
            structured_evidence=(structured,),
            semantic_evidence=semantic,
        )


def test_hybrid_route_rejects_structured_evidence_for_unrequested_need() -> None:
    """A valid structured class must still match the exact evidence need requested."""
    decision = _route(EvidenceNeed.VULNERABILITY_FACTS, EvidenceNeed.REMEDIATION_GUIDANCE)
    risk = _structured_row(need=EvidenceNeed.RISK_PRIORITY, row_key="risk-1")
    semantic = project_semantic_retrieval_evidence(_retrieval_evidence())

    with pytest.raises(HybridRetrievalValidationError, match="exactly every authorized"):
        assemble_hybrid_evidence(
            authority_decision=decision,
            structured_evidence=(risk,),
            semantic_evidence=semantic,
        )


def test_unsupported_route_cannot_produce_an_evidence_envelope() -> None:
    """Known out-of-authority runtime exposure must stop before evidence composition."""
    decision = _route(EvidenceNeed.RUNTIME_EXPOSURE)

    with pytest.raises(HybridRetrievalValidationError, match="unsupported route"):
        assemble_hybrid_evidence(authority_decision=decision)


def test_semantic_evidence_must_come_from_one_retrieval_operation() -> None:
    """V1 must not merge unrelated retrieval operations into one semantic authority set."""
    decision = _route(EvidenceNeed.REMEDIATION_GUIDANCE)
    first = _semantic_chunk(retrieval_id="retrieval-1", chunk_id="chunk-1", rank=1)
    second = _semantic_chunk(retrieval_id="retrieval-2", chunk_id="chunk-2", rank=1)

    with pytest.raises(HybridRetrievalValidationError, match="exactly one retrieval"):
        assemble_hybrid_evidence(
            authority_decision=decision,
            semantic_evidence=(first, second),
        )


def test_semantic_evidence_requires_contiguous_ranks() -> None:
    """Missing rank positions must fail before a semantic evidence set is admitted."""
    decision = _route(EvidenceNeed.REMEDIATION_GUIDANCE)
    first = _semantic_chunk(retrieval_id="retrieval-1", chunk_id="chunk-1", rank=1)
    third = _semantic_chunk(retrieval_id="retrieval-1", chunk_id="chunk-3", rank=3)

    with pytest.raises(HybridRetrievalValidationError, match="contiguous"):
        assemble_hybrid_evidence(
            authority_decision=decision,
            semantic_evidence=(third, first),
        )


def test_envelope_identity_is_canonical_across_structured_input_order() -> None:
    """Equivalent admitted evidence sets must produce the same content-addressed envelope."""
    decision = _route(EvidenceNeed.VULNERABILITY_FACTS, EvidenceNeed.RISK_PRIORITY)
    vulnerability = _structured_row(
        need=EvidenceNeed.VULNERABILITY_FACTS,
        row_key="finding-1",
    )
    risk = _structured_row(need=EvidenceNeed.RISK_PRIORITY, row_key="risk-1")

    first = assemble_hybrid_evidence(
        authority_decision=decision,
        structured_evidence=(risk, vulnerability),
    )
    second = assemble_hybrid_evidence(
        authority_decision=decision,
        structured_evidence=(vulnerability, risk),
    )

    assert first == second
    assert first.identity_sha256 == second.identity_sha256
    assert first.envelope_id == second.envelope_id


def test_duplicate_structured_evidence_is_rejected() -> None:
    """Repeated content-addressed evidence must not inflate perceived completeness."""
    decision = _route(EvidenceNeed.VULNERABILITY_FACTS)
    row = _structured_row(need=EvidenceNeed.VULNERABILITY_FACTS, row_key="finding-1")

    with pytest.raises(HybridRetrievalValidationError, match="IDs must be unique"):
        assemble_hybrid_evidence(
            authority_decision=decision,
            structured_evidence=(row, row),
        )


def test_invalid_authority_decision_object_fails_closed() -> None:
    """Application assembly must reject values that bypass the Gate 8.1 authority contract."""
    invalid = cast(HybridRouteDecision, object())

    with pytest.raises(HybridRetrievalValidationError, match="authority_decision"):
        assemble_hybrid_evidence(authority_decision=invalid)
