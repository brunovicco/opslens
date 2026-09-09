"""Regression coverage for the measured Gate 14.2 run 10 delete-waiter boundary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_POLICY_PATH = _PROJECT_ROOT / "infra" / "bootstrap" / "github_agentcore_deploy_permissions.tf"
_EVIDENCE_PATH = (
    _PROJECT_ROOT
    / "labs"
    / "evidence"
    / "phase-14-gate-14-2-tenth-runtime-attempt-delete-waiter-read-failure-v1.json"
)


def _load_evidence() -> dict[str, Any]:
    return json.loads(_EVIDENCE_PATH.read_text(encoding="utf-8"))


def test_runtime_lifecycle_read_is_exact_family_scoped_without_tag_dependency() -> None:
    """Delete waiters must retain exact-family read authority after runtime tags stop matching."""
    text = _POLICY_PATH.read_text(encoding="utf-8")

    read_statement = text.split(
        'sid     = "ReadExactBoundedAgentCoreRuntimeLifecycle"', maxsplit=1
    )[1].split("\n  }", maxsplit=1)[0]

    assert 'actions = ["bedrock-agentcore:GetAgentRuntime"]' in read_statement
    assert "local.dev_agentcore_runtime_arn" in read_statement
    assert "local.dev_agentcore_runtime_precreation_arn" not in read_statement
    assert 'resources = ["*"]' not in read_statement
    assert "aws:ResourceTag/" not in read_statement
    assert "DeleteAgentRuntime" not in read_statement
    assert "UpdateAgentRuntime" not in read_statement
    assert "TagResource" not in read_statement
    assert "UntagResource" not in read_statement
    assert "InvokeAgentRuntime" not in read_statement


def test_runtime_mutation_remains_resource_tag_bounded() -> None:
    """Separating lifecycle reads must not weaken mutation/delete authorization."""
    text = _POLICY_PATH.read_text(encoding="utf-8")

    manage_statement = text.split(
        'sid    = "ManageExactBoundedAgentCoreRuntime"', maxsplit=1
    )[1].split("\n  }", maxsplit=1)[0]

    assert '"bedrock-agentcore:GetAgentRuntime"' not in manage_statement
    assert '"bedrock-agentcore:DeleteAgentRuntime"' in manage_statement
    assert '"bedrock-agentcore:UpdateAgentRuntime"' in manage_statement
    assert '"bedrock-agentcore:TagResource"' in manage_statement
    assert '"bedrock-agentcore:UntagResource"' in manage_statement
    assert "local.dev_agentcore_runtime_arn" in manage_statement
    assert 'variable = "aws:ResourceTag/Project"' in manage_statement
    assert 'variable = "aws:ResourceTag/Environment"' in manage_statement
    assert 'variable = "aws:ResourceTag/Purpose"' in manage_statement


def test_run10_evidence_preserves_successful_bounded_execution_and_failed_waiter() -> None:
    """Run 10 is successful runtime evidence but not successful workflow cleanup evidence."""
    evidence = _load_evidence()

    assert evidence["source_main_sha"] == "ac944c4c2592c428a8005b1c18fd35229c5324cf"
    assert evidence["workflow_run"]["id"] == 34375198394
    assert evidence["workflow_run"]["runtime_ready"] is True
    assert evidence["bounded_runtime_evidence"]["replay_cases"] == 6
    assert evidence["bounded_runtime_evidence"]["replay_passed"] == 6
    assert evidence["bounded_runtime_evidence"]["capability_executions"] == 0
    assert evidence["bounded_runtime_evidence"]["sdk_retry_attempts"] == 0
    assert evidence["terraform_cleanup"]["runtime_cleanup_proven_by_workflow"] is False


def test_run10_cloudtrail_proves_delete_then_late_read_denial() -> None:
    """CloudTrail must retain the measured successful delete and late waiter read transition."""
    evidence = _load_evidence()
    delete_event = evidence["cloudtrail_delete_event"]
    get_sequence = evidence["cloudtrail_get_agent_runtime_sequence"]

    assert delete_event["event_name"] == "DeleteAgentRuntime"
    assert delete_event["error_code"] is None
    assert delete_event["response_status"] == "DELETING"
    assert delete_event["request_id"] == "be5fde9b-94db-40bf-8826-28a680816b0d"

    assert len(get_sequence) == 6
    assert [item["error_code"] for item in get_sequence[:4]] == [None, None, None, None]
    assert [item["error_code"] for item in get_sequence[4:]] == [
        "AccessDenied",
        "AccessDenied",
    ]


def test_run10_human_checkpoint_proves_final_control_plane_absence() -> None:
    """Human authority must prove both runtime and managed identity ultimately disappeared."""
    checkpoint = _load_evidence()["human_control_plane_checkpoint"]

    assert checkpoint["get_agent_runtime_result"] == "ResourceNotFoundException"
    assert checkpoint["exact_name_list_count"] == 0
    assert checkpoint["get_workload_identity_result"] == "ResourceNotFoundException"
    assert checkpoint["runtime_absent"] is True
    assert checkpoint["managed_workload_identity_absent"] is True


def test_run10_remediation_preserves_authority_separation() -> None:
    """Measured waiter remediation must not widen data-plane or account-level authority."""
    policy = _POLICY_PATH.read_text(encoding="utf-8")
    invariants = _load_evidence()["authority_invariants"]

    assert invariants["github_deployment_runtime_read_wildcard_resource_authority"] is False
    assert invariants["github_deployment_runtime_invoke_authority"] is False
    assert invariants["github_deployment_get_workload_identity_authority"] is False
    assert invariants["github_deployment_create_service_linked_role_authority"] is False
    assert invariants["runtime_mutation_without_resource_tag_authority"] is False

    assert '"bedrock-agentcore:InvokeAgentRuntime"' not in policy
    assert '"bedrock-agentcore:GetWorkloadIdentity"' not in policy
    assert '"iam:CreateServiceLinkedRole"' not in policy
