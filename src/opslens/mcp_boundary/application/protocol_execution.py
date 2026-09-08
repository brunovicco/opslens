"""Application service binding deterministic MCP admission to one typed execution."""

from __future__ import annotations

from dataclasses import dataclass

from opslens.agent_baseline.application import (
    AgentCapabilityExecutors,
    execute_authorized_capability,
)
from opslens.mcp_boundary.application.admission import admit_mcp_tool_call
from opslens.mcp_boundary.application.protocol_admission import (
    resolve_mcp_invocation_reference,
)
from opslens.mcp_boundary.domain import McpBoundaryValidationError, McpToolName
from opslens.mcp_boundary.domain.execution import (
    MCP_CAPABILITY_EXECUTION_CONTRACT_VERSION,
    McpCapabilityExecutionBridge,
)
from opslens.mcp_boundary.ports import McpInvocationResolver


@dataclass(frozen=True, slots=True)
class McpExecutionProjection:
    """Content-minimized protocol projection of one MCP-admitted typed execution."""

    contract_version: str
    tool_name: str
    capability: str
    action_id: str
    invocation_id: str
    invocation_sha256: str
    admission_id: str
    admission_sha256: str
    execution_id: str
    execution_sha256: str
    downstream_result_sha256: str
    bridge_id: str
    bridge_sha256: str

    @classmethod
    def from_bridge(cls, bridge: McpCapabilityExecutionBridge) -> McpExecutionProjection:
        """Project only deterministic execution identity and digest evidence."""
        if type(bridge) is not McpCapabilityExecutionBridge:
            raise McpBoundaryValidationError(
                "MCP execution projection requires deterministic bridge evidence"
            )
        return cls(
            contract_version=MCP_CAPABILITY_EXECUTION_CONTRACT_VERSION,
            tool_name=bridge.tool_name.value,
            capability=bridge.capability.value,
            action_id=bridge.action_id,
            invocation_id=bridge.invocation_id,
            invocation_sha256=bridge.invocation_sha256,
            admission_id=bridge.admission_id,
            admission_sha256=bridge.admission_sha256,
            execution_id=bridge.execution_id,
            execution_sha256=bridge.execution_sha256,
            downstream_result_sha256=bridge.downstream_result_sha256,
            bridge_id=bridge.bridge_id,
            bridge_sha256=bridge.bridge_sha256,
        )


def execute_mcp_invocation_reference(
    *,
    tool_name: McpToolName,
    invocation_id: str,
    invocation_sha256: str,
    resolver: McpInvocationResolver,
    executors: AgentCapabilityExecutors,
) -> McpExecutionProjection:
    """Admit and execute one exact existing typed invocation exactly once."""
    if type(tool_name) is not McpToolName:
        raise McpBoundaryValidationError("tool_name must be McpToolName")

    invocation = resolve_mcp_invocation_reference(
        invocation_id=invocation_id,
        invocation_sha256=invocation_sha256,
        resolver=resolver,
    )
    admission = admit_mcp_tool_call(tool_name=tool_name, invocation=invocation)
    execution = execute_authorized_capability(invocation, executors)
    bridge = McpCapabilityExecutionBridge.create(
        admission=admission,
        invocation=invocation,
        execution=execution,
    )
    return McpExecutionProjection.from_bridge(bridge)


__all__ = ["McpExecutionProjection", "execute_mcp_invocation_reference"]
