"""Official MCP Python SDK adapters over frozen OpsLens authority boundaries."""

from collections.abc import Mapping
from typing import TypedDict, cast

from mcp import MCPError
from mcp.server import MCPServer, ServerRequestContext
from mcp.server.context import CallNext, HandlerResult
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import INVALID_PARAMS

from opslens.agent_baseline.application import (
    AgentCapabilityExecutionError,
    AgentCapabilityExecutors,
)
from opslens.mcp_boundary.application import (
    McpAdmissionProjection,
    McpExecutionProjection,
    admit_mcp_invocation_reference,
    execute_mcp_invocation_reference,
)
from opslens.mcp_boundary.application.protocol_result import (
    project_mcp_structured_result_reference,
)
from opslens.mcp_boundary.domain import McpBoundaryValidationError, McpToolName
from opslens.mcp_boundary.domain.result_projection import (
    McpStructuredSecurityResultProjection,
)
from opslens.mcp_boundary.ports import McpInvocationResolver

_ADMISSION_SERVER_NAME = "OpsLens Bounded MCP"
_EXECUTION_SERVER_NAME = "OpsLens Bounded MCP Execution"
_RESULT_SERVER_NAME = "OpsLens Bounded MCP Structured Result"
_REJECTED_REFERENCE_MESSAGE = "MCP invocation reference rejected."
_RESOLUTION_FAILURE_MESSAGE = "MCP invocation resolution failed."
_REJECTED_ARGUMENTS_MESSAGE = "MCP tool arguments rejected."
_EXECUTION_REJECTED_MESSAGE = "MCP capability execution rejected."
_EXECUTION_FAILURE_MESSAGE = "MCP capability execution failed."
_RESULT_PROJECTION_REJECTED_MESSAGE = "MCP business result projection rejected."
_RESULT_PROJECTION_FAILURE_MESSAGE = "MCP business result projection failed."
_ALLOWED_REFERENCE_ARGUMENTS = frozenset({"invocation_id", "invocation_sha256"})
_CLOSED_TOOL_NAMES = frozenset(tool_name.value for tool_name in McpToolName)


class McpAdmissionProtocolOutput(TypedDict):
    """Exact structured-output shape exposed by the admission-only MCP adapter."""

    contract_version: str
    tool_name: str
    capability: str
    action_id: str
    invocation_id: str
    invocation_sha256: str
    admission_id: str
    admission_sha256: str


class McpExecutionProtocolOutput(TypedDict):
    """Identity-only structured output exposed by the MCP execution bridge."""

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


class McpStructuredEpssRowProtocolOutput(TypedDict):
    """Allowlisted business row exposed by the first MCP result transport."""

    cve: str
    epss_score: str


class McpStructuredResultProtocolOutput(TypedDict):
    """Bounded business-result output for structured-security MCP transport only."""

    contract_version: str
    tool_name: str
    capability: str
    invocation_id: str
    execution_id: str
    bridge_id: str
    result_sha256: str
    columns: list[str]
    rows: list[McpStructuredEpssRowProtocolOutput]
    projection_id: str
    projection_sha256: str


def _admission_protocol_output(
    projection: McpAdmissionProjection,
) -> McpAdmissionProtocolOutput:
    """Convert deterministic admission evidence into an SDK-schema-friendly shape."""
    return McpAdmissionProtocolOutput(
        contract_version=projection.contract_version,
        tool_name=projection.tool_name,
        capability=projection.capability,
        action_id=projection.action_id,
        invocation_id=projection.invocation_id,
        invocation_sha256=projection.invocation_sha256,
        admission_id=projection.admission_id,
        admission_sha256=projection.admission_sha256,
    )


def _execution_protocol_output(
    projection: McpExecutionProjection,
) -> McpExecutionProtocolOutput:
    """Convert deterministic execution-bridge evidence into identity-only protocol output."""
    return McpExecutionProtocolOutput(
        contract_version=projection.contract_version,
        tool_name=projection.tool_name,
        capability=projection.capability,
        action_id=projection.action_id,
        invocation_id=projection.invocation_id,
        invocation_sha256=projection.invocation_sha256,
        admission_id=projection.admission_id,
        admission_sha256=projection.admission_sha256,
        execution_id=projection.execution_id,
        execution_sha256=projection.execution_sha256,
        downstream_result_sha256=projection.downstream_result_sha256,
        bridge_id=projection.bridge_id,
        bridge_sha256=projection.bridge_sha256,
    )


