#!/usr/bin/env python3
"""Admit fresh Gate 19.7 Terraform plans while keeping apply authority false."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import cast

_GATE19_7_CONTRACT_VERIFIER = Path(
    "scripts/verify_phase19_gate19_7_materialization_contract.py"
)
_GATE19_6_PLAN_VERIFIER = Path("scripts/verify_phase19_gate19_6_exact_plan.py")
_GATE19_7_PLAN_INPUT = Path("labs/evidence/phase-19-gate-19-7-plan-input-v1.tfvars.json")
_GATE19_7_ADMISSION = Path(
    "labs/evidence/phase-19-gate-19-7-fresh-plan-admission-v1.json"
)
_GATE19_7_RECOVERY_CONTRACT = Path(
    "labs/evidence/phase-19-gate-19-7-recovery-contract-v1.json"
)
_GATE19_7_RECONCILIATION = Path(
    "labs/evidence/phase-19-gate-19-7-failed-apply-reconciliation-v1.json"
)
_RUNTIME_TF = Path("infra/environments/dev/public_async_runtime.tf")
_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_INDEX_SUFFIX = re.compile(r"\[\d+\]$")
_API_ADDRESS = "aws_lambda_function.public_async_api"
_WORKER_ADDRESS = "aws_lambda_function.public_async_worker"
_MAPPING_ADDRESS = "aws_lambda_event_source_mapping.public_async_worker"
_HTTP_API_ADDRESS = "aws_apigatewayv2_api.public_async"


class Gate19_7FreshPlanError(RuntimeError):
    """Raised when a fresh Gate 19.7 plan cannot be admitted."""


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise Gate19_7FreshPlanError(f"{label} must be an object")
    raw = cast(dict[object, object], value)
    if any(type(key) is not str for key in raw):
        raise Gate19_7FreshPlanError(f"{label} keys must be strings")
    return cast(dict[str, object], raw)


def _objects(value: object, *, label: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise Gate19_7FreshPlanError(f"{label} must be an array")
    return [_object(item, label=f"{label}[]") for item in cast(list[object], value)]


def _strings(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise Gate19_7FreshPlanError(f"{label} must be an array")
    result: list[str] = []
    for item in cast(list[object], value):
        if type(item) is not str:
            raise Gate19_7FreshPlanError(f"{label} values must be strings")
        result.append(item)
    return result


def _load(path: Path) -> dict[str, object]:
    try:
        raw = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise Gate19_7FreshPlanError(f"cannot read {path}: {exc}") from exc
    return _object(raw, label=str(path))


def _sha256(path: Path) -> str:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise Gate19_7FreshPlanError(f"cannot read {path}: {exc}") from exc
    if not payload:
        raise Gate19_7FreshPlanError(f"{path} must not be empty")
    return hashlib.sha256(payload).hexdigest()


def _git_head() -> str:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise Gate19_7FreshPlanError("cannot resolve repository HEAD") from exc
    if _FULL_SHA.fullmatch(head) is None:
        raise Gate19_7FreshPlanError("repository HEAD is not a full lowercase SHA")
    return head


def _run_offline(command: list[str], *, label: str) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise Gate19_7FreshPlanError(f"cannot execute {label}") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown failure"
        raise Gate19_7FreshPlanError(f"{label} failed: {detail}")
    return result


def _verify_source_head(expected_source_head: str) -> str:
    if _FULL_SHA.fullmatch(expected_source_head) is None:
        raise Gate19_7FreshPlanError("--expected-source-head must be a full lowercase SHA")
    actual = _git_head()
    if actual != expected_source_head:
        raise Gate19_7FreshPlanError(
            f"repository HEAD {actual} differs from reviewed source {expected_source_head}"
        )
    return actual


def _verify_inherited_admission(
    summary: dict[str, object], *, expected_source_head: str
) -> None:
    if summary.get("artifact_type") != "phase-19-gate-19-6-plan-admission:v1":
        raise Gate19_7FreshPlanError("retained exact-plan verifier returned wrong artifact type")
    if summary.get("source_head_sha") != expected_source_head:
        raise Gate19_7FreshPlanError("retained plan admission source head drifted")
    if summary.get("managed_create_count") != 21:
        raise Gate19_7FreshPlanError("fresh Gate 19.7 plan must contain exactly 21 creates")
    safety = _object(summary.get("safety"), label="retained_plan.safety")
    expected_safety: dict[str, object] = {
        "iam_mutations": 0,
        "plan_only": True,
        "provider_heavy_public_executions": 0,
        "public_endpoint_enablements": 0,
        "remote_state_lock_disabled": True,
        "runtime_resources_mutated": 0,
        "terraform_apply_authorized": False,
    }
    if safety != expected_safety:
        raise Gate19_7FreshPlanError("retained exact-plan safety result drifted")


def _write_summary(
    output: Path,
    *,
    source_head_sha: str,
    plan_binary: Path,
    retained_summary: dict[str, object],
) -> None:
    summary = {
        "schema_version": 1,
        "artifact_type": "phase-19-gate-19-7-fresh-plan-admission:v1",
        "source_head_sha": source_head_sha,
        "plan_binary_sha256": _sha256(plan_binary),
        "plan_json_sha256": retained_summary.get("plan_json_sha256"),
        "terraform_format_version": retained_summary.get("terraform_format_version"),
        "terraform_version": retained_summary.get("terraform_version"),
        "selected_design": retained_summary.get("selected_design"),
        "managed_create_count": retained_summary.get("managed_create_count"),
        "managed_create_inventory": retained_summary.get("managed_create_inventory"),
        "account_id": retained_summary.get("account_id"),
        "region": retained_summary.get("region"),
        "artifacts": retained_summary.get("artifacts"),
        "plan_observability": retained_summary.get("plan_observability"),
        "authority": {
            "fresh_plan": True,
            "retained_gate19_6_exact_plan_engine_pass": True,
            "gate19_6_binary_plan_reuse_forbidden": True,
            "materialized_not_enabled": True,
            "explicit_human_apply_authorization_required": True,
            "terraform_apply_authorized": False,
            "apply_authorization_status": "PENDING_EXPLICIT_HUMAN_AUTHORIZATION",
        },
        "safety": {
            "remote_state_lock_disabled_during_plan": True,
            "runtime_resources_mutated": 0,
            "iam_mutations": 0,
            "public_endpoint_enablements": 0,
            "provider_heavy_public_executions": 0,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _segment(text: str, *, start: str, end: str, label: str) -> str:
    start_index = text.find(start)
    if start_index < 0:
        raise Gate19_7FreshPlanError(f"{label} start marker is missing")
    end_index = text.find(end, start_index + len(start))
    if end_index < 0:
        raise Gate19_7FreshPlanError(f"{label} end marker is missing")
    return text[start_index:end_index]


def _verify_recovery_contract() -> dict[str, object]:
    contract = _load(_GATE19_7_RECOVERY_CONTRACT)
    reconciliation = _load(_GATE19_7_RECONCILIATION)
    admission = _load(_GATE19_7_ADMISSION)

    if contract.get("artifact_type") != "phase-19-gate-19-7-recovery-contract:v1":
        raise Gate19_7FreshPlanError("Gate 19.7 recovery contract type drifted")
    if reconciliation.get("artifact_type") != (
        "phase-19-gate-19-7-failed-apply-reconciliation:v1"
    ):
        raise Gate19_7FreshPlanError("Gate 19.7 reconciliation type drifted")

    failed_apply = _object(contract.get("failed_apply"), label="recovery.failed_apply")
    failed_plan = _object(reconciliation.get("failed_plan"), label="reconciliation.failed_plan")
    classification = _object(
        reconciliation.get("failure_classification"),
        label="reconciliation.failure_classification",
    )
    lambda_account = _object(
        reconciliation.get("lambda_account"), label="reconciliation.lambda_account"
    )
    if failed_apply.get("failed_plan_binary_sha256") != failed_plan.get(
        "plan_binary_sha256"
    ):
        raise Gate19_7FreshPlanError("recovery contract binary-plan hash drifted")
    if failed_apply.get("failed_plan_json_sha256") != failed_plan.get(
        "plan_json_sha256"
    ):
        raise Gate19_7FreshPlanError("recovery contract plan-JSON hash drifted")
    if failed_plan.get("reusable") is not False or failed_apply.get(
        "failed_plan_reusable"
    ) is not False:
        raise Gate19_7FreshPlanError("failed Gate 19.7 plan must remain non-reusable")
    if failed_apply.get("retry_authorized") is not False:
        raise Gate19_7FreshPlanError("failed Gate 19.7 plan retry unexpectedly authorized")
    if failed_apply.get("failure_class") != classification.get("class"):
        raise Gate19_7FreshPlanError("recovery failure classification drifted")
    if failed_apply.get("account_concurrent_executions_limit") != lambda_account.get(
        "concurrent_executions_limit"
    ):
        raise Gate19_7FreshPlanError("recovery account concurrency evidence drifted")

    partial_state = _object(contract.get("partial_state"), label="recovery.partial_state")
    reconciled_state = _object(
        reconciliation.get("terraform_state"), label="reconciliation.terraform_state"
    )
    if partial_state.get("expected_managed_resource_count") != reconciled_state.get(
        "expected_gate19_7_resources"
    ):
        raise Gate19_7FreshPlanError("recovery expected resource count drifted")
    if partial_state.get("managed_expected_resource_count") != reconciled_state.get(
        "currently_managed_expected_resources"
    ):
        raise Gate19_7FreshPlanError("recovery managed partial-state count drifted")
    expected_missing = set(
        _strings(
            partial_state.get("missing_managed_create_inventory"),
            label="recovery missing inventory",
        )
    )
    reconciled_missing = set(
        _strings(
            reconciled_state.get("missing_expected_resources"),
            label="reconciled missing inventory",
        )
    )
    if expected_missing != reconciled_missing or len(expected_missing) != 5:
        raise Gate19_7FreshPlanError("recovery missing-resource inventory drifted")
    if reconciled_state.get("unexpected_public_async_resources") != []:
        raise Gate19_7FreshPlanError("reconciliation contains unexpected public-async resources")

    recovery_design = _object(
        contract.get("recovery_design"), label="recovery.recovery_design"
    )
    expected_design: dict[str, object] = {
        "api_reserved_concurrency": 0,
        "worker_reserved_concurrency": 0,
        "api_submit_enabled": False,
        "worker_enabled": False,
        "worker_event_source_enabled": False,
        "execute_api_endpoint_disabled": True,
        "custom_public_domain_present": False,
        "provider_heavy_worker_executor_composed": False,
        "only_existing_resource_allowed_to_update": _API_ADDRESS,
        "maximum_existing_resource_update_count": 1,
        "managed_delete_count": 0,
        "managed_replacement_count": 0,
    }
    for field, expected in expected_design.items():
        if recovery_design.get(field) != expected:
            raise Gate19_7FreshPlanError(f"recovery design drifted at {field}")

    authority = _object(contract.get("plan_authority"), label="recovery.plan_authority")
    for field in (
        "failed_binary_plan_reuse_forbidden",
        "fresh_human_plan_required",
        "explicit_human_apply_authorization_required",
    ):
        if authority.get(field) is not True:
            raise Gate19_7FreshPlanError(f"recovery authority drifted at {field}")
    for field in (
        "terraform_apply_authorized",
        "runtime_enablement_authorized",
        "public_endpoint_enablement_authorized",
        "worker_enablement_authorized",
        "event_source_enablement_authorized",
        "provider_heavy_execution_authorized",
        "iam_broadening_authorized",
    ):
        if authority.get(field) is not False:
            raise Gate19_7FreshPlanError(f"recovery authority expanded at {field}")

    artifacts = _object(admission.get("artifacts"), label="admission.artifacts")
    observed_artifacts = _object(
        reconciliation.get("artifact_observation"),
        label="reconciliation.artifact_observation",
    )
    api_artifact = _object(artifacts.get("api"), label="admission.artifacts.api")
    worker_artifact = _object(
        artifacts.get("worker"), label="admission.artifacts.worker"
    )
    if observed_artifacts.get("api_code_sha256") != api_artifact.get(
        "lambda_source_code_hash"
    ):
        raise Gate19_7FreshPlanError("API artifact hash drifted during partial apply")
    if observed_artifacts.get("worker_code_sha256") != worker_artifact.get(
        "lambda_source_code_hash"
    ):
        raise Gate19_7FreshPlanError("worker artifact hash drifted during partial apply")

    try:
        runtime_tf = _RUNTIME_TF.read_text(encoding="utf-8")
    except OSError as exc:
        raise Gate19_7FreshPlanError("cannot read public async runtime Terraform") from exc
    api_segment = _segment(
        runtime_tf,
        start='resource "aws_lambda_function" "public_async_api"',
        end='resource "aws_lambda_function" "public_async_worker"',
        label="API Lambda Terraform",
    )
    worker_segment = _segment(
        runtime_tf,
        start='resource "aws_lambda_function" "public_async_worker"',
        end='resource "aws_lambda_event_source_mapping" "public_async_worker"',
        label="worker Lambda Terraform",
    )
    if "reserved_concurrent_executions = 0" not in api_segment:
        raise Gate19_7FreshPlanError("recovery API Lambda must be hard-disabled at concurrency zero")
    if "reserved_concurrent_executions = 2" in api_segment:
        raise Gate19_7FreshPlanError("historical API concurrency leaked into live recovery resource")
    if 'OPSLENS_ASYNC_SUBMIT_ENABLED           = "false"' not in api_segment:
        raise Gate19_7FreshPlanError("recovery API submit switch must remain false")
    if "reserved_concurrent_executions = 0" not in worker_segment:
        raise Gate19_7FreshPlanError("recovery worker concurrency must remain zero")
    if 'OPSLENS_ASYNC_WORKER_ENABLED       = "false"' not in worker_segment:
        raise Gate19_7FreshPlanError("recovery worker switch must remain false")
    if "disable_execute_api_endpoint = true" not in runtime_tf:
        raise Gate19_7FreshPlanError("recovery execute-api endpoint must remain disabled")
    if 'resource "aws_apigatewayv2_domain_name"' in runtime_tf:
        raise Gate19_7FreshPlanError("recovery source must not add a custom public domain")
    if 'output "public_async_api_reserved_concurrency"' not in runtime_tf:
        raise Gate19_7FreshPlanError("recovery API concurrency safety output is missing")

    return contract


def _plan_variable_value(plan: dict[str, object], name: str) -> object:
    variables = _object(plan.get("variables"), label="plan.variables")
    entry = _object(variables.get(name), label=f"plan.variables.{name}")
    if "value" not in entry:
        raise Gate19_7FreshPlanError(f"plan variable {name} is missing value")
    return entry["value"]


def _verify_recovery_plan_variables(plan: dict[str, object]) -> None:
    plan_input = _load(_GATE19_7_PLAN_INPUT)
    for name, expected in plan_input.items():
        if _plan_variable_value(plan, name) != expected:
            raise Gate19_7FreshPlanError(f"recovery plan variable {name} drifted")


def _verify_output_after(plan: dict[str, object], name: str, expected: object) -> None:
    outputs = _object(plan.get("output_changes"), label="plan.output_changes")
    entry = _object(outputs.get(name), label=f"plan.output_changes.{name}")
    if entry.get("after") != expected:
        raise Gate19_7FreshPlanError(f"recovery safety output {name} drifted")
    if entry.get("after_unknown") not in (False, None):
        raise Gate19_7FreshPlanError(f"recovery safety output {name} must be plan-known")


def _contains_unknown(value: object) -> bool:
    if value is True:
        return True
    if isinstance(value, dict):
        return any(_contains_unknown(item) for item in cast(dict[object, object], value).values())
    if isinstance(value, list):
        return any(_contains_unknown(item) for item in cast(list[object], value))
    return False


def _verify_switch_or_unknown(
    entry: dict[str, object],
    *,
    label: str,
    switch_name: str,
) -> bool:
    change = _object(entry.get("change"), label=f"{label}.change")
    after = _object(change.get("after"), label=f"{label}.change.after")
    environment = after.get("environment")
    if isinstance(environment, list) and environment:
        first = _object(cast(list[object], environment)[0], label=f"{label}.environment[0]")
        variables = first.get("variables")
        if isinstance(variables, dict):
            typed_variables = _object(variables, label=f"{label}.environment.variables")
            if typed_variables.get(switch_name) != "false":
                raise Gate19_7FreshPlanError(f"{label} switch {switch_name} must remain false")
            return True
    if not _contains_unknown(change.get("after_unknown")):
        raise Gate19_7FreshPlanError(
            f"{label} environment is missing without a provider-unknown marker"
        )
    return False


def _normalize_address(address: str) -> str:
    return _INDEX_SUFFIX.sub("", address)


def _verify_recovery_plan(
    plan: dict[str, object], contract: dict[str, object]
) -> dict[str, object]:
    _verify_recovery_plan_variables(plan)
    for name, expected in {
        "public_async_runtime_materialized": True,
        "public_async_execute_api_endpoint_disabled": True,
        "public_async_submit_enabled": False,
        "public_async_api_reserved_concurrency": 0,
        "public_async_worker_event_source_enabled": False,
        "public_async_worker_reserved_concurrency": 0,
    }.items():
        _verify_output_after(plan, name, expected)

    partial_state = _object(contract.get("partial_state"), label="recovery.partial_state")
    expected_creates = set(
        _strings(
            partial_state.get("missing_managed_create_inventory"),
            label="recovery expected creates",
        )
    )
    entries = _objects(plan.get("resource_changes"), label="plan.resource_changes")
    creates: set[str] = set()
    updates: set[str] = set()
    observed: dict[str, dict[str, object]] = {}
    for entry in entries:
        if entry.get("mode", "managed") != "managed":
            continue
        raw_address = entry.get("address")
        if type(raw_address) is not str:
            raise Gate19_7FreshPlanError("managed resource change address must be a string")
        address = _normalize_address(raw_address)
        if address in observed:
            raise Gate19_7FreshPlanError(f"duplicate managed resource change {address}")
        observed[address] = entry
        change = _object(entry.get("change"), label=f"{address}.change")
        actions = _strings(change.get("actions"), label=f"{address}.actions")
        if actions == ["no-op"]:
            continue
        if actions == ["create"]:
            creates.add(address)
            continue
        if actions == ["update"]:
            updates.add(address)
            continue
        raise Gate19_7FreshPlanError(
            f"recovery plan contains forbidden managed actions {actions} at {address}"
        )

    if creates != expected_creates:
        missing = sorted(expected_creates - creates)
        unexpected = sorted(creates - expected_creates)
        raise Gate19_7FreshPlanError(
            f"recovery create inventory mismatch; missing={missing}, unexpected={unexpected}"
        )
    if updates - {_API_ADDRESS}:
        raise Gate19_7FreshPlanError(
            f"recovery plan updates unexpected existing resources: {sorted(updates - {_API_ADDRESS})}"
        )
    if len(updates) > 1:
        raise Gate19_7FreshPlanError("recovery plan may update at most the API Lambda")

    for required in (_API_ADDRESS, _WORKER_ADDRESS, _MAPPING_ADDRESS, _HTTP_API_ADDRESS):
        if required not in observed:
            raise Gate19_7FreshPlanError(f"recovery plan is missing proof for {required}")

    plan_input = _load(_GATE19_7_PLAN_INPUT)
    api_entry = observed[_API_ADDRESS]
    api_change = _object(api_entry.get("change"), label="API Lambda change")
    api_after = _object(api_change.get("after"), label="API Lambda after")
    api_expected: dict[str, object] = {
        "s3_key": plan_input["public_async_api_artifact_key"],
        "s3_object_version": plan_input["public_async_api_artifact_version_id"],
        "source_code_hash": plan_input["public_async_api_source_code_hash"],
        "reserved_concurrent_executions": 0,
    }
    for field, expected in api_expected.items():
        if api_after.get(field) != expected:
            raise Gate19_7FreshPlanError(f"recovery API Lambda {field} drifted")
    api_env_known = _verify_switch_or_unknown(
        api_entry,
        label="API Lambda",
        switch_name="OPSLENS_ASYNC_SUBMIT_ENABLED",
    )

    worker_entry = observed[_WORKER_ADDRESS]
    worker_change = _object(worker_entry.get("change"), label="worker Lambda change")
    worker_after = _object(worker_change.get("after"), label="worker Lambda after")
    worker_expected: dict[str, object] = {
        "s3_key": plan_input["public_async_worker_artifact_key"],
        "s3_object_version": plan_input["public_async_worker_artifact_version_id"],
        "source_code_hash": plan_input["public_async_worker_source_code_hash"],
        "reserved_concurrent_executions": 0,
    }
    for field, expected in worker_expected.items():
        if worker_after.get(field) != expected:
            raise Gate19_7FreshPlanError(f"recovery worker Lambda {field} drifted")
    worker_env_known = _verify_switch_or_unknown(
        worker_entry,
        label="worker Lambda",
        switch_name="OPSLENS_ASYNC_WORKER_ENABLED",
    )

    mapping_change = _object(
        observed[_MAPPING_ADDRESS].get("change"), label="worker mapping change"
    )
    mapping_after = _object(mapping_change.get("after"), label="worker mapping after")
    if mapping_after.get("enabled") is not False:
        raise Gate19_7FreshPlanError("recovery event-source mapping must remain disabled")

    api_gateway_change = _object(
        observed[_HTTP_API_ADDRESS].get("change"), label="HTTP API change"
    )
    api_gateway_after = _object(api_gateway_change.get("after"), label="HTTP API after")
    if api_gateway_after.get("disable_execute_api_endpoint") is not True:
        raise Gate19_7FreshPlanError("recovery execute-api endpoint must remain disabled")

    return {
        "managed_create_count": len(creates),
        "managed_create_inventory": sorted(creates),
        "managed_update_count": len(updates),
        "managed_update_inventory": sorted(updates),
        "api_environment_variables_plan_known": api_env_known,
        "worker_environment_variables_plan_known": worker_env_known,
    }


def _write_recovery_summary(
    output: Path,
    *,
    source_head_sha: str,
    plan_json: Path,
    plan_binary: Path,
    plan: dict[str, object],
    result: dict[str, object],
) -> None:
    admission = _load(_GATE19_7_ADMISSION)
    summary = {
        "schema_version": 1,
        "artifact_type": "phase-19-gate-19-7-recovery-plan-admission:v1",
        "source_head_sha": source_head_sha,
        "plan_binary_sha256": _sha256(plan_binary),
        "plan_json_sha256": _sha256(plan_json),
        "terraform_format_version": plan.get("format_version"),
        "terraform_version": plan.get("terraform_version"),
        "account_id": admission.get("account_id"),
        "region": admission.get("region"),
        "artifacts": admission.get("artifacts"),
        "managed_create_count": result.get("managed_create_count"),
        "managed_create_inventory": result.get("managed_create_inventory"),
        "managed_update_count": result.get("managed_update_count"),
        "managed_update_inventory": result.get("managed_update_inventory"),
        "plan_observability": {
            "api_environment_variables_plan_known": result.get(
                "api_environment_variables_plan_known"
            ),
            "worker_environment_variables_plan_known": result.get(
                "worker_environment_variables_plan_known"
            ),
            "unknown_environment_values_admitted_only_with_retained_source_contract": True,
        },
        "recovery": {
            "previous_failed_plan_reusable": False,
            "previous_failed_plan_retry_authorized": False,
            "api_reserved_concurrency": 0,
            "worker_reserved_concurrency": 0,
            "partial_state_recovery": True,
        },
        "authority": {
            "fresh_plan": True,
            "materialized_not_enabled": True,
            "explicit_human_apply_authorization_required": True,
            "terraform_apply_authorized": False,
            "apply_authorization_status": "PENDING_EXPLICIT_HUMAN_AUTHORIZATION",
        },
        "safety": {
            "remote_state_lock_disabled_during_plan": True,
            "managed_deletes": 0,
            "managed_replacements": 0,
            "public_endpoint_enablements": 0,
            "provider_heavy_public_executions": 0,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-json", type=Path, required=True)
    parser.add_argument("--plan-binary", type=Path, required=True)
    parser.add_argument("--expected-source-head", required=True)
    parser.add_argument(
        "--recovery",
        action="store_true",
        help="Admit the Gate 19.7 partial-materialization recovery plan.",
    )
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    """Admit one fresh plan entirely offline after the human Terraform plan completes."""
    args = _parser().parse_args()
    source_head = _verify_source_head(args.expected_source_head)

    _run_offline(
        [sys.executable, str(_GATE19_7_CONTRACT_VERIFIER)],
        label="Gate 19.7 materialization contract verifier",
    )

    if args.recovery:
        contract = _verify_recovery_contract()
        plan = _load(args.plan_json)
        result = _verify_recovery_plan(plan, contract)
        plan_binary_sha256 = _sha256(args.plan_binary)
        if args.output is not None:
            _write_recovery_summary(
                args.output,
                source_head_sha=source_head,
                plan_json=args.plan_json,
                plan_binary=args.plan_binary,
                plan=plan,
                result=result,
            )
        print(
            "phase19_gate19_7_recovery_plan=PASS "
            f"managed_creates={result['managed_create_count']} "
            f"managed_updates={result['managed_update_count']} "
            "deletes=0 replacements=0 "
            f"plan_binary_sha256={plan_binary_sha256} "
            "api_reserved_concurrency=0 worker_reserved_concurrency=0 "
            "materialized_not_enabled=true terraform_apply_authorized=false "
            "human_apply_authorization_required=true"
        )
        return 0

    with tempfile.TemporaryDirectory(prefix="opslens-gate19-7-") as temp_dir:
        retained_output = Path(temp_dir) / "retained-plan-admission.json"
        result = _run_offline(
            [
                sys.executable,
                str(_GATE19_6_PLAN_VERIFIER),
                "--plan-json",
                str(args.plan_json),
                "--plan-input",
                str(_GATE19_7_PLAN_INPUT),
                "--output",
                str(retained_output),
            ],
            label="retained Gate 19.6 exact-plan verifier",
        )
        if "phase19_gate19_6_plan=PASS" not in result.stdout:
            raise Gate19_7FreshPlanError(
                "retained exact-plan verifier did not emit its PASS marker"
            )
        retained_summary = _load(retained_output)

    _verify_inherited_admission(retained_summary, expected_source_head=source_head)
    plan_binary_sha256 = _sha256(args.plan_binary)
    if args.output is not None:
        _write_summary(
            args.output,
            source_head_sha=source_head,
            plan_binary=args.plan_binary,
            retained_summary=retained_summary,
        )

    print(
        "phase19_gate19_7_plan=PASS "
        "managed_creates=21 updates=0 deletes=0 replacements=0 "
        f"plan_binary_sha256={plan_binary_sha256} "
        "materialized_not_enabled=true terraform_apply_authorized=false "
        "human_apply_authorization_required=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
