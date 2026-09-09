"""Regression tests for bounded AgentCore deployment authority."""

from __future__ import annotations

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_POLICY_PATH = _PROJECT_ROOT / "infra" / "bootstrap" / "github_agentcore_deploy_permissions.tf"


def test_default_endpoint_create_uses_measured_precreation_scope() -> None:
    """DEFAULT endpoint creation must use only the measured account/region precreation ARN."""
    text = _POLICY_PATH.read_text(encoding="utf-8")

    assert 'dev_agentcore_runtime_precreation_arn = (' in text
    assert (
        '"arn:aws:bedrock-agentcore:${var.aws_region}:'
        '${data.aws_caller_identity.current.account_id}:runtime/*"'
    ) in text
    assert 'sid     = "CreateAgentCoreDefaultRuntimeEndpointDependency"' in text
    assert 'actions = ["bedrock-agentcore:CreateAgentRuntimeEndpoint"]' in text

    create_statement = text.split(
        'sid     = "CreateAgentCoreDefaultRuntimeEndpointDependency"', maxsplit=1
    )[1].split("\n  }", maxsplit=1)[0]
    assert "local.dev_agentcore_runtime_precreation_arn" in create_statement
    assert "DeleteAgentRuntimeEndpoint" not in create_statement


def _assert_exact_create_time_tags(statement: str) -> None:
    assert "aws:ResourceTag/" not in statement
    assert 'test     = "ForAllValues:StringEquals"' in statement
    assert 'variable = "aws:TagKeys"' in statement

    expected_request_tags = {
        'variable = "aws:RequestTag/Project"': 'values   = ["opslens"]',
        'variable = "aws:RequestTag/Environment"': 'values   = ["dev"]',
        'variable = "aws:RequestTag/Purpose"': (
            "values   = [local.dev_agentcore_runtime_purpose]"
        ),
        'variable = "aws:RequestTag/ManagedBy"': 'values   = ["terraform"]',
        'variable = "aws:RequestTag/Repository"': (
            'values   = ["brunovicco/opslens"]'
        ),
    }
    for variable, expected_value in expected_request_tags.items():
        assert variable in statement
        assert expected_value in statement

    for tag_key in ("Environment", "ManagedBy", "Project", "Purpose", "Repository"):
        assert f'"{tag_key}"' in statement


def test_precreation_runtime_tag_dependency_is_request_tag_bounded() -> None:
    """Create-time runtime tagging must be precreation-scoped and exact-tag constrained."""
    text = _POLICY_PATH.read_text(encoding="utf-8")

    assert 'sid     = "TagAgentCoreRuntimeDuringCreateDependency"' in text
    tag_statement = text.split(
        'sid     = "TagAgentCoreRuntimeDuringCreateDependency"', maxsplit=1
    )[1].split("\n  }", maxsplit=1)[0]

    assert 'actions = ["bedrock-agentcore:TagResource"]' in tag_statement
    assert "local.dev_agentcore_runtime_precreation_arn" in tag_statement
    _assert_exact_create_time_tags(tag_statement)


def test_precreation_workload_identity_tag_dependency_is_request_tag_bounded() -> None:
    """Managed workload-identity tagging must use only the measured precreation scope."""
    text = _POLICY_PATH.read_text(encoding="utf-8")

    assert 'dev_agentcore_workload_identity_precreation_arn = (' in text
    assert (
        '"arn:aws:bedrock-agentcore:${var.aws_region}:'
        '${data.aws_caller_identity.current.account_id}:'
        'workload-identity-directory/default/workload-identity/*"'
    ) in text
    assert 'sid     = "TagAgentCoreWorkloadIdentityDuringCreateDependency"' in text

    tag_statement = text.split(
        'sid     = "TagAgentCoreWorkloadIdentityDuringCreateDependency"', maxsplit=1
    )[1].split("\n  }", maxsplit=1)[0]
    assert 'actions = ["bedrock-agentcore:TagResource"]' in tag_statement
    assert "local.dev_agentcore_workload_identity_precreation_arn" in tag_statement
    assert "bedrock-agentcore:CreateWorkloadIdentity" not in tag_statement
    _assert_exact_create_time_tags(tag_statement)


