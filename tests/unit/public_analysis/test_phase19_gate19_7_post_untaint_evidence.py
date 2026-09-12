"""Fail-closed tests for Gate 19.7 post-untaint evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

EVIDENCE = Path(
    "labs/evidence/phase-19-gate-19-7-post-untaint-verification-v1.json"
)


def _load() -> dict[str, object]:
    raw = cast(object, json.loads(EVIDENCE.read_text(encoding="utf-8")))
    assert isinstance(raw, dict)
    return cast(dict[str, object], raw)


def test_gate19_7_post_untaint_state_transition_is_bounded() -> None:
    """Require one-target taint clearance with stable lineage and inventory."""
    evidence = _load()

    assert evidence["artifact_type"] == (
        "phase-19-gate-19-7-post-untaint-verification:v1"
    )
    assert evidence["protected_source_head_sha"] == (
        "c9bba86e231d471c8f56b415f49023dc26dedf46"
    )

    operation = evidence["authorized_operation"]
    assert isinstance(operation, dict)
    typed_operation = cast(dict[str, object], operation)
    assert typed_operation == {
        "operation": "terraform untaint",
        "target": "aws_lambda_function.public_async_api[0]",
        "execution_succeeded": True,
        "maximum_target_count": 1,
    }

    state = evidence["terraform_state"]
    assert isinstance(state, dict)
    typed_state = cast(dict[str, object], state)
    assert typed_state["lineage_unchanged"] is True
    assert typed_state["lineage_before"] == typed_state["lineage_after"]
    assert typed_state["serial_before"] == 115
    assert typed_state["serial_after"] == 116
    assert typed_state["serial_increment"] == 1
    assert typed_state["target_status_before"] == "tainted"
    assert typed_state["target_status_after"] == "READY_OR_UNMARKED"
    assert typed_state["target_tainted_before"] is True
    assert typed_state["target_tainted_after"] is False
    assert typed_state["resource_inventory_unchanged"] is True


def test_gate19_7_post_untaint_proves_no_aws_runtime_change() -> None:
    """Freeze the remote Lambda non-mutation proof and disabled submit switch."""
    evidence = _load()
    api = evidence["aws_remote_api_lambda"]
    assert isinstance(api, dict)
    typed_api = cast(dict[str, object], api)

    assert typed_api["configuration_unchanged"] is True
    assert typed_api["state"] == "Active"
    assert typed_api["last_update_status"] == "Successful"
    assert typed_api["code_sha256"] == (
        "mUd2dtzEE0XGPtKMgbtBx/n0e89bByJUvB7w4s/Nh24="
    )
    assert typed_api["submit_switch"] == "false"
    assert typed_api["reserved_concurrency"] is None
    assert typed_api["reserved_concurrency_observation"] == (
        "NOT_CONFIGURED_OR_NOT_OBSERVED"
    )


def test_gate19_7_post_untaint_resets_authority_fail_closed() -> None:
    """Require all mutation and runtime authorities to remain false."""
    evidence = _load()
    authority = evidence["authority"]
    assert isinstance(authority, dict)
    typed_authority = cast(dict[str, object], authority)
    assert typed_authority
    assert all(value is False for value in typed_authority.values())

    quarantine = evidence["quarantine"]
    assert isinstance(quarantine, dict)
    typed_quarantine = cast(dict[str, object], quarantine)
    assert typed_quarantine["original_failed_plan_present"] is True
    assert typed_quarantine["rejected_recovery_plan_present"] is True
    assert typed_quarantine["failed_plan_reusable"] is False
    assert typed_quarantine["rejected_plan_reusable"] is False


def test_gate19_7_post_untaint_next_plan_remains_non_destructive() -> None:
    """Freeze the expected recovery-plan shape without granting plan/apply authority."""
    evidence = _load()
    boundary = evidence["next_boundary"]
    assert isinstance(boundary, dict)
    typed_boundary = cast(dict[str, object], boundary)

    assert typed_boundary["fresh_recovery_plan_required"] is True
    assert typed_boundary["human_review_required_before_plan"] is True
    assert typed_boundary["expected_missing_creates"] == 5
    assert typed_boundary["maximum_existing_resource_updates"] == 1
    assert typed_boundary["allowed_existing_resource_update"] == (
        "aws_lambda_function.public_async_api"
    )
    assert typed_boundary["deletes_allowed"] == 0
    assert typed_boundary["replacements_allowed"] == 0
    assert typed_boundary["terraform_apply_authorized"] is False
