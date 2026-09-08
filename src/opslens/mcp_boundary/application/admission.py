"""Deterministic MCP admission over already-authorized typed capability invocations."""

from opslens.agent_baseline.domain.errors import AgentCapabilityExecutionValidationError
from opslens.agent_baseline.domain.execution import (
    AgentCapabilityInvocation,
    action_for_invocation,
    capability_for_invocation,
)
from opslens.mcp_boundary.domain import (
    McpBoundaryValidationError,
    McpToolCallAdmission,
    McpToolName,
    capability_for_mcp_tool,
)


def admit_mcp_tool_call(
    *,
    tool_name: McpToolName,
    invocation: AgentCapabilityInvocation,
) -> McpToolCallAdmission:
    """Bind one MCP tool to one existing typed invocation without executing it."""
    if type(tool_name) is not McpToolName:
        raise McpBoundaryValidationError("tool_name must be McpToolName")

    try:
        invocation_capability = capability_for_invocation(invocation)
        action = action_for_invocation(invocation)
    except AgentCapabilityExecutionValidationError:
        raise McpBoundaryValidationError(
            "MCP admission requires one recognized typed capability invocation"
        ) from None

    expected_capability = capability_for_mcp_tool(tool_name)
    if invocation_capability is not expected_capability:
        raise McpBoundaryValidationError(
            "MCP tool does not match the typed invocation capability"
        )
    if action.capability is not invocation_capability:
        raise McpBoundaryValidationError(
            "typed invocation authorization does not match its capability"
        )

    return McpToolCallAdmission.create(
        tool_name=tool_name,
        capability=invocation_capability,
        action_id=action.action_id,
        invocation_id=invocation.invocation_id,
        invocation_sha256=invocation.invocation_sha256,
    )


__all__ = ["admit_mcp_tool_call"]
