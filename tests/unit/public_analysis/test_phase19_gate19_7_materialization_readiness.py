"""Fail-closed tests for Gate 19.7 disabled materialization readiness."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import cast

CONTRACT = Path("labs/evidence/phase-19-gate-19-7-materialization-contract-v1.json")
RECOVERY_CONTRACT = Path(
    "labs/evidence/phase-19-gate-19-7-recovery-contract-v1.json"
)
RECONCILIATION = Path(
    "labs/evidence/phase-19-gate-19-7-failed-apply-reconciliation-v1.json"
)
CONTRACT_VERIFIER = Path("scripts/verify_phase19_gate19_7_materialization_contract.py")
FRESH_PLAN_VERIFIER = Path("scripts/verify_phase19_gate19_7_fresh_plan.py")
PLAN_FIXTURE = Path("tests/fixtures/phase19/gate19-6-exact-plan-pass.json")
RECOVERY_PLAN_FIXTURE = Path(
    "tests/fixtures/phase19/gate19-7-recovery-plan-pass.json"
)
RUNTIME_TF = Path("infra/environments/dev/public_async_runtime.tf")


def _head() -> str:
    """Resolve the exact repository HEAD used by the test process."""
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _load(path: Path) -> dict[str, object]:
    """Load a JSON object from the repository or temporary evidence path."""
    raw = cast(object, json.loads(path.read_text(encoding="utf-8")))
    assert isinstance(raw, dict)
    return cast(dict[str, object], raw)


def test_gate19_7_materialization_contract_verifier_passes_offline() -> None:
    """Require the frozen Gate 19.7 authority contract to verify offline."""
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
    """Freeze source lineage, disabled controls, and absent apply authority."""
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
    """Bind fresh-plan admission to both the saved plan bytes and source HEAD."""
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
    """Reject a plan when the caller supplies a source SHA other than HEAD."""
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


def test_gate19_7_recovery_contract_freezes_partial_state_and_authority() -> None:
    """Freeze the failed-plan quarantine and exact partial-state recovery boundary."""
    contract = _load(RECOVERY_CONTRACT)
    reconciliation = _load(RECONCILIATION)

    assert contract["artifact_type"] == "phase-19-gate-19-7-recovery-contract:v1"
    assert reconciliation["artifact_type"] == (
        "phase-19-gate-19-7-failed-apply-reconciliation:v1"
    )

    failed_apply = contract["failed_apply"]
    assert isinstance(failed_apply, dict)
    typed_failed_apply = cast(dict[str, object], failed_apply)
    assert typed_failed_apply["failed_plan_reusable"] is False
    assert typed_failed_apply["retry_authorized"] is False
    assert typed_failed_apply["requested_reserved_concurrency"] == 2
    assert typed_failed_apply["account_concurrent_executions_limit"] == 10

    partial_state = contract["partial_state"]
    assert isinstance(partial_state, dict)
    typed_partial_state = cast(dict[str, object], partial_state)
    assert typed_partial_state["expected_managed_resource_count"] == 21
    assert typed_partial_state["managed_expected_resource_count"] == 16
    assert typed_partial_state["missing_managed_create_count"] == 5

    recovery_design = contract["recovery_design"]
    assert isinstance(recovery_design, dict)
    typed_recovery_design = cast(dict[str, object], recovery_design)
    assert typed_recovery_design["api_reserved_concurrency"] == 0
    assert typed_recovery_design["worker_reserved_concurrency"] == 0
    assert typed_recovery_design["maximum_existing_resource_update_count"] == 1

    authority = contract["plan_authority"]
    assert isinstance(authority, dict)
    typed_authority = cast(dict[str, object], authority)
    assert typed_authority["fresh_human_plan_required"] is True
    assert typed_authority["failed_binary_plan_reuse_forbidden"] is True
    assert typed_authority["terraform_apply_authorized"] is False
    assert typed_authority["runtime_enablement_authorized"] is False


def test_gate19_7_recovery_source_hard_disables_api_lambda() -> None:
    """Require the live API Lambda resource to use zero reserved concurrency."""
    runtime_tf = RUNTIME_TF.read_text(encoding="utf-8")
    start = runtime_tf.index('resource "aws_lambda_function" "public_async_api"')
    end = runtime_tf.index('resource "aws_lambda_function" "public_async_worker"')
    api_segment = runtime_tf[start:end]

    assert "reserved_concurrent_executions = 0" in api_segment
    assert "reserved_concurrent_executions = 2" not in api_segment
    assert 'OPSLENS_ASYNC_SUBMIT_ENABLED           = "false"' in api_segment
    assert 'output "public_async_api_reserved_concurrency"' in runtime_tf


def test_gate19_7_recovery_plan_binds_new_binary_and_partial_state(
    tmp_path: Path,
) -> None:
    """Admit only the five missing creates plus the bounded API hard-disable update."""
    plan_binary = tmp_path / "opslens-gate19-7-recovery.tfplan"
    plan_binary.write_bytes(b"synthetic-gate19-7-recovery-plan-binary\n")
    output = tmp_path / "recovery-admission.json"
    source_head = _head()

    result = subprocess.run(
        [
            sys.executable,
            str(FRESH_PLAN_VERIFIER),
            "--recovery",
            "--plan-json",
            str(RECOVERY_PLAN_FIXTURE),
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
    assert "phase19_gate19_7_recovery_plan=PASS" in result.stdout
    assert "managed_creates=5" in result.stdout
    assert "managed_updates=1" in result.stdout
    assert "api_reserved_concurrency=0" in result.stdout
    assert "terraform_apply_authorized=false" in result.stdout

    evidence = _load(output)
    assert evidence["artifact_type"] == (
        "phase-19-gate-19-7-recovery-plan-admission:v1"
    )
    assert evidence["source_head_sha"] == source_head
    assert evidence["managed_create_count"] == 5
    assert evidence["managed_update_count"] == 1
    assert evidence["plan_binary_sha256"] == hashlib.sha256(
        plan_binary.read_bytes()
    ).hexdigest()

    recovery = evidence["recovery"]
    assert isinstance(recovery, dict)
    typed_recovery = cast(dict[str, object], recovery)
    assert typed_recovery["previous_failed_plan_reusable"] is False
    assert typed_recovery["previous_failed_plan_retry_authorized"] is False
    assert typed_recovery["api_reserved_concurrency"] == 0

    authority = evidence["authority"]
    assert isinstance(authority, dict)
    typed_authority = cast(dict[str, object], authority)
    assert typed_authority["terraform_apply_authorized"] is False
    assert typed_authority["materialized_not_enabled"] is True


def test_gate19_7_recovery_rejects_historical_full_create_plan(tmp_path: Path) -> None:
    """Reject reuse of the historical 21-create plan through the recovery mode."""
    plan_binary = tmp_path / "old-plan.tfplan"
    plan_binary.write_bytes(b"historical-plan-must-not-be-reused\n")

    result = subprocess.run(
        [
            sys.executable,
            str(FRESH_PLAN_VERIFIER),
            "--recovery",
            "--plan-json",
            str(PLAN_FIXTURE),
            "--plan-binary",
            str(plan_binary),
            "--expected-source-head",
            _head(),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert (
        "recovery safety output public_async_api_reserved_concurrency"
        in result.stderr
        or "recovery create inventory mismatch" in result.stderr
    )
