"""Application bridge from Phase 4 evidence into deterministic Risk Policy v1."""

from __future__ import annotations

from opslens.repository_intelligence.domain.analysis_result import (
    RepositoryAnalysisFinding,
    RepositoryAnalysisResult,
)
from opslens.risk_policy.domain import (
    RISK_POLICY_V1,
    RiskEpssState,
    RiskFindingInput,
    RiskKevState,
    RiskPolicyV1,
    RiskPrioritizationResult,
    evaluate_risk_finding_v1,
)


def build_risk_finding_input(
    finding: RepositoryAnalysisFinding,
) -> RiskFindingInput:
    """Project only deterministic Phase 4 facts authorized for Risk Policy v1."""
    nvd_cvss = finding.nvd_enrichment.nvd_cvss
    unsupported_cvss_families = (
        nvd_cvss.cvss.unsupported_cvss_families if nvd_cvss is not None else ()
    )
    epss_record = finding.epss_record

    return RiskFindingInput(
        analysis_finding_id=finding.analysis_finding_id,
        source_evidence_sha256=finding.evidence_sha256,
        kev_state=RiskKevState(finding.kev_state.value),
        epss_state=RiskEpssState(finding.epss_state.value),
        epss_score=epss_record.epss if epss_record is not None else None,
        cvss_base_scores=tuple(metric.base_score for metric in finding.cvss_metrics),
        unsupported_cvss_families=unsupported_cvss_families,
        fixed_version_available=finding.fixed_version is not None,
    )


def prioritize_repository_analysis(
    analysis: RepositoryAnalysisResult,
    policy: RiskPolicyV1 = RISK_POLICY_V1,
) -> RiskPrioritizationResult:
    """Evaluate and deterministically rank every affected Phase 4 finding."""
    evaluations = tuple(
        evaluate_risk_finding_v1(build_risk_finding_input(finding), policy)
        for finding in analysis.findings
    )
    return RiskPrioritizationResult(
        source_analysis_id=analysis.analysis_id,
        source_analysis_sha256=analysis.evidence_sha256,
        policy=policy,
        evaluations=evaluations,
    )
