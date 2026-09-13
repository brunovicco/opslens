"""Regression tests for the retained AgentCore Runtime Identity service-linked-role boundary."""

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SLR_PATH = (
    _PROJECT_ROOT
    / "infra"
    / "bootstrap"
    / "agentcore_runtime_identity_service_linked_role.tf"
)
_DEPLOY_POLICY_PATH = (
    _PROJECT_ROOT / "infra" / "bootstrap" / "github_agentcore_deploy_permissions.tf"
)
_REPLAY_ROLE_PATH = (
    _PROJECT_ROOT / "infra" / "bootstrap" / "github_agentcore_replay_role.tf"
)


def test_runtime_identity_slr_is_human_bootstrap_owned_and_protected() -> None:
    """The account-level Runtime Identity SLR remains protected bootstrap infrastructure."""
    text = _SLR_PATH.read_text(encoding="utf-8")

    assert (
        'resource "aws_iam_service_linked_role" '
        '"bedrock_agentcore_runtime_identity" {'
    ) in text
    assert (
        'aws_service_name = "runtime-identity.bedrock-agentcore.amazonaws.com"'
        in text
    )
    assert "custom_suffix" not in text
    assert "prevent_destroy = true" in text


def test_gate14_4_removes_github_agentcore_authority_without_deleting_slr() -> None:
    """Standing GitHub AgentCore authority is retired while the protected service role remains."""
    assert _SLR_PATH.exists()
    assert not _DEPLOY_POLICY_PATH.exists()
    assert not _REPLAY_ROLE_PATH.exists()
