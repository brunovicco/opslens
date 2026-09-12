#!/usr/bin/env python3
"""Offline verifier for the Gate 19.6 exact Terraform plan JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import cast

_PLAN_INPUT = Path("labs/evidence/phase-19-gate-19-6-plan-input-v1.tfvars.json")
_GATE19_4 = Path("labs/evidence/phase-19-gate-19-4-disabled-async-runtime-v1.json")
_GATE19_4_VERIFIER = Path("scripts/verify_phase19_gate19_4_disabled_async_runtime.py")
_PUBLICATION = Path("labs/evidence/phase-19-gate-19-5-artifact-publication-v1.json")
_EXPECTED_DESIGN = "HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB"
_EXPECTED_ROLES = {"api", "worker"}
_EXPECTED_SAFETY_OUTPUTS: dict[str, object] = {
    "public_async_runtime_materialized": True,
    "public_async_execute_api_endpoint_disabled": True,
    "public_async_submit_enabled": False,
    "public_async_worker_event_source_enabled": False,
    "public_async_worker_reserved_concurrency": 0,
}
_INDEX_SUFFIX = re.compile(r"\[\d+\]$")


class Gate19_6PlanVerificationError(RuntimeError):
    """Raised when an exact Terraform plan violates the frozen Gate 19.6 contract."""


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise Gate19_6PlanVerificationError(f"{label} must be an object")
    raw = cast(dict[object, object], value)
    if any(type(key) is not str for key in raw):
        raise Gate19_6PlanVerificationError(f"{label} keys must be strings")
    return cast(dict[str, object], raw)


def _objects(value: object, *, label: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise Gate19_6PlanVerificationError(f"{label} must be an array")
    return [_object(item, label=f"{label}[]") for item in cast(list[object], value)]


def _strings(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise Gate19_6PlanVerificationError(f"{label} must be an array")
    result: list[str] = []
    for item in cast(list[object], value):
        if type(item) is not str:
            raise Gate19_6PlanVerificationError(f"{label} values must be strings")
        result.append(item)
    return result


def _required_string(mapping: dict[str, object], field: str) -> str:
    value = mapping.get(field)
    if type(value) is not str or not value:
        raise Gate19_6PlanVerificationError(f"{field} must be a non-empty string")
    return value


def _load(path: Path) -> dict[str, object]:
    try:
        raw = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise Gate19_6PlanVerificationError(f"cannot read {path}: {exc}") from exc
    return _object(raw, label=str(path))


def _normalize_address(address: str) -> str:
    return _INDEX_SUFFIX.sub("", address)


def _publication_by_role(root: dict[str, object]) -> dict[str, dict[str, object]]:
    artifacts = _objects(root.get("artifacts"), label="publication.artifacts")
    result: dict[str, dict[str, object]] = {}
    for artifact in artifacts:
        role = artifact.get("role")
        if type(role) is not str or role in result:
            raise Gate19_6PlanVerificationError("publication role inventory is invalid")
        result[role] = artifact
    if set(result) != _EXPECTED_ROLES:
        raise Gate19_6PlanVerificationError("publication must contain exactly API and worker")
    return result


def _verify_plan_input(
    plan_input: dict[str, object],
    publication: dict[str, object],
) -> dict[str, dict[str, object]]:
    if plan_input.get("public_async_runtime_materialized") is not True:
        raise Gate19_6PlanVerificationError(
            "Gate 19.6 exact plan input must select materialization for planning"
        )
    if publication.get("artifact_type") != "phase-19-gate-19-5-artifact-publication:v1":
        raise Gate19_6PlanVerificationError("Gate 19.5 publication type drifted")
    for field in (
        "runtime_resource_mutation_count",
        "iam_mutation_count",
        "terraform_apply_count",
        "public_endpoint_enablement_count",
    ):
        if publication.get(field) != 0:
            raise Gate19_6PlanVerificationError(f"Gate 19.5 {field} evidence drifted")

    artifacts = _publication_by_role(publication)
    fields = {
        "api": {
            "key": "public_async_api_artifact_key",
            "version": "public_async_api_artifact_version_id",
            "hash": "public_async_api_source_code_hash",
        },
        "worker": {
            "key": "public_async_worker_artifact_key",
            "version": "public_async_worker_artifact_version_id",
            "hash": "public_async_worker_source_code_hash",
        },
    }
    for role, names in fields.items():
        artifact = artifacts[role]
        expected = {
            names["key"]: artifact.get("key"),
            names["version"]: artifact.get("version_id"),
            names["hash"]: artifact.get("lambda_source_code_hash"),
        }
        for field, value in expected.items():
            if plan_input.get(field) != value:
                raise Gate19_6PlanVerificationError(
                    f"Gate 19.6 plan input {field} differs from admitted Gate 19.5 evidence"
                )
    return artifacts


def _verify_retained_gate19_4_source_contract() -> None:
    """Re-run the retained offline Gate 19.4 source/evidence verifier."""
    try:
        result = subprocess.run(
            [sys.executable, str(_GATE19_4_VERIFIER)],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise Gate19_6PlanVerificationError(
            "cannot execute retained Gate 19.4 offline verifier"
        ) from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown failure"
        raise Gate19_6PlanVerificationError(
            f"retained Gate 19.4 source contract failed: {detail}"
        )


def _plan_variable_value(plan: dict[str, object], name: str) -> object:
    variables = _object(plan.get("variables"), label="plan.variables")
    entry = _object(variables.get(name), label=f"plan.variables.{name}")
    if "value" not in entry:
        raise Gate19_6PlanVerificationError(f"plan variable {name} has no value")
    return entry["value"]


def _verify_plan_variables(plan: dict[str, object], plan_input: dict[str, object]) -> None:
    for name, expected in plan_input.items():
        if _plan_variable_value(plan, name) != expected:
            raise Gate19_6PlanVerificationError(
                f"Terraform plan variable {name} differs from frozen Gate 19.6 input"
            )


def _verify_safety_outputs(plan: dict[str, object]) -> None:
    output_changes = _object(plan.get("output_changes"), label="plan.output_changes")
    admitted_actions = (["create"], ["update"], ["no-op"])
    for name, expected in _EXPECTED_SAFETY_OUTPUTS.items():
        change = _object(output_changes.get(name), label=f"plan.output_changes.{name}")
        actions = _strings(change.get("actions"), label=f"plan.output_changes.{name}.actions")
        if actions not in admitted_actions:
            raise Gate19_6PlanVerificationError(
                f"plan output {name} has forbidden actions {actions}"
            )
        if change.get("after") != expected:
            raise Gate19_6PlanVerificationError(
                f"plan output {name} differs from the disabled Gate 19.6 contract"
            )
        if change.get("after_unknown") is True:
            raise Gate19_6PlanVerificationError(
                f"plan output {name} must be known during planning"
            )


def _managed_change_inventory(
    plan: dict[str, object], expected: set[str]
) -> dict[str, dict[str, object]]:
    changes = _objects(plan.get("resource_changes"), label="plan.resource_changes")
    observed: dict[str, dict[str, object]] = {}
    unexpected: list[str] = []
    for entry in changes:
        if entry.get("mode") != "managed":
            continue
        address = _required_string(entry, "address")
        resource_type = _required_string(entry, "type")
        if resource_type == "aws_apigatewayv2_domain_name":
            raise Gate19_6PlanVerificationError(
                f"custom public domain is present in plan: {address}"
            )
        change = _object(entry.get("change"), label=f"{address}.change")
        actions = _strings(change.get("actions"), label=f"{address}.change.actions")
        if actions == ["no-op"]:
            continue
        normalized = _normalize_address(address)
        if normalized not in expected:
            unexpected.append(address)
            continue
        if actions != ["create"]:
            raise Gate19_6PlanVerificationError(
                f"{address} must be exactly a create action, observed {actions}"
            )
        if normalized in observed:
            raise Gate19_6PlanVerificationError(
                f"duplicate planned managed resource after normalization: {normalized}"
            )
        observed[normalized] = entry

    if unexpected:
        raise Gate19_6PlanVerificationError(
            f"unrelated managed non-no-op changes are forbidden: {sorted(unexpected)}"
        )
    if set(observed) != expected:
        missing = sorted(expected - set(observed))
        extra = sorted(set(observed) - expected)
        raise Gate19_6PlanVerificationError(
            f"Gate 19.6 managed create inventory mismatch; missing={missing}, extra={extra}"
        )
    return observed


def _after(entry: dict[str, object], *, label: str) -> dict[str, object]:
    change = _object(entry.get("change"), label=f"{label}.change")
    return _object(change.get("after"), label=f"{label}.change.after")


def _environment_variables_if_known(
    after: dict[str, object], *, label: str
) -> dict[str, object] | None:
    raw = after.get("environment")
    if raw is None:
        return None
    if isinstance(raw, list):
        blocks = [
            _object(item, label=f"{label}.environment[]")
            for item in cast(list[object], raw)
        ]
        if len(blocks) != 1:
            raise Gate19_6PlanVerificationError(
                f"{label}.environment must contain exactly one block"
            )
        env = blocks[0]
    else:
        env = _object(raw, label=f"{label}.environment")
    variables = env.get("variables")
    if variables is None:
        return None
    return _object(variables, label=f"{label}.environment.variables")


def _contains_unknown(value: object) -> bool:
    if value is True:
        return True
    if isinstance(value, list):
        return any(_contains_unknown(item) for item in cast(list[object], value))
    if isinstance(value, dict):
        return any(
            _contains_unknown(item)
            for item in cast(dict[object, object], value).values()
        )
    return False


def _environment_variables_are_unknown(
    entry: dict[str, object], *, label: str
) -> bool:
    change = _object(entry.get("change"), label=f"{label}.change")
    raw_unknown = change.get("after_unknown")
    if not isinstance(raw_unknown, dict):
        return False
    after_unknown = _object(raw_unknown, label=f"{label}.change.after_unknown")
    environment = after_unknown.get("environment")
    if environment is True:
        return True
    if isinstance(environment, list):
        for item in cast(list[object], environment):
            if isinstance(item, dict):
                block = _object(
                    item, label=f"{label}.change.after_unknown.environment[]"
                )
                if _contains_unknown(block.get("variables")):
                    return True
        return False
    if isinstance(environment, dict):
        block = _object(
            environment, label=f"{label}.change.after_unknown.environment"
        )
        return _contains_unknown(block.get("variables"))
    return False


def _verify_environment_switch(
    entry: dict[str, object],
    after: dict[str, object],
    *,
    label: str,
    switch_name: str,
) -> bool:
    variables = _environment_variables_if_known(after, label=label)
    if variables is not None:
        if variables.get(switch_name) != "false":
            raise Gate19_6PlanVerificationError(
                f"planned {label} switch {switch_name} must remain false"
            )
        return True
    if not _environment_variables_are_unknown(entry, label=label):
        raise Gate19_6PlanVerificationError(
            f"planned {label} environment variables are missing without an unknown marker"
        )
    return False


def _verify_critical_after_values(
    observed: dict[str, dict[str, object]],
    plan_input: dict[str, object],
) -> dict[str, bool]:
    api_entry = observed["aws_lambda_function.public_async_api"]
    worker_entry = observed["aws_lambda_function.public_async_worker"]
    api = _after(api_entry, label="api Lambda")
    worker = _after(worker_entry, label="worker Lambda")
    event_mapping = _after(
        observed["aws_lambda_event_source_mapping.public_async_worker"],
        label="worker event source mapping",
    )
    api_gateway = _after(
        observed["aws_apigatewayv2_api.public_async"], label="HTTP API"
    )

    api_expected = {
        "s3_key": plan_input["public_async_api_artifact_key"],
        "s3_object_version": plan_input["public_async_api_artifact_version_id"],
        "source_code_hash": plan_input["public_async_api_source_code_hash"],
        "reserved_concurrent_executions": 2,
    }
    worker_expected = {
        "s3_key": plan_input["public_async_worker_artifact_key"],
        "s3_object_version": plan_input["public_async_worker_artifact_version_id"],
        "source_code_hash": plan_input["public_async_worker_source_code_hash"],
        "reserved_concurrent_executions": 0,
    }
    for field, expected in api_expected.items():
        if api.get(field) != expected:
            raise Gate19_6PlanVerificationError(
                f"planned API Lambda {field} differs from Gate 19.6 contract"
            )
    for field, expected in worker_expected.items():
        if worker.get(field) != expected:
            raise Gate19_6PlanVerificationError(
                f"planned worker Lambda {field} differs from Gate 19.6 contract"
            )

    api_env_known = _verify_environment_switch(
        api_entry,
        api,
        label="API Lambda",
        switch_name="OPSLENS_ASYNC_SUBMIT_ENABLED",
    )
    worker_env_known = _verify_environment_switch(
        worker_entry,
        worker,
        label="worker Lambda",
        switch_name="OPSLENS_ASYNC_WORKER_ENABLED",
    )
    if event_mapping.get("enabled") is not False:
        raise Gate19_6PlanVerificationError(
            "planned SQS-to-worker event source mapping must remain disabled"
        )
    if api_gateway.get("disable_execute_api_endpoint") is not True:
        raise Gate19_6PlanVerificationError(
            "planned execute-api endpoint must remain disabled"
        )
    return {
        "api_environment_variables_plan_known": api_env_known,
        "worker_environment_variables_plan_known": worker_env_known,
    }


def _git_head() -> str:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise Gate19_6PlanVerificationError("cannot resolve repository HEAD") from exc
    if len(head) != 40:
        raise Gate19_6PlanVerificationError("repository HEAD is not a full SHA")
    return head


def _write_summary(
    output: Path,
    *,
    plan_bytes: bytes,
    plan: dict[str, object],
    source_head_sha: str,
    expected_inventory: set[str],
    artifacts: dict[str, dict[str, object]],
    publication: dict[str, object],
    plan_observability: dict[str, bool],
) -> None:
    summary = {
        "schema_version": 1,
        "artifact_type": "phase-19-gate-19-6-plan-admission:v1",
        "source_head_sha": source_head_sha,
        "plan_json_sha256": hashlib.sha256(plan_bytes).hexdigest(),
        "terraform_format_version": _required_string(plan, "format_version"),
        "terraform_version": _required_string(plan, "terraform_version"),
        "selected_design": _EXPECTED_DESIGN,
        "managed_create_count": len(expected_inventory),
        "managed_create_inventory": sorted(expected_inventory),
        "account_id": publication.get("account_id"),
        "region": publication.get("region"),
        "artifacts": {
            role: {
                "key": artifacts[role].get("key"),
                "version_id": artifacts[role].get("version_id"),
                "lambda_source_code_hash": artifacts[role].get(
                    "lambda_source_code_hash"
                ),
            }
            for role in sorted(_EXPECTED_ROLES)
        },
        "plan_observability": {
            **plan_observability,
            "unknown_environment_values_admitted_only_with_retained_gate19_4_source_contract": True,
        },
        "safety": {
            "plan_only": True,
            "remote_state_lock_disabled": True,
            "runtime_resources_mutated": 0,
            "iam_mutations": 0,
            "public_endpoint_enablements": 0,
            "provider_heavy_public_executions": 0,
            "terraform_apply_authorized": False,
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
    parser.add_argument("--plan-input", type=Path, default=_PLAN_INPUT)
    parser.add_argument("--gate19-4", type=Path, default=_GATE19_4)
    parser.add_argument("--publication", type=Path, default=_PUBLICATION)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    """Verify a Terraform plan without contacting AWS or mutating Terraform state."""
    args = _parser().parse_args()
    try:
        plan_bytes = args.plan_json.read_bytes()
        raw_plan = cast(object, json.loads(plan_bytes))
    except (OSError, json.JSONDecodeError) as exc:
        raise Gate19_6PlanVerificationError(
            f"cannot read Terraform plan JSON {args.plan_json}: {exc}"
        ) from exc

    plan = _object(raw_plan, label="plan")
    plan_input = _load(args.plan_input)
    gate19_4 = _load(args.gate19_4)
    publication = _load(args.publication)
    if gate19_4.get("selected_design") != _EXPECTED_DESIGN:
        raise Gate19_6PlanVerificationError("Gate 19.4 selected design drifted")
    if gate19_4.get("deployment_authorized") is not False:
        raise Gate19_6PlanVerificationError("Gate 19.4 deployment authority drifted")

    expected_inventory = set(
        _strings(
            gate19_4.get("terraform_resource_inventory"),
            label="Gate 19.4 terraform_resource_inventory",
        )
    )
    if len(expected_inventory) != 21:
        raise Gate19_6PlanVerificationError("Gate 19.4 resource inventory must remain 21")

    _verify_retained_gate19_4_source_contract()
    artifacts = _verify_plan_input(plan_input, publication)
    _verify_plan_variables(plan, plan_input)
    _verify_safety_outputs(plan)
    observed = _managed_change_inventory(plan, expected_inventory)
    plan_observability = _verify_critical_after_values(observed, plan_input)

    source_head_sha = _git_head()
    if args.output is not None:
        _write_summary(
            args.output,
            plan_bytes=plan_bytes,
            plan=plan,
            source_head_sha=source_head_sha,
            expected_inventory=expected_inventory,
            artifacts=artifacts,
            publication=publication,
            plan_observability=plan_observability,
        )

    print(
        "phase19_gate19_6_plan=PASS "
        f"managed_creates={len(expected_inventory)} "
        "updates=0 deletes=0 replacements=0 "
        "execute_api_endpoint_disabled=true "
        "worker_event_source_enabled=false "
        "worker_reserved_concurrency=0 "
        "terraform_apply_authorized=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
