"""Deterministic evaluation over the three canonical OpsLens V1 demo scenarios."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256

from opslens.demo.controlled_benign import (
    CONTROLLED_BENIGN_SCENARIO_ID,
    ControlledBenignDemoResult,
    build_controlled_benign_demo,
)
from opslens.demo.fail_closed import (
    FAIL_CLOSED_SCENARIO_ID,
    FailClosedDemoResult,
    build_fail_closed_incomplete_evidence_demo,
)
from opslens.demo.material_vulnerability import (
    MATERIAL_VULNERABILITY_SCENARIO_ID,
    DemoContractError,
    DemoRunResult,
    build_material_vulnerability_demo,
)

type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None

DEMO_SUITE_EVALUATION_CONTRACT_VERSION = "opslens-demo-suite-evaluation:v1"


def _canonical_json(value: object) -> bytes:
    """Serialize one deterministic suite evaluation."""
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class DemoSuiteEvaluation:
    """Content-addressed evaluation over the three V1 demonstration outcomes."""

    material: DemoRunResult
    controlled_benign: ControlledBenignDemoResult
    fail_closed: FailClosedDemoResult

    def __post_init__(self) -> None:
        """Require the three scenarios to demonstrate distinct authority outcomes."""
        analysis = self.material.repository_analysis.analysis
        evaluation = self.material.prioritization.ranked_findings[0].evaluation
        if analysis.finding_count != 1:
            raise DemoContractError("suite material scenario must retain one finding")
        if evaluation.priority_score != 90 or evaluation.priority_tier.value != "P0":
            raise DemoContractError("suite material scenario risk result drifted")

        benign_analysis = self.controlled_benign.repository_analysis.analysis
        if benign_analysis.finding_count != 0:
            raise DemoContractError("suite controlled-benign scenario must have zero findings")
        benign_inventory = self.controlled_benign.source_execution.normalization_inventory
        if benign_inventory.unsupported_normalization:
            raise DemoContractError(
                "suite controlled-benign scenario requires complete dependency identity"
            )
        if not self.controlled_benign.threat_scope.dependencies:
            raise DemoContractError(
                "suite controlled-benign scenario requires admitted threat scope"
            )

        fail_inventory = self.fail_closed.source_execution.normalization_inventory
        if not fail_inventory.unsupported_normalization:
            raise DemoContractError(
                "suite fail-closed scenario must retain incomplete dependency evidence"
            )

    @property
    def canonical_payload(self) -> dict[str, JsonValue]:
        """Return stable suite evidence without introducing new business authority."""
        material_evaluation = self.material.prioritization.ranked_findings[0].evaluation
        return {
            "contract_version": DEMO_SUITE_EVALUATION_CONTRACT_VERSION,
            "scenario_count": 3,
            "scenario_order": [
                MATERIAL_VULNERABILITY_SCENARIO_ID,
                CONTROLLED_BENIGN_SCENARIO_ID,
                FAIL_CLOSED_SCENARIO_ID,
            ],
            "scenarios": {
                MATERIAL_VULNERABILITY_SCENARIO_ID: {
                    "state": "MATERIAL_FINDING",
                    "finding_count": 1,
                    "priority_score": material_evaluation.priority_score,
                    "priority_tier": material_evaluation.priority_tier.value,
                    "result_id": self.material.result_id,
                },
                CONTROLLED_BENIGN_SCENARIO_ID: {
                    "state": "NO_MATERIAL_FINDING",
                    "finding_count": 0,
                    "scoped_evidence_complete": True,
                    "live_repository_safety_claim": False,
                    "result_id": self.controlled_benign.result_id,
                },
                FAIL_CLOSED_SCENARIO_ID: {
                    "state": "REJECTED_INCOMPLETE_EVIDENCE",
                    "analysis_performed": False,
                    "risk_prioritization_performed": False,
                    "benign_conclusion": False,
                    "result_id": self.fail_closed.result_id,
                },
            },
            "assertions": {
                "controlled_no_finding_requires_complete_scoped_evidence": True,
                "controlled_no_finding_is_fixture_scoped": True,
                "missing_evidence_is_not_benign": True,
                "fail_closed_precedes_risk_prioritization": True,
                "model_has_no_business_truth_authority": True,
                "third_party_repository_code_execution": False,
            },
            "authority": {
                "mode": "OFFLINE_DETERMINISTIC",
                "network_access": False,
                "live_provider_execution": False,
                "model_execution": False,
            },
        }

    @property
    def canonical_json(self) -> bytes:
        """Return byte-stable suite evaluation JSON."""
        return _canonical_json(self.canonical_payload)

    @property
    def evidence_sha256(self) -> str:
        """Return SHA-256 of the exact suite evaluation projection."""
        return sha256(self.canonical_json).hexdigest()

    @property
    def evaluation_id(self) -> str:
        """Return the content-addressed suite evaluation identity."""
        return (
            f"{DEMO_SUITE_EVALUATION_CONTRACT_VERSION}@sha256:"
            f"{self.evidence_sha256}"
        )

    def to_text(self) -> str:
        """Render a concise reviewer comparison of all three authority outcomes."""
        return "\n".join(
            (
                "OpsLens V1 deterministic demo suite evaluation",
                "material-vulnerability: MATERIAL_FINDING / P0 90/100",
                (
                    "controlled-benign: NO_MATERIAL_FINDING / "
                    "complete scoped fixture evidence"
                ),
                (
                    "fail-closed-incomplete-evidence: "
                    "REJECTED_INCOMPLETE_EVIDENCE / no risk result"
                ),
                "assertion: controlled no-finding is fixture-scoped, not a live safety claim",
                "assertion: missing evidence != benign evidence",
                "authority: deterministic facts only; no model/provider execution",
                f"suite evaluation: {self.evaluation_id}",
                "",
            )
        )


def build_demo_suite_evaluation() -> DemoSuiteEvaluation:
    """Execute and evaluate the three canonical offline V1 scenarios."""
    return DemoSuiteEvaluation(
        material=build_material_vulnerability_demo(),
        controlled_benign=build_controlled_benign_demo(),
        fail_closed=build_fail_closed_incomplete_evidence_demo(),
    )


__all__ = [
    "DEMO_SUITE_EVALUATION_CONTRACT_VERSION",
    "DemoSuiteEvaluation",
    "build_demo_suite_evaluation",
]
