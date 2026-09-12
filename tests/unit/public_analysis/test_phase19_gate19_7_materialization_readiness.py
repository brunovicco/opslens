"""Fail-closed tests for Gate 19.7 disabled materialization readiness."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import cast

CONTRACT = Path("labs/evidence/phase-19-gate-19-7-materialization-contract-v1.json")
CONTRACT_VERIFIER = Path("scripts/verify_phase19_gate19_7_materialization_contract.py")
FRESH_PLAN_VERIFIER = Path("scripts/verify_phase19_gate19_7_fresh_plan.py")
PLAN_FIXTURE = Path("tests/fixtures/phase19/gate19-6-exact-plan-pass.json")


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _load(path: Path) -> dict[str, object]:
    raw = cast(object, json.loads(path.read_text(encoding="utf-8")))
    assert isinstance(raw, dict)
    return cast(dict[str, object], raw)


def test_gate19_7_materialization_contract_verifier_passes_offline() -> None:
    result = subprocess.run(
        [sys.executable, str(CONTRACT_VERIFIER)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "phase19_gate19_7_contract=PASS" in result.stdout
    assert "terraform_apply_authorized=false" in result.stdout
    assert "human_apply_authorization_required=true" in result.stdout


def test_gate19_7_materialization_contract_freezes_authority() -> None:
    contract = _load(CONTRACT)

    assert contract["artifact_type"] == "phase-19-gate-19-7-materialization-contract:v1"
    assert contract["preparation_source_main_sha"] == (
        "99954adbdaa071414d16cd1bf02a465187ec728d"
    )
    assert contract["gate19_6_closeout_sha"] == (
        "c76432dfcd97110ca43d91d77084f4367b9a89fd"
    )

    fresh_plan = contract["fresh_plan"]
    assert isinstance(fresh_plan, dict)
    typed_fresh_plan = cast(dict[str, object], fresh_plan)
    assert typed_fresh_plan["required"] is True
    assert typed_fresh_plan["reuse_gate19_6_binary_plan_for_apply"] is False
    assert typed_fresh_plan["expected_managed_create_count"] == 21

    invariants = contract["materialization_invariants"]
    assert isinstance(invariants, dict)
    assert cast(dict[str, object], invariants) == {
        "public_async_runtime_materialized_for_plan": True,
        "execute_api_endpoint_disabled": True,
        "submit_enabled": False,
        "worker_enabled": False,
        "worker_event_source_enabled": False,
        "worker_reserved_concurrency": 0,
        "custom_public_domain_present": False,
        "provider_heavy_worker_executor_composed": False,
    }

    authority = contract["authority"]
    assert isinstance(authority, dict)
    typed_authority = cast(dict[str, object], authority)
    assert typed_authority["terraform_apply_authorized"] is False
    assert typed_authority["explicit_human_apply_authorization_required"] is True
    assert typed_authority["apply_command_present_in_preparation_runbook"] is False
    assert typed_authority["runtime_enablement_authorized"] is False


def test_gate19_7_fresh_plan_binds_binary_hash_and_source_head(tmp_path: Path) -> None:
    plan_binary = tmp_path / "opslens-gate19-7.tfplan"
    plan_binary.write_bytes(b"synthetic-gate19-7-plan-binary\n")
    output = tmp_path / "admission.json"
    source_head = _head()

    result = subprocess.run(
        [
            sys.executable,
            str(FRESH_PLAN_VERIFIER),
            "--plan-json",
            str(PLAN_FIXTURE),
            "--plan-binary",
            str(plan_binary),
            "--expected-source-head",
            source_head,
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "phase19_gate19_7_plan=PASS" in result.stdout
    assert "terraform_apply_authorized=false" in result.stdout
    assert "human_apply_authorization_required=true" in result.stdout

    evidence = _load(output)
    assert evidence["artifact_type"] == "phase-19-gate-19-7-fresh-plan-admission:v1"
    assert evidence["source_head_sha"] == source_head
    assert evidence["plan_binary_sha256"] == hashlib.sha256(
        plan_binary.read_bytes()
    ).hexdigest()
    assert evidence["managed_create_count"] == 21

    authority = evidence["authority"]
    assert isinstance(authority, dict)
    assert cast(dict[str, object], authority) == {
        "fresh_plan": True,
        "retained_gate19_6_exact_plan_engine_pass": True,
        "gate19_6_binary_plan_reuse_forbidden": True,
        "materialized_not_enabled": True,
        "explicit_human_apply_authorization_required": True,
        "terraform_apply_authorized": False,
        "apply_authorization_status": "PENDING_EXPLICIT_HUMAN_AUTHORIZATION",
    }


def test_gate19_7_fresh_plan_rejects_unreviewed_source_head(tmp_path: Path) -> None:
    plan_binary = tmp_path / "opslens-gate19-7.tfplan"
    plan_binary.write_bytes(b"synthetic-gate19-7-plan-binary\n")

    result = subprocess.run(
        [
            sys.executable,
            str(FRESH_PLAN_VERIFIER),
            "--plan-json",
            str(PLAN_FIXTURE),
            "--plan-binary",
            str(plan_binary),
            "--expected-source-head",
            "0000000000000000000000000000000000000000",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "differs from reviewed source" in result.stderr
