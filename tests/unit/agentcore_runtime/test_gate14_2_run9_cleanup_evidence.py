"""Regression coverage for the measured Gate 14.2 run 9 cleanup boundary."""

import json
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_RETIRED_POLICY_PATH = (
    _PROJECT_ROOT / "infra" / "bootstrap" / "github_agentcore_deploy_permissions.tf"
)
_EVIDENCE_PATH = (
    _PROJECT_ROOT
    / "labs"
    / "evidence"
    / "phase-14-gate-14-2-ninth-runtime-attempt-cleanup-iam-failure-v1.json"
)


def _load_evidence() -> dict[str, Any]:
    return json.loads(_EVIDENCE_PATH.read_text(encoding="utf-8"))


def test_run9_evidence_preserves_successful_replay_and_cleanup_failure() -> None:
    """Run 9 remains successful bounded execution evidence but failed cleanup evidence."""
    evidence = _load_evidence()

    assert evidence["source_main_sha"] == "9153bad5bef098598f84953bc157c1d369e176d8"
    assert evidence["workflow_run"]["id"] == 34357918962
    assert evidence["workflow_run"]["runtime_ready"] is True
    assert evidence["bounded_runtime_evidence"]["replay_cases"] == 6
    assert evidence["bounded_runtime_evidence"]["replay_passed"] == 6
    assert evidence["bounded_runtime_evidence"]["capability_executions"] == 0
    assert evidence["bounded_runtime_evidence"]["sdk_retry_attempts"] == 0
    assert evidence["terraform_cleanup"]["runtime_cleanup_proven"] is False
    assert evidence["human_control_plane_checkpoint"]["status"] == "READY"


def test_run9_cloudtrail_classification_matches_measured_delete_dependency() -> None:
    """CloudTrail must pin the cleanup failure to directory-scoped DeleteWorkloadIdentity."""
    evidence = _load_evidence()
    event = evidence["cloudtrail_delete_event"]

    assert event["event_name"] == "DeleteAgentRuntime"
    assert event["error_code"] == "AccessDenied"
    assert event["missing_action"] == "bedrock-agentcore:DeleteWorkloadIdentity"
    assert event["authorization_resource"] == (
        "arn:aws:bedrock-agentcore:us-east-1:487757851499:"
        "workload-identity-directory/default"
    )
    assert event["request_id"] == "a83c40f9-bc85-4c84-a1da-c20e3d3f24eb"


def test_run9_historical_invariants_survive_policy_retirement() -> None:
    """Retiring the policy must preserve the historical run 9 least-privilege evidence."""
    evidence = _load_evidence()
    invariants = evidence["authority_invariants"]

    assert invariants["github_deployment_get_workload_identity_authority"] is False
    assert invariants["github_deployment_create_service_linked_role_authority"] is False
    assert invariants["github_deployment_runtime_invoke_authority"] is False
    assert invariants["delete_workload_identity_wildcard_resource_authority"] is False
    assert not _RETIRED_POLICY_PATH.exists()
