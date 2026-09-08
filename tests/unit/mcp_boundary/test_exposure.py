"""Tests for Phase 13 Gate 13.1 bounded MCP capability exposure."""

from __future__ import annotations

from datetime import date
from typing import cast

import pytest

from opslens.agent_baseline.application import authorize_agent_action
from opslens.agent_baseline.domain import (
    AgentCapability,
    AgentCapabilityInvocation,
    AgentDecision,
    AuthorizedAgentAction,
    StructuredSecurityQueryInvocation,
    create_agent_action_proposal,
    create_single_agent_task,
)
from opslens.mcp_boundary import (
    MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION,
    McpBoundaryValidationError,
    McpCapabilityExposure,
    McpToolCallAdmission,
    McpToolName,
    admit_mcp_tool_call,
    capability_for_mcp_tool,
    list_mcp_capability_exposures,
    mcp_tool_for_capability,
    parse_mcp_tool_name,
)
from opslens.semantic_query.domain import (
    EpssFilters,
    SemanticDimension,
    SemanticMetric,
    SemanticQuery,
)


def _authorized_action(capability: AgentCapability) -> AuthorizedAgentAction:
    """Create one real authorization using the frozen Phase 11 boundary."""
    task = create_single_agent_task(
        text=f"Use {capability.value}",
        allowed_capabilities=(capability,),
    )
    proposal = create_agent_action_proposal(
        task_id=task.task_id,
        decision=AgentDecision.ACT,
        capability=capability,
    )
    result = authorize_agent_action(task, proposal)
    assert type(result) is AuthorizedAgentAction
    return result


def _structured_invocation() -> StructuredSecurityQueryInvocation:
    """Create one existing typed invocation without executing it."""
    action = _authorized_action(AgentCapability.STRUCTURED_SECURITY_QUERY)
    query = SemanticQuery(
        metric=SemanticMetric.EPSS_SCORE,
        dimensions=(SemanticDimension.CVE,),
        filters=EpssFilters(
            snapshot_date=date(2026, 9, 8),
            minimum_score=0.7,
        ),
        limit=3,
    )
    return StructuredSecurityQueryInvocation.create(action=action, query=query)


def test_exposure_contract_is_closed_and_one_to_one() -> None:
    """Every existing bounded capability has exactly one deterministic MCP tool."""
    exposures = list_mcp_capability_exposures()

    assert MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION == "mcp-capability-exposure:v1"
    assert len(exposures) == len(McpToolName) == len(AgentCapability) == 4
    assert {item.tool_name for item in exposures} == set(McpToolName)
    assert {item.capability for item in exposures} == set(AgentCapability)
    assert len({item.exposure_id for item in exposures}) == 4

    for exposure in exposures:
        assert capability_for_mcp_tool(exposure.tool_name) is exposure.capability
        assert mcp_tool_for_capability(exposure.capability) is exposure.tool_name


def test_transport_tool_name_parser_fails_closed() -> None:
    """Only exact closed tool names cross the raw transport-name boundary."""
    assert (
        parse_mcp_tool_name("opslens.structured_security_query")
        is McpToolName.STRUCTURED_SECURITY_QUERY
    )

    with pytest.raises(McpBoundaryValidationError, match="unknown MCP tool name"):
        parse_mcp_tool_name("opslens.run_shell")

    with pytest.raises(McpBoundaryValidationError, match="must be a string"):
        parse_mcp_tool_name(123)


def test_exposure_identity_is_deterministic_and_binding_is_code_owned() -> None:
    """Equivalent exposures share identity and cross-capability bindings are rejected."""
    first = McpCapabilityExposure.create(
        tool_name=McpToolName.KNOWLEDGE_GUIDANCE,
        capability=AgentCapability.KNOWLEDGE_GUIDANCE,
    )
    equivalent = McpCapabilityExposure.create(
        tool_name=McpToolName.KNOWLEDGE_GUIDANCE,
        capability=AgentCapability.KNOWLEDGE_GUIDANCE,
    )

    assert first == equivalent

    with pytest.raises(McpBoundaryValidationError, match="not code-owned"):
        McpCapabilityExposure.create(
            tool_name=McpToolName.KNOWLEDGE_GUIDANCE,
            capability=AgentCapability.PUBLIC_REPOSITORY_ANALYSIS,
        )


def test_mcp_admission_binds_existing_authorization_and_typed_invocation() -> None:
    """MCP admission references existing typed authority and performs no execution."""
    invocation = _structured_invocation()

    admission = admit_mcp_tool_call(
        tool_name=McpToolName.STRUCTURED_SECURITY_QUERY,
        invocation=invocation,
    )

    assert admission.tool_name is McpToolName.STRUCTURED_SECURITY_QUERY
    assert admission.capability is AgentCapability.STRUCTURED_SECURITY_QUERY
    assert admission.action_id == invocation.action.action_id
    assert admission.invocation_id == invocation.invocation_id
    assert admission.invocation_sha256 == invocation.invocation_sha256
    assert admission.admission_id.startswith(
        f"{MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION}:admission:"
    )


def test_tool_and_typed_invocation_capability_mismatch_fails_closed() -> None:
    """A tool name cannot reinterpret an already-authorized invocation capability."""
    invocation = _structured_invocation()

    with pytest.raises(McpBoundaryValidationError, match="does not match"):
        admit_mcp_tool_call(
            tool_name=McpToolName.KNOWLEDGE_GUIDANCE,
            invocation=invocation,
        )


def test_unknown_typed_invocation_fails_closed_before_mcp_admission() -> None:
    """Unknown runtime objects cannot enter MCP admission as dynamic tools."""
    unknown = cast(AgentCapabilityInvocation, object())

    with pytest.raises(McpBoundaryValidationError, match="recognized typed capability"):
        admit_mcp_tool_call(
            tool_name=McpToolName.STRUCTURED_SECURITY_QUERY,
            invocation=unknown,
        )


def test_forged_mcp_admission_identity_is_rejected() -> None:
    """Caller-visible MCP evidence cannot forge its content-addressed identity."""
    invocation = _structured_invocation()
    admitted = admit_mcp_tool_call(
        tool_name=McpToolName.STRUCTURED_SECURITY_QUERY,
        invocation=invocation,
    )

    with pytest.raises(McpBoundaryValidationError, match="canonical MCP semantics"):
        McpToolCallAdmission(
            tool_name=admitted.tool_name,
            capability=admitted.capability,
            action_id=admitted.action_id,
            invocation_id=admitted.invocation_id,
            invocation_sha256=admitted.invocation_sha256,
            admission_sha256="0" * 64,
            admission_id=(
                f"{MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION}:admission:{'0' * 64}"
            ),
        )
