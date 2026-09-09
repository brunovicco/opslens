"""Regression tests for the AgentCore Runtime Identity bootstrap boundary."""

from __future__ import annotations

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


def test_runtime_identity_slr_is_human_bootstrap_owned() -> None:
    """The account-level Runtime Identity SLR must be explicit bootstrap infrastructure."""
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


def test_github_deployment_role_cannot_create_service_linked_roles() -> None:
    """GitHub deployment authority must not create account-level service-linked roles."""
    text = _DEPLOY_POLICY_PATH.read_text(encoding="utf-8")

    assert '"iam:CreateServiceLinkedRole"' not in text


def test_slr_bootstrap_does_not_blur_runtime_invocation_boundary() -> None:
    """Provisioning the SLR must not add AgentCore data-plane authority to deployment CI."""
    text = _DEPLOY_POLICY_PATH.read_text(encoding="utf-8")

    assert '"bedrock-agentcore:InvokeAgentRuntime"' not in text
