"""Application service for bounded structured-security MCP result projection."""

from __future__ import annotations

from opslens.agent_baseline.application import AgentCapabilityExecutors
from opslens.agent_baseline.domain import (
    StructuredSecurityQueryInvocation,
    StructuredSecurityQueryResultBinding,
)
from opslens.mcp_boundary.application.protocol_execution import (
    execute_mcp_invocation_reference_outcome,
)
from opslens.mcp_boundary.domain import McpBoundaryValidationError, McpToolName
from opslens.mcp_boundary.domain.result_projection import (
    McpStructuredSecurityResultProjection,
)
from opslens.mcp_boundary.ports import McpInvocationResolver


def project_mcp_structured_result_reference(
    *,
    tool_name: McpToolName,
    invocation_id: str,
    invocation_sha256: str,
    resolver: McpInvocationResolver,
    executors: AgentCapabilityExecutors,
) -> McpStructuredSecurityResultProjection:
    """Execute and project one structured-security result through explicit policy."""
    if tool_name is not McpToolName.STRUCTURED_SECURITY_QUERY:
        raise McpBoundaryValidationError(
            "MCP business result projection supports only structured_security_query"
        )

    outcome = execute_mcp_invocation_reference_outcome(
        tool_name=tool_name,
        invocation_id=invocation_id,
        invocation_sha256=invocation_sha256,
        resolver=resolver,
        executors=executors,
    )
    invocation = outcome.invocation
    result = outcome.capability_outcome.result
    if type(invocation) is not StructuredSecurityQueryInvocation:
        raise McpBoundaryValidationError(
            "MCP structured result projection resolved an unsupported invocation"
        )
    if type(result) is not StructuredSecurityQueryResultBinding:
        raise McpBoundaryValidationError(
            "MCP structured result projection received an unsupported result"
        )

    return McpStructuredSecurityResultProjection.create(
        invocation=invocation,
        bridge=outcome.bridge,
        result=result,
    )


__all__ = ["project_mcp_structured_result_reference"]
