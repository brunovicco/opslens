#!/usr/bin/env python3
"""Offline verifier for the Gate 19.7 disabled-materialization authority contract."""

import json
import subprocess
import sys
from pathlib import Path
from typing import cast

_CONTRACT = Path("labs/evidence/phase-19-gate-19-7-materialization-contract-v1.json")
_GATE19_6_ADMISSION = Path("labs/evidence/phase-19-gate-19-6-plan-admission-v1.json")
_GATE19_6_PLAN_INPUT = Path("labs/evidence/phase-19-gate-19-6-plan-input-v1.tfvars.json")
_GATE19_7_PLAN_INPUT = Path("labs/evidence/phase-19-gate-19-7-plan-input-v1.tfvars.json")
_GATE19_4_VERIFIER = Path("scripts/verify_phase19_gate19_4_disabled_async_runtime.py")
_EXPECTED_PREPARATION_SOURCE = "99954adbdaa071414d16cd1bf02a465187ec728d"
_EXPECTED_GATE19_6_CLOSEOUT = "c76432dfcd97110ca43d91d77084f4367b9a89fd"
_EXPECTED_GATE19_6_PLAN_SOURCE = "d4d852c7ebc97f6fd9ee19d868fa12bc4ab031f2"
_EXPECTED_GATE19_6_PLAN_HASH = "eb01396b92879243fd2e16e7791957e3289b459facc9db9524a4d890574aa83f"


class Gate19_7MaterializationContractError(RuntimeError):
    """Raised when the Gate 19.7 materialization contract drifts."""


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise Gate19_7MaterializationContractError(f"{label} must be an object")
    raw = cast(dict[object, object], value)
    if any(type(key) is not str for key in raw):
        raise Gate19_7MaterializationContractError(f"{label} keys must be strings")
    return cast(dict[str, object], raw)


