"""Domain contracts for bounded MCP capability exposure, execution, and results."""

from opslens.mcp_boundary.domain.errors import McpBoundaryValidationError
from opslens.mcp_boundary.domain.execution import (
    MCP_CAPABILITY_EXECUTION_CONTRACT_VERSION,
    McpCapabilityExecutionBridge,
)
from opslens.mcp_boundary.domain.exposure import (
    MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION,
    McpCapabilityExposure,
    McpToolCallAdmission,
    McpToolName,
    capability_for_mcp_tool,
    list_mcp_capability_exposures,
    mcp_tool_for_capability,
    parse_mcp_tool_name,
)
from opslens.mcp_boundary.domain.reference import McpInvocationReference
from opslens.mcp_boundary.domain.result_projection import (
    MAX_MCP_EPSS_TEXT_CHARS,
    MAX_MCP_RESULT_ROWS,
    MCP_RESULT_PROJECTION_CONTRACT_VERSION,
    McpStructuredEpssRow,
    McpStructuredSecurityResultProjection,
)

__all__ = [
    "MAX_MCP_EPSS_TEXT_CHARS",
    "MAX_MCP_RESULT_ROWS",
    "MCP_CAPABILITY_EXECUTION_CONTRACT_VERSION",
    "MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION",
    "MCP_RESULT_PROJECTION_CONTRACT_VERSION",
    "McpBoundaryValidationError",
    "McpCapabilityExecutionBridge",
    "McpCapabilityExposure",
    "McpInvocationReference",
    "McpStructuredEpssRow",
    "McpStructuredSecurityResultProjection",
    "McpToolCallAdmission",
    "McpToolName",
    "capability_for_mcp_tool",
    "list_mcp_capability_exposures",
    "mcp_tool_for_capability",
    "parse_mcp_tool_name",
]
