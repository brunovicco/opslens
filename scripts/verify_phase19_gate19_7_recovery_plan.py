#!/usr/bin/env python3
"""Admit a fresh Gate 19.7 partial-apply recovery plan entirely offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import cast

_CONTRACT = Path("labs/evidence/phase-19-gate-19-7-recovery-contract-v1.json")
_CONTRACT_VERIFIER = Path("scripts/verify_phase19_gate19_7_recovery_contract.py")
_PLAN_INPUT = Path("labs/evidence/phase-19-gate-19-7-plan-input-v1.tfvars.json")
_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_INDEX_SUFFIX = re.compile(r"\[\d+\]$")

_EXPECTED_CREATES = {
    "aws_apigatewayv2_integration.public_async_api_lambda",
    "aws_apigatewayv2_route.public_async_result",
    "aws_apigatewayv2_route.public_async_status",
    "aws_apigatewayv2_route.public_async_submit",
    "aws_lambda_permission.public_async_api_gateway",
}
_EXPECTED_UPDATE = "aws_lambda_function.public_async_api"
_EXPECTED_OUTPUTS: dict[str, object] = {
    "public_async_runtime_materialized": True,
    "public_async_execute_api_endpoint_disabled": True,
    "public_async_submit_enabled": False,
    "public_async_worker_event_source_enabled": False,
    "public_async_worker_reserved_concurrency": 0,
}


class Gate19_7RecoveryPlanError(RuntimeError):
    """Raised when a recovery plan exceeds the frozen partial-apply authority."""


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


def _load(path: Path) -> dict[str, object]:
    try:
        parsed = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise Gate19_7RecoveryPlanError(f"cannot load {path}: {exc}") from exc
    return _object(parsed, label=str(path))


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
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise Gate19_7RecoveryPlanError("cannot resolve repository HEAD") from exc
    head = result.stdout.strip()
    if _FULL_SHA.fullmatch(head) is None:
        raise Gate19_7RecoveryPlanError("repository HEAD is not a full lowercase SHA")
    return head


def _run_contract_verifier() -> None:
    try:
        result = subprocess.run(
            [sys.executable, str(_CONTRACT_VERIFIER)],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise Gate19_7RecoveryPlanError("cannot execute recovery contract verifier") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown failure"
        raise Gate19_7RecoveryPlanError(f"recovery contract verifier failed: {detail}")
    if "phase19_gate19_7_recovery_contract=PASS" not in result.stdout:
        raise Gate19_7RecoveryPlanError("recovery contract verifier did not emit PASS")


def _normalize(address: str) -> str:
    return _INDEX_SUFFIX.sub("", address)


def _actions(entry: dict[str, object]) -> list[str]:
    change = _object(entry.get("change"), label="resource_change.change")
    raw = change.get("actions")
    if not isinstance(raw, list) or any(
        type(item) is not str for item in cast(list[object], raw)
    ):
        raise Gate19_7RecoveryPlanError("resource actions must be a string array")
    return cast(list[str], raw)


def _after(entry: dict[str, object], *, label: str) -> dict[str, object]:
    change = _object(entry.get("change"), label=f"{label}.change")
    return _object(change.get("after"), label=f"{label}.change.after")


def _environment_variables_if_known(
    after: dict[str, object], *, label: str
) -> dict[str, object] | None:
    environment = after.get("environment")
    if environment is None:
        return None
    if isinstance(environment, list):
        if len(environment) != 1:
            raise Gate19_7RecoveryPlanError(f"{label} environment must contain one block")
        block = _object(
            cast(list[object], environment)[0],
            label=f"{label}.environment[0]",
        )
    elif isinstance(environment, dict):
        block = _object(cast(object, environment), label=f"{label}.environment")
    else:
        return None
    variables = block.get("variables")
    if variables is None:
        return None
    if not isinstance(variables, dict):
        return None
    return _object(cast(object, variables), label=f"{label}.environment.variables")


def _verify_plan_variables(plan: dict[str, object], plan_input: dict[str, object]) -> None:
    variables = _object(plan.get("variables"), label="plan.variables")
    for name, expected in plan_input.items():
        entry = _object(variables.get(name), label=f"plan.variables.{name}")
        if entry.get("value") != expected:
            raise Gate19_7RecoveryPlanError(f"plan variable {name} drifted")


def _verify_output_changes(plan: dict[str, object]) -> None:
    outputs = _object(plan.get("output_changes"), label="plan.output_changes")
    for name, expected in _EXPECTED_OUTPUTS.items():
        entry = _object(outputs.get(name), label=f"output_changes.{name}")
        if entry.get("after") != expected:
            raise Gate19_7RecoveryPlanError(
                f"recovery plan safety output {name} must remain {expected!r}"
            )


def _verify_resource_changes(
    plan: dict[str, object], plan_input: dict[str, object]
) -> tuple[int, int]:
    entries = _objects(plan.get("resource_changes"), label="resource_changes")
    creates: set[str] = set()
    updates: set[str] = set()

    for entry in entries:
        if entry.get("mode", "managed") != "managed":
            continue
        address = entry.get("address")
        if type(address) is not str:
            raise Gate19_7RecoveryPlanError("managed resource address must be a string")
        normalized = _normalize(address)
        actions = _actions(entry)

        if "delete" in actions:
            raise Gate19_7RecoveryPlanError(
                f"recovery plan must not delete or replace managed resource {normalized}"
            )
        if actions == ["create"]:
            creates.add(normalized)
            continue
        if actions == ["update"]:
            updates.add(normalized)
            if normalized != _EXPECTED_UPDATE:
                raise Gate19_7RecoveryPlanError(
                    f"recovery plan contains unauthorized update {normalized}"
                )
            api = _after(entry, label="API Lambda recovery update")
            if api.get("reserved_concurrent_executions") != 0:
                raise Gate19_7RecoveryPlanError(
                    "API Lambda recovery update must set reserved concurrency to zero"
                )
            expected_api = {
                "s3_key": plan_input["public_async_api_artifact_key"],
                "s3_object_version": plan_input["public_async_api_artifact_version_id"],
                "source_code_hash": plan_input["public_async_api_source_code_hash"],
            }
            for field, expected in expected_api.items():
                if api.get(field) != expected:
                    raise Gate19_7RecoveryPlanError(
                        f"API Lambda recovery {field} differs from admitted artifact"
                    )
            variables = _environment_variables_if_known(api, label="API Lambda recovery")
            if (
                variables is not None
                and variables.get("OPSLENS_ASYNC_SUBMIT_ENABLED") != "false"
            ):
                raise Gate19_7RecoveryPlanError(
                    "API Lambda submit switch must remain false during recovery"
                )
            continue
        if actions == ["no-op"]:
            continue
        raise Gate19_7RecoveryPlanError(
            f"unsupported recovery action {actions!r} for {normalized}"
        )

    if creates != _EXPECTED_CREATES:
        raise Gate19_7RecoveryPlanError(
            f"recovery create inventory mismatch; expected={sorted(_EXPECTED_CREATES)}, "
            f"observed={sorted(creates)}"
        )
    if updates != {_EXPECTED_UPDATE}:
        raise Gate19_7RecoveryPlanError(
            f"recovery update inventory mismatch; observed={sorted(updates)}"
        )
    return len(creates), len(updates)


def _write_summary(
    output: Path,
    *,
    source_head_sha: str,
    plan_json: Path,
    plan_binary: Path,
    plan: dict[str, object],
    create_count: int,
    update_count: int,
) -> None:
    contract = _load(_CONTRACT)
    summary = {
        "schema_version": 1,
        "artifact_type": "phase-19-gate-19-7-recovery-plan-admission:v1",
        "source_head_sha": source_head_sha,
        "plan_binary_sha256": _sha256(plan_binary),
        "plan_json_sha256": _sha256(plan_json),
        "terraform_format_version": plan.get("format_version"),
        "terraform_version": plan.get("terraform_version"),
        "expected_create_inventory": sorted(_EXPECTED_CREATES),
        "allowed_update_inventory": [_EXPECTED_UPDATE],
        "managed_create_count": create_count,
        "managed_update_count": update_count,
        "managed_delete_count": 0,
        "managed_replacement_count": 0,
        "failed_plan": contract.get("failed_plan"),
        "recovery": {
            "api_reserved_concurrency": 0,
            "worker_reserved_concurrency": 0,
            "materialized_not_enabled": True,
            "partial_state_reconciled": True,
        },
        "authority": {
            "terraform_apply_authorized": False,
            "explicit_human_apply_authorization_required": True,
            "failed_plan_retry_authorized": False,
            "runtime_enablement_authorized": False,
            "public_endpoint_enablement_authorized": False,
            "provider_heavy_execution_authorized": False,
            "apply_authorization_status": "PENDING_EXPLICIT_HUMAN_AUTHORIZATION",
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
    """Verify a fresh recovery plan without provider access or Terraform mutation."""
    args = _parser().parse_args()
    if _FULL_SHA.fullmatch(args.expected_source_head) is None:
        raise Gate19_7RecoveryPlanError("--expected-source-head must be a full SHA")
    source_head = _git_head()
    if source_head != args.expected_source_head:
        raise Gate19_7RecoveryPlanError(
            f"repository HEAD {source_head} differs from reviewed recovery source "
            f"{args.expected_source_head}"
        )

    _run_contract_verifier()
    plan = _load(args.plan_json)
    plan_input = _load(_PLAN_INPUT)
    _verify_plan_variables(plan, plan_input)
    _verify_output_changes(plan)
    create_count, update_count = _verify_resource_changes(plan, plan_input)

    if args.output is not None:
        _write_summary(
            args.output,
            source_head_sha=source_head,
            plan_json=args.plan_json,
            plan_binary=args.plan_binary,
            plan=plan,
            create_count=create_count,
            update_count=update_count,
        )

    print(
        "phase19_gate19_7_recovery_plan=PASS "
        f"creates={create_count} updates={update_count} deletes=0 replacements=0 "
        f"plan_binary_sha256={_sha256(args.plan_binary)} "
        "api_reserved_concurrency=0 materialized_not_enabled=true "
        "terraform_apply_authorized=false human_apply_authorization_required=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
