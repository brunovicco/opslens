"""Application services for bounded MCP admission and execution bridging."""

from opslens.mcp_boundary.application.admission import admit_mcp_tool_call
from opslens.mcp_boundary.application.protocol_admission import (
    McpAdmissionProjection,
    admit_mcp_invocation_reference,
    resolve_mcp_invocation_reference,
)
from opslens.mcp_boundary.application.protocol_execution import (
    McpExecutionProjection,
    execute_mcp_invocation_reference,
)

__all__ = [
    "McpAdmissionProjection",
    "McpExecutionProjection",
    "admit_mcp_invocation_reference",
    "admit_mcp_tool_call",
    "execute_mcp_invocation_reference",
    "resolve_mcp_invocation_reference",
]
