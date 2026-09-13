#!/usr/bin/env python3
"""Verify the deterministic offline Gate 19.10 demo runner contract."""

import json
from pathlib import Path
from typing import cast

from opslens.demo import (
    DEMO_RESULT_CONTRACT_VERSION,
    MATERIAL_VULNERABILITY_SCENARIO_ID,
    DemoContractError,
    build_material_vulnerability_demo,
)
from opslens.demo.cli import render_demo, run_demo

type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "labs/evidence/phase-19-gate-19-10-demo-runner-v1.json"
LAB_PATH = ROOT / "labs/phase-19-gate-19-10-demo-runner.md"
DEMO_PATHS = (
    ROOT / "src/opslens/demo/__init__.py",
    ROOT / "src/opslens/demo/material_vulnerability.py",
    ROOT / "src/opslens/demo/cli.py",
    ROOT / "scripts/demo_opslens.py",
)

EXPECTED_MAIN_SHA = "68a135a0c80dacb8cf0b668022796b159878637e"
EXPECTED_CODEQL_RUN_ID = 34715722016


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
    """Verify frozen issue/checkpoint/authority facts without provider access."""
    evidence = _load_json(EVIDENCE_PATH)
    assert evidence["schema_version"] == "opslens.phase19.gate19_10.demo_runner.v1"
    assert evidence["phase"] == 19
    assert evidence["gate"] == "19.10"
    assert evidence["issue"] == 378
    assert evidence["source_protected_main_sha"] == EXPECTED_MAIN_SHA
    assert evidence["decision"] == "IMPLEMENT_CANONICAL_OFFLINE_DEMO_RUNNER"

    gate_19_9 = _object(evidence["gate_19_9"], field="gate_19_9")
    assert gate_19_9["issue"] == 376
    assert gate_19_9["pull_request"] == 377
    assert gate_19_9["merge_sha"] == EXPECTED_MAIN_SHA
    assert gate_19_9["post_merge_codeql_run_id"] == EXPECTED_CODEQL_RUN_ID
    assert gate_19_9["post_merge_codeql_conclusion"] == "success"

    scenario = _object(evidence["scenario"], field="scenario")
    assert scenario["id"] == MATERIAL_VULNERABILITY_SCENARIO_ID
    assert scenario["expected_finding_count"] == 1
    assert scenario["expected_priority_score"] == 90
    assert scenario["expected_priority_tier"] == "P0"

    required = _object(evidence["required_properties"], field="required_properties")
    assert required["aws_credentials_required"] is False
    assert required["network_after_dependency_installation"] is False
    assert required["live_provider_execution"] is False
    assert required["model_execution"] is False
    assert required["third_party_repository_code_execution"] is False
    assert required["stable_json_output"] is True
    assert required["human_readable_output"] is True
    assert required["invalid_inputs_fail_closed"] is True

    authority = _object(evidence["authority_impact"], field="authority_impact")
    assert all(
        isinstance(value, int) and not isinstance(value, bool) and value == 0
        for value in authority.values()
    )


def _verify_runner() -> None:
    """Prove determinism and retained authority composition using the frozen fixture."""
    first = build_material_vulnerability_demo()
    second = build_material_vulnerability_demo()

    assert first.canonical_json == second.canonical_json
    assert first.evidence_sha256 == second.evidence_sha256
    assert first.result_id == second.result_id
    assert first.scenario_id == MATERIAL_VULNERABILITY_SCENARIO_ID
    assert first.repository_analysis.analysis.finding_count == 1

    evaluation = first.prioritization.ranked_findings[0].evaluation
    assert evaluation.priority_score == 90
    assert evaluation.priority_tier.value == "P0"
    assert evaluation.review_required is False

    payload = cast(JsonValue, json.loads(first.canonical_json.decode("utf-8")))
    root = _object(payload, field="demo_result")
    assert root["contract_version"] == DEMO_RESULT_CONTRACT_VERSION
    authority = _object(root["authority"], field="demo_result.authority")
    assert authority["mode"] == "OFFLINE_DETERMINISTIC"
    assert authority["network_access"] is False
    assert authority["live_provider_execution"] is False
    assert authority["model_execution"] is False
    assert authority["third_party_repository_code_execution"] is False

    text = render_demo(first, "text")
    assert "priority: P0 (90/100)" in text
    assert first.result_id in text
    assert render_demo(first, "json") == first.canonical_json.decode("utf-8") + "\n"

    try:
        run_demo("unknown-scenario")
    except DemoContractError:
        pass
    else:
        raise AssertionError("unsupported demo scenario did not fail closed")

    try:
        render_demo(first, "yaml")
    except DemoContractError:
        pass
    else:
        raise AssertionError("unsupported demo output format did not fail closed")


def _verify_no_provider_or_process_execution_surface() -> None:
    """Reject accidental network/provider/process execution in the canonical demo surface."""
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
    """Run every offline Gate 19.10 verification and print the content-addressed result."""
    _verify_contract_artifact()
    _verify_runner()
    _verify_no_provider_or_process_execution_surface()

    lab = LAB_PATH.read_text(encoding="utf-8")
    for marker in (
        "material-vulnerability",
        "PublicRepositoryEvidenceExecution",
        "RepositoryAnalysisResult",
        "Risk Policy v1",
        "READ, NEVER EXECUTE third-party repository code.",
    ):
        assert marker in lab, marker

    result = build_material_vulnerability_demo()
    print(f"Gate 19.10 deterministic demo runner verification: PASS {result.result_id}")


if __name__ == "__main__":
    main()