def _structured_result_protocol_output(
    projection: McpStructuredSecurityResultProjection,
) -> McpStructuredResultProtocolOutput:
    """Convert one validated projection into its exact MCP transport shape."""
    return McpStructuredResultProtocolOutput(
        contract_version=projection.contract_version,
        tool_name=projection.tool_name.value,
        capability=projection.capability.value,
        invocation_id=projection.invocation_id,
        execution_id=projection.execution_id,
        bridge_id=projection.bridge_id,
        result_sha256=projection.result_sha256,
        columns=list(projection.columns),
        rows=[
            McpStructuredEpssRowProtocolOutput(
                cve=row.cve,
                epss_score=row.epss_score,
            )
            for row in projection.rows
        ],
        projection_id=projection.projection_id,
        projection_sha256=projection.projection_sha256,
    )


async def _reject_unexpected_tool_arguments(
    ctx: ServerRequestContext[None, object],
    call_next: CallNext,
) -> HandlerResult:
    """Fail closed on extra/missing raw arguments before SDK function-model validation."""
    if ctx.method != "tools/call":
        return await call_next(ctx)

    params = ctx.params
    if params is None:
        raise MCPError(code=INVALID_PARAMS, message=_REJECTED_ARGUMENTS_MESSAGE)

    raw_tool_name = params.get("name")
    if type(raw_tool_name) is not str or raw_tool_name not in _CLOSED_TOOL_NAMES:
        return await call_next(ctx)

    raw_arguments = params.get("arguments")
    if not isinstance(raw_arguments, Mapping):
        raise MCPError(code=INVALID_PARAMS, message=_REJECTED_ARGUMENTS_MESSAGE)
    arguments = cast(Mapping[object, object], raw_arguments)
    if len(arguments) != len(_ALLOWED_REFERENCE_ARGUMENTS) or any(
        argument_name not in arguments for argument_name in _ALLOWED_REFERENCE_ARGUMENTS
    ):
        raise MCPError(code=INVALID_PARAMS, message=_REJECTED_ARGUMENTS_MESSAGE)

    return await call_next(ctx)


def _admit_reference(
    *,
    tool_name: McpToolName,
    invocation_id: str,
    invocation_sha256: str,
    resolver: McpInvocationResolver,
) -> McpAdmissionProtocolOutput:
    """Translate one protocol call into deterministic admission without execution."""
    try:
        projection = admit_mcp_invocation_reference(
            tool_name=tool_name,
            invocation_id=invocation_id,
            invocation_sha256=invocation_sha256,
            resolver=resolver,
        )
        return _admission_protocol_output(projection)
    except McpBoundaryValidationError as exc:
        raise ToolError(_REJECTED_REFERENCE_MESSAGE) from exc
    except Exception as exc:
        raise ToolError(_RESOLUTION_FAILURE_MESSAGE) from exc


def _execute_reference(
    *,
    tool_name: McpToolName,
    invocation_id: str,
    invocation_sha256: str,
    resolver: McpInvocationResolver,
    executors: AgentCapabilityExecutors,
) -> McpExecutionProtocolOutput:
    """Admit then execute one exact typed invocation and expose identity evidence only."""
    try:
        projection = execute_mcp_invocation_reference(
            tool_name=tool_name,
            invocation_id=invocation_id,
            invocation_sha256=invocation_sha256,
            resolver=resolver,
            executors=executors,
        )
        return _execution_protocol_output(projection)
    except AgentCapabilityExecutionError as exc:
        raise ToolError(_EXECUTION_FAILURE_MESSAGE) from exc
    except McpBoundaryValidationError as exc:
        raise ToolError(_EXECUTION_REJECTED_MESSAGE) from exc
    except Exception as exc:
        raise ToolError(_EXECUTION_FAILURE_MESSAGE) from exc


