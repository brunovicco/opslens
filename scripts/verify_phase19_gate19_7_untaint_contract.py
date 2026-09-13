#!/usr/bin/env python3
"""Verify the Gate 19.7 controlled Terraform-state untaint contract offline."""

import json
from pathlib import Path
from typing import cast

_DIAGNOSIS = Path(
    "labs/evidence/phase-19-gate-19-7-replacement-diagnosis-v1.json"
)
_CONTRACT = Path("labs/evidence/phase-19-gate-19-7-untaint-contract-v1.json")
_RUNTIME_TF = Path("infra/environments/dev/public_async_runtime.tf")

_API_NORMALIZED = "aws_lambda_function.public_async_api"
_API_INDEXED = "aws_lambda_function.public_async_api[0]"
_EXPECTED_DIAGNOSIS_HEAD = "46fb069beffe2a49c1bde647d51ac8d7bcf4a687"
_EXPECTED_CODE_SHA256 = "mUd2dtzEE0XGPtKMgbtBx/n0e89bByJUvB7w4s/Nh24="


class Gate19_7UntaintContractError(RuntimeError):
    """Reject drift that would broaden the controlled state-reconciliation boundary."""


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise Gate19_7UntaintContractError(f"{label} must be an object")
    raw = cast(dict[object, object], value)
    if any(type(key) is not str for key in raw):
        raise Gate19_7UntaintContractError(f"{label} keys must be strings")
    return cast(dict[str, object], raw)


