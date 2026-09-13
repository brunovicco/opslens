"""Offline interoperability tests for the Phase 13 Gate 13.2 official MCP SDK adapter."""

from datetime import date

import pytest
from mcp import Client, MCPError
from mcp_types import INVALID_PARAMS

from opslens.agent_baseline.application import authorize_agent_action
from opslens.agent_baseline.domain import (
    AgentCapability,
    AgentCapabilityInvocation,
    AgentDecision,
    AuthorizedAgentAction,
    StructuredSecurityQueryInvocation,
    create_agent_action_proposal,
    create_single_agent_task,
)
from opslens.mcp_boundary import (
    MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION,
    InMemoryMcpInvocationResolver,
    McpBoundaryValidationError,
    McpToolName,
    admit_mcp_invocation_reference,
    build_offline_mcp_server,
)
from opslens.semantic_query.domain import (
    EpssFilters,
    SemanticDimension,
    SemanticMetric,
    SemanticQuery,
)


def anyio_backend() -> str:
    """Keep official MCP in-process tests on one deterministic async backend."""
    return "asyncio"


def _authorized_action() -> AuthorizedAgentAction:
    """Create one authorization using the frozen Phase 11 authority boundary."""
    capability = AgentCapability.STRUCTURED_SECURITY_QUERY
    task = create_single_agent_task(
        text="Use structured security facts",
        allowed_capabilities=(capability,),
    )
    proposal = create_agent_action_proposal(
        task_id=task.task_id,
        decision=AgentDecision.ACT,
        capability=capability,
    )
    result = authorize_agent_action(task, proposal)
    assert type(result) is AuthorizedAgentAction
    return result


def _structured_invocation(*, minimum_score: float) -> StructuredSecurityQueryInvocation:
    """Create one existing typed invocation without capability execution."""
    query = SemanticQuery(
        metric=SemanticMetric.EPSS_SCORE,
        dimensions=(SemanticDimension.CVE,),
        filters=EpssFilters(
            snapshot_date=date(2026, 9, 8),
            minimum_score=minimum_score,
        ),
        limit=3,
    )
    return StructuredSecurityQueryInvocation.create(action=_authorized_action(), query=query)


class _SubstitutingResolver:
    """Test double that violates the exact invocation-reference resolver contract."""

    def __init__(self, invocation: AgentCapabilityInvocation) -> None:
        self._invocation = invocation

    def resolve(
        self,
        invocation_id: str,
        invocation_sha256: str,
    ) -> AgentCapabilityInvocation:
        """Return a different invocation regardless of requested identity."""
        del invocation_id, invocation_sha256
        return self._invocation


def test_protocol_service_rejects_resolver_identity_substitution() -> None:
    """A resolver hit cannot substitute another already-valid typed invocation."""
    requested = _structured_invocation(minimum_score=0.7)
    substituted = _structured_invocation(minimum_score=0.8)

    with pytest.raises(McpBoundaryValidationError, match="different invocation_id"):
        admit_mcp_invocation_reference(
            tool_name=McpToolName.STRUCTURED_SECURITY_QUERY,
            invocation_id=requested.invocation_id,
            invocation_sha256=requested.invocation_sha256,
            resolver=_SubstitutingResolver(substituted),
        )


@pytest.mark.anyio
async def test_official_sdk_lists_exact_closed_tool_surface() -> None:
    """The real SDK exposes exactly the four Gate 13.1 code-owned tool identities."""
    invocation = _structured_invocation(minimum_score=0.7)
    server = build_offline_mcp_server(
        resolver=InMemoryMcpInvocationResolver((invocation,)),
    )

    async with Client(server, raise_exceptions=True) as client:
        listed = await client.list_tools()

    assert {tool.name for tool in listed.tools} == {tool.value for tool in McpToolName}


@pytest.mark.anyio
async def test_official_sdk_admits_reference_and_returns_minimized_evidence_only() -> None:
    """A real protocol call reaches Gate 13.1 admission and stops before execution."""
    invocation = _structured_invocation(minimum_score=0.7)
    server = build_offline_mcp_server(
        resolver=InMemoryMcpInvocationResolver((invocation,)),
    )

    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool(
            McpToolName.STRUCTURED_SECURITY_QUERY.value,
            {
                "invocation_id": invocation.invocation_id,
                "invocation_sha256": invocation.invocation_sha256,
            },
        )

    assert not result.is_error
    assert result.structured_content == {
        "contract_version": MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION,
        "tool_name": McpToolName.STRUCTURED_SECURITY_QUERY.value,
        "capability": AgentCapability.STRUCTURED_SECURITY_QUERY.value,
        "action_id": invocation.action.action_id,
        "invocation_id": invocation.invocation_id,
        "invocation_sha256": invocation.invocation_sha256,
        "admission_id": result.structured_content["admission_id"],
        "admission_sha256": result.structured_content["admission_sha256"],
    }
    assert set(result.structured_content) == {
        "contract_version",
        "tool_name",
        "capability",
        "action_id",
        "invocation_id",
        "invocation_sha256",
        "admission_id",
        "admission_sha256",
    }


@pytest.mark.anyio
async def test_official_sdk_tool_capability_mismatch_fails_closed_without_reference_leak() -> None:
    """A different MCP tool cannot reinterpret one valid typed invocation."""
    invocation = _structured_invocation(minimum_score=0.7)
    server = build_offline_mcp_server(
        resolver=InMemoryMcpInvocationResolver((invocation,)),
    )

    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool(
            McpToolName.KNOWLEDGE_GUIDANCE.value,
            {
                "invocation_id": invocation.invocation_id,
                "invocation_sha256": invocation.invocation_sha256,
            },
        )

    assert result.is_error is True
    assert result.structured_content is None
    assert invocation.invocation_id not in repr(result.content)
    assert invocation.invocation_sha256 not in repr(result.content)


@pytest.mark.anyio
async def test_official_sdk_unknown_invocation_fails_closed() -> None:
    """A well-shaped but unknown invocation reference cannot cross the resolver boundary."""
    digest = "a" * 64
    invocation_id = f"single-agent-execution:v1:invocation:{digest}"
    server = build_offline_mcp_server(
        resolver=InMemoryMcpInvocationResolver(()),
    )

    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool(
            McpToolName.STRUCTURED_SECURITY_QUERY.value,
            {
                "invocation_id": invocation_id,
                "invocation_sha256": digest,
            },
        )

    assert result.is_error is True
    assert result.structured_content is None
    assert invocation_id not in repr(result.content)
    assert digest not in repr(result.content)


@pytest.mark.anyio
async def test_official_sdk_rejects_arbitrary_executable_argument_surface() -> None:
    """Protocol callers cannot smuggle SQL or arbitrary execution arguments into the tool."""
    invocation = _structured_invocation(minimum_score=0.7)
    server = build_offline_mcp_server(
        resolver=InMemoryMcpInvocationResolver((invocation,)),
    )

    async with Client(server, raise_exceptions=True) as client:
        with pytest.raises(MCPError) as exc_info:
            await client.call_tool(
                McpToolName.STRUCTURED_SECURITY_QUERY.value,
                {
                    "invocation_id": invocation.invocation_id,
                    "invocation_sha256": invocation.invocation_sha256,
                    "sql": "DROP TABLE findings",
                },
            )

    assert exc_info.value.error.code == INVALID_PARAMS
    assert exc_info.value.error.message == "MCP tool arguments rejected."
