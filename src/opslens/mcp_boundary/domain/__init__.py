"""Domain contracts for bounded MCP capability exposure and execution bridging."""

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

__all__ = [
    "MCP_CAPABILITY_EXECUTION_CONTRACT_VERSION",
    "MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION",
    "McpBoundaryValidationError",
    "McpCapabilityExecutionBridge",
    "McpCapabilityExposure",
    "McpInvocationReference",
    "McpToolCallAdmission",
    "McpToolName",
    "capability_for_mcp_tool",
    "list_mcp_capability_exposures",
    "mcp_tool_for_capability",
    "parse_mcp_tool_name",
]
