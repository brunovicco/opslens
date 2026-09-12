#!/usr/bin/env python3
"""Admit a Gate 19.7 partial-materialization recovery plan offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import cast

_MATERIALIZATION_VERIFIER = Path(
    "scripts/verify_phase19_gate19_7_materialization_contract.py"
)
_RECOVERY_CONTRACT = Path(
    "labs/evidence/phase-19-gate-19-7-recovery-contract-v1.json"
)
_RECONCILIATION = Path(
    "labs/evidence/phase-19-gate-19-7-failed-apply-reconciliation-v1.json"
)
_FRESH_ADMISSION = Path(
    "labs/evidence/phase-19-gate-19-7-fresh-plan-admission-v1.json"
)
_PLAN_INPUT = Path("labs/evidence/phase-19-gate-19-7-plan-input-v1.tfvars.json")
_RUNTIME_TF = Path("infra/environments/dev/public_async_runtime.tf")
_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_INDEX_SUFFIX = re.compile(r"\[\d+\]$")
_API = "aws_lambda_function.public_async_api"
_WORKER = "aws_lambda_function.public_async_worker"
_MAPPING = "aws_lambda_event_source_mapping.public_async_worker"
_HTTP_API = "aws_apigatewayv2_api.public_async"


class Gate19_7RecoveryPlanError(RuntimeError):
    """Reject recovery plans that exceed the frozen partial-state boundary."""


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise Gate19_7RecoveryPlanError(f"{label} must be an object")
    raw = cast(dict[object, object], value)
    if any(type(key) is not str for key in raw):
        raise Gate19_7RecoveryPlanError(f"{label} keys must be strings")
    return cast(dict[str, object], raw)


def _objects(value: object, *, label: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise Gate19_7RecoveryPlanError(f"{label} must be an array")
    return [_object(item, label=f"{label}[]") for item in cast(list[object], value)]


def _strings(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise Gate19_7RecoveryPlanError(f"{label} must be an array")
    result: list[str] = []
    for item in cast(list[object], value):
        if type(item) is not str:
            raise Gate19_7RecoveryPlanError(f"{label} values must be strings")
        result.append(item)
    return result


def _load(path: Path) -> dict[str, object]:
    try:
        raw = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise Gate19_7RecoveryPlanError(f"cannot read {path}: {exc}") from exc
    return _object(raw, label=str(path))


def _sha256(path: Path) -> str:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise Gate19_7RecoveryPlanError(f"cannot read {path}: {exc}") from exc
    if not payload:
        raise Gate19_7RecoveryPlanError(f"{path} must not be empty")
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
        raise Gate19_7RecoveryPlanError("cannot resolve repository HEAD") from exc
    if _FULL_SHA.fullmatch(head) is None:
        raise Gate19_7RecoveryPlanError("repository HEAD is not a full lowercase SHA")
    return head


def _verify_source_head(expected: str) -> str:
    if _FULL_SHA.fullmatch(expected) is None:
        raise Gate19_7RecoveryPlanError(
            "--expected-source-head must be a full lowercase SHA"
        )
    actual = _git_head()
    if actual != expected:
        raise Gate19_7RecoveryPlanError(
            f"repository HEAD {actual} differs from reviewed source {expected}"
        )
    return actual


def _run_materialization_verifier() -> None:
    try:
        result = subprocess.run(
            [sys.executable, str(_MATERIALIZATION_VERIFIER)],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise Gate19_7RecoveryPlanError(
            "cannot execute retained Gate 19.7 materialization verifier"
        ) from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown failure"
        raise Gate19_7RecoveryPlanError(
            f"retained Gate 19.7 materialization contract failed: {detail}"
        )


def _segment(text: str, *, start: str, end: str, label: str) -> str:
    start_index = text.find(start)
    if start_index < 0:
        raise Gate19_7RecoveryPlanError(f"{label} start marker is missing")
    end_index = text.find(end, start_index + len(start))
    if end_index < 0:
        raise Gate19_7RecoveryPlanError(f"{label} end marker is missing")
    return text[start_index:end_index]


def _verify_recovery_evidence() -> tuple[dict[str, object], set[str]]:
    contract = _load(_RECOVERY_CONTRACT)
    reconciliation = _load(_RECONCILIATION)
    admission = _load(_FRESH_ADMISSION)

    if contract.get("artifact_type") != "phase-19-gate-19-7-recovery-contract:v1":
        raise Gate19_7RecoveryPlanError("recovery contract type drifted")
    if reconciliation.get("artifact_type") != (
        "phase-19-gate-19-7-failed-apply-reconciliation:v1"
    ):
        raise Gate19_7RecoveryPlanError("failed-apply reconciliation type drifted")

    failed_apply = _object(contract.get("failed_apply"), label="failed_apply")
    failed_plan = _object(reconciliation.get("failed_plan"), label="failed_plan")
    classification = _object(
        reconciliation.get("failure_classification"),
        label="failure_classification",
    )
    lambda_account = _object(
        reconciliation.get("lambda_account"), label="lambda_account"
    )

    if failed_apply.get("failed_plan_binary_sha256") != failed_plan.get(
        "plan_binary_sha256"
    ):
        raise Gate19_7RecoveryPlanError("failed binary-plan hash drifted")
    if failed_apply.get("failed_plan_json_sha256") != failed_plan.get(
        "plan_json_sha256"
    ):
        raise Gate19_7RecoveryPlanError("failed plan-JSON hash drifted")
    if failed_apply.get("failed_plan_reusable") is not False:
        raise Gate19_7RecoveryPlanError("failed plan unexpectedly became reusable")
    if failed_apply.get("retry_authorized") is not False:
        raise Gate19_7RecoveryPlanError("failed plan retry unexpectedly authorized")
    if failed_plan.get("reusable") is not False:
        raise Gate19_7RecoveryPlanError("reconciliation marks failed plan reusable")
    if failed_apply.get("failure_class") != classification.get("class"):
        raise Gate19_7RecoveryPlanError("failure classification drifted")
    if failed_apply.get("requested_reserved_concurrency") != 2:
        raise Gate19_7RecoveryPlanError("failed API concurrency evidence drifted")
    if lambda_account.get("concurrent_executions_limit") != 10:
        raise Gate19_7RecoveryPlanError("Lambda account concurrency evidence drifted")

    partial = _object(contract.get("partial_state"), label="partial_state")
    state = _object(reconciliation.get("terraform_state"), label="terraform_state")
    if partial.get("expected_managed_resource_count") != 21:
        raise Gate19_7RecoveryPlanError("expected resource count must remain 21")
    if partial.get("managed_expected_resource_count") != 16:
        raise Gate19_7RecoveryPlanError("managed partial-state count must remain 16")
    if state.get("currently_managed_expected_resources") != 16:
        raise Gate19_7RecoveryPlanError("reconciled partial-state count drifted")
    if state.get("unexpected_public_async_resources") != []:
        raise Gate19_7RecoveryPlanError("unexpected public_async resources observed")

    missing = set(
        _strings(
            partial.get("missing_managed_create_inventory"),
            label="missing_managed_create_inventory",
        )
    )
    reconciled_missing = set(
        _strings(
            state.get("missing_expected_resources"),
            label="missing_expected_resources",
        )
    )
    if missing != reconciled_missing or len(missing) != 5:
        raise Gate19_7RecoveryPlanError("frozen five-resource missing inventory drifted")

    design = _object(contract.get("recovery_design"), label="recovery_design")
    expected_design: dict[str, object] = {
        "api_reserved_concurrency": 0,
        "worker_reserved_concurrency": 0,
        "api_submit_enabled": False,
        "worker_enabled": False,
        "worker_event_source_enabled": False,
        "execute_api_endpoint_disabled": True,
        "custom_public_domain_present": False,
        "provider_heavy_worker_executor_composed": False,
        "only_existing_resource_allowed_to_update": _API,
        "maximum_existing_resource_update_count": 1,
        "managed_delete_count": 0,
        "managed_replacement_count": 0,
    }
    for field, expected in expected_design.items():
        if design.get(field) != expected:
            raise Gate19_7RecoveryPlanError(f"recovery design drifted at {field}")

    authority = _object(contract.get("plan_authority"), label="plan_authority")
    true_fields = {
        "fresh_human_plan_required",
        "failed_binary_plan_reuse_forbidden",
        "explicit_human_apply_authorization_required",
    }
    for field in true_fields:
        if authority.get(field) is not True:
            raise Gate19_7RecoveryPlanError(f"recovery authority drifted at {field}")
    false_fields = {
        "terraform_apply_authorized",
        "runtime_enablement_authorized",
        "public_endpoint_enablement_authorized",
        "worker_enablement_authorized",
        "event_source_enablement_authorized",
        "provider_heavy_execution_authorized",
        "iam_broadening_authorized",
    }
    for field in false_fields:
        if authority.get(field) is not False:
            raise Gate19_7RecoveryPlanError(f"recovery authority expanded at {field}")

    artifacts = _object(admission.get("artifacts"), label="admission.artifacts")
    api_artifact = _object(artifacts.get("api"), label="admission.artifacts.api")
    worker_artifact = _object(
        artifacts.get("worker"), label="admission.artifacts.worker"
    )
    observed = _object(
        reconciliation.get("artifact_observation"), label="artifact_observation"
    )
    if observed.get("api_code_sha256") != api_artifact.get("lambda_source_code_hash"):
        raise Gate19_7RecoveryPlanError("API artifact hash drifted after failed apply")
    if observed.get("worker_code_sha256") != worker_artifact.get(
        "lambda_source_code_hash"
    ):
        raise Gate19_7RecoveryPlanError("worker artifact hash drifted after failed apply")

    try:
        runtime_tf = _RUNTIME_TF.read_text(encoding="utf-8")
    except OSError as exc:
        raise Gate19_7RecoveryPlanError("cannot read public async runtime Terraform") from exc
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
        raise Gate19_7RecoveryPlanError("API Lambda must be hard-disabled at concurrency zero")
    if "reserved_concurrent_executions = 2" in api_segment:
        raise Gate19_7RecoveryPlanError("historical API limit leaked into live resource")
    if 'OPSLENS_ASYNC_SUBMIT_ENABLED           = "false"' not in api_segment:
        raise Gate19_7RecoveryPlanError("API submit switch must remain false")
    if "reserved_concurrent_executions = 0" not in worker_segment:
        raise Gate19_7RecoveryPlanError("worker concurrency must remain zero")
    if 'OPSLENS_ASYNC_WORKER_ENABLED       = "false"' not in worker_segment:
        raise Gate19_7RecoveryPlanError("worker switch must remain false")
    if "disable_execute_api_endpoint = true" not in runtime_tf:
        raise Gate19_7RecoveryPlanError("execute-api endpoint must remain disabled")
    if 'resource "aws_apigatewayv2_domain_name"' in runtime_tf:
        raise Gate19_7RecoveryPlanError("custom public domain is forbidden")
    if 'output "public_async_api_reserved_concurrency"' not in runtime_tf:
        raise Gate19_7RecoveryPlanError("API concurrency safety output is missing")

    return admission, missing


def _plan_variable(plan: dict[str, object], name: str) -> object:
    variables = _object(plan.get("variables"), label="plan.variables")
    entry = _object(variables.get(name), label=f"plan.variables.{name}")
    if "value" not in entry:
        raise Gate19_7RecoveryPlanError(f"plan variable {name} is missing value")
    return entry["value"]


def _verify_plan_variables(plan: dict[str, object]) -> None:
    expected = _load(_PLAN_INPUT)
    for name, value in expected.items():
        if _plan_variable(plan, name) != value:
            raise Gate19_7RecoveryPlanError(f"recovery plan variable {name} drifted")


def _verify_output(plan: dict[str, object], name: str, expected: object) -> None:
    outputs = _object(plan.get("output_changes"), label="plan.output_changes")
    entry = _object(outputs.get(name), label=f"plan.output_changes.{name}")
    if entry.get("after") != expected:
        raise Gate19_7RecoveryPlanError(f"recovery safety output {name} drifted")
    if entry.get("after_unknown") not in (False, None):
        raise Gate19_7RecoveryPlanError(f"recovery safety output {name} is unknown")


def _contains_unknown(value: object) -> bool:
    if value is True:
        return True
    if isinstance(value, dict):
        raw = cast(dict[object, object], value)
        return any(_contains_unknown(item) for item in raw.values())
    if isinstance(value, list):
        return any(_contains_unknown(item) for item in cast(list[object], value))
    return False


def _verify_switch(
    entry: dict[str, object], *, label: str, switch_name: str
) -> bool:
    change = _object(entry.get("change"), label=f"{label}.change")
    after = _object(change.get("after"), label=f"{label}.change.after")
    environment = after.get("environment")
    if isinstance(environment, list) and environment:
        first_raw = cast(list[object], environment)[0]
        first = _object(first_raw, label=f"{label}.environment[0]")
        variables = first.get("variables")
        if isinstance(variables, dict):
            typed = _object(cast(object, variables), label=f"{label}.variables")
            if typed.get(switch_name) != "false":
                raise Gate19_7RecoveryPlanError(
                    f"{label} switch {switch_name} must remain false"
                )
            return True
    if not _contains_unknown(change.get("after_unknown")):
        raise Gate19_7RecoveryPlanError(
            f"{label} environment missing without provider-unknown marker"
        )
    return False


def _normalize(address: str) -> str:
    return _INDEX_SUFFIX.sub("", address)


def _after(entry: dict[str, object], *, label: str) -> dict[str, object]:
    change = _object(entry.get("change"), label=f"{label}.change")
    return _object(change.get("after"), label=f"{label}.change.after")


def _verify_plan(
    plan: dict[str, object], expected_creates: set[str]
) -> dict[str, object]:
    _verify_plan_variables(plan)
    expected_outputs: dict[str, object] = {
        "public_async_runtime_materialized": True,
        "public_async_execute_api_endpoint_disabled": True,
        "public_async_submit_enabled": False,
        "public_async_api_reserved_concurrency": 0,
        "public_async_worker_event_source_enabled": False,
        "public_async_worker_reserved_concurrency": 0,
    }
    for name, expected in expected_outputs.items():
        _verify_output(plan, name, expected)

    entries = _objects(plan.get("resource_changes"), label="plan.resource_changes")
    creates: set[str] = set()
    updates: set[str] = set()
    observed: dict[str, dict[str, object]] = {}

    for entry in entries:
        if entry.get("mode", "managed") != "managed":
            continue
        raw_address = entry.get("address")
        if type(raw_address) is not str:
            raise Gate19_7RecoveryPlanError("managed address must be a string")
        address = _normalize(raw_address)
        if address in observed:
            raise Gate19_7RecoveryPlanError(f"duplicate managed change {address}")
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
        raise Gate19_7RecoveryPlanError(
            f"forbidden managed actions {actions} at {address}"
        )

    if creates != expected_creates:
        missing = sorted(expected_creates - creates)
        unexpected = sorted(creates - expected_creates)
        raise Gate19_7RecoveryPlanError(
            f"recovery create inventory mismatch; missing={missing}, unexpected={unexpected}"
        )
    unexpected_updates = sorted(updates - {_API})
    if unexpected_updates:
        raise Gate19_7RecoveryPlanError(
            f"recovery plan updates unexpected resources: {unexpected_updates}"
        )
    if len(updates) > 1:
        raise Gate19_7RecoveryPlanError("recovery may update at most the API Lambda")

    required_proofs = (_API, _WORKER, _MAPPING, _HTTP_API)
    for address in required_proofs:
        if address not in observed:
            raise Gate19_7RecoveryPlanError(f"plan is missing proof for {address}")

    plan_input = _load(_PLAN_INPUT)
    api = _after(observed[_API], label="API Lambda")
    expected_api: dict[str, object] = {
        "s3_key": plan_input["public_async_api_artifact_key"],
        "s3_object_version": plan_input["public_async_api_artifact_version_id"],
        "source_code_hash": plan_input["public_async_api_source_code_hash"],
        "reserved_concurrent_executions": 0,
    }
    for field, expected in expected_api.items():
        if api.get(field) != expected:
            raise Gate19_7RecoveryPlanError(f"recovery API Lambda {field} drifted")
    api_env_known = _verify_switch(
        observed[_API],
        label="API Lambda",
        switch_name="OPSLENS_ASYNC_SUBMIT_ENABLED",
    )

    worker = _after(observed[_WORKER], label="worker Lambda")
    expected_worker: dict[str, object] = {
        "s3_key": plan_input["public_async_worker_artifact_key"],
        "s3_object_version": plan_input["public_async_worker_artifact_version_id"],
        "source_code_hash": plan_input["public_async_worker_source_code_hash"],
        "reserved_concurrent_executions": 0,
    }
    for field, expected in expected_worker.items():
        if worker.get(field) != expected:
            raise Gate19_7RecoveryPlanError(f"recovery worker Lambda {field} drifted")
    worker_env_known = _verify_switch(
        observed[_WORKER],
        label="worker Lambda",
        switch_name="OPSLENS_ASYNC_WORKER_ENABLED",
    )

    mapping = _after(observed[_MAPPING], label="worker event-source mapping")
    if mapping.get("enabled") is not False:
        raise Gate19_7RecoveryPlanError("worker event-source mapping must remain disabled")

    http_api = _after(observed[_HTTP_API], label="HTTP API")
    if http_api.get("disable_execute_api_endpoint") is not True:
        raise Gate19_7RecoveryPlanError("execute-api endpoint must remain disabled")

    return {
        "managed_create_count": len(creates),
        "managed_create_inventory": sorted(creates),
        "managed_update_count": len(updates),
        "managed_update_inventory": sorted(updates),
        "api_environment_variables_plan_known": api_env_known,
        "worker_environment_variables_plan_known": worker_env_known,
    }


def _write_summary(
    output: Path,
    *,
    source_head: str,
    plan_json: Path,
    plan_binary: Path,
    plan: dict[str, object],
    admission: dict[str, object],
    result: dict[str, object],
) -> None:
    summary = {
        "schema_version": 1,
        "artifact_type": "phase-19-gate-19-7-recovery-plan-admission:v1",
        "source_head_sha": source_head,
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
            "unknown_environment_values_require_explicit_unknown_markers": True,
        },
        "recovery": {
            "previous_failed_plan_reusable": False,
            "previous_failed_plan_retry_authorized": False,
            "partial_state_recovery": True,
            "api_reserved_concurrency": 0,
            "worker_reserved_concurrency": 0,
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
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    """Admit one fresh partial-state recovery plan without contacting AWS."""
    args = _parser().parse_args()
    source_head = _verify_source_head(args.expected_source_head)
    _run_materialization_verifier()
    admission, expected_creates = _verify_recovery_evidence()
    plan = _load(args.plan_json)
    result = _verify_plan(plan, expected_creates)
    binary_sha = _sha256(args.plan_binary)

    if args.output is not None:
        _write_summary(
            args.output,
            source_head=source_head,
            plan_json=args.plan_json,
            plan_binary=args.plan_binary,
            plan=plan,
            admission=admission,
            result=result,
        )

    print(
        "phase19_gate19_7_recovery_plan=PASS "
        f"managed_creates={result['managed_create_count']} "
        f"managed_updates={result['managed_update_count']} "
        "deletes=0 replacements=0 "
        f"plan_binary_sha256={binary_sha} "
        "api_reserved_concurrency=0 worker_reserved_concurrency=0 "
        "materialized_not_enabled=true terraform_apply_authorized=false "
        "human_apply_authorization_required=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
