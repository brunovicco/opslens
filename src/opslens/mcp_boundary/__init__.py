"""Bounded MCP interoperability contracts for OpsLens."""

from opslens.mcp_boundary.adapters import (
    InMemoryMcpInvocationResolver,
    build_offline_mcp_server,
)
from opslens.mcp_boundary.application import (
    McpAdmissionProjection,
    admit_mcp_invocation_reference,
    admit_mcp_tool_call,
)
from opslens.mcp_boundary.domain import (
    MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION,
    McpBoundaryValidationError,
    McpCapabilityExposure,
    McpInvocationReference,
    McpToolCallAdmission,
    McpToolName,
    capability_for_mcp_tool,
    list_mcp_capability_exposures,
    mcp_tool_for_capability,
    parse_mcp_tool_name,
)
from opslens.mcp_boundary.ports import McpInvocationResolver

__all__ = [
    "MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION",
    "InMemoryMcpInvocationResolver",
    "McpAdmissionProjection",
    "McpBoundaryValidationError",
    "McpCapabilityExposure",
    "McpInvocationReference",
    "McpInvocationResolver",
    "McpToolCallAdmission",
    "McpToolName",
    "admit_mcp_invocation_reference",
    "admit_mcp_tool_call",
    "build_offline_mcp_server",
    "capability_for_mcp_tool",
    "list_mcp_capability_exposures",
    "mcp_tool_for_capability",
    "parse_mcp_tool_name",
]