def test_managed_workload_identity_create_uses_only_measured_scope_and_tags() -> None:
    """Managed workload-identity creation must remain isolated to the measured dependency."""
    text = _POLICY_PATH.read_text(encoding="utf-8")

    assert 'sid     = "CreateAgentCoreManagedWorkloadIdentityDependency"' in text
    create_statement = text.split(
        'sid     = "CreateAgentCoreManagedWorkloadIdentityDependency"', maxsplit=1
    )[1].split("\n  }", maxsplit=1)[0]

    assert 'actions = ["bedrock-agentcore:CreateWorkloadIdentity"]' in create_statement
    assert "local.dev_agentcore_workload_identity_precreation_arn" in create_statement
    assert 'resources = ["*"]' not in create_statement
    assert "bedrock-agentcore:GetWorkloadIdentity" not in create_statement
    assert "bedrock-agentcore:DeleteWorkloadIdentity" not in create_statement
    assert "bedrock-agentcore:TagResource" not in create_statement
    _assert_exact_create_time_tags(create_statement)


def test_postcreation_runtime_tagging_remains_exact_family_scoped() -> None:
    """Post-creation tag mutation must retain exact-family resource-tag authority."""
    text = _POLICY_PATH.read_text(encoding="utf-8")

    manage_statement = text.split(
        'sid    = "ManageExactBoundedAgentCoreRuntime"', maxsplit=1
    )[1].split("\n  }", maxsplit=1)[0]
    assert '"bedrock-agentcore:TagResource"' in manage_statement
    assert '"bedrock-agentcore:UntagResource"' in manage_statement
    assert "local.dev_agentcore_runtime_arn" in manage_statement
    assert "local.dev_agentcore_runtime_precreation_arn" not in manage_statement
    assert 'variable = "aws:ResourceTag/Project"' in manage_statement
    assert 'variable = "aws:ResourceTag/Environment"' in manage_statement
    assert 'variable = "aws:ResourceTag/Purpose"' in manage_statement


def test_postcreation_endpoint_delete_remains_exact_family_scoped() -> None:
    """Endpoint cleanup must remain bounded to the OpsLens runtime family."""
    text = _POLICY_PATH.read_text(encoding="utf-8")

    assert 'sid     = "DeleteExactAgentCoreDefaultRuntimeEndpointDependency"' in text
    delete_statement = text.split(
        'sid     = "DeleteExactAgentCoreDefaultRuntimeEndpointDependency"', maxsplit=1
    )[1].split("\n  }", maxsplit=1)[0]
    assert 'actions = ["bedrock-agentcore:DeleteAgentRuntimeEndpoint"]' in delete_statement
    assert "local.dev_agentcore_runtime_arn" in delete_statement
    assert "local.dev_agentcore_runtime_endpoint_arn" in delete_statement
    assert "local.dev_agentcore_runtime_precreation_arn" not in delete_statement


def test_workload_identity_cleanup_remains_exact_family_scoped() -> None:
    """Generated workload-identity cleanup must not use the precreation wildcard scope."""
    text = _POLICY_PATH.read_text(encoding="utf-8")

    assert 'sid     = "DeleteAgentCoreGeneratedWorkloadIdentityDependency"' in text
    delete_statement = text.split(
        'sid     = "DeleteAgentCoreGeneratedWorkloadIdentityDependency"', maxsplit=1
    )[1].split("\n  }", maxsplit=1)[0]
    assert 'actions = ["bedrock-agentcore:DeleteWorkloadIdentity"]' in delete_statement
    assert "local.dev_agentcore_workload_identity_arn" in delete_statement
    assert "local.dev_agentcore_workload_identity_precreation_arn" not in delete_statement


def test_deployment_role_never_receives_runtime_invoke_authority() -> None:
    """Control-plane deployment authority must stay separate from data-plane invocation."""
    text = _POLICY_PATH.read_text(encoding="utf-8")

    assert '"bedrock-agentcore:InvokeAgentRuntime"' not in text
    assert '"iam:CreateServiceLinkedRole"' not in text
    assert '"bedrock-agentcore:GetWorkloadIdentity"' not in text
