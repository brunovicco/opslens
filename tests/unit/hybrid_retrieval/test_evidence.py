"""Unit tests for the Phase 8 Gate 8.2 evidence domain contract."""

from __future__ import annotations

import math

import pytest

from opslens.hybrid_retrieval.application import project_semantic_retrieval_evidence
from opslens.hybrid_retrieval.domain import (
    EvidenceNeed,
    HybridRetrievalValidationError,
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


def _structured_row(
    *,
    evidence_need: EvidenceNeed = EvidenceNeed.VULNERABILITY_FACTS,
    authority: StructuredEvidenceAuthority = StructuredEvidenceAuthority.REPOSITORY_ANALYSIS,
    row_key: str = "finding-1",
    fields: tuple[StructuredEvidenceField, ...] | None = None,
) -> StructuredEvidenceRow:
    """Build one valid structured evidence row for focused contract tests."""
    return StructuredEvidenceRow(
        evidence_need=evidence_need,
        authority=authority,
        source_artifact_id="repository-analysis:v1:test",
        source_artifact_sha256="a" * 64,
        row_key=row_key,
        fields=fields
        or (
            StructuredEvidenceField(name="cve", value="CVE-2026-0001"),
            StructuredEvidenceField(name="affected", value=True),
        ),
    )


def _retrieval_evidence() -> RetrievalEvidence:
    """Build one already-admitted Phase 7 retrieval operation for projection tests."""
    chunk = RetrievedChunk.from_text(
        chunk_id="chunk-1",
        document_id="doc-1",
        source_id="source-1",
        source_type=KnowledgeSourceType.VENDOR_ADVISORY,
        canonical_uri="https://example.com/advisory",
        document_content_sha256="b" * 64,
        text="Upgrade to the fixed release and rotate affected credentials.",
        rank=1,
        relevance_score=0.91,
        title="Vendor advisory",
        section_path=("Remediation",),
    )
    return RetrievalEvidence(
        retrieval_id="retrieval-1",
        request=RetrievalRequest(query="How should this vulnerability be remediated?"),
        chunks=(chunk,),
        backend=RetrievalBackend.OFFLINE_GOLDEN,
    )


def test_structured_row_identity_is_canonical_across_field_ordering() -> None:
    """Equivalent structured rows must hash identically regardless of caller field order."""
    cve = StructuredEvidenceField(name="cve", value="CVE-2026-0001")
    affected = StructuredEvidenceField(name="affected", value=True)

    first = _structured_row(fields=(cve, affected))
    second = _structured_row(fields=(affected, cve))

    assert first.fields == (affected, cve)
    assert first.evidence_sha256 == second.evidence_sha256
    assert first.evidence_id == second.evidence_id


def test_risk_priority_requires_risk_policy_authority() -> None:
    """Repository analysis must not be relabeled as deterministic risk-priority authority."""
    with pytest.raises(
        HybridRetrievalValidationError,
        match="authority is not authorized",
    ):
        _structured_row(evidence_need=EvidenceNeed.RISK_PRIORITY)


def test_risk_priority_accepts_risk_policy_authority() -> None:
    """Risk Policy evidence may satisfy the risk-priority need without changing class."""
    row = _structured_row(
        evidence_need=EvidenceNeed.RISK_PRIORITY,
        authority=StructuredEvidenceAuthority.RISK_POLICY,
    )

    assert row.evidence_need is EvidenceNeed.RISK_PRIORITY
    assert row.authority is StructuredEvidenceAuthority.RISK_POLICY


def test_structured_evidence_cannot_claim_remediation_authority() -> None:
    """Structured rows must not impersonate semantic remediation guidance."""
    with pytest.raises(
        HybridRetrievalValidationError,
        match="structured evidence cannot satisfy",
    ):
        _structured_row(evidence_need=EvidenceNeed.REMEDIATION_GUIDANCE)


def test_structured_field_rejects_non_finite_float() -> None:
    """Content-addressed structured evidence must not admit non-canonical JSON floats."""
    with pytest.raises(HybridRetrievalValidationError, match="floats must be finite"):
        StructuredEvidenceField(name="score", value=math.inf)


def test_semantic_projection_preserves_admitted_chunk_provenance() -> None:
    """The hybrid projection must preserve exact Phase 7 semantic evidence provenance."""
    retrieval = _retrieval_evidence()

    projected = project_semantic_retrieval_evidence(retrieval)

    assert len(projected) == 1
    semantic = projected[0]
    source = retrieval.chunks[0]
    assert semantic.evidence_need is EvidenceNeed.REMEDIATION_GUIDANCE
    assert semantic.retrieval_id == retrieval.retrieval_id
    assert semantic.chunk_id == source.chunk_id
    assert semantic.document_id == source.document_id
    assert semantic.source_id == source.source_id
    assert semantic.source_type == source.source_type.value
    assert semantic.canonical_uri == source.canonical_uri
    assert semantic.document_content_sha256 == source.document_content_sha256
    assert semantic.chunk_content_sha256 == source.chunk_content_sha256
    assert semantic.text == source.text
    assert semantic.rank == source.rank
    assert semantic.relevance_score == source.relevance_score


def test_semantic_evidence_id_is_content_addressed_and_stable() -> None:
    """Repeating an offline projection of the same admitted evidence must keep identity."""
    retrieval = _retrieval_evidence()

    first = project_semantic_retrieval_evidence(retrieval)[0]
    second = project_semantic_retrieval_evidence(retrieval)[0]

    assert first.evidence_sha256 == second.evidence_sha256
    assert first.evidence_id == second.evidence_id
    assert first.evidence_id.startswith("hybrid-semantic:v1:")