def _project_structured_reference(
    *,
    invocation_id: str,
    invocation_sha256: str,
    resolver: McpInvocationResolver,
    executors: AgentCapabilityExecutors,
) -> McpStructuredResultProtocolOutput:
    """Execute and project the sole business-result family authorized in Gate 13.4."""
    try:
        projection = project_mcp_structured_result_reference(
            tool_name=McpToolName.STRUCTURED_SECURITY_QUERY,
            invocation_id=invocation_id,
            invocation_sha256=invocation_sha256,
            resolver=resolver,
            executors=executors,
        )
        return _structured_result_protocol_output(projection)
    except AgentCapabilityExecutionError as exc:
        raise ToolError(_EXECUTION_FAILURE_MESSAGE) from exc
    except McpBoundaryValidationError as exc:
        raise ToolError(_RESULT_PROJECTION_REJECTED_MESSAGE) from exc
    except Exception as exc:
        raise ToolError(_RESULT_PROJECTION_FAILURE_MESSAGE) from exc


def build_offline_mcp_server(*, resolver: McpInvocationResolver) -> MCPServer[None]:
    """Build the bounded four-tool MCP admission server without capability execution."""
    server = MCPServer[None](
        _ADMISSION_SERVER_NAME,
        description=(
            "Exposes only content-addressed references to already-authorized OpsLens "
            "capability invocations. This server does not execute capabilities."
        ),
        middleware=[_reject_unexpected_tool_arguments],
    )

    def structured_security_query(
        invocation_id: str,
        invocation_sha256: str,
    ) -> McpAdmissionProtocolOutput:
        """Admit an existing structured-security invocation reference."""
        return _admit_reference(
            tool_name=McpToolName.STRUCTURED_SECURITY_QUERY,
            invocation_id=invocation_id,
            invocation_sha256=invocation_sha256,
            resolver=resolver,
        )

    def knowledge_guidance(
        invocation_id: str,
        invocation_sha256: str,
    ) -> McpAdmissionProtocolOutput:
        """Admit an existing knowledge-guidance invocation reference."""
        return _admit_reference(
            tool_name=McpToolName.KNOWLEDGE_GUIDANCE,
            invocation_id=invocation_id,
            invocation_sha256=invocation_sha256,
            resolver=resolver,
        )

    def hybrid_security_answer(
        invocation_id: str,
        invocation_sha256: str,
    ) -> McpAdmissionProtocolOutput:
        """Admit an existing hybrid-security invocation reference."""
        return _admit_reference(
            tool_name=McpToolName.HYBRID_SECURITY_ANSWER,
            invocation_id=invocation_id,
            invocation_sha256=invocation_sha256,
            resolver=resolver,
        )

    def public_repository_analysis(
        invocation_id: str,
        invocation_sha256: str,
    ) -> McpAdmissionProtocolOutput:
        """Admit an existing public-repository invocation reference."""
        return _admit_reference(
            tool_name=McpToolName.PUBLIC_REPOSITORY_ANALYSIS,
            invocation_id=invocation_id,
            invocation_sha256=invocation_sha256,
            resolver=resolver,
        )

    server.add_tool(
        structured_security_query,
        name=McpToolName.STRUCTURED_SECURITY_QUERY.value,
        structured_output=True,
    )
    server.add_tool(
        knowledge_guidance,
        name=McpToolName.KNOWLEDGE_GUIDANCE.value,
        structured_output=True,
    )
    server.add_tool(
        hybrid_security_answer,
        name=McpToolName.HYBRID_SECURITY_ANSWER.value,
        structured_output=True,
    )
    server.add_tool(
        public_repository_analysis,
        name=McpToolName.PUBLIC_REPOSITORY_ANALYSIS.value,
        structured_output=True,
    )
    return server


