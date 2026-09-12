"""Tests for the three canonical deterministic OpsLens V1 demo scenarios."""

from __future__ import annotations

import json
from typing import cast

from opslens.demo import (
    CONTROLLED_BENIGN_SCENARIO_ID,
    FAIL_CLOSED_SCENARIO_ID,
    MATERIAL_VULNERABILITY_SCENARIO_ID,
    build_controlled_benign_demo,
    build_demo_suite_evaluation,
    build_fail_closed_incomplete_evidence_demo,
)
from opslens.demo.cli import render_demo, run_demo


def _object(value: object) -> dict[str, object]:
    """Require one JSON object in test projections."""
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def test_controlled_benign_is_deterministic_complete_and_fixture_scoped() -> None:
    """No-finding truth must come from complete scoped evidence, not missing evidence."""
    first = build_controlled_benign_demo()
    second = build_controlled_benign_demo()

    assert first.canonical_json == second.canonical_json
    assert first.result_id == second.result_id
    assert first.repository_analysis.analysis.finding_count == 0
    assert first.prioritization.ranked_findings == ()
    assert first.source_execution.normalization_inventory.unsupported_normalization == ()
    assert len(first.threat_scope.dependencies) == 1

    payload = _object(json.loads(first.canonical_json))
    outcome = _object(payload["outcome"])
    assert outcome["state"] == "NO_MATERIAL_FINDING"
    assert outcome["scoped_evidence_complete"] is True
    assert outcome["unsupported_normalization_count"] == 0
    assert outcome["benign_claim_scope"] == "controlled_fixture_only"
    assert outcome["live_repository_safety_claim"] is False


def test_fail_closed_rejects_before_analysis_risk_or_benign_truth() -> None:
    """Incomplete identity evidence must stop before any benign or risk conclusion."""
    first = build_fail_closed_incomplete_evidence_demo()
    second = build_fail_closed_incomplete_evidence_demo()

    assert first.canonical_json == second.canonical_json
    assert first.result_id == second.result_id
    inventory = first.source_execution.normalization_inventory
    assert inventory.normalized_dependencies == ()
    assert len(inventory.unsupported_normalization) == 1
    assert inventory.unsupported_normalization[0].reason_code == "invalid_version"

    payload = _object(json.loads(first.canonical_json))
    outcome = _object(payload["outcome"])
    assert outcome["state"] == "REJECTED_INCOMPLETE_EVIDENCE"
    assert outcome["analysis_performed"] is False
    assert outcome["risk_prioritization_performed"] is False
    assert outcome["benign_conclusion"] is False
    assert outcome["missing_evidence_treated_as_benign"] is False


def test_cli_dispatches_exactly_three_canonical_scenarios() -> None:
    """The V1 runner must expose each admitted scenario through one bounded surface."""
    material = run_demo(MATERIAL_VULNERABILITY_SCENARIO_ID)
    benign = run_demo(CONTROLLED_BENIGN_SCENARIO_ID)
    fail_closed = run_demo(FAIL_CLOSED_SCENARIO_ID)

    assert "scenario: material-vulnerability" in render_demo(material, "text")
    assert "scenario: controlled-benign" in render_demo(benign, "text")
    assert "scenario: fail-closed-incomplete-evidence" in render_demo(fail_closed, "text")

    benign_json = _object(json.loads(render_demo(benign, "json")))
    fail_json = _object(json.loads(render_demo(fail_closed, "json")))
    assert _object(benign_json["scenario"])["id"] == CONTROLLED_BENIGN_SCENARIO_ID
    assert _object(fail_json["scenario"])["id"] == FAIL_CLOSED_SCENARIO_ID


def test_suite_evaluation_is_byte_stable_and_preserves_authority_distinctions() -> None:
    """Repeated suite runs must produce identical cross-scenario evidence."""
    first = build_demo_suite_evaluation()
    second = build_demo_suite_evaluation()

    assert first.canonical_json == second.canonical_json
    assert first.evaluation_id == second.evaluation_id

    payload = _object(json.loads(first.canonical_json))
    assert payload["scenario_count"] == 3
    assertions = _object(payload["assertions"])
    assert assertions["controlled_no_finding_requires_complete_scoped_evidence"] is True
    assert assertions["controlled_no_finding_is_fixture_scoped"] is True
    assert assertions["missing_evidence_is_not_benign"] is True
    assert assertions["fail_closed_precedes_risk_prioritization"] is True
    assert assertions["model_has_no_business_truth_authority"] is True
    assert assertions["third_party_repository_code_execution"] is False


def test_suite_text_distinguishes_no_finding_from_incomplete_evidence() -> None:
    """Reviewer output must never collapse controlled no-finding into fail-closed state."""
    text = build_demo_suite_evaluation().to_text()

    assert "controlled-benign: NO_MATERIAL_FINDING" in text
    assert "complete scoped fixture evidence" in text
    assert "REJECTED_INCOMPLETE_EVIDENCE / no risk result" in text
    assert "missing evidence != benign evidence" in text
