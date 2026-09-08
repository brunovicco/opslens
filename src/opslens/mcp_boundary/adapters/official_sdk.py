"""Official MCP Python SDK adapter over the frozen OpsLens admission boundary."""

from __future__ import annotations

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from opslens.mcp_boundary.application import (
    McpAdmissionProjection,
    admit_mcp_invocation_reference,
)
from opslens.mcp_boundary.domain import McpBoundaryValidationError, McpToolName
from opslens.mcp_boundary.ports import McpInvocationResolver

_SERVER_NAME = "OpsLens Bounded MCP"
_REJECTED_REFERENCE_MESSAGE = "MCP invocation reference rejected."
_RESOLUTION_FAILURE_MESSAGE = "MCP invocation resolution failed."


def _admit_reference(
    *,
    tool_name: McpToolName,
    invocation_id: str,
    invocation_sha256: str,
    resolver: McpInvocationResolver,
) -> McpAdmissionProjection:
    """Translate one protocol call into deterministic admission without execution."""
    try:
        return admit_mcp_invocation_reference(
            tool_name=tool_name,
            invocation_id=invocation_id,
            invocation_sha256=invocation_sha256,
            resolver=resolver,
        )
    except McpBoundaryValidationError as exc:
        raise ToolError(_REJECTED_REFERENCE_MESSAGE) from exc
    except Exception as exc:
        raise ToolError(_RESOLUTION_FAILURE_MESSAGE) from exc


def build_offline_mcp_server(*, resolver: McpInvocationResolver) -> MCPServer[None]:
    """Build the bounded four-tool MCP server for offline/in-process interoperability."""
    server = MCPServer[None](
        _SERVER_NAME,
        description=(
            "Exposes only content-addressed references to already-authorized OpsLens "
            "capability invocations. This server does not execute capabilities."
        ),
    )

    @server.tool(
        name=McpToolName.STRUCTURED_SECURITY_QUERY.value,
        structured_output=True,
    )
    def structured_security_query(
        invocation_id: str,
        invocation_sha256: str,
    ) -> McpAdmissionProjection:
        """Admit an existing structured-security invocation reference."""
        return _admit_reference(
            tool_name=McpToolName.STRUCTURED_SECURITY_QUERY,
            invocation_id=invocation_id,
            invocation_sha256=invocation_sha256,
            resolver=resolver,
        )

    @server.tool(
        name=McpToolName.KNOWLEDGE_GUIDANCE.value,
        structured_output=True,
    )
    def knowledge_guidance(
        invocation_id: str,
        invocation_sha256: str,
    ) -> McpAdmissionProjection:
        """Admit an existing knowledge-guidance invocation reference."""
        return _admit_reference(
            tool_name=McpToolName.KNOWLEDGE_GUIDANCE,
            invocation_id=invocation_id,
            invocation_sha256=invocation_sha256,
            resolver=resolver,
        )

    @server.tool(
        name=McpToolName.HYBRID_SECURITY_ANSWER.value,
        structured_output=True,
    )
    def hybrid_security_answer(
        invocation_id: str,
        invocation_sha256: str,
    ) -> McpAdmissionProjection:
        """Admit an existing hybrid-security invocation reference."""
        return _admit_reference(
            tool_name=McpToolName.HYBRID_SECURITY_ANSWER,
            invocation_id=invocation_id,
            invocation_sha256=invocation_sha256,
            resolver=resolver,
        )

    @server.tool(
        name=McpToolName.PUBLIC_REPOSITORY_ANALYSIS.value,
        structured_output=True,
    )
    def public_repository_analysis(
        invocation_id: str,
        invocation_sha256: str,
    ) -> McpAdmissionProjection:
        """Admit an existing public-repository invocation reference."""
        return _admit_reference(
            tool_name=McpToolName.PUBLIC_REPOSITORY_ANALYSIS,
            invocation_id=invocation_id,
            invocation_sha256=invocation_sha256,
            resolver=resolver,
        )

    return server


__all__ = ["build_offline_mcp_server"]
