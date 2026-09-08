"""Domain contracts for bounded MCP capability exposure."""

from opslens.mcp_boundary.domain.errors import McpBoundaryValidationError
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

__all__ = [
    "MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION",
    "McpBoundaryValidationError",
    "McpCapabilityExposure",
    "McpToolCallAdmission",
    "McpToolName",
    "capability_for_mcp_tool",
    "list_mcp_capability_exposures",
    "mcp_tool_for_capability",
    "parse_mcp_tool_name",
]
