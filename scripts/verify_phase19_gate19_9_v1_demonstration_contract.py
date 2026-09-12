#!/usr/bin/env python3
"""Verify the offline Gate 19.9 V1 demonstration contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "labs/evidence/phase-19-gate-19-9-v1-demonstration-contract-v1.json"
LAB_PATH = ROOT / "labs/phase-19-gate-19-9-v1-demonstration-contract.md"
ADR_PATH = ROOT / "docs/adr/0077-phase19-v1-demonstration-boundary.md"

EXPECTED_MAIN_SHA = "e538fa3e96c29cf76dd3aa83a9967e090587b6fb"
EXPECTED_CODEQL_RUN_ID = 34713360403
EXPECTED_GATES = [
    "19.9_v1_contract_and_sync",
    "19.10_deterministic_demo_runner",
    "19.11_curated_scenarios_and_evaluation",
    "19.12_local_visual_demo",
    "19.13_portfolio_polish",
    "19.14_v1_closeout_and_release_readiness",
]
EXPECTED_SCENARIOS = [
    "material_vulnerability",
    "controlled_benign",
    "fail_closed_incomplete_or_ambiguous_evidence",
]


def _load_json(path: Path) -> dict[str, JsonValue]:
    payload = cast(JsonValue, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(payload, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return payload


def _require_object(value: JsonValue, *, field: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise AssertionError(f"{field} must be an object")
    return value


def main() -> None:
    """Verify deterministic Gate 19.9 contract facts without provider access."""
    evidence = _load_json(EVIDENCE_PATH)
    lab = LAB_PATH.read_text(encoding="utf-8")
    adr = ADR_PATH.read_text(encoding="utf-8")

    assert evidence["schema_version"] == "opslens.phase19.gate19_9.v1_demonstration_contract.v1"
    assert evidence["phase"] == 19
    assert evidence["gate"] == "19.9"
    assert evidence["source_protected_main_sha"] == EXPECTED_MAIN_SHA

    gate_19_8 = _require_object(evidence["gate_19_8"], field="gate_19_8")
    assert gate_19_8["issue"] == 374
    assert gate_19_8["pull_request"] == 375
    assert gate_19_8["merge_sha"] == EXPECTED_MAIN_SHA
    assert gate_19_8["post_merge_codeql_run_id"] == EXPECTED_CODEQL_RUN_ID
    assert gate_19_8["post_merge_codeql_conclusion"] == "success"

    assert evidence["v1_product_mode"] == "DEMONSTRATION_ARCHITECTURE_LAB"
    assert evidence["required_completion_gates"] == EXPECTED_GATES
    assert evidence["required_demo_scenarios"] == EXPECTED_SCENARIOS

    authority = _require_object(evidence["authority_impact"], field="authority_impact")
    assert all(
        isinstance(value, int) and not isinstance(value, bool) and value == 0
        for value in authority.values()
    )

    required_markers = (
        "demonstration and architecture lab",
        "Gate 19.10  deterministic end-to-end demo runner",
        "Gate 19.14  V1 closeout + release readiness",
        "materialized != enabled",
        "demonstration readiness != production readiness",
    )
    for marker in required_markers:
        assert marker in lab or marker in adr, marker

    verifier_source = Path(__file__).read_text(encoding="utf-8")
    forbidden_provider_markers = (
        "import " + "boto3",
        "boto3" + ".client(",
    )
    for marker in forbidden_provider_markers:
        assert marker not in verifier_source, marker

    print("Gate 19.9 V1 demonstration contract verification: PASS")


if __name__ == "__main__":
    main()
