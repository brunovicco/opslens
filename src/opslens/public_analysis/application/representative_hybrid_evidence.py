"""Assemble representative structured and semantic evidence under public route authority."""

from __future__ import annotations

from opslens.hybrid_retrieval.application import assemble_hybrid_evidence
from opslens.hybrid_retrieval.domain import HybridEvidenceEnvelope
from opslens.public_analysis.application.representative_repository_analysis import (
    RepresentativeRepositoryAnalysis,
)
from opslens.public_analysis.application.representative_semantic_evidence import (
    RepresentativeSemanticEvidence,
)
from opslens.public_analysis.application.representative_structured_evidence import (
    build_representative_structured_evidence,
)
from opslens.public_analysis.domain import PublicAnalysisAdmissionHandoff
from opslens.risk_policy.domain import RiskPrioritizationResult


def build_representative_hybrid_evidence(
    *,
    handoff: PublicAnalysisAdmissionHandoff,
    repository_analysis: RepresentativeRepositoryAnalysis,
    prioritization: RiskPrioritizationResult,
    semantic_evidence: RepresentativeSemanticEvidence,
) -> HybridEvidenceEnvelope:
    """Satisfy the exact admitted public route without granting model authority over truth."""
    if type(handoff) is not PublicAnalysisAdmissionHandoff:
        raise TypeError("handoff must be PublicAnalysisAdmissionHandoff")
    if type(repository_analysis) is not RepresentativeRepositoryAnalysis:
        raise TypeError("repository_analysis must be RepresentativeRepositoryAnalysis")
    if type(prioritization) is not RiskPrioritizationResult:
        raise TypeError("prioritization must be RiskPrioritizationResult")
    if type(semantic_evidence) is not RepresentativeSemanticEvidence:
        raise TypeError("semantic_evidence must be RepresentativeSemanticEvidence")
    if handoff.source_execution != repository_analysis.source_execution:
        raise ValueError("repository analysis must originate from the exact public handoff source")
    analysis = repository_analysis.analysis
    if (
        prioritization.source_analysis_id != analysis.analysis_id
        or prioritization.source_analysis_sha256 != analysis.evidence_sha256
    ):
        raise ValueError("risk prioritization must reference the exact representative analysis")
    if semantic_evidence.source_analysis_id != analysis.analysis_id:
        raise ValueError("semantic evidence must reference the exact representative analysis")
    if semantic_evidence.source_prioritization_id != prioritization.prioritization_id:
        raise ValueError("semantic evidence must reference the exact risk prioritization")

    structured = build_representative_structured_evidence(
        analysis=analysis,
        prioritization=prioritization,
    )
    return assemble_hybrid_evidence(
        authority_decision=handoff.route_decision,
        structured_evidence=structured,
        semantic_evidence=semantic_evidence.semantic_chunks,
    )


__all__ = ["build_representative_hybrid_evidence"]
