"""Unit tests for the pure deterministic OpsLens Risk Policy v1."""

from __future__ import annotations

import re

import pytest

from opslens.risk_policy.domain import (
    RISK_POLICY_V1,
    RiskEpssState,
    RiskEvidenceCompleteness,
    RiskFindingInput,
    RiskKevState,
    RiskPrioritizationResult,
    RiskPriorityTier,
    evaluate_risk_finding_v1,
)

_SHA256 = "a" * 64


def _input(
    *,
    finding_id: str = "repository-analysis-finding:v1@sha256:test",
    kev_state: RiskKevState = RiskKevState.PRESENT,
    epss_state: RiskEpssState = RiskEpssState.SCORE_PRESENT,
    epss_score: float | None = 0.70,
    cvss_base_scores: tuple[float, ...] = (9.8, 8.8),
    unsupported_cvss_families: tuple[str, ...] = (),
    fixed_version_available: bool = True,
) -> RiskFindingInput:
    """Build one valid deterministic policy input."""
    return RiskFindingInput(
        analysis_finding_id=finding_id,
        source_evidence_sha256=_SHA256,
        kev_state=kev_state,
        epss_state=epss_state,
        epss_score=epss_score,
        cvss_base_scores=cvss_base_scores,
        unsupported_cvss_families=unsupported_cvss_families,
        fixed_version_available=fixed_version_available,
    )


def test_policy_definition_is_frozen_content_addressed_and_bounded() -> None:
    """Risk Policy v1 is explicit, reproducible, and bounded to 100 points."""
    policy = RISK_POLICY_V1

    assert policy.version == "1"
    assert policy.max_score == 100
    assert policy.canonical_json == RISK_POLICY_V1.canonical_json
    assert re.fullmatch(r"risk-policy:v1@sha256:[0-9a-f]{64}", policy.policy_id)


def test_all_positive_factors_produce_maximum_p0_priority() -> None:
    """KEV, high EPSS, critical CVSS, and a fix produce the v1 maximum."""
    evaluation = evaluate_risk_finding_v1(_input())

    assert evaluation.priority_score == 100
    assert evaluation.priority_tier is RiskPriorityTier.P0
    assert evaluation.evidence_completeness is RiskEvidenceCompleteness.COMPLETE
    assert evaluation.review_required is False
    assert evaluation.selected_cvss_base_score == 9.8
    assert [factor.points for factor in evaluation.factors] == [40, 30, 20, 10]


@pytest.mark.parametrize(
    ("score", "expected_points", "expected_reason"),
    [
        (0.70, 30, "epss_at_least_0_70"),
        (0.699999, 20, "epss_at_least_0_30"),
        (0.30, 20, "epss_at_least_0_30"),
        (0.299999, 10, "epss_at_least_0_10"),
        (0.10, 10, "epss_at_least_0_10"),
        (0.099999, 0, "epss_below_0_10"),
    ],
)
def test_epss_thresholds_are_inclusive_and_deterministic(
    score: float,
    expected_points: int,
    expected_reason: str,
) -> None:
    """EPSS v1 bucket boundaries cannot drift through model interpretation."""
    evaluation = evaluate_risk_finding_v1(_input(epss_score=score))
    factor = evaluation.factors[1]

    assert factor.points == expected_points
    assert factor.reason_code == expected_reason


@pytest.mark.parametrize(
    ("score", "expected_points", "expected_reason"),
    [
        (9.0, 20, "cvss_at_least_9_0"),
        (8.9, 10, "cvss_at_least_7_0"),
        (7.0, 10, "cvss_at_least_7_0"),
        (6.9, 5, "cvss_at_least_4_0"),
        (4.0, 5, "cvss_at_least_4_0"),
        (3.9, 0, "cvss_below_4_0"),
    ],
)
def test_cvss_thresholds_use_explicit_max_supported_aggregation(
    score: float,
    expected_points: int,
    expected_reason: str,
) -> None:
    """The policy aggregates source metrics explicitly instead of inventing source truth."""
    evaluation = evaluate_risk_finding_v1(
        _input(cvss_base_scores=(score, max(0.0, score - 1.0)))
    )
    factor = evaluation.factors[2]

    assert evaluation.selected_cvss_base_score == score
    assert factor.points == expected_points
    assert factor.reason_code == expected_reason


def test_proven_kev_absence_is_zero_points_but_complete_evidence() -> None:
    """Complete-catalog negative evidence is not treated as missing evidence."""
    evaluation = evaluate_risk_finding_v1(_input(kev_state=RiskKevState.ABSENT))

    assert evaluation.factors[0].points == 0
    assert evaluation.factors[0].reason_code == "kev_absent_in_complete_snapshot"
    assert evaluation.evidence_completeness is RiskEvidenceCompleteness.COMPLETE
    assert evaluation.review_required is False


def test_missing_cve_identity_is_not_interpreted_as_kev_absence() -> None:
    """CVE-unavailable KEV evidence contributes no points and requires review."""
    evaluation = evaluate_risk_finding_v1(
        _input(kev_state=RiskKevState.CVE_UNAVAILABLE)
    )

    assert evaluation.factors[0].points == 0
    assert evaluation.factors[0].reason_code == "kev_cve_unavailable"
    assert evaluation.evidence_completeness is RiskEvidenceCompleteness.PARTIAL
    assert evaluation.review_required is True


