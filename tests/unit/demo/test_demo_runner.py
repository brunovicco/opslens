"""Tests for the deterministic offline OpsLens V1 demonstration runner."""

from __future__ import annotations

import json
from typing import cast

import pytest

from opslens.demo import (
    DEMO_RESULT_CONTRACT_VERSION,
    MATERIAL_VULNERABILITY_SCENARIO_ID,
    DemoContractError,
    build_material_vulnerability_demo,
)
from opslens.demo.cli import main, render_demo, run_demo


def _object(value: object) -> dict[str, object]:
    """Require one JSON object in test projections."""
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def test_material_vulnerability_demo_is_deterministic() -> None:
    """Two offline executions must produce byte-identical content-addressed results."""
    first = build_material_vulnerability_demo()
    second = build_material_vulnerability_demo()

    assert first.canonical_json == second.canonical_json
    assert first.evidence_sha256 == second.evidence_sha256
    assert first.result_id == second.result_id
    assert first.to_text() == second.to_text()
    assert first.repository_analysis.analysis.finding_count == 1

    evaluation = first.prioritization.ranked_findings[0].evaluation
    assert evaluation.priority_score == 90
    assert evaluation.priority_tier.value == "P0"
    assert evaluation.review_required is False


def test_json_projection_exposes_authority_and_provenance() -> None:
    """JSON output must distinguish deterministic fixture authority from provider/model work."""
    result = build_material_vulnerability_demo()
    payload = _object(json.loads(result.canonical_json))

    assert payload["contract_version"] == DEMO_RESULT_CONTRACT_VERSION
    scenario = _object(payload["scenario"])
    assert scenario["id"] == MATERIAL_VULNERABILITY_SCENARIO_ID
    assert scenario["source_kind"] == "offline_synthetic_fixture"

    authority = _object(payload["authority"])
    assert authority == {
        "aws_credentials_required": False,
        "live_provider_execution": False,
        "mode": "OFFLINE_DETERMINISTIC",
        "model_execution": False,
        "network_access": False,
        "third_party_repository_code_execution": False,
    }

    summary = _object(payload["summary"])
    assert summary["dependency"] == "requests"
    assert summary["installed_version"] == "2.31.0"
    assert summary["cve_id"] == "CVE-2026-12345"
    assert summary["fixed_version"] == "2.32.0"
    assert summary["priority_tier"] == "P0"

    identities = _object(payload["identities"])
    assert str(identities["repository_execution_id"]).startswith(
        "public-repository-evidence:v1@sha256:"
    )
    assert str(identities["repository_analysis_id"]).startswith(
        "repository-analysis:v1@sha256:"
    )
    assert str(identities["risk_policy_id"]).startswith("risk-policy:v1@sha256:")


def test_text_and_json_render_the_same_admitted_result() -> None:
    """Human and machine formats must project the same deterministic result."""
    result = build_material_vulnerability_demo()
    text = render_demo(result, "text")
    json_output = render_demo(result, "json")

    assert "OpsLens V1 deterministic offline demo" in text
    assert "priority: P0 (90/100)" in text
    assert result.result_id in text

    payload = _object(json.loads(json_output))
    summary = _object(payload["summary"])
    assert summary["priority_score"] == 90
    assert summary["priority_tier"] == "P0"


def test_run_demo_fails_closed_for_unknown_scenario() -> None:
    """Programmatic dispatch must never silently coerce unsupported scenarios."""
    with pytest.raises(DemoContractError, match="unsupported demo scenario"):
        run_demo("unknown-scenario")


def test_render_demo_fails_closed_for_unknown_format() -> None:
    """Programmatic rendering must reject unsupported output formats."""
    result = build_material_vulnerability_demo()
    with pytest.raises(DemoContractError, match="unsupported demo output format"):
        render_demo(result, "yaml")


def test_cli_json_output_is_stable(capsys: pytest.CaptureFixture[str]) -> None:
    """The canonical CLI must emit stable JSON and return success offline."""
    assert main(["--scenario", MATERIAL_VULNERABILITY_SCENARIO_ID, "--format", "json"]) == 0
    first = capsys.readouterr().out
    assert main(["--scenario", MATERIAL_VULNERABILITY_SCENARIO_ID, "--format", "json"]) == 0
    second = capsys.readouterr().out

    assert first == second
    payload = _object(json.loads(first))
    assert payload["contract_version"] == DEMO_RESULT_CONTRACT_VERSION


def test_cli_rejects_unknown_scenario() -> None:
    """Argparse admission must return a non-zero exit for unknown scenario identities."""
    with pytest.raises(SystemExit) as exc_info:
        main(["--scenario", "unknown-scenario"])
    assert exc_info.value.code == 2