def build_offline_mcp_execution_server(
    *,
    resolver: McpInvocationResolver,
    executors: AgentCapabilityExecutors,
) -> MCPServer[None]:
    """Build a separate four-tool server that admits then executes exactly one typed invocation."""
    server = MCPServer[None](
        _EXECUTION_SERVER_NAME,
        description=(
            "Executes exactly one already-authorized typed OpsLens capability invocation after "
            "deterministic MCP admission. Business result content is not transported."
        ),
        middleware=[_reject_unexpected_tool_arguments],
    )

    def structured_security_query(
        invocation_id: str,
        invocation_sha256: str,
    ) -> McpExecutionProtocolOutput:
        """Admit and execute one existing structured-security invocation."""
        return _execute_reference(
            tool_name=McpToolName.STRUCTURED_SECURITY_QUERY,
            invocation_id=invocation_id,
            invocation_sha256=invocation_sha256,
            resolver=resolver,
            executors=executors,
        )

    def knowledge_guidance(
        invocation_id: str,
        invocation_sha256: str,
    ) -> McpExecutionProtocolOutput:
        """Admit and execute one existing knowledge-guidance invocation."""
        return _execute_reference(
            tool_name=McpToolName.KNOWLEDGE_GUIDANCE,
            invocation_id=invocation_id,
            invocation_sha256=invocation_sha256,
            resolver=resolver,
            executors=executors,
        )

    def hybrid_security_answer(
        invocation_id: str,
        invocation_sha256: str,
    ) -> McpExecutionProtocolOutput:
        """Admit and execute one existing hybrid-security invocation."""
        return _execute_reference(
            tool_name=McpToolName.HYBRID_SECURITY_ANSWER,
            invocation_id=invocation_id,
            invocation_sha256=invocation_sha256,
            resolver=resolver,
            executors=executors,
        )

    def public_repository_analysis(
        invocation_id: str,
        invocation_sha256: str,
    ) -> McpExecutionProtocolOutput:
        """Admit and execute one existing public-repository invocation."""
        return _execute_reference(
            tool_name=McpToolName.PUBLIC_REPOSITORY_ANALYSIS,
            invocation_id=invocation_id,
            invocation_sha256=invocation_sha256,
            resolver=resolver,
            executors=executors,
        )

    server.add_tool(
        structured_security_query,
        name=McpToolName.STRUCTURED_SECURITY_QUERY.value,
        structured_output=True,
    )
    server.add_tool(
        knowledge_guidance,
        name=McpToolName.KNOWLEDGE_GUIDANCE.value,
        structured_output=True,
    )
    server.add_tool(
        hybrid_security_answer,
        name=McpToolName.HYBRID_SECURITY_ANSWER.value,
        structured_output=True,
    )
    server.add_tool(
        public_repository_analysis,
        name=McpToolName.PUBLIC_REPOSITORY_ANALYSIS.value,
        structured_output=True,
    )
    return server


def build_offline_mcp_structured_result_server(
    *,
    resolver: McpInvocationResolver,
    executors: AgentCapabilityExecutors,
) -> MCPServer[None]:
    """Build the first business-result MCP proof for structured security only."""
    server = MCPServer[None](
        _RESULT_SERVER_NAME,
        description=(
            "Executes exactly one already-authorized structured-security invocation and "
            "projects only allowlisted CVE and EPSS rows."
        ),
        middleware=[_reject_unexpected_tool_arguments],
    )

    def structured_security_query(
        invocation_id: str,
        invocation_sha256: str,
    ) -> McpStructuredResultProtocolOutput:
        """Execute and project one existing structured-security invocation."""
        return _project_structured_reference(
            invocation_id=invocation_id,
            invocation_sha256=invocation_sha256,
            resolver=resolver,
            executors=executors,
        )

    server.add_tool(
        structured_security_query,
        name=McpToolName.STRUCTURED_SECURITY_QUERY.value,
        structured_output=True,
    )
    return server


__all__ = [
    "McpAdmissionProtocolOutput",
    "McpExecutionProtocolOutput",
    "McpStructuredEpssRowProtocolOutput",
    "McpStructuredResultProtocolOutput",
    "build_offline_mcp_execution_server",
    "build_offline_mcp_server",
    "build_offline_mcp_structured_result_server",
]
