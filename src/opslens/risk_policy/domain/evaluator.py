"""Pure deterministic evaluator for OpsLens Risk Policy v1."""

from __future__ import annotations

from opslens.risk_policy.domain.models import (
    RISK_POLICY_V1,
    RiskEvidenceCompleteness,
    RiskEpssState,
    RiskFactorContribution,
    RiskFactorName,
    RiskFindingEvaluation,
    RiskFindingInput,
    RiskKevState,
    RiskPolicyV1,
)


def evaluate_risk_finding_v1(
    source: RiskFindingInput,
    policy: RiskPolicyV1 = RISK_POLICY_V1,
) -> RiskFindingEvaluation:
    """Evaluate one immutable finding through the frozen Risk Policy v1."""
    kev_factor, kev_complete = _evaluate_kev(source, policy)
    epss_factor, epss_complete = _evaluate_epss(source, policy)
    cvss_factor, cvss_complete, selected_cvss = _evaluate_cvss(source, policy)
    fix_factor = _evaluate_fix(source, policy)

    factors = (kev_factor, epss_factor, cvss_factor, fix_factor)
    priority_score = sum(factor.points for factor in factors)
    complete = kev_complete and epss_complete and cvss_complete
    evidence_completeness = (
        RiskEvidenceCompleteness.COMPLETE
        if complete
        else RiskEvidenceCompleteness.PARTIAL
    )

    return RiskFindingEvaluation(
        policy=policy,
        source=source,
        factors=factors,
        priority_score=priority_score,
        priority_tier=policy.tier_for_score(priority_score),
        evidence_completeness=evidence_completeness,
        review_required=not complete,
        selected_cvss_base_score=selected_cvss,
    )


def _evaluate_kev(
    source: RiskFindingInput,
    policy: RiskPolicyV1,
) -> tuple[RiskFactorContribution, bool]:
    """Evaluate complete-snapshot KEV membership without inferring missing CVEs."""
    if source.kev_state is RiskKevState.PRESENT:
        return (
            RiskFactorContribution(
                factor=RiskFactorName.KEV,
                points=policy.kev_present_points,
                max_points=policy.kev_present_points,
                reason_code="kev_present",
                observed_value=source.kev_state.value,
            ),
            True,
        )
    if source.kev_state is RiskKevState.ABSENT:
        return (
            RiskFactorContribution(
                factor=RiskFactorName.KEV,
                points=0,
                max_points=policy.kev_present_points,
                reason_code="kev_absent_in_complete_snapshot",
                observed_value=source.kev_state.value,
            ),
            True,
        )
    return (
        RiskFactorContribution(
            factor=RiskFactorName.KEV,
            points=0,
            max_points=policy.kev_present_points,
            reason_code="kev_cve_unavailable",
            observed_value=source.kev_state.value,
        ),
        False,
    )


def _evaluate_epss(
    source: RiskFindingInput,
    policy: RiskPolicyV1,
) -> tuple[RiskFactorContribution, bool]:
    """Evaluate the exact selected EPSS snapshot with explicit threshold semantics."""
    if source.epss_state is RiskEpssState.CVE_UNAVAILABLE:
        return (
            RiskFactorContribution(
                factor=RiskFactorName.EPSS,
                points=0,
                max_points=policy.epss_high_points,
                reason_code="epss_cve_unavailable",
                observed_value=source.epss_state.value,
            ),
            False,
        )
    if source.epss_state is RiskEpssState.SCORE_ABSENT:
        return (
            RiskFactorContribution(
                factor=RiskFactorName.EPSS,
                points=0,
                max_points=policy.epss_high_points,
                reason_code="epss_absent_in_complete_snapshot",
                observed_value=source.epss_state.value,
            ),
            True,
        )

    score = source.epss_score
    if score is None:
        raise ValueError("Validated score_present input must carry an EPSS score.")

    if score >= policy.epss_high_threshold:
        points = policy.epss_high_points
        reason_code = "epss_at_least_0_70"
    elif score >= policy.epss_medium_threshold:
        points = policy.epss_medium_points
        reason_code = "epss_at_least_0_30"
    elif score >= policy.epss_elevated_threshold:
        points = policy.epss_elevated_points
        reason_code = "epss_at_least_0_10"
    else:
        points = 0
        reason_code = "epss_below_0_10"

    return (
        RiskFactorContribution(
            factor=RiskFactorName.EPSS,
            points=points,
            max_points=policy.epss_high_points,
            reason_code=reason_code,
            observed_value=f"{score:.6f}",
        ),
        True,
    )


def _evaluate_cvss(
    source: RiskFindingInput,
    policy: RiskPolicyV1,
) -> tuple[RiskFactorContribution, bool, float | None]:
    """Apply the explicit v1 max-supported-base-score policy aggregation."""
    if source.unsupported_cvss_families:
        observed = ",".join(source.unsupported_cvss_families)
        return (
            RiskFactorContribution(
                factor=RiskFactorName.CVSS,
                points=0,
                max_points=policy.cvss_critical_points,
                reason_code="cvss_unsupported_family",
                observed_value=observed,
            ),
            False,
            None,
        )
    if not source.cvss_base_scores:
        return (
            RiskFactorContribution(
                factor=RiskFactorName.CVSS,
                points=0,
                max_points=policy.cvss_critical_points,
                reason_code="cvss_unavailable",
                observed_value="unavailable",
            ),
            False,
            None,
        )

    selected = max(source.cvss_base_scores)
    if selected >= policy.cvss_critical_threshold:
        points = policy.cvss_critical_points
        reason_code = "cvss_at_least_9_0"
    elif selected >= policy.cvss_high_threshold:
        points = policy.cvss_high_points
        reason_code = "cvss_at_least_7_0"
    elif selected >= policy.cvss_medium_threshold:
        points = policy.cvss_medium_points
        reason_code = "cvss_at_least_4_0"
    else:
        points = 0
        reason_code = "cvss_below_4_0"

    return (
        RiskFactorContribution(
            factor=RiskFactorName.CVSS,
            points=points,
            max_points=policy.cvss_critical_points,
            reason_code=reason_code,
            observed_value=f"{selected:.1f}",
        ),
        True,
        selected,
    )


def _evaluate_fix(
    source: RiskFindingInput,
    policy: RiskPolicyV1,
) -> RiskFactorContribution:
    """Add the explicit actionability bonus when a fixed version is known."""
    if source.fixed_version_available:
        return RiskFactorContribution(
            factor=RiskFactorName.FIX_AVAILABILITY,
            points=policy.fixed_version_points,
            max_points=policy.fixed_version_points,
            reason_code="fixed_version_available",
            observed_value="true",
        )
    return RiskFactorContribution(
        factor=RiskFactorName.FIX_AVAILABILITY,
        points=0,
        max_points=policy.fixed_version_points,
        reason_code="fixed_version_unavailable",
        observed_value="false",
    )
