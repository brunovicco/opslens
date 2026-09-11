#!/usr/bin/env python3
"""Verify the Gate 19.4 disabled async runtime without AWS or provider access."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import cast

_ARTIFACT = Path("labs/evidence/phase-19-gate-19-4-disabled-async-runtime-v1.json")
_GATE19_3 = Path("labs/evidence/phase-19-gate-19-3-async-topology-contract-v1.json")
_RUNTIME_TF = Path("infra/environments/dev/public_async_runtime.tf")
_IAM_TF = Path("infra/environments/dev/public_async_runtime_iam.tf")
_OBSERVABILITY_TF = Path("infra/environments/dev/public_async_runtime_observability.tf")
_RUNTIME_CONFIG = Path("src/opslens/public_analysis/async_runtime_config.py")
_LAMBDA_COMPOSITION = Path("src/opslens/public_analysis/async_lambda.py")

_EXPECTED_SOURCE_MAIN_SHA = "18d31c03d27448c88a6ffcba16683f3875a5ba15"
_EXPECTED_DESIGN = "HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB"
_EXPECTED_INTERACTION = "ASYNC_SUBMIT_STATUS_RESULT"

_EXPECTED_RESOURCES = {
    "aws_dynamodb_table.public_async_jobs",
    "aws_sqs_queue.public_async_job_dlq",
    "aws_sqs_queue.public_async_job_queue",
    "aws_sqs_queue_redrive_allow_policy.public_async_job_dlq",
    "aws_lambda_function.public_async_api",
    "aws_lambda_function.public_async_worker",
    "aws_lambda_event_source_mapping.public_async_worker",
    "aws_apigatewayv2_api.public_async",
    "aws_apigatewayv2_integration.public_async_api_lambda",
    "aws_apigatewayv2_route.public_async_submit",
    "aws_apigatewayv2_route.public_async_status",
    "aws_apigatewayv2_route.public_async_result",
    "aws_apigatewayv2_stage.public_async_default",
    "aws_lambda_permission.public_async_api_gateway",
    "aws_cloudwatch_log_group.public_async_api",
    "aws_cloudwatch_log_group.public_async_worker",
    "aws_cloudwatch_log_group.public_async_access",
    "aws_iam_role.public_async_api",
    "aws_iam_role_policy.public_async_api",
    "aws_iam_role.public_async_worker",
    "aws_iam_role_policy.public_async_worker",
}

_EXPECTED_API_BUSINESS_ACTIONS = {
    "sqs:SendMessage",
    "dynamodb:GetItem",
    "dynamodb:PutItem",
    "dynamodb:UpdateItem",
    "dynamodb:TransactWriteItems",
}

_EXPECTED_WORKER_BUSINESS_ACTIONS = {
    "sqs:ReceiveMessage",
    "sqs:DeleteMessage",
    "sqs:ChangeMessageVisibility",
    "sqs:GetQueueAttributes",
    "dynamodb:GetItem",
    "dynamodb:UpdateItem",
    "bedrock:Retrieve",
    "bedrock:InvokeModel",
}

_EXPECTED_RUNTIME_SUPPORT_ACTIONS = {
    "logs:CreateLogStream",
    "logs:PutLogEvents",
    "xray:PutTelemetryRecords",
    "xray:PutTraceSegments",
}

_EXPECTED_LIMITS = {
    "api_reserved_concurrency": 2,
    "worker_reserved_concurrency": 0,
    "api_timeout_seconds": 15,
    "worker_timeout_seconds": 60,
    "queue_visibility_seconds": 120,
    "queue_redrive_receive_count": 4,
    "worker_max_attempts": 3,
    "http_api_throttling_burst_limit": 10,
    "http_api_throttling_rate_limit": 5,
}

_RESOURCE_RE = re.compile(r'^resource\s+"([^"]+)"\s+"([^"]+)"\s+\{', re.MULTILINE)


class Gate19_4VerificationError(ValueError):
    """Reject drift or accidental authority expansion in Gate 19.4 evidence."""


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise Gate19_4VerificationError(f"{label} must be a JSON object")
    return cast(dict[str, object], value)


def _objects(value: object, *, label: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise Gate19_4VerificationError(f"{label} must be a JSON array")
    result: list[dict[str, object]] = []
    for index, item in enumerate(cast(list[object], value)):
        result.append(_object(item, label=f"{label}[{index}]"))
    return result


def _strings(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise Gate19_4VerificationError(f"{label} must be a string array")
    values = cast(list[object], value)
    if any(type(item) is not str for item in values):
        raise Gate19_4VerificationError(f"{label} must be a string array")
    return cast(list[str], values)


def _load_json(path: Path) -> dict[str, object]:
    try:
        parsed = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Gate19_4VerificationError(f"could not load {path}") from exc
    return _object(parsed, label=str(path))


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Gate19_4VerificationError(f"could not read {path}") from exc


def _require_contains(text: str, needle: str, *, label: str) -> None:
    if needle not in text:
        raise Gate19_4VerificationError(f"{label} is missing required text {needle!r}")


def _require_absent(text: str, needle: str, *, label: str) -> None:
    if needle in text:
        raise Gate19_4VerificationError(f"{label} contains forbidden text {needle!r}")


def _segment(text: str, *, start: str, end: str, label: str) -> str:
    start_index = text.find(start)
    if start_index < 0:
        raise Gate19_4VerificationError(f"{label} start marker is missing")
    end_index = text.find(end, start_index + len(start))
    if end_index < 0:
        raise Gate19_4VerificationError(f"{label} end marker is missing")
    return text[start_index:end_index]


def _verify_identity(root: dict[str, object], gate19_3: dict[str, object]) -> None:
    expected: dict[str, object] = {
        "artifact_type": "phase-19-gate-19-4-disabled-async-runtime:v1",
        "schema_version": 1,
        "phase": 19,
        "gate": "19.4",
        "issue": 350,
        "pr": 351,
        "source_main_sha": _EXPECTED_SOURCE_MAIN_SHA,
        "source_gate_19_3_artifact": str(_GATE19_3),
        "selected_design": _EXPECTED_DESIGN,
        "interaction_pattern": _EXPECTED_INTERACTION,
        "status": "IMPLEMENTED_DISABLED_NO_DEPLOYMENT",
        "deployment_authorized": False,
    }
    for field, expected_value in expected.items():
        if root.get(field) != expected_value:
            raise Gate19_4VerificationError(f"Gate 19.4 identity drifted at {field}")

    if gate19_3.get("decision") != _EXPECTED_DESIGN:
        raise Gate19_4VerificationError("Gate 19.3 selected design drifted")
    if gate19_3.get("source_gate_19_2_decision") != _EXPECTED_INTERACTION:
        raise Gate19_4VerificationError("Gate 19.3 interaction pattern drifted")
    if gate19_3.get("deployment_authorized") is not False:
        raise Gate19_4VerificationError("Gate 19.3 unexpectedly authorizes deployment")

    authority = _object(root.get("authority_impact"), label="authority_impact")
    expected_authority = {
        "public_endpoints_enabled": 0,
        "aws_resources_created_changed_deleted": 0,
        "iam_roles_or_policies_created_changed": 0,
        "aws_or_provider_live_executions": 0,
        "third_party_repository_code_executions": 0,
        "pr_89_modifications": 0,
    }
    if authority != expected_authority:
        raise Gate19_4VerificationError("Gate 19.4 acquired deployment or execution authority")


def _verify_defaults(root: dict[str, object], runtime_tf: str) -> None:
    defaults = _object(root.get("fail_closed_defaults"), label="fail_closed_defaults")
    expected_defaults = {
        "runtime_materialized": False,
        "execute_api_endpoint_disabled": True,
        "submit_enabled": False,
        "worker_enabled": False,
        "worker_event_source_mapping_enabled": False,
        "worker_reserved_concurrency": 0,
        "custom_domain_present": False,
        "provider_executor_composed": False,
    }
    if defaults != expected_defaults:
        raise Gate19_4VerificationError("Gate 19.4 fail-closed defaults drifted")

    required_runtime_text = (
        'variable "public_async_runtime_materialized"',
        "default     = false",
        "public_async_runtime_count = var.public_async_runtime_materialized ? 1 : 0",
        "disable_execute_api_endpoint = true",
        "OPSLENS_ASYNC_SUBMIT_ENABLED            = \"false\"",
        "OPSLENS_ASYNC_WORKER_ENABLED        = \"false\"",
        "enabled                            = false",
        "reserved_concurrent_executions = 0",
    )
    for needle in required_runtime_text:
        _require_contains(runtime_tf, needle, label="public async runtime Terraform")
    _require_absent(
        runtime_tf,
        'resource "aws_apigatewayv2_domain_name"',
        label="public async runtime Terraform",
    )


def _resource_addresses(text: str) -> set[str]:
    return {f"{match.group(1)}.{match.group(2)}" for match in _RESOURCE_RE.finditer(text)}


def _verify_resource_inventory(
    root: dict[str, object], terraform_texts: tuple[str, ...]
) -> None:
    artifact_resources = set(
        _strings(root.get("terraform_resource_inventory"), label="terraform_resource_inventory")
    )
    if artifact_resources != _EXPECTED_RESOURCES:
        raise Gate19_4VerificationError("Gate 19.4 artifact resource inventory drifted")

    combined_resources: set[str] = set()
    for text in terraform_texts:
        combined_resources.update(_resource_addresses(text))
    if combined_resources != _EXPECTED_RESOURCES:
        unexpected = sorted(combined_resources - _EXPECTED_RESOURCES)
        missing = sorted(_EXPECTED_RESOURCES - combined_resources)
        raise Gate19_4VerificationError(
            f"Gate 19.4 Terraform inventory mismatch; missing={missing}, unexpected={unexpected}"
        )

    for text in terraform_texts:
        matches = list(_RESOURCE_RE.finditer(text))
        for index, match in enumerate(matches):
            next_start = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            block_text = text[match.start():next_start]
            address = f"{match.group(1)}.{match.group(2)}"
            if "count = local.public_async_runtime_count" not in block_text:
                raise Gate19_4VerificationError(
                    f"{address} is not gated by the disabled materialization count"
                )


def _verify_iam(root: dict[str, object], iam_tf: str) -> None:
    binding = _object(
        root.get("iam_responsibility_binding"), label="iam_responsibility_binding"
    )
    api = _object(binding.get("api_handler_role"), label="api_handler_role")
    worker = _object(binding.get("worker_role"), label="worker_role")

    if set(_strings(api.get("business_actions"), label="api business_actions")) != (
        _EXPECTED_API_BUSINESS_ACTIONS
    ):
        raise Gate19_4VerificationError("API business authority drifted")
    if set(_strings(worker.get("business_actions"), label="worker business_actions")) != (
        _EXPECTED_WORKER_BUSINESS_ACTIONS
    ):
        raise Gate19_4VerificationError("worker business authority drifted")
    for role_name, role in (("api", api), ("worker", worker)):
        if set(_strings(role.get("runtime_support_actions"), label=f"{role_name} support")) != (
            _EXPECTED_RUNTIME_SUPPORT_ACTIONS
        ):
            raise Gate19_4VerificationError(f"{role_name} runtime support authority drifted")

    api_segment = _segment(
        iam_tf,
        start='data "aws_iam_policy_document" "public_async_api_runtime"',
        end='resource "aws_iam_role_policy" "public_async_api"',
        label="API IAM policy",
    )
    worker_segment = _segment(
        iam_tf,
        start='data "aws_iam_policy_document" "public_async_worker_runtime"',
        end='resource "aws_iam_role_policy" "public_async_worker"',
        label="worker IAM policy",
    )

    for action in _EXPECTED_API_BUSINESS_ACTIONS | _EXPECTED_RUNTIME_SUPPORT_ACTIONS:
        _require_contains(api_segment, f'"{action}"', label="API IAM policy")
    for forbidden in {
        "bedrock:InvokeModel",
        "bedrock:Retrieve",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:ChangeMessageVisibility",
        "dynamodb:Scan",
        "iam:",
    }:
        _require_absent(api_segment, forbidden, label="API IAM policy")
    for resource in (
        "aws_sqs_queue.public_async_job_queue[0].arn",
        "aws_dynamodb_table.public_async_jobs[0].arn",
    ):
        _require_contains(api_segment, resource, label="API IAM policy")

    for action in _EXPECTED_WORKER_BUSINESS_ACTIONS | _EXPECTED_RUNTIME_SUPPORT_ACTIONS:
        _require_contains(worker_segment, f'"{action}"', label="worker IAM policy")
    for forbidden in {
        "sqs:SendMessage",
        "dynamodb:PutItem",
        "dynamodb:TransactWriteItems",
        "dynamodb:Scan",
        "dynamodb:DeleteTable",
        "iam:",
    }:
        _require_absent(worker_segment, forbidden, label="worker IAM policy")
    for resource in (
        "aws_sqs_queue.public_async_job_queue[0].arn",
        "aws_dynamodb_table.public_async_jobs[0].arn",
        "local.public_async_knowledge_base_arn",
        "local.public_async_inference_profile_arn",
        "local.public_async_foundation_model_arns",
    ):
        _require_contains(worker_segment, resource, label="worker IAM policy")


def _verify_configured_limits(root: dict[str, object], runtime_tf: str) -> None:
    limits = _objects(root.get("configured_limits"), label="configured_limits")
    observed: dict[str, int] = {}
    for item in limits:
        name = item.get("name")
        value = item.get("value")
        classification = item.get("classification")
        if type(name) is not str or type(value) is not int:
            raise Gate19_4VerificationError("configured limit name/value types are invalid")
        if classification != "CONFIGURED_LIMIT":
            raise Gate19_4VerificationError(f"configured limit {name} was relabeled")
        observed[name] = value
    if observed != _EXPECTED_LIMITS:
        raise Gate19_4VerificationError("Gate 19.4 configured limits drifted")

    for needle in (
        "public_async_worker_timeout_seconds   = 60",
        "public_async_queue_visibility_seconds = 120",
        "public_async_redrive_receive_count    = 4",
        "public_async_max_attempts             = 3",
        "reserved_concurrent_executions = 2",
        "reserved_concurrent_executions = 0",
        "timeout                        = 15",
        "throttling_burst_limit   = 10",
        "throttling_rate_limit    = 5",
    ):
        _require_contains(runtime_tf, needle, label="configured-limit Terraform")


def _verify_runtime_fail_closed(
    root: dict[str, object],
    config_text: str,
    lambda_text: str,
) -> None:
    _require_contains(
        config_text,
        "environment.get(name, AsyncRuntimeSwitch.FALSE.value)",
        label="async runtime configuration",
    )
    for needle in (
        "async worker execution is enabled but provider executor composition is not admitted",
        "disabled worker must not access DynamoDB",
        "disabled worker must not execute provider-heavy analysis",
    ):
        _require_contains(lambda_text, needle, label="async Lambda composition")

    verification = _object(root.get("verification"), label="verification")
    expected_verification = {
        "offline_only": True,
        "aws_credentials_required": False,
        "terraform_apply_allowed": False,
        "provider_live_execution_allowed": False,
        "verifier": "scripts/verify_phase19_gate19_4_disabled_async_runtime.py",
    }
    if verification != expected_verification:
        raise Gate19_4VerificationError("Gate 19.4 verification boundary drifted")


def _verify_implementation_files(root: dict[str, object]) -> None:
    files = _strings(root.get("implementation_files"), label="implementation_files")
    if len(files) != len(set(files)):
        raise Gate19_4VerificationError("implementation_files contains duplicates")
    for path_value in files:
        if not Path(path_value).is_file():
            raise Gate19_4VerificationError(f"implementation file is missing: {path_value}")


def main() -> int:
    """Verify exact Gate 19.4 repository evidence without crossing a provider boundary."""
    root = _load_json(_ARTIFACT)
    gate19_3 = _load_json(_GATE19_3)
    runtime_tf = _read_text(_RUNTIME_TF)
    iam_tf = _read_text(_IAM_TF)
    observability_tf = _read_text(_OBSERVABILITY_TF)
    config_text = _read_text(_RUNTIME_CONFIG)
    lambda_text = _read_text(_LAMBDA_COMPOSITION)

    _verify_identity(root, gate19_3)
    _verify_defaults(root, runtime_tf)
    _verify_resource_inventory(root, (runtime_tf, iam_tf, observability_tf))
    _verify_iam(root, iam_tf)
    _verify_configured_limits(root, runtime_tf)
    _verify_runtime_fail_closed(root, config_text, lambda_text)
    _verify_implementation_files(root)

    print(
        "phase19_gate19_4=PASS "
        f"design={_EXPECTED_DESIGN} "
        "deployment_authorized=false "
        "runtime_materialized_default=false "
        "public_endpoints_enabled=0 "
        "aws_mutations=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