def _strings(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise Gate19_7UntaintContractError(f"{label} must be an array")
    result: list[str] = []
    for item in cast(list[object], value):
        if type(item) is not str:
            raise Gate19_7UntaintContractError(f"{label} values must be strings")
        result.append(item)
    return result


def _load(path: Path) -> dict[str, object]:
    try:
        raw = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise Gate19_7UntaintContractError(f"cannot read {path}: {exc}") from exc
    return _object(raw, label=str(path))


def _require_false_fields(obj: dict[str, object], fields: set[str], *, label: str) -> None:
    for field in fields:
        if obj.get(field) is not False:
            raise Gate19_7UntaintContractError(f"{label}.{field} must remain false")


def _verify_diagnosis() -> dict[str, object]:
    diagnosis = _load(_DIAGNOSIS)
    if diagnosis.get("artifact_type") != "phase-19-gate-19-7-replacement-diagnosis:v1":
        raise Gate19_7UntaintContractError("replacement diagnosis artifact type drifted")
    if diagnosis.get("source_head_sha") != _EXPECTED_DIAGNOSIS_HEAD:
        raise Gate19_7UntaintContractError("replacement diagnosis source head drifted")

    state = _object(diagnosis.get("terraform_state"), label="diagnosis.terraform_state")
    if state.get("api_lambda_instance_status") != "tainted" or state.get("tainted") is not True:
        raise Gate19_7UntaintContractError("diagnosis must prove the API Lambda state is tainted")

    rejected = _object(
        diagnosis.get("rejected_recovery_plan"), label="diagnosis.rejected_recovery_plan"
    )
    if _strings(rejected.get("actions"), label="diagnosis.rejected_recovery_plan.actions") != [
        "delete",
        "create",
    ]:
        raise Gate19_7UntaintContractError("rejected plan must retain delete/create actions")
    if rejected.get("action_reason") != "replace_because_tainted":
        raise Gate19_7UntaintContractError("replacement reason must remain taint")
    if rejected.get("admitted") is not False:
        raise Gate19_7UntaintContractError("rejected recovery plan unexpectedly became admitted")
    if rejected.get("after_reserved_concurrency") != 0:
        raise Gate19_7UntaintContractError("recovery API concurrency target drifted")

    aws_api = _object(diagnosis.get("aws_api_lambda"), label="diagnosis.aws_api_lambda")
    if aws_api.get("configuration_matches_expected") is not True:
        raise Gate19_7UntaintContractError("remote API Lambda must match reviewed configuration")
    if aws_api.get("state") != "Active":
        raise Gate19_7UntaintContractError("remote API Lambda must remain Active")
    if aws_api.get("last_update_status") != "Successful":
        raise Gate19_7UntaintContractError("remote API Lambda update status must remain Successful")
    if aws_api.get("reserved_concurrency") is not None:
        raise Gate19_7UntaintContractError("diagnosis must not invent positive API reserved concurrency")
    if aws_api.get("reserved_concurrency_observation") != "NOT_CONFIGURED_OR_NOT_OBSERVED":
        raise Gate19_7UntaintContractError("reserved-concurrency observation semantics drifted")

    observed = _object(aws_api.get("observed"), label="diagnosis.aws_api_lambda.observed")
    if observed.get("code_sha256") != _EXPECTED_CODE_SHA256:
        raise Gate19_7UntaintContractError("remote API Lambda artifact hash drifted")
    if observed.get("submit_switch") != "false":
        raise Gate19_7UntaintContractError("remote API submit switch must remain false")

    authority = _object(diagnosis.get("authority"), label="diagnosis.authority")
    _require_false_fields(
        authority,
        {
            "replacement_authorized",
            "runtime_enablement_authorized",
            "terraform_apply_authorized",
            "terraform_state_mutation_authorized",
            "terraform_untaint_authorized",
        },
        label="diagnosis.authority",
    )
    return diagnosis


def _verify_contract() -> None:
    contract = _load(_CONTRACT)
    if contract.get("artifact_type") != "phase-19-gate-19-7-untaint-contract:v1":
        raise Gate19_7UntaintContractError("untaint contract artifact type drifted")
    if contract.get("diagnosis_source_head_sha") != _EXPECTED_DIAGNOSIS_HEAD:
        raise Gate19_7UntaintContractError("untaint contract diagnosis head drifted")

    rejected = _object(contract.get("rejected_recovery_plan"), label="contract.rejected_recovery_plan")
    if rejected.get("summary") != "6 to add, 0 to change, 1 to destroy":
        raise Gate19_7UntaintContractError("rejected recovery-plan summary drifted")
    if _strings(rejected.get("api_lambda_actions"), label="contract.api_lambda_actions") != [
        "delete",
        "create",
    ]:
        raise Gate19_7UntaintContractError("contract must freeze the rejected replacement")
    if rejected.get("api_lambda_action_reason") != "replace_because_tainted":
        raise Gate19_7UntaintContractError("contract replacement reason drifted")
    for field in ("admitted", "reusable", "apply_authorized"):
        if rejected.get(field) is not False:
            raise Gate19_7UntaintContractError(f"contract rejected plan field {field} must remain false")

    target = _object(contract.get("untaint_target"), label="contract.untaint_target")
    expected_target: dict[str, object] = {
        "resource_address": _API_INDEXED,
        "normalized_resource_address": _API_NORMALIZED,
        "expected_pre_status": "tainted",
        "expected_remote_function_name": "opslens-dev-public-analysis-api",
        "expected_remote_code_sha256": _EXPECTED_CODE_SHA256,
        "expected_submit_switch": "false",
        "expected_remote_state": "Active",
        "expected_last_update_status": "Successful",
        "expected_reserved_concurrency_before": None,
        "expected_reserved_concurrency_observation_before": "NOT_CONFIGURED_OR_NOT_OBSERVED",
    }
    for field, expected in expected_target.items():
        if target.get(field) != expected:
            raise Gate19_7UntaintContractError(f"untaint target drifted at {field}")

    design = _object(contract.get("state_mutation_design"), label="contract.state_mutation_design")
    expected_design: dict[str, object] = {
        "operation": "terraform untaint",
        "aws_resource_mutation_expected": False,
        "terraform_state_mutation_expected": True,
        "state_lock_required": True,
        "allow_lock_false": False,
        "allow_import": False,
        "allow_state_rm": False,
        "allow_replace": False,
        "allow_destroy": False,
        "allow_apply": False,
        "maximum_target_count": 1,
    }
    for field, expected in expected_design.items():
        if design.get(field) != expected:
            raise Gate19_7UntaintContractError(f"state mutation design drifted at {field}")

    pre = _object(
        contract.get("required_pre_authorization_evidence"),
        label="contract.required_pre_authorization_evidence",
    )
    for field in {
        "exact_protected_main_sha_required",
        "clean_worktree_required",
        "terraform_state_lineage_required",
        "terraform_state_serial_required",
        "target_still_tainted_required",
        "remote_configuration_still_matches_expected_required",
        "rejected_recovery_plan_still_quarantined_required",
        "explicit_human_untaint_authorization_required",
    }:
        if pre.get(field) is not True:
            raise Gate19_7UntaintContractError(f"pre-authorization evidence drifted at {field}")
    if pre.get("aws_account_id") != "487757851499" or pre.get("aws_region") != "us-east-1":
        raise Gate19_7UntaintContractError("pre-authorization AWS scope drifted")

    post = _object(
        contract.get("required_post_untaint_evidence"),
        label="contract.required_post_untaint_evidence",
    )
    if post.get("target_no_longer_tainted_required") is not True:
        raise Gate19_7UntaintContractError("post-untaint taint-clear proof must remain required")
    if post.get("remote_configuration_unchanged_required") is not True:
        raise Gate19_7UntaintContractError("post-untaint remote-config proof must remain required")
    if post.get("fresh_recovery_plan_required") is not True:
        raise Gate19_7UntaintContractError("fresh recovery plan must remain required")
    if post.get("fresh_recovery_plan_expected_creates") != 5:
        raise Gate19_7UntaintContractError("post-untaint expected create count drifted")
    if post.get("fresh_recovery_plan_maximum_updates") != 1:
        raise Gate19_7UntaintContractError("post-untaint update bound drifted")
    if post.get("fresh_recovery_plan_allowed_update") != _API_NORMALIZED:
        raise Gate19_7UntaintContractError("post-untaint allowed update drifted")
    if post.get("fresh_recovery_plan_deletes") != 0 or post.get("fresh_recovery_plan_replacements") != 0:
        raise Gate19_7UntaintContractError("post-untaint destructive actions must remain zero")
    if post.get("terraform_apply_authorized") is not False:
        raise Gate19_7UntaintContractError("post-untaint apply unexpectedly authorized")

    authority = _object(contract.get("authority"), label="contract.authority")
    _require_false_fields(
        authority,
        {
            "terraform_untaint_authorized",
            "terraform_state_mutation_authorized",
            "terraform_apply_authorized",
            "aws_runtime_mutation_authorized",
            "iam_mutation_authorized",
            "runtime_enablement_authorized",
            "public_endpoint_enablement_authorized",
            "worker_enablement_authorized",
            "event_source_enablement_authorized",
            "provider_heavy_execution_authorized",
            "replacement_authorized",
            "destroy_authorized",
        },
        label="contract.authority",
    )


def _verify_live_source() -> None:
    try:
        runtime_tf = _RUNTIME_TF.read_text(encoding="utf-8")
    except OSError as exc:
        raise Gate19_7UntaintContractError("cannot read public async runtime Terraform") from exc
    start = runtime_tf.find('resource "aws_lambda_function" "public_async_api"')
    end = runtime_tf.find('resource "aws_lambda_function" "public_async_worker"', start + 1)
    if start < 0 or end < 0:
        raise Gate19_7UntaintContractError("API Lambda Terraform segment is missing")
    api_segment = runtime_tf[start:end]
    if "reserved_concurrent_executions = 0" not in api_segment:
        raise Gate19_7UntaintContractError("API Lambda must remain hard-disabled at concurrency zero")
    if "reserved_concurrent_executions = 2" in api_segment:
        raise Gate19_7UntaintContractError("historical API concurrency leaked into live resource")
    if 'OPSLENS_ASYNC_SUBMIT_ENABLED           = "false"' not in api_segment:
        raise Gate19_7UntaintContractError("API submit switch must remain false")
    if "disable_execute_api_endpoint = true" not in runtime_tf:
        raise Gate19_7UntaintContractError("execute-api endpoint must remain disabled")


def main() -> int:
    """Verify all static evidence required before any human untaint authorization."""
    _verify_diagnosis()
    _verify_contract()
    _verify_live_source()
    print(
        "phase19_gate19_7_untaint_contract=PASS "
        "target=aws_lambda_function.public_async_api[0] "
        "taint_confirmed=true remote_config_matches=true "
        "state_mutation_authorized=false terraform_untaint_authorized=false "
        "terraform_apply_authorized=false human_untaint_authorization_required=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