def test_proven_epss_absence_is_distinct_from_unavailable_cve() -> None:
    """Complete-snapshot EPSS absence stays negative evidence rather than uncertainty."""
    absent = evaluate_risk_finding_v1(
        _input(epss_state=RiskEpssState.SCORE_ABSENT, epss_score=None)
    )
    unavailable = evaluate_risk_finding_v1(
        _input(epss_state=RiskEpssState.CVE_UNAVAILABLE, epss_score=None)
    )

    assert absent.factors[1].reason_code == "epss_absent_in_complete_snapshot"
    assert absent.evidence_completeness is RiskEvidenceCompleteness.COMPLETE
    assert unavailable.factors[1].reason_code == "epss_cve_unavailable"
    assert unavailable.evidence_completeness is RiskEvidenceCompleteness.PARTIAL


def test_unsupported_future_cvss_family_fails_closed_for_cvss_points() -> None:
    """Unknown CVSS semantics cannot silently inherit points from older metrics."""
    evaluation = evaluate_risk_finding_v1(
        _input(
            cvss_base_scores=(9.8,),
            unsupported_cvss_families=("cvssMetricV50",),
        )
    )

    assert evaluation.factors[2].points == 0
    assert evaluation.factors[2].reason_code == "cvss_unsupported_family"
    assert evaluation.selected_cvss_base_score is None
    assert evaluation.evidence_completeness is RiskEvidenceCompleteness.PARTIAL
    assert evaluation.review_required is True


def test_missing_cvss_evidence_requires_review_without_fabricating_severity() -> None:
    """No NVD/CVSS observation produces no CVSS points and explicit partial evidence."""
    evaluation = evaluate_risk_finding_v1(_input(cvss_base_scores=()))

    assert evaluation.factors[2].points == 0
    assert evaluation.factors[2].reason_code == "cvss_unavailable"
    assert evaluation.evidence_completeness is RiskEvidenceCompleteness.PARTIAL
    assert evaluation.review_required is True


def test_fixed_version_is_an_actionability_bonus_not_applicability_truth() -> None:
    """Known remediation changes priority by exactly the policy actionability bonus."""
    with_fix = evaluate_risk_finding_v1(_input(fixed_version_available=True))
    without_fix = evaluate_risk_finding_v1(_input(fixed_version_available=False))

    assert with_fix.priority_score - without_fix.priority_score == 10
    assert with_fix.factors[3].reason_code == "fixed_version_available"
    assert without_fix.factors[3].reason_code == "fixed_version_unavailable"


def test_same_evidence_and_policy_reproduce_the_same_evaluation_identity() -> None:
    """Risk Policy v1 produces content-addressed reproducible evaluation evidence."""
    first = evaluate_risk_finding_v1(_input())
    second = evaluate_risk_finding_v1(_input())

    assert first.canonical_json == second.canonical_json
    assert first.evaluation_id == second.evaluation_id
    assert re.fullmatch(r"risk-evaluation:v1@sha256:[0-9a-f]{64}", first.evaluation_id)


def test_changing_one_policy_factor_changes_evaluation_identity() -> None:
    """Priority evidence commits to every scoring input rather than only the final score."""
    baseline = evaluate_risk_finding_v1(_input(epss_score=0.70))
    changed = evaluate_risk_finding_v1(_input(epss_score=0.69))

    assert baseline.evaluation_id != changed.evaluation_id


def test_priority_tier_boundaries_are_frozen() -> None:
    """Tier thresholds remain explicit policy semantics."""
    policy = RISK_POLICY_V1

    assert policy.tier_for_score(80) is RiskPriorityTier.P0
    assert policy.tier_for_score(79) is RiskPriorityTier.P1
    assert policy.tier_for_score(60) is RiskPriorityTier.P1
    assert policy.tier_for_score(59) is RiskPriorityTier.P2
    assert policy.tier_for_score(30) is RiskPriorityTier.P2
    assert policy.tier_for_score(29) is RiskPriorityTier.P3


def test_aggregate_ranking_sorts_by_score_then_opaque_stable_id() -> None:
    """Equal-score tie breaking is deterministic and explicitly has no risk semantics."""
    high = evaluate_risk_finding_v1(
        _input(finding_id="finding-b", epss_score=0.70)
    )
    tied_a = evaluate_risk_finding_v1(
        _input(
            finding_id="finding-a",
            kev_state=RiskKevState.ABSENT,
            epss_score=0.70,
        )
    )
    tied_c = evaluate_risk_finding_v1(
        _input(
            finding_id="finding-c",
            kev_state=RiskKevState.ABSENT,
            epss_score=0.70,
        )
    )
    result = RiskPrioritizationResult(
        source_analysis_id="repository-analysis:v1@sha256:test",
        source_analysis_sha256="b" * 64,
        policy=RISK_POLICY_V1,
        evaluations=(tied_c, high, tied_a),
    )

    assert [item.rank for item in result.ranked_findings] == [1, 2, 3]
    assert [
        item.evaluation.source.analysis_finding_id for item in result.ranked_findings
    ] == ["finding-b", "finding-a", "finding-c"]
    assert re.fullmatch(
        r"risk-prioritization:v1@sha256:[0-9a-f]{64}",
        result.prioritization_id,
    )


def test_aggregate_rejects_duplicate_source_findings() -> None:
    """One source finding cannot appear twice in a prioritization result."""
    evaluation = evaluate_risk_finding_v1(_input())

    with pytest.raises(ValueError, match="duplicate source findings"):
        RiskPrioritizationResult(
            source_analysis_id="repository-analysis:v1@sha256:test",
            source_analysis_sha256="b" * 64,
            policy=RISK_POLICY_V1,
            evaluations=(evaluation, evaluation),
        )


def test_input_contract_rejects_epss_score_without_score_present_state() -> None:
    """Policy inputs fail closed when source-state semantics are inconsistent."""
    with pytest.raises(ValueError, match="allowed only"):
        _input(epss_state=RiskEpssState.SCORE_ABSENT, epss_score=0.42)
