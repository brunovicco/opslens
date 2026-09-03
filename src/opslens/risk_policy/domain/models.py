"""Versioned deterministic evidence models for OpsLens Risk Policy v1."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from enum import StrEnum

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_RISK_POLICY_SCHEMA_VERSION = "1"
_RISK_POLICY_ENGINE = "opslens.phase5.risk-policy.v1"


class RiskKevState(StrEnum):
    """KEV evidence states understood by Risk Policy v1."""

    PRESENT = "present"
    ABSENT = "absent"
    CVE_UNAVAILABLE = "cve_unavailable"


class RiskEpssState(StrEnum):
    """EPSS evidence states understood by Risk Policy v1."""

    SCORE_PRESENT = "score_present"
    SCORE_ABSENT = "score_absent"
    CVE_UNAVAILABLE = "cve_unavailable"


class RiskFactorName(StrEnum):
    """Risk Policy v1 factor names."""

    KEV = "kev"
    EPSS = "epss"
    CVSS = "cvss"
    FIX_AVAILABILITY = "fix_availability"


class RiskPriorityTier(StrEnum):
    """Ordered priority tiers emitted by Risk Policy v1."""

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class RiskEvidenceCompleteness(StrEnum):
    """Whether Risk Policy v1 could evaluate every required threat factor."""

    COMPLETE = "complete"
    PARTIAL = "partial"


@dataclass(frozen=True, slots=True)
class RiskPolicyV1:
    """Frozen Risk Policy v1 semantics.

    The points represent OpsLens prioritization policy, not source truth, exploit
    probability, CVSS severity, or runtime exposure.
    """

    version: str = field(default="1", init=False)
    kev_present_points: int = field(default=40, init=False)
    epss_high_threshold: float = field(default=0.70, init=False)
    epss_high_points: int = field(default=30, init=False)
    epss_medium_threshold: float = field(default=0.30, init=False)
    epss_medium_points: int = field(default=20, init=False)
    epss_elevated_threshold: float = field(default=0.10, init=False)
    epss_elevated_points: int = field(default=10, init=False)
    cvss_critical_threshold: float = field(default=9.0, init=False)
    cvss_critical_points: int = field(default=20, init=False)
    cvss_high_threshold: float = field(default=7.0, init=False)
    cvss_high_points: int = field(default=10, init=False)
    cvss_medium_threshold: float = field(default=4.0, init=False)
    cvss_medium_points: int = field(default=5, init=False)
    fixed_version_points: int = field(default=10, init=False)
    p0_threshold: int = field(default=80, init=False)
    p1_threshold: int = field(default=60, init=False)
    p2_threshold: int = field(default=30, init=False)

    @property
    def max_score(self) -> int:
        """Return the maximum possible priority score."""
        return (
            self.kev_present_points
            + self.epss_high_points
            + self.cvss_critical_points
            + self.fixed_version_points
        )

    def tier_for_score(self, score: int) -> RiskPriorityTier:
        """Map one deterministic score to its versioned priority tier."""
        if type(score) is not int or not 0 <= score <= self.max_score:
            raise ValueError("Risk priority score must be an integer inside policy bounds.")
        if score >= self.p0_threshold:
            return RiskPriorityTier.P0
        if score >= self.p1_threshold:
            return RiskPriorityTier.P1
        if score >= self.p2_threshold:
            return RiskPriorityTier.P2
        return RiskPriorityTier.P3

    @property
    def canonical_json(self) -> bytes:
        """Return canonical JSON for the frozen policy definition."""
        payload: dict[str, object] = {
            "schema_version": _RISK_POLICY_SCHEMA_VERSION,
            "engine": _RISK_POLICY_ENGINE,
            "policy_version": self.version,
            "weights": {
                "kev_present": self.kev_present_points,
                "epss": {
                    "high": {
                        "threshold": self.epss_high_threshold,
                        "points": self.epss_high_points,
                    },
                    "medium": {
                        "threshold": self.epss_medium_threshold,
                        "points": self.epss_medium_points,
                    },
                    "elevated": {
                        "threshold": self.epss_elevated_threshold,
                        "points": self.epss_elevated_points,
                    },
                },
                "cvss": {
                    "aggregation": "max_supported_base_score",
                    "critical": {
                        "threshold": self.cvss_critical_threshold,
                        "points": self.cvss_critical_points,
                    },
                    "high": {
                        "threshold": self.cvss_high_threshold,
                        "points": self.cvss_high_points,
                    },
                    "medium": {
                        "threshold": self.cvss_medium_threshold,
                        "points": self.cvss_medium_points,
                    },
                },
                "fixed_version_available": self.fixed_version_points,
            },
            "priority_tiers": {
                "P0_min": self.p0_threshold,
                "P1_min": self.p1_threshold,
                "P2_min": self.p2_threshold,
                "P3_min": 0,
            },
            "max_score": self.max_score,
            "missing_evidence": {
                "adds_points": False,
                "requires_review": True,
            },
        }
        return _canonical_json(payload)

    @property
    def evidence_sha256(self) -> str:
        """Return SHA-256 of the exact policy definition."""
        return hashlib.sha256(self.canonical_json).hexdigest()

    @property
    def policy_id(self) -> str:
        """Return the content-addressed Risk Policy v1 identity."""
        return f"risk-policy:v1@sha256:{self.evidence_sha256}"


RISK_POLICY_V1 = RiskPolicyV1()


@dataclass(frozen=True, slots=True)
class RiskFindingInput:
    """Source-preserving deterministic facts consumed by Risk Policy v1."""

    analysis_finding_id: str
    source_evidence_sha256: str
    kev_state: RiskKevState
    epss_state: RiskEpssState
    epss_score: float | None
    cvss_base_scores: tuple[float, ...]
    unsupported_cvss_families: tuple[str, ...]
    fixed_version_available: bool

    def __post_init__(self) -> None:
        """Validate policy inputs without inventing missing source evidence."""
        if not self.analysis_finding_id.strip():
            raise ValueError("Analysis finding identity cannot be blank.")
        if _SHA256_PATTERN.fullmatch(self.source_evidence_sha256) is None:
            raise ValueError("Source finding SHA-256 must be 64 lowercase hex characters.")

        if self.epss_state is RiskEpssState.SCORE_PRESENT:
            if self.epss_score is None:
                raise ValueError("EPSS score_present requires an EPSS score.")
        elif self.epss_score is not None:
            raise ValueError("EPSS score is allowed only when state is score_present.")

        if self.epss_score is not None and (
            not math.isfinite(self.epss_score) or not 0.0 <= self.epss_score <= 1.0
        ):
            raise ValueError("EPSS score must be finite and between 0.0 and 1.0.")

        for score in self.cvss_base_scores:
            if not math.isfinite(score) or not 0.0 <= score <= 10.0:
                raise ValueError("CVSS base scores must be finite and between 0.0 and 10.0.")

        for family in self.unsupported_cvss_families:
            if not family.strip():
                raise ValueError("Unsupported CVSS family names cannot be blank.")


@dataclass(frozen=True, slots=True)
class RiskFactorContribution:
    """Explain one deterministic Risk Policy v1 factor contribution."""

    factor: RiskFactorName
    points: int
    max_points: int
    reason_code: str
    observed_value: str

    def __post_init__(self) -> None:
        """Validate stable factor evidence."""
        if type(self.points) is not int or type(self.max_points) is not int:
            raise ValueError("Risk factor points must be integers.")
        if self.max_points < 0 or not 0 <= self.points <= self.max_points:
            raise ValueError("Risk factor points must remain inside factor bounds.")
        if not self.reason_code.strip():
            raise ValueError("Risk factor reason code cannot be blank.")
        if not self.observed_value.strip():
            raise ValueError("Risk factor observed value cannot be blank.")

    def to_payload(self) -> dict[str, object]:
        """Return deterministic JSON-ready factor evidence."""
        return {
            "factor": self.factor.value,
            "points": self.points,
            "max_points": self.max_points,
            "reason_code": self.reason_code,
            "observed_value": self.observed_value,
        }


@dataclass(frozen=True, slots=True)
class RiskFindingEvaluation:
    """Content-addressed deterministic priority evaluation for one Phase 4 finding."""

    policy: RiskPolicyV1
    source: RiskFindingInput
    factors: tuple[RiskFactorContribution, ...]
    priority_score: int
    priority_tier: RiskPriorityTier
    evidence_completeness: RiskEvidenceCompleteness
    review_required: bool
    selected_cvss_base_score: float | None

    def __post_init__(self) -> None:
        """Require evaluation fields to agree with the factor evidence."""
        factor_names = tuple(factor.factor for factor in self.factors)
        expected_names = (
            RiskFactorName.KEV,
            RiskFactorName.EPSS,
            RiskFactorName.CVSS,
            RiskFactorName.FIX_AVAILABILITY,
        )
        if factor_names != expected_names:
            raise ValueError("Risk Policy v1 factors must use the canonical factor order.")

        calculated_score = sum(factor.points for factor in self.factors)
        if self.priority_score != calculated_score:
            raise ValueError("Priority score must equal the sum of factor contributions.")
        if self.priority_tier is not self.policy.tier_for_score(self.priority_score):
            raise ValueError("Priority tier does not match the versioned policy thresholds.")

        expected_review = self.evidence_completeness is RiskEvidenceCompleteness.PARTIAL
        if self.review_required is not expected_review:
            raise ValueError("review_required must reflect partial evidence completeness.")

        if self.selected_cvss_base_score is not None:
            if self.selected_cvss_base_score not in self.source.cvss_base_scores:
                raise ValueError("Selected CVSS score must come from exact source evidence.")
            if self.source.unsupported_cvss_families:
                raise ValueError("Unsupported CVSS families prevent policy CVSS selection.")

    @property
    def canonical_json(self) -> bytes:
        """Return canonical policy-evaluation evidence."""
        payload: dict[str, object] = {
            "schema_version": _RISK_POLICY_SCHEMA_VERSION,
            "engine": _RISK_POLICY_ENGINE,
            "policy": {
                "policy_id": self.policy.policy_id,
                "policy_version": self.policy.version,
                "policy_sha256": self.policy.evidence_sha256,
            },
            "source": {
                "analysis_finding_id": self.source.analysis_finding_id,
                "source_evidence_sha256": self.source.source_evidence_sha256,
                "kev_state": self.source.kev_state.value,
                "epss_state": self.source.epss_state.value,
                "epss_score": self.source.epss_score,
                "cvss_base_scores": list(self.source.cvss_base_scores),
                "unsupported_cvss_families": list(
                    self.source.unsupported_cvss_families
                ),
                "fixed_version_available": self.source.fixed_version_available,
            },
            "factors": [factor.to_payload() for factor in self.factors],
            "result": {
                "priority_score": self.priority_score,
                "priority_tier": self.priority_tier.value,
                "evidence_completeness": self.evidence_completeness.value,
                "review_required": self.review_required,
                "selected_cvss_base_score": self.selected_cvss_base_score,
            },
        }
        return _canonical_json(payload)

    @property
    def evidence_sha256(self) -> str:
        """Return SHA-256 of the exact policy evaluation."""
        return hashlib.sha256(self.canonical_json).hexdigest()

    @property
    def evaluation_id(self) -> str:
        """Return content-addressed identity for this finding priority evaluation."""
        return f"risk-evaluation:v1@sha256:{self.evidence_sha256}"


@dataclass(frozen=True, slots=True)
class RankedRiskFinding:
    """Attach deterministic rank position to one evaluated finding."""

    rank: int
    evaluation: RiskFindingEvaluation

    def __post_init__(self) -> None:
        """Require one-based positive rank positions."""
        if type(self.rank) is not int or self.rank < 1:
            raise ValueError("Risk finding rank must be a positive one-based integer.")


@dataclass(frozen=True, slots=True)
class RiskPrioritizationResult:
    """Deterministic ordered Phase 5 projection over one repository analysis."""

    source_analysis_id: str
    source_analysis_sha256: str
    policy: RiskPolicyV1
    evaluations: tuple[RiskFindingEvaluation, ...]
    ranked_findings: tuple[RankedRiskFinding, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Validate source identity and derive deterministic ranking."""
        if not self.source_analysis_id.strip():
            raise ValueError("Source analysis identity cannot be blank.")
        if _SHA256_PATTERN.fullmatch(self.source_analysis_sha256) is None:
            raise ValueError("Source analysis SHA-256 must be 64 lowercase hex characters.")

        source_ids = [item.source.analysis_finding_id for item in self.evaluations]
        evaluation_ids = [item.evaluation_id for item in self.evaluations]
        if len(set(source_ids)) != len(source_ids):
            raise ValueError("Risk prioritization cannot contain duplicate source findings.")
        if len(set(evaluation_ids)) != len(evaluation_ids):
            raise ValueError("Risk prioritization cannot contain duplicate evaluations.")
        if any(item.policy != self.policy for item in self.evaluations):
            raise ValueError("Every risk evaluation must use the aggregate policy.")

        ordered = sorted(
            self.evaluations,
            key=lambda item: (-item.priority_score, item.source.analysis_finding_id),
        )
        ranked = tuple(
            RankedRiskFinding(rank=index, evaluation=item)
            for index, item in enumerate(ordered, start=1)
        )
        object.__setattr__(self, "ranked_findings", ranked)

    @property
    def canonical_json(self) -> bytes:
        """Return canonical aggregate prioritization evidence."""
        payload: dict[str, object] = {
            "schema_version": _RISK_POLICY_SCHEMA_VERSION,
            "engine": _RISK_POLICY_ENGINE,
            "source_analysis": {
                "analysis_id": self.source_analysis_id,
                "analysis_sha256": self.source_analysis_sha256,
            },
            "policy": {
                "policy_id": self.policy.policy_id,
                "policy_version": self.policy.version,
                "policy_sha256": self.policy.evidence_sha256,
            },
            "ranking_semantics": {
                "primary": "priority_score_desc",
                "tie_breaker": "analysis_finding_id_asc",
                "tie_breaker_has_risk_semantics": False,
            },
            "ranked_findings": [
                {
                    "rank": item.rank,
                    "analysis_finding_id": item.evaluation.source.analysis_finding_id,
                    "evaluation_id": item.evaluation.evaluation_id,
                    "priority_score": item.evaluation.priority_score,
                    "priority_tier": item.evaluation.priority_tier.value,
                    "evidence_completeness": (
                        item.evaluation.evidence_completeness.value
                    ),
                    "review_required": item.evaluation.review_required,
                }
                for item in self.ranked_findings
            ],
        }
        return _canonical_json(payload)

    @property
    def evidence_sha256(self) -> str:
        """Return SHA-256 of the complete prioritization result."""
        return hashlib.sha256(self.canonical_json).hexdigest()

    @property
    def prioritization_id(self) -> str:
        """Return content-addressed identity for the complete ranking."""
        return f"risk-prioritization:v1@sha256:{self.evidence_sha256}"


def _canonical_json(payload: dict[str, object]) -> bytes:
    """Serialize one JSON object deterministically."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
