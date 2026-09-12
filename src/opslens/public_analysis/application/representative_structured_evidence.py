"""Project deterministic repository and risk truth into hybrid structured evidence."""

from opslens.hybrid_retrieval.domain import (
    EvidenceNeed,
    StructuredEvidenceAuthority,
    StructuredEvidenceField,
    StructuredEvidenceRow,
)
from opslens.hybrid_retrieval.domain.synthesis import MAX_HYBRID_SYNTHESIS_STRUCTURED_FACTS
from opslens.repository_intelligence.domain import RepositoryAnalysisResult
from opslens.risk_policy.domain import RiskPrioritizationResult

_REPOSITORY_FACTS_PER_FINDING = 4
_RISK_FACTS_PER_FINDING = 4
_FACTS_PER_FINDING = _REPOSITORY_FACTS_PER_FINDING + _RISK_FACTS_PER_FINDING
MAX_REPRESENTATIVE_STRUCTURED_FINDINGS = (
    MAX_HYBRID_SYNTHESIS_STRUCTURED_FACTS // _FACTS_PER_FINDING
)


def build_representative_structured_evidence(
    *,
    analysis: RepositoryAnalysisResult,
    prioritization: RiskPrioritizationResult,
) -> tuple[StructuredEvidenceRow, ...]:
    """Project the highest-priority bounded finding set without re-querying source truth."""
    if type(analysis) is not RepositoryAnalysisResult:
        raise TypeError("analysis must be RepositoryAnalysisResult")
    if type(prioritization) is not RiskPrioritizationResult:
        raise TypeError("prioritization must be RiskPrioritizationResult")
    if (
        prioritization.source_analysis_id != analysis.analysis_id
        or prioritization.source_analysis_sha256 != analysis.evidence_sha256
    ):
        raise ValueError("risk prioritization must reference the exact repository analysis")

    findings_by_id = {
        finding.analysis_finding_id: finding for finding in analysis.findings
    }
    rows: list[StructuredEvidenceRow] = []
    selected = prioritization.ranked_findings[:MAX_REPRESENTATIVE_STRUCTURED_FINDINGS]

    for ranked in selected:
        evaluation = ranked.evaluation
        finding = findings_by_id.get(evaluation.source.analysis_finding_id)
        if finding is None:
            raise ValueError("risk prioritization references an unknown repository finding")
        if evaluation.source.source_evidence_sha256 != finding.evidence_sha256:
            raise ValueError("risk evaluation source hash drifted from repository finding")

        rows.append(
            StructuredEvidenceRow(
                evidence_need=EvidenceNeed.VULNERABILITY_FACTS,
                authority=StructuredEvidenceAuthority.REPOSITORY_ANALYSIS,
                source_artifact_id=finding.analysis_finding_id,
                source_artifact_sha256=finding.evidence_sha256,
                row_key=finding.analysis_finding_id,
                fields=(
                    StructuredEvidenceField(name="cve_id", value=finding.cve_id),
                    StructuredEvidenceField(name="dependency_purl", value=finding.purl),
                    StructuredEvidenceField(name="ghsa_id", value=finding.ghsa_id),
                    StructuredEvidenceField(
                        name="installed_version",
                        value=finding.installed_version,
                    ),
                ),
            )
        )
        rows.append(
            StructuredEvidenceRow(
                evidence_need=EvidenceNeed.RISK_PRIORITY,
                authority=StructuredEvidenceAuthority.RISK_POLICY,
                source_artifact_id=evaluation.evaluation_id,
                source_artifact_sha256=evaluation.evidence_sha256,
                row_key=evaluation.source.analysis_finding_id,
                fields=(
                    StructuredEvidenceField(
                        name="priority_score",
                        value=evaluation.priority_score,
                    ),
                    StructuredEvidenceField(
                        name="priority_tier",
                        value=evaluation.priority_tier.value,
                    ),
                    StructuredEvidenceField(name="rank", value=ranked.rank),
                    StructuredEvidenceField(
                        name="review_required",
                        value=evaluation.review_required,
                    ),
                ),
            )
        )

    if len(rows) * (_FACTS_PER_FINDING // 2) > MAX_HYBRID_SYNTHESIS_STRUCTURED_FACTS:
        raise AssertionError("representative structured projection exceeds synthesis bound")
    return tuple(rows)


__all__ = [
    "MAX_REPRESENTATIVE_STRUCTURED_FINDINGS",
    "build_representative_structured_evidence",
]
