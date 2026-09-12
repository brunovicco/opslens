"""Unit tests for the admitted Gate 19.6 human exact-plan evidence."""

import json
from pathlib import Path
from typing import cast

EVIDENCE_PATH = Path("labs/evidence/phase-19-gate-19-6-plan-admission-v1.json")

EXPECTED_INVENTORY = {
    "aws_apigatewayv2_api.public_async",
    "aws_apigatewayv2_integration.public_async_api_lambda",
    "aws_apigatewayv2_route.public_async_result",
    "aws_apigatewayv2_route.public_async_status",
    "aws_apigatewayv2_route.public_async_submit",
    "aws_apigatewayv2_stage.public_async_default",
    "aws_cloudwatch_log_group.public_async_access",
    "aws_cloudwatch_log_group.public_async_api",
    "aws_cloudwatch_log_group.public_async_worker",
    "aws_dynamodb_table.public_async_jobs",
    "aws_iam_role.public_async_api",
    "aws_iam_role.public_async_worker",
    "aws_iam_role_policy.public_async_api",
    "aws_iam_role_policy.public_async_worker",
    "aws_lambda_event_source_mapping.public_async_worker",
    "aws_lambda_function.public_async_api",
    "aws_lambda_function.public_async_worker",
    "aws_lambda_permission.public_async_api_gateway",
    "aws_sqs_queue.public_async_job_dlq",
    "aws_sqs_queue.public_async_job_queue",
    "aws_sqs_queue_redrive_allow_policy.public_async_job_dlq",
}

API_ARTIFACT_KEY = (
    "lambda/public-analysis/api/"
    "sha256=99477676dcc41345c63ed28c81bb41c7f9f47bcf5b072254bc1ef0e2cfcd876e/"
    "opslens-public-async-api.zip"
)
WORKER_ARTIFACT_KEY = (
    "lambda/public-analysis/worker/"
    "sha256=0d04b472476ad7825b5190352da1642db9a7d42d1ce349d21a39fac8f6ecbdc9/"
    "opslens-public-async-worker.zip"
)


def _load() -> dict[str, object]:
    """Load the bounded committed admission evidence."""
    raw = cast(object, json.loads(EVIDENCE_PATH.read_text(encoding="utf-8")))
    assert isinstance(raw, dict)
    return cast(dict[str, object], raw)


def test_gate19_6_human_plan_admission_evidence_is_frozen() -> None:
    """Freeze the admitted source, inventory, artifacts, and safety decisions."""
    evidence = _load()

    assert evidence["schema_version"] == 1
    assert evidence["artifact_type"] == "phase-19-gate-19-6-plan-admission:v1"
    assert evidence["source_head_sha"] == "d4d852c7ebc97f6fd9ee19d868fa12bc4ab031f2"
    assert evidence["plan_json_sha256"] == (
        "eb01396b92879243fd2e16e7791957e3289b459facc9db9524a4d890574aa83f"
    )
    assert evidence["selected_design"] == "HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB"
    assert evidence["account_id"] == "487757851499"
    assert evidence["region"] == "us-east-1"
    assert evidence["terraform_format_version"] == "1.2"
    assert evidence["terraform_version"] == "1.15.8"

    inventory = evidence["managed_create_inventory"]
    assert isinstance(inventory, list)
    assert evidence["managed_create_count"] == 21
    assert set(cast(list[str], inventory)) == EXPECTED_INVENTORY

    artifacts = evidence["artifacts"]
    assert isinstance(artifacts, dict)
    typed_artifacts = cast(dict[str, dict[str, object]], artifacts)
    assert typed_artifacts["api"] == {
        "key": API_ARTIFACT_KEY,
        "lambda_source_code_hash": "mUd2dtzEE0XGPtKMgbtBx/n0e89bByJUvB7w4s/Nh24=",
        "version_id": "E.jfB7dlkGCD.wHAurP7QXo4fuS_PW63",
    }
    assert typed_artifacts["worker"] == {
        "key": WORKER_ARTIFACT_KEY,
        "lambda_source_code_hash": "DQS0ckdq14JbUZA1LaFkLbmn1C0c40nSGjn6yPbsvck=",
        "version_id": "sxiOdii4yFwR13t23xP5A8EU1JPV_7P1",
    }

    assert evidence["plan_observability"] == {
        "api_environment_variables_plan_known": False,
        "unknown_environment_values_admitted_only_with_retained_gate19_4_source_contract": True,
        "worker_environment_variables_plan_known": False,
    }
    assert evidence["safety"] == {
        "iam_mutations": 0,
        "plan_only": True,
        "provider_heavy_public_executions": 0,
        "public_endpoint_enablements": 0,
        "remote_state_lock_disabled": True,
        "runtime_resources_mutated": 0,
        "terraform_apply_authorized": False,
    }
