"""Fail-closed tests for Gate 19.7 post-apply evidence."""

import json
from pathlib import Path
from typing import cast

EVIDENCE = Path(
    "labs/evidence/phase-19-gate-19-7-post-apply-verification-v1.json"
)


def _load() -> dict[str, object]:
    raw = cast(object, json.loads(EVIDENCE.read_text(encoding="utf-8")))
    assert isinstance(raw, dict)
    return cast(dict[str, object], raw)


def test_gate19_7_post_apply_identity_and_action_shape_are_exact() -> None:
    """Require the exact single-use plan identity and admitted apply shape."""
    evidence = _load()

    assert evidence["artifact_type"] == (
        "phase-19-gate-19-7-post-apply-verification:v1"
    )

    identity = evidence["plan_identity"]
    assert isinstance(identity, dict)
    typed_identity = cast(dict[str, object], identity)
    assert typed_identity == {
        "source_head_sha": "d6546e9d48253694e3e276940ebd2388f301d8ad",
        "protected_evidence_checkpoint": (
            "fd590df290502950b9dccc7eef93abcabff6d039"
        ),
        "plan_binary_sha256": (
            "48cb15a8466cc0ce77fdbe1d827b5a0aebb88460b8e8151d8c88d3c85eb9ea55"
        ),
        "plan_json_sha256": (
            "8a1f95ab8cbcbf96c708c6ced0d0127d862391a6f8e72c250fe5e7499d2a0bf7"
        ),
    }

    apply = evidence["authorized_apply"]
    assert isinstance(apply, dict)
    typed_apply = cast(dict[str, object], apply)
    assert typed_apply == {
        "invocation_count": 1,
        "execution_succeeded": True,
        "authorization_consumed": True,
        "retry_authorized": False,
        "resources_added": 5,
        "resources_changed": 1,
        "resources_destroyed": 0,
    }


def test_gate19_7_post_apply_state_delta_is_bounded() -> None:
    """Freeze the exact five additions and stable Terraform lineage."""
    evidence = _load()
    state = evidence["terraform_state"]
    assert isinstance(state, dict)
    typed_state = cast(dict[str, object], state)

    assert typed_state["lineage_before"] == (
        "6c958ab2-4cc6-7f96-a528-89535504f65c"
    )
    assert typed_state["lineage_after"] == typed_state["lineage_before"]
    assert typed_state["lineage_unchanged"] is True
    assert typed_state["serial_before"] == 116
    assert typed_state["serial_after"] == 117
    assert typed_state["serial_advanced"] is True
    assert typed_state["removed_resource_addresses"] == []
    assert typed_state["added_resource_addresses"] == [
        "aws_apigatewayv2_integration.public_async_api_lambda[0]",
        "aws_apigatewayv2_route.public_async_result[0]",
        "aws_apigatewayv2_route.public_async_status[0]",
        "aws_apigatewayv2_route.public_async_submit[0]",
        "aws_lambda_permission.public_async_api_gateway[0]",
    ]


def test_gate19_7_post_apply_runtime_remains_disabled() -> None:
    """Require materialization without any runtime enablement path."""
    evidence = _load()
    controls = evidence["materialized_controls"]
    assert isinstance(controls, dict)
    typed_controls = cast(dict[str, object], controls)

    assert typed_controls["api_id"] == "4f9jxjh7mj"
    assert typed_controls["execute_api_endpoint_disabled"] is True
    assert typed_controls["submit_switch"] == "false"
    assert typed_controls["api_reserved_concurrency"] == 0
    assert typed_controls["worker_switch"] == "false"
    assert typed_controls["worker_reserved_concurrency"] == 0
    assert typed_controls["worker_event_source_mapping_state"] == "Disabled"
    assert typed_controls["custom_domain_mapping_present"] is False
    assert (
        typed_controls["provider_heavy_public_execution_path_enabled"] is False
    )

    artifacts = evidence["artifacts"]
    assert isinstance(artifacts, dict)
    typed_artifacts = cast(dict[str, object], artifacts)
    assert typed_artifacts["api_lambda_source_code_hash"] == (
        "mUd2dtzEE0XGPtKMgbtBx/n0e89bByJUvB7w4s/Nh24="
    )
    assert typed_artifacts["worker_lambda_source_code_hash"] == (
        "DQS0ckdq14JbUZA1LaFkLbmn1C0c40nSGjn6yPbsvck="
    )


def test_gate19_7_post_apply_authority_resets_fail_closed() -> None:
    """Require consumed apply authority and no implicit next mutation authority."""
    evidence = _load()
    authority = evidence["authority_after_apply"]
    assert isinstance(authority, dict)
    typed_authority = cast(dict[str, object], authority)

    assert typed_authority["terraform_apply_authorization_consumed"] is True

    false_keys = {
        "terraform_apply_retry_authorized",
        "additional_terraform_apply_authorized",
        "terraform_replan_authorized",
        "terraform_destroy_authorized",
        "terraform_replacement_authorized",
        "terraform_import_authorized",
        "terraform_state_rm_authorized",
        "terraform_untaint_authorized",
        "runtime_enablement_authorized",
        "public_endpoint_enablement_authorized",
        "worker_enablement_authorized",
        "event_source_enablement_authorized",
        "provider_heavy_execution_authorized",
    }

    assert false_keys <= typed_authority.keys()
    assert all(typed_authority[key] is False for key in false_keys)

    boundary = evidence["next_boundary"]
    assert isinstance(boundary, dict)
    typed_boundary = cast(dict[str, object], boundary)
    assert typed_boundary["protected_post_apply_evidence_required"] is True
    assert typed_boundary["runtime_remains_disabled"] is True
    assert typed_boundary["gate19_7_materialization_complete_candidate"] is True
