#!/usr/bin/env python3
"""Verify the Gate 19.7 partial-apply recovery contract entirely offline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

_RECONCILIATION = Path(
    "labs/evidence/phase-19-gate-19-7-failed-apply-reconciliation-v1.json"
)
_CONTRACT = Path("labs/evidence/phase-19-gate-19-7-recovery-contract-v1.json")
_OVERRIDE = Path("infra/environments/dev/public_async_runtime_recovery_override.tf")

_EXPECTED_MISSING = {
    "aws_apigatewayv2_integration.public_async_api_lambda",
    "aws_apigatewayv2_route.public_async_result",
    "aws_apigatewayv2_route.public_async_status",
    "aws_apigatewayv2_route.public_async_submit",
    "aws_lambda_permission.public_async_api_gateway",
}
_EXPECTED_FAILED_BINARY_SHA = (
    "4f9c7a07e792da2dfbde7ba38ecfb8286386a2fc7eba8ef79ae346b4a53e757d"
)
_EXPECTED_FAILED_JSON_SHA = (
    "5918eb69040af7ae3e7aa3fc428e4488b9ae6de98ebf8a0251f9faed2892580a"
)
_EXPECTED_FAILED_SOURCE_SHA = "71da658a27860aa538778ec64943c613f45b4636"


class Gate19_7RecoveryContractError(RuntimeError):
    """Raised when recovery evidence or authority drifts from the frozen contract."""


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise Gate19_7RecoveryContractError(f"{label} must be an object")
    raw = cast(dict[object, object], value)
    if any(type(key) is not str for key in raw):
        raise Gate19_7RecoveryContractError(f"{label} keys must be strings")
    return cast(dict[str, object], raw)


def _strings(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise Gate19_7RecoveryContractError(f"{label} must be an array")
    result: list[str] = []
    for item in cast(list[object], value):
        if type(item) is not str:
            raise Gate19_7RecoveryContractError(f"{label} values must be strings")
        result.append(item)
    return result


def _load(path: Path) -> dict[str, object]:
    try:
        parsed = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise Gate19_7RecoveryContractError(f"cannot load {path}: {exc}") from exc
    return _object(parsed, label=str(path))


def _verify_reconciliation(root: dict[str, object]) -> None:
    if root.get("artifact_type") != "phase-19-gate-19-7-failed-apply-reconciliation:v1":
        raise Gate19_7RecoveryContractError("reconciliation artifact type drifted")

    authority = _object(root.get("authority"), label="reconciliation.authority")
    for field in (
        "retry_authorized",
        "terraform_apply_authorized",
        "runtime_enablement_authorized",
        "public_endpoint_enablement_authorized",
        "worker_enablement_authorized",
        "event_source_enablement_authorized",
        "provider_heavy_execution_authorized",
    ):
        if authority.get(field) is not False:
            raise Gate19_7RecoveryContractError(
                f"reconciliation unexpectedly authorizes {field}"
            )

    failed_plan = _object(root.get("failed_plan"), label="reconciliation.failed_plan")
    expected_plan = {
        "source_head_sha": _EXPECTED_FAILED_SOURCE_SHA,
        "plan_binary_sha256": _EXPECTED_FAILED_BINARY_SHA,
        "plan_json_sha256": _EXPECTED_FAILED_JSON_SHA,
        "quarantined": True,
        "reusable": False,
    }
    if failed_plan != expected_plan:
        raise Gate19_7RecoveryContractError("failed-plan authority drifted")

    failure = _object(root.get("failure_classification"), label="failure_classification")
    if failure.get("class") != "LAMBDA_RESERVED_CONCURRENCY_ACCOUNT_CONSTRAINT":
        raise Gate19_7RecoveryContractError("failure classification drifted")
    if failure.get("failed_resource") != "aws_lambda_function.public_async_api":
        raise Gate19_7RecoveryContractError("unexpected failed resource")
    if failure.get("failed_operation") != "PutFunctionConcurrency":
        raise Gate19_7RecoveryContractError("unexpected failed operation")
    if failure.get("requested_reserved_concurrency") != 2:
        raise Gate19_7RecoveryContractError("unexpected failed concurrency request")
    if failure.get("safe_retry_without_new_review") is not False:
        raise Gate19_7RecoveryContractError("failed plan became retryable")

    account = _object(root.get("lambda_account"), label="lambda_account")
    if account.get("concurrent_executions_limit") != 10:
        raise Gate19_7RecoveryContractError("observed Lambda account limit drifted")
    if account.get("unreserved_concurrent_executions") is not None:
        raise Gate19_7RecoveryContractError(
            "unmeasured unreserved concurrency must remain null"
        )

    state = _object(root.get("terraform_state"), label="terraform_state")
    if state.get("currently_managed_expected_resources") != 16:
        raise Gate19_7RecoveryContractError("partial managed-resource count drifted")
    if state.get("expected_gate19_7_resources") != 21:
        raise Gate19_7RecoveryContractError("expected resource count drifted")
    missing = set(
        _strings(state.get("missing_expected_resources"), label="missing_expected_resources")
    )
    if missing != _EXPECTED_MISSING:
        raise Gate19_7RecoveryContractError("partial-state missing inventory drifted")
    unexpected = _strings(
        state.get("unexpected_public_async_resources"),
        label="unexpected_public_async_resources",
    )
    if unexpected:
        raise Gate19_7RecoveryContractError("unexpected public-async resources exist")

    controls = _object(root.get("runtime_controls_observed"), label="runtime_controls")
    expected_controls = {
        "api_reserved_concurrency": None,
        "api_submit_switch": "false",
        "http_api_execute_endpoint_disabled": True,
        "worker_event_source_states": ["Disabled"],
        "worker_reserved_concurrency": 0,
        "worker_switch": "false",
    }
    if controls != expected_controls:
        raise Gate19_7RecoveryContractError("observed disabled controls drifted")

    artifacts = _object(root.get("artifact_observation"), label="artifact_observation")
    if artifacts.get("api_code_sha256") != artifacts.get("expected_api_code_sha256"):
        raise Gate19_7RecoveryContractError("API artifact hash mismatch")
    if artifacts.get("worker_code_sha256") != artifacts.get("expected_worker_code_sha256"):
        raise Gate19_7RecoveryContractError("worker artifact hash mismatch")


def _verify_contract(root: dict[str, object]) -> None:
    if root.get("artifact_type") != "phase-19-gate-19-7-recovery-contract:v1":
        raise Gate19_7RecoveryContractError("recovery contract type drifted")
    if root.get("source_issue") != 361:
        raise Gate19_7RecoveryContractError("recovery contract source issue drifted")

    failed_plan = _object(root.get("failed_plan"), label="contract.failed_plan")
    if failed_plan.get("source_head_sha") != _EXPECTED_FAILED_SOURCE_SHA:
        raise Gate19_7RecoveryContractError("contract failed source SHA drifted")
    if failed_plan.get("plan_binary_sha256") != _EXPECTED_FAILED_BINARY_SHA:
        raise Gate19_7RecoveryContractError("contract failed binary SHA drifted")
    if failed_plan.get("plan_json_sha256") != _EXPECTED_FAILED_JSON_SHA:
        raise Gate19_7RecoveryContractError("contract failed JSON SHA drifted")
    if failed_plan.get("retry_authorized") is not False or failed_plan.get("reusable") is not False:
        raise Gate19_7RecoveryContractError("contract accidentally reauthorizes failed plan")

    partial = _object(root.get("partial_materialization"), label="partial_materialization")
    if partial.get("expected_total_resources") != 21:
        raise Gate19_7RecoveryContractError("recovery total resource count drifted")
    if partial.get("managed_expected_resources") != 16:
        raise Gate19_7RecoveryContractError("recovery partial state count drifted")
    missing = set(
        _strings(partial.get("missing_expected_resources"), label="contract missing inventory")
    )
    if missing != _EXPECTED_MISSING:
        raise Gate19_7RecoveryContractError("recovery missing inventory drifted")

    recovery_source = _object(root.get("recovery_source"), label="recovery_source")
    if recovery_source.get("api_reserved_concurrency") != 0:
        raise Gate19_7RecoveryContractError("recovery API concurrency must be zero")
    if recovery_source.get("worker_reserved_concurrency") != 0:
        raise Gate19_7RecoveryContractError("recovery worker concurrency must remain zero")
    if recovery_source.get("historical_gate19_4_configured_api_reserved_concurrency") != 2:
        raise Gate19_7RecoveryContractError("historical Gate 19.4 limit was rewritten")
    if recovery_source.get("historical_gate19_4_evidence_rewritten") is not False:
        raise Gate19_7RecoveryContractError("historical evidence rewrite is forbidden")

    expected_plan = _object(root.get("expected_recovery_plan"), label="expected_recovery_plan")
    create_inventory = set(
        _strings(expected_plan.get("expected_create_inventory"), label="expected create inventory")
    )
    if create_inventory != _EXPECTED_MISSING:
        raise Gate19_7RecoveryContractError("recovery create inventory drifted")
    allowed_updates = _strings(
        expected_plan.get("allowed_update_inventory"), label="allowed update inventory"
    )
    if allowed_updates != ["aws_lambda_function.public_async_api"]:
        raise Gate19_7RecoveryContractError("recovery update authority broadened")
    allowed_api_update = _object(
        expected_plan.get("allowed_api_update"), label="allowed_api_update"
    )
    if allowed_api_update != {"reserved_concurrent_executions": 0}:
        raise Gate19_7RecoveryContractError("recovery API update drifted")
    for field in (
        "deletes_allowed",
        "replacements_allowed",
        "unrelated_managed_changes_allowed",
    ):
        if expected_plan.get(field) != 0:
            raise Gate19_7RecoveryContractError(f"{field} must remain zero")

    authority = _object(root.get("authority"), label="contract.authority")
    for field in (
        "terraform_apply_authorized",
        "runtime_enablement_authorized",
        "public_endpoint_enablement_authorized",
        "worker_enablement_authorized",
        "event_source_enablement_authorized",
        "provider_heavy_execution_authorized",
        "iam_broadening_authorized",
        "custom_domain_creation_authorized",
        "failed_plan_retry_authorized",
    ):
        if authority.get(field) is not False:
            raise Gate19_7RecoveryContractError(f"recovery contract authorizes {field}")
    if authority.get("explicit_human_apply_authorization_required") is not True:
        raise Gate19_7RecoveryContractError("explicit human recovery apply authorization is required")


def _verify_override(text: str) -> None:
    required = (
        'resource "aws_lambda_function" "public_async_api"',
        "reserved_concurrent_executions = 0",
        "historical Gate 19.4",
        "later, separately authorized runtime-enablement gate",
    )
    for needle in required:
        if needle not in text:
            raise Gate19_7RecoveryContractError(
                f"recovery override is missing required text {needle!r}"
            )
    forbidden = (
        "OPSLENS_ASYNC_SUBMIT_ENABLED = \"true\"",
        "OPSLENS_ASYNC_WORKER_ENABLED = \"true\"",
        "enabled = true",
    )
    for needle in forbidden:
        if needle in text:
            raise Gate19_7RecoveryContractError(
                f"recovery override contains forbidden enablement {needle!r}"
            )


def main() -> int:
    """Verify partial-state evidence and recovery authority without provider access."""
    reconciliation = _load(_RECONCILIATION)
    contract = _load(_CONTRACT)
    try:
        override = _OVERRIDE.read_text(encoding="utf-8")
    except OSError as exc:
        raise Gate19_7RecoveryContractError(f"cannot read {_OVERRIDE}: {exc}") from exc

    _verify_reconciliation(reconciliation)
    _verify_contract(contract)
    _verify_override(override)

    print(
        "phase19_gate19_7_recovery_contract=PASS "
        "partial_managed=16 missing_creates=5 "
        "api_reserved_concurrency_recovery=0 "
        "failed_plan_retry_authorized=false "
        "terraform_apply_authorized=false materialized_not_enabled=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
