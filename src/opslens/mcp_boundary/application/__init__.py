"""Application services for bounded MCP admission, execution, and result projection."""

from opslens.mcp_boundary.application.admission import admit_mcp_tool_call
from opslens.mcp_boundary.application.protocol_admission import (
    McpAdmissionProjection,
    admit_mcp_invocation_reference,
    resolve_mcp_invocation_reference,
)
from opslens.mcp_boundary.application.protocol_execution import (
    McpExecutionOutcome,
    McpExecutionProjection,
    execute_mcp_invocation_reference,
    execute_mcp_invocation_reference_outcome,
)
from opslens.mcp_boundary.application.protocol_result import (
    project_mcp_structured_result_reference,
)

__all__ = [
    "McpAdmissionProjection",
    "McpExecutionOutcome",
    "McpExecutionProjection",
    "admit_mcp_invocation_reference",
    "admit_mcp_tool_call",
    "execute_mcp_invocation_reference",
    "execute_mcp_invocation_reference_outcome",
    "project_mcp_structured_result_reference",
    "resolve_mcp_invocation_reference",
]
