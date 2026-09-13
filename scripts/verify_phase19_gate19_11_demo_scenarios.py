#!/usr/bin/env python3
"""Verify the deterministic offline Gate 19.11 demo-scenario contract."""

import json
from pathlib import Path
from typing import cast

from opslens.demo import (
    CONTROLLED_BENIGN_SCENARIO_ID,
    FAIL_CLOSED_SCENARIO_ID,
    MATERIAL_VULNERABILITY_SCENARIO_ID,
    build_controlled_benign_demo,
    build_demo_suite_evaluation,
    build_fail_closed_incomplete_evidence_demo,
    build_material_vulnerability_demo,
)

type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "labs/evidence/phase-19-gate-19-11-demo-scenarios-v1.json"
LAB_PATH = ROOT / "labs/phase-19-gate-19-11-demo-scenarios.md"
SCENARIOS_DOC_PATH = ROOT / "docs/demo/SCENARIOS.md"
DEMO_PATHS = (
    ROOT / "src/opslens/demo/material_vulnerability.py",
    ROOT / "src/opslens/demo/controlled_benign.py",
    ROOT / "src/opslens/demo/fail_closed.py",
    ROOT / "src/opslens/demo/evaluation.py",
    ROOT / "src/opslens/demo/cli.py",
    ROOT / "scripts/demo_opslens.py",
    ROOT / "scripts/evaluate_opslens_demo.py",
)

EXPECTED_MAIN_SHA = "50456d304e7847fadd0d29373079afa1669acc9d"
EXPECTED_CODEQL_RUN_ID = 34716596100
EXPECTED_SCENARIOS = [
    MATERIAL_VULNERABILITY_SCENARIO_ID,
    CONTROLLED_BENIGN_SCENARIO_ID,
    FAIL_CLOSED_SCENARIO_ID,
]