def _strings(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise Gate19_7MaterializationContractError(f"{label} must be an array")
    result: list[str] = []
    for item in cast(list[object], value):
        if type(item) is not str:
            raise Gate19_7MaterializationContractError(f"{label} values must be strings")
        result.append(item)
    return result


def _load(path: Path) -> dict[str, object]:
    try:
        raw = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise Gate19_7MaterializationContractError(f"cannot read {path}: {exc}") from exc
    return _object(raw, label=str(path))


def _verify_retained_gate19_4_source_contract() -> None:
    try:
        result = subprocess.run(
            [sys.executable, str(_GATE19_4_VERIFIER)],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise Gate19_7MaterializationContractError(
            "cannot execute retained Gate 19.4 verifier"
        ) from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown failure"
        raise Gate19_7MaterializationContractError(
            f"retained Gate 19.4 source contract failed: {detail}"
        )


def _verify_gate19_6_lineage(
    contract: dict[str, object], admission: dict[str, object]
) -> set[str]:
    if contract.get("preparation_source_main_sha") != _EXPECTED_PREPARATION_SOURCE:
        raise Gate19_7MaterializationContractError("Gate 19.7 preparation source drifted")
    if contract.get("gate19_6_closeout_pr") != 360:
        raise Gate19_7MaterializationContractError("Gate 19.6 closeout PR drifted")
    if contract.get("gate19_6_closeout_sha") != _EXPECTED_GATE19_6_CLOSEOUT:
        raise Gate19_7MaterializationContractError("Gate 19.6 closeout SHA drifted")

    gate19_6 = _object(
        contract.get("gate19_6_plan_admission"), label="gate19_6_plan_admission"
    )
    expected_gate19_6 = {
        "source_head_sha": _EXPECTED_GATE19_6_PLAN_SOURCE,
        "plan_json_sha256": _EXPECTED_GATE19_6_PLAN_HASH,
        "managed_create_count": 21,
        "terraform_apply_authorized": False,
    }
    if gate19_6 != expected_gate19_6:
        raise Gate19_7MaterializationContractError(
            "Gate 19.6 lineage in the Gate 19.7 contract drifted"
        )
    for field, expected in expected_gate19_6.items():
        if admission.get(field) != expected and field != "terraform_apply_authorized":
            raise Gate19_7MaterializationContractError(
                f"committed Gate 19.6 admission {field} drifted"
            )

    safety = _object(admission.get("safety"), label="gate19_6.safety")
    if safety.get("terraform_apply_authorized") is not False:
        raise Gate19_7MaterializationContractError(
            "Gate 19.6 must retain terraform_apply_authorized=false"
        )
    inventory = set(
        _strings(
            admission.get("managed_create_inventory"),
            label="gate19_6.managed_create_inventory",
        )
    )
    if admission.get("managed_create_count") != 21 or len(inventory) != 21:
        raise Gate19_7MaterializationContractError(
            "Gate 19.6 admitted inventory must remain exactly 21 resources"
        )
    return inventory


def _verify_fresh_plan_contract(
    contract: dict[str, object], expected_inventory: set[str]
) -> None:
    fresh_plan = _object(contract.get("fresh_plan"), label="fresh_plan")
    if fresh_plan.get("required") is not True:
        raise Gate19_7MaterializationContractError("Gate 19.7 requires a fresh plan")
    if fresh_plan.get("plan_input") != str(_GATE19_7_PLAN_INPUT):
        raise Gate19_7MaterializationContractError("Gate 19.7 plan input path drifted")
    if fresh_plan.get("reuse_gate19_6_binary_plan_for_apply") is not False:
        raise Gate19_7MaterializationContractError(
            "Gate 19.6 binary plan reuse must remain forbidden"
        )
    if fresh_plan.get("remote_state_lock_disabled_during_plan") is not True:
        raise Gate19_7MaterializationContractError(
            "fresh Gate 19.7 plan must retain -lock=false"
        )
    if fresh_plan.get("expected_managed_create_count") != 21:
        raise Gate19_7MaterializationContractError(
            "Gate 19.7 expected managed create count must remain 21"
        )
    inventory = set(
        _strings(
            fresh_plan.get("expected_managed_create_inventory"),
            label="fresh_plan.expected_managed_create_inventory",
        )
    )
    if inventory != expected_inventory:
        raise Gate19_7MaterializationContractError(
            "Gate 19.7 expected inventory differs from admitted Gate 19.6 inventory"
        )


def _verify_safety_contract(contract: dict[str, object]) -> None:
    materialization = _object(
        contract.get("materialization_invariants"), label="materialization_invariants"
    )
    expected_materialization: dict[str, object] = {
        "public_async_runtime_materialized_for_plan": True,
        "execute_api_endpoint_disabled": True,
        "submit_enabled": False,
        "worker_enabled": False,
        "worker_event_source_enabled": False,
        "worker_reserved_concurrency": 0,
        "custom_public_domain_present": False,
        "provider_heavy_worker_executor_composed": False,
    }
    if materialization != expected_materialization:
        raise Gate19_7MaterializationContractError(
            "Gate 19.7 disabled materialization invariants drifted"
        )

    authority = _object(contract.get("authority"), label="authority")
    expected_authority: dict[str, object] = {
        "terraform_apply_authorized": False,
        "explicit_human_apply_authorization_required": True,
        "apply_authorization_must_bind_exact_plan_binary_sha256": True,
        "apply_authorization_must_bind_exact_plan_json_sha256": True,
        "apply_authorization_must_bind_exact_source_head_sha": True,
        "apply_command_present_in_preparation_runbook": False,
        "runtime_enablement_authorized": False,
        "public_endpoint_enablement_authorized": False,
        "worker_enablement_authorized": False,
        "event_source_enablement_authorized": False,
        "provider_heavy_execution_authorized": False,
        "iam_broadening_authorized": False,
    }
    if authority != expected_authority:
        raise Gate19_7MaterializationContractError("Gate 19.7 authority boundary drifted")

    post_apply = _object(
        contract.get("post_apply_if_later_authorized"),
        label="post_apply_if_later_authorized",
    )
    expected_post_apply: dict[str, object] = {
        "materialized_must_remain_disabled": True,
        "fresh_convergence_plan_required": True,
        "aws_read_verification_required": True,
        "bounded_evidence_required": True,
    }
    if post_apply != expected_post_apply:
        raise Gate19_7MaterializationContractError(
            "Gate 19.7 post-apply verification obligations drifted"
        )


def main() -> int:
    """Verify the frozen Gate 19.7 contract without contacting AWS."""
    contract = _load(_CONTRACT)
    admission = _load(_GATE19_6_ADMISSION)
    gate19_6_input = _load(_GATE19_6_PLAN_INPUT)
    gate19_7_input = _load(_GATE19_7_PLAN_INPUT)

    if contract.get("schema_version") != 1:
        raise Gate19_7MaterializationContractError("unsupported Gate 19.7 schema")
    if contract.get("artifact_type") != "phase-19-gate-19-7-materialization-contract:v1":
        raise Gate19_7MaterializationContractError("Gate 19.7 artifact type drifted")
    if contract.get("source_issue") != 361:
        raise Gate19_7MaterializationContractError("Gate 19.7 source issue drifted")
    if gate19_7_input != gate19_6_input:
        raise Gate19_7MaterializationContractError(
            "Gate 19.7 plan input must retain the exact admitted Gate 19.6 coordinates"
        )
    if gate19_7_input.get("public_async_runtime_materialized") is not True:
        raise Gate19_7MaterializationContractError(
            "Gate 19.7 plan input must select materialization for planning"
        )

    expected_inventory = _verify_gate19_6_lineage(contract, admission)
    _verify_fresh_plan_contract(contract, expected_inventory)
    _verify_safety_contract(contract)
    _verify_retained_gate19_4_source_contract()

    retained = set(
        _strings(contract.get("retained_invariants"), label="retained_invariants")
    )
    required = {
        "plan != apply",
        "materialized != enabled",
        "queue delivery != business execution authority",
        "provider retry != business retry authority",
        "artifact hash != S3 VersionId",
    }
    if retained != required:
        raise Gate19_7MaterializationContractError("retained invariant set drifted")

    print(
        "phase19_gate19_7_contract=PASS "
        "fresh_plan_required=true managed_creates=21 "
        "materialized_not_enabled=true terraform_apply_authorized=false "
        "human_apply_authorization_required=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
