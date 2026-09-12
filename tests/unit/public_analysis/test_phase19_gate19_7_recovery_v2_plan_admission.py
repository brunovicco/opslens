"""Fail-closed tests for Gate 19.7 recovery-v2 plan admission evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

EVIDENCE = Path(
    "labs/evidence/phase-19-gate-19-7-recovery-v2-plan-admission-v1.json"
)


def _load() -> dict[str, object]:
    raw = cast(object, json.loads(EVIDENCE.read_text(encoding="utf-8")))
    assert isinstance(raw, dict)
    return cast(dict[str, object], raw)


def test_gate19_7_recovery_v2_binds_exact_source_and_hashes() -> None:
    """Freeze the exact protected source and local plan identities."""
    evidence = _load()

    assert evidence["artifact_type"] == (
        "phase-19-gate-19-7-recovery-plan-admission:v1"
    )
    assert evidence["source_head_sha"] == (
        "d6546e9d48253694e3e276940ebd2388f301d8ad"
    )
    assert evidence["plan_binary_sha256"] == (
        "48cb15a8466cc0ce77fdbe1d827b5a0aebb88460b8e8151d8c88d3c85eb9ea55"
    )
    assert evidence["plan_json_sha256"] == (
        "8a1f95ab8cbcbf96c708c6ced0d0127d862391a6f8e72c250fe5e7499d2a0bf7"
    )
    assert evidence["account_id"] == "487757851499"
    assert evidence["region"] == "us-east-1"
    assert evidence["terraform_version"] == "1.15.8"
    assert evidence["terraform_format_version"] == "1.2"


def test_gate19_7_recovery_v2_action_shape_is_exact() -> None:
    """Allow only the five missing creates and one API-Lambda in-place update."""
    evidence = _load()

    assert evidence["managed_create_count"] == 5
    assert evidence["managed_create_inventory"] == [
        "aws_apigatewayv2_integration.public_async_api_lambda",
        "aws_apigatewayv2_route.public_async_result",
        "aws_apigatewayv2_route.public_async_status",
        "aws_apigatewayv2_route.public_async_submit",
        "aws_lambda_permission.public_async_api_gateway",
    ]
    assert evidence["managed_update_count"] == 1
    assert evidence["managed_update_inventory"] == [
        "aws_lambda_function.public_async_api"
    ]

    safety = evidence["safety"]
    assert isinstance(safety, dict)
    typed_safety = cast(dict[str, object], safety)
    assert typed_safety["managed_deletes"] == 0
    assert typed_safety["managed_replacements"] == 0
    assert typed_safety["public_endpoint_enablements"] == 0
    assert typed_safety["provider_heavy_public_executions"] == 0


def test_gate19_7_recovery_v2_retains_hard_disabled_concurrency() -> None:
    """Freeze API and worker reserved concurrency at zero in the admitted plan."""
    evidence = _load()
    recovery = evidence["recovery"]
    assert isinstance(recovery, dict)
    typed_recovery = cast(dict[str, object], recovery)

    assert typed_recovery["partial_state_recovery"] is True
    assert typed_recovery["api_reserved_concurrency"] == 0
    assert typed_recovery["worker_reserved_concurrency"] == 0
    assert typed_recovery["previous_failed_plan_retry_authorized"] is False
    assert typed_recovery["previous_failed_plan_reusable"] is False


def test_gate19_7_recovery_v2_apply_authority_remains_fail_closed() -> None:
    """Require a separate explicit human authorization before any apply."""
    evidence = _load()
    authority = evidence["authority"]
    assert isinstance(authority, dict)
    typed_authority = cast(dict[str, object], authority)

    assert typed_authority["fresh_plan"] is True
    assert typed_authority["materialized_not_enabled"] is True
    assert typed_authority["terraform_apply_authorized"] is False
    assert typed_authority["explicit_human_apply_authorization_required"] is True
    assert typed_authority["apply_authorization_status"] == (
        "PENDING_EXPLICIT_HUMAN_AUTHORIZATION"
    )

    observability = evidence["plan_observability"]
    assert isinstance(observability, dict)
    typed_observability = cast(dict[str, object], observability)
    assert typed_observability["api_environment_variables_plan_known"] is True
    assert typed_observability["worker_environment_variables_plan_known"] is True