def _load_json(path: Path) -> dict[str, JsonValue]:
    payload = cast(JsonValue, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(payload, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return payload


def _object(value: JsonValue, *, field: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise AssertionError(f"{field} must be an object")
    return value


def _verify_contract_artifact() -> None:
    """Verify frozen source checkpoint and zero-authority-impact facts."""
    evidence = _load_json(EVIDENCE_PATH)
    assert evidence["schema_version"] == "opslens.phase19.gate19_11.demo_scenarios.v1"
    assert evidence["phase"] == 19
    assert evidence["gate"] == "19.11"
    assert evidence["issue"] == 380
    assert evidence["source_protected_main_sha"] == EXPECTED_MAIN_SHA
    assert evidence["decision"] == "ADMIT_THREE_CANONICAL_OFFLINE_SCENARIOS"
    assert evidence["canonical_scenario_ids"] == EXPECTED_SCENARIOS

    gate_19_10 = _object(evidence["gate_19_10"], field="gate_19_10")
    assert gate_19_10["issue"] == 378
    assert gate_19_10["pull_request"] == 379
    assert gate_19_10["merge_sha"] == EXPECTED_MAIN_SHA
    assert gate_19_10["post_merge_codeql_run_id"] == EXPECTED_CODEQL_RUN_ID
    assert gate_19_10["post_merge_codeql_run_number"] == 421
    assert gate_19_10["post_merge_codeql_conclusion"] == "success"

    required = _object(evidence["required_properties"], field="required_properties")
    assert required["scenario_count"] == 3
    assert required["network_after_dependency_installation"] is False
    assert required["live_provider_execution"] is False
    assert required["model_execution"] is False
    assert required["third_party_repository_code_execution"] is False
    assert required["stable_json_output"] is True
    assert required["human_readable_output"] is True
    assert required["missing_evidence_not_benign"] is True
    assert required["controlled_benign_uses_complete_scoped_evidence"] is True
    assert required["fail_closed_precedes_risk_prioritization"] is True

    authority = _object(evidence["authority_impact"], field="authority_impact")
    assert all(
        isinstance(value, int) and not isinstance(value, bool) and value == 0
        for value in authority.values()
    )


def _verify_three_scenarios() -> None:
    """Prove repeatability and the distinction between no-finding and incomplete evidence."""
    material_a = build_material_vulnerability_demo()
    material_b = build_material_vulnerability_demo()
    assert material_a.canonical_json == material_b.canonical_json
    assert material_a.repository_analysis.analysis.finding_count == 1
    material_risk = material_a.prioritization.ranked_findings[0].evaluation
    assert material_risk.priority_score == 90
    assert material_risk.priority_tier.value == "P0"

    benign_a = build_controlled_benign_demo()
    benign_b = build_controlled_benign_demo()
    assert benign_a.canonical_json == benign_b.canonical_json
    assert benign_a.repository_analysis.analysis.finding_count == 0
    assert benign_a.prioritization.ranked_findings == ()
    assert benign_a.source_execution.normalization_inventory.unsupported_normalization == ()
    assert benign_a.threat_scope.dependencies
    benign_payload = _object(
        cast(JsonValue, json.loads(benign_a.canonical_json.decode("utf-8"))),
        field="controlled_benign",
    )
    benign_outcome = _object(benign_payload["outcome"], field="controlled_benign.outcome")
    assert benign_outcome["scoped_evidence_complete"] is True
    assert benign_outcome["live_repository_safety_claim"] is False

    fail_a = build_fail_closed_incomplete_evidence_demo()
    fail_b = build_fail_closed_incomplete_evidence_demo()
    assert fail_a.canonical_json == fail_b.canonical_json
    assert fail_a.source_execution.normalization_inventory.normalized_dependencies == ()
    unsupported = fail_a.source_execution.normalization_inventory.unsupported_normalization
    assert len(unsupported) == 1
    assert unsupported[0].reason_code == "invalid_version"
    fail_payload = _object(
        cast(JsonValue, json.loads(fail_a.canonical_json.decode("utf-8"))),
        field="fail_closed",
    )
    fail_outcome = _object(fail_payload["outcome"], field="fail_closed.outcome")
    assert fail_outcome["analysis_performed"] is False
    assert fail_outcome["risk_prioritization_performed"] is False
    assert fail_outcome["benign_conclusion"] is False
    assert fail_outcome["missing_evidence_treated_as_benign"] is False


def _verify_suite_evaluation() -> None:
    """Prove byte-stable cross-scenario evaluation with no added truth authority."""
    first = build_demo_suite_evaluation()
    second = build_demo_suite_evaluation()
    assert first.canonical_json == second.canonical_json
    assert first.evaluation_id == second.evaluation_id

    payload = _object(
        cast(JsonValue, json.loads(first.canonical_json.decode("utf-8"))),
        field="suite",
    )
    assert payload["scenario_count"] == 3
    assert payload["scenario_order"] == EXPECTED_SCENARIOS
    assertions = _object(payload["assertions"], field="suite.assertions")
    assert assertions["controlled_no_finding_requires_complete_scoped_evidence"] is True
    assert assertions["controlled_no_finding_is_fixture_scoped"] is True
    assert assertions["missing_evidence_is_not_benign"] is True
    assert assertions["fail_closed_precedes_risk_prioritization"] is True
    assert assertions["model_has_no_business_truth_authority"] is True


def _verify_no_provider_or_process_execution_surface() -> None:
    """Reject accidental network/provider/process execution in the demo surface."""
    forbidden_markers = (
        "import " + "boto3",
        "from " + "boto3",
        "import " + "subprocess",
        "from " + "subprocess",
        "import " + "socket",
        "urllib" + ".request",
        "httpx" + ".",
        "requests" + ".get(",
        "requests" + ".post(",
        "os" + ".system(",
    )
    for path in DEMO_PATHS:
        source = path.read_text(encoding="utf-8")
        for marker in forbidden_markers:
            assert marker not in source, f"{path} contains forbidden execution marker {marker}"


def main() -> None:
    """Run every offline Gate 19.11 verification."""
    _verify_contract_artifact()
    _verify_three_scenarios()
    _verify_suite_evaluation()
    _verify_no_provider_or_process_execution_surface()

    documentation = LAB_PATH.read_text(encoding="utf-8") + SCENARIOS_DOC_PATH.read_text(
        encoding="utf-8"
    )
    for marker in (
        "material-vulnerability",
        "controlled-benign",
        "fail-closed-incomplete-evidence",
        "missing evidence != benign evidence",
        "controlled fixture only",
        "READ, NEVER EXECUTE third-party repository code.",
    ):
        assert marker in documentation, marker

    evaluation = build_demo_suite_evaluation()
    print(f"Gate 19.11 demo scenario verification: PASS {evaluation.evaluation_id}")


if __name__ == "__main__":
    main()
