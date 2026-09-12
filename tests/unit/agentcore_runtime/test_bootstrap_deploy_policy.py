"""Regression tests for the Gate 14.4 AgentCore bootstrap IAM retirement."""

import json
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEPLOY_POLICY_PATH = (
    _PROJECT_ROOT / "infra" / "bootstrap" / "github_agentcore_deploy_permissions.tf"
)
_REPLAY_ROLE_PATH = (
    _PROJECT_ROOT / "infra" / "bootstrap" / "github_agentcore_replay_role.tf"
)
_OUTPUTS_PATH = _PROJECT_ROOT / "infra" / "bootstrap" / "outputs.tf"
_PREDEPLOY_EVIDENCE_PATH = (
    _PROJECT_ROOT
    / "labs"
    / "evidence"
    / "phase-14-gate-14-4-agentcore-iam-cleanup-predeploy-v1.json"
)


def _load_predeploy_evidence() -> dict[str, Any]:
    return json.loads(_PREDEPLOY_EVIDENCE_PATH.read_text(encoding="utf-8"))


def test_agentcore_deploy_policy_configuration_is_removed() -> None:
    """The shared GitHub deploy role must no longer receive standing AgentCore authority."""
    assert not _DEPLOY_POLICY_PATH.exists()


def test_agentcore_replay_role_configuration_is_removed() -> None:
    """The invocation-only replay role must not remain as ambient experiment authority."""
    assert not _REPLAY_ROLE_PATH.exists()


def test_agentcore_replay_role_output_is_removed() -> None:
    """Bootstrap outputs must not reference the retired replay role."""
    text = _OUTPUTS_PATH.read_text(encoding="utf-8")

    assert "github_actions_agentcore_replay_role_arn" not in text
    assert "github_actions_agentcore_replay" not in text
    assert "OpsLensAgentCoreReplayRole" not in text


def test_gate14_4_predeploy_evidence_freezes_expected_destroy_set() -> None:
    """The predeploy artifact must enumerate only the experiment-specific IAM destroy set."""
    evidence = _load_predeploy_evidence()

    assert evidence["status"] == "predeploy_ready"
    assert evidence["aws_mutation"]["feature_branch"] is False
    assert evidence["aws_mutation"]["current_gate_aws_deletions"] == 0
    assert evidence["authority_invariants"]["github_oidc_changed"] is False
    assert evidence["authority_invariants"]["shared_github_deploy_role_removed"] is False
    assert evidence["authority_invariants"][
        "replacement_agentcore_standing_authority_added"
    ] is False

    assert set(evidence["expected_human_bootstrap_destroy_set"]) == {
        "aws_iam_role_policy_attachment.github_actions_agentcore_deploy",
        "aws_iam_policy.github_actions_agentcore_deploy",
        "aws_iam_role_policy.github_actions_agentcore_replay",
        "aws_iam_role.github_actions_agentcore_replay",
    }


def test_gate14_4_keeps_service_linked_role_outside_destructive_cleanup() -> None:
    """The Runtime Identity SLR must remain explicitly outside this bounded destroy set."""
    evidence = _load_predeploy_evidence()
    slr = evidence["service_linked_role_decision"]

    assert slr["gate_14_4_action"] == "RETAIN"
    assert slr["prevent_destroy"] is True
    assert (
        "aws_iam_service_linked_role.bedrock_agentcore_runtime_identity"
        in evidence["must_not_destroy"]
    )
