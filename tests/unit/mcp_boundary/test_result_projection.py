"""Offline tests for Phase 13 Gate 13.4 bounded MCP business-result transport."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date

import pytest
from mcp import Client, MCPError
from mcp_types import INVALID_PARAMS

from opslens.agent_baseline.application import (
    AgentCapabilityExecutors,
    authorize_agent_action,
)
from opslens.agent_baseline.domain import (
    AgentCapability,
    AgentDecision,
    AuthorizedAgentAction,
    HybridSecurityAnswerInvocation,
    KnowledgeGuidanceInvocation,
    PublicRepositoryAnalysisInvocation,
    StructuredSecurityQueryInvocation,
    StructuredSecurityQueryResultBinding,
    create_agent_action_proposal,
    create_single_agent_task,
)
from opslens.hybrid_retrieval.domain.synthesis import HybridSynthesisResult
from opslens.knowledge_retrieval.domain.synthesis import SynthesisResult
from opslens.mcp_boundary import (
    MCP_RESULT_PROJECTION_CONTRACT_VERSION,
    InMemoryMcpInvocationResolver,
    McpBoundaryValidationError,
    McpToolName,
    build_offline_mcp_structured_result_server,
    project_mcp_structured_result_reference,
)
from opslens.public_analysis.domain.semantic_planning import PublicAnalysisAdmissionHandoff
from opslens.semantic_query.application.models import AthenaQueryResult
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
    """Create one real Gate 11.1 structured-security authorization."""
    capability = AgentCapability.STRUCTURED_SECURITY_QUERY
    task = create_single_agent_task(
        text="Project bounded structured security facts",
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


def _structured_invocation(*, limit: int = 3) -> StructuredSecurityQueryInvocation:
    """Create one exact typed invocation with a bounded semantic row limit."""
    query = SemanticQuery(
        metric=SemanticMetric.EPSS_SCORE,
        dimensions=(SemanticDimension.CVE,),
        filters=EpssFilters(
            snapshot_date=date(2026, 9, 8),
            minimum_score=0.7,
        ),
        limit=limit,
    )
    return StructuredSecurityQueryInvocation.create(
        action=_authorized_action(),
        query=query,
    )


def _empty_calls() -> list[StructuredSecurityQueryInvocation]:
    return []


@dataclass(slots=True)
class _StructuredExecutor:
    """Return deterministic structured evidence while recording exact call identity."""

    rows: tuple[tuple[str | None, ...], ...] = (("CVE-2026-0001", "0.9100"),)
    columns: tuple[str, ...] = ("cve", "epss")
    fail: bool = False
    calls: list[StructuredSecurityQueryInvocation] = field(default_factory=_empty_calls)

    def execute_structured_security_query(
        self,
        invocation: StructuredSecurityQueryInvocation,
    ) -> StructuredSecurityQueryResultBinding:
        self.calls.append(invocation)
        if self.fail:
            raise RuntimeError("secret Athena/provider failure")
        return StructuredSecurityQueryResultBinding.create(
            invocation=invocation,
            result=AthenaQueryResult(
                query_execution_id="gate-13-4-offline-query",
                columns=self.columns,
                rows=self.rows,
                data_scanned_bytes=256,
                engine_execution_time_ms=12,
                total_execution_time_ms=19,
            ),
        )


class _UnusedKnowledgeExecutor:
    def execute_knowledge_guidance(
        self,
        invocation: KnowledgeGuidanceInvocation,
    ) -> SynthesisResult:
        del invocation
        raise AssertionError("knowledge executor must not be called")


class _UnusedHybridExecutor:
    def execute_hybrid_security_answer(
        self,
        invocation: HybridSecurityAnswerInvocation,
    ) -> HybridSynthesisResult:
        del invocation
        raise AssertionError("hybrid executor must not be called")


class _UnusedPublicExecutor:
    def execute_public_repository_analysis(
        self,
        invocation: PublicRepositoryAnalysisInvocation,
    ) -> PublicAnalysisAdmissionHandoff:
        del invocation
        raise AssertionError("public executor must not be called")


def _executors(structured: _StructuredExecutor) -> AgentCapabilityExecutors:
    return AgentCapabilityExecutors(
        structured_security_query=structured,
        knowledge_guidance=_UnusedKnowledgeExecutor(),
        hybrid_security_answer=_UnusedHybridExecutor(),
        public_repository_analysis=_UnusedPublicExecutor(),
    )


def test_structured_result_projection_is_explicit_bounded_and_content_addressed() -> None:
    """Projection exposes only code-owned CVE/EPSS content plus provenance identities."""
    invocation = _structured_invocation()
    executor = _StructuredExecutor()

    projection = project_mcp_structured_result_reference(
        tool_name=McpToolName.STRUCTURED_SECURITY_QUERY,
        invocation_id=invocation.invocation_id,
        invocation_sha256=invocation.invocation_sha256,
        resolver=InMemoryMcpInvocationResolver((invocation,)),
        executors=_executors(executor),
    )

    assert executor.calls == [invocation]
    assert projection.contract_version == MCP_RESULT_PROJECTION_CONTRACT_VERSION
    assert projection.tool_name is McpToolName.STRUCTURED_SECURITY_QUERY
    assert projection.capability is AgentCapability.STRUCTURED_SECURITY_QUERY
    assert projection.columns == ("cve", "epss_score")
    assert tuple(row.canonical_payload() for row in projection.rows) == (
        {"cve": "CVE-2026-0001", "epss_score": "0.91"},
    )
    assert projection.projection_id.endswith(projection.projection_sha256)

    with pytest.raises(McpBoundaryValidationError, match="projection_sha256"):
        replace(projection, projection_sha256="0" * 64)


def test_projection_rejects_rows_beyond_semantic_query_limit_after_one_execution() -> None:
    """Even admitted result evidence cannot broaden the invocation's row authority."""
    invocation = _structured_invocation(limit=2)
    executor = _StructuredExecutor(
        rows=(
            ("CVE-2026-0001", "0.91"),
            ("CVE-2026-0002", "0.88"),
            ("CVE-2026-0003", "0.82"),
        )
    )

    with pytest.raises(McpBoundaryValidationError, match="semantic-query row limit"):
        project_mcp_structured_result_reference(
            tool_name=McpToolName.STRUCTURED_SECURITY_QUERY,
            invocation_id=invocation.invocation_id,
            invocation_sha256=invocation.invocation_sha256,
            resolver=InMemoryMcpInvocationResolver((invocation,)),
            executors=_executors(executor),
        )

    assert executor.calls == [invocation]


def test_projection_rejects_non_compiler_columns_and_invalid_epss_content() -> None:
    """Result transport does not inherit arbitrary column or value serialization authority."""
    invocation = _structured_invocation()

    wrong_columns = _StructuredExecutor(columns=("cve", "severity"))
    with pytest.raises(McpBoundaryValidationError, match="columns"):
        project_mcp_structured_result_reference(
            tool_name=McpToolName.STRUCTURED_SECURITY_QUERY,
            invocation_id=invocation.invocation_id,
            invocation_sha256=invocation.invocation_sha256,
            resolver=InMemoryMcpInvocationResolver((invocation,)),
            executors=_executors(wrong_columns),
        )

    invalid_score = _StructuredExecutor(rows=(("CVE-2026-0001", "1.5"),))
    with pytest.raises(McpBoundaryValidationError, match="EPSS"):
        project_mcp_structured_result_reference(
            tool_name=McpToolName.STRUCTURED_SECURITY_QUERY,
            invocation_id=invocation.invocation_id,
            invocation_sha256=invocation.invocation_sha256,
            resolver=InMemoryMcpInvocationResolver((invocation,)),
            executors=_executors(invalid_score),
        )


def test_non_structured_business_result_projection_fails_before_execution() -> None:
    """Gate 13.4 cannot project another capability through a generic fallback."""
    invocation = _structured_invocation()
    executor = _StructuredExecutor()

    with pytest.raises(McpBoundaryValidationError, match="supports only"):
        project_mcp_structured_result_reference(
            tool_name=McpToolName.KNOWLEDGE_GUIDANCE,
            invocation_id=invocation.invocation_id,
            invocation_sha256=invocation.invocation_sha256,
            resolver=InMemoryMcpInvocationResolver((invocation,)),
            executors=_executors(executor),
        )

    assert executor.calls == []


@pytest.mark.anyio
async def test_official_sdk_result_server_transports_only_allowlisted_business_fields() -> None:
    """Official MCP transport exposes bounded CVE/EPSS rows and no engine metadata."""
    invocation = _structured_invocation()
    executor = _StructuredExecutor()
    server = build_offline_mcp_structured_result_server(
        resolver=InMemoryMcpInvocationResolver((invocation,)),
        executors=_executors(executor),
    )

    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool(
            McpToolName.STRUCTURED_SECURITY_QUERY.value,
            {
                "invocation_id": invocation.invocation_id,
                "invocation_sha256": invocation.invocation_sha256,
            },
        )

    assert result.is_error is False
    assert executor.calls == [invocation]
    assert result.structured_content is not None
    assert result.structured_content["columns"] == ["cve", "epss_score"]
    assert result.structured_content["rows"] == [
        {"cve": "CVE-2026-0001", "epss_score": "0.91"}
    ]
    serialized = repr(result.structured_content)
    assert "gate-13-4-offline-query" not in serialized
    assert "data_scanned_bytes" not in serialized
    assert "engine_execution_time_ms" not in serialized
    assert "SELECT" not in serialized


@pytest.mark.anyio
async def test_official_sdk_result_server_rejects_extra_argument_before_execution() -> None:
    """Gate 13.2 raw argument refusal remains ahead of result execution and projection."""
    invocation = _structured_invocation()
    executor = _StructuredExecutor()
    server = build_offline_mcp_structured_result_server(
        resolver=InMemoryMcpInvocationResolver((invocation,)),
        executors=_executors(executor),
    )

    async with Client(server, raise_exceptions=True) as client:
        with pytest.raises(MCPError) as exc_info:
            await client.call_tool(
                McpToolName.STRUCTURED_SECURITY_QUERY.value,
                {
                    "invocation_id": invocation.invocation_id,
                    "invocation_sha256": invocation.invocation_sha256,
                    "sql": "SELECT * FROM secrets",
                },
            )

    assert exc_info.value.error.code == INVALID_PARAMS
    assert exc_info.value.error.message == "MCP tool arguments rejected."
    assert executor.calls == []


@pytest.mark.anyio
async def test_official_sdk_result_server_minimizes_executor_failure() -> None:
    """Downstream failure text never becomes MCP business-result transport evidence."""
    invocation = _structured_invocation()
    executor = _StructuredExecutor(fail=True)
    server = build_offline_mcp_structured_result_server(
        resolver=InMemoryMcpInvocationResolver((invocation,)),
        executors=_executors(executor),
    )

    async with Client(server, raise_exceptions=True) as client:
        result = await client.call_tool(
            McpToolName.STRUCTURED_SECURITY_QUERY.value,
            {
                "invocation_id": invocation.invocation_id,
                "invocation_sha256": invocation.invocation_sha256,
            },
        )

    assert result.is_error is True
    assert executor.calls == [invocation]
    assert "MCP capability execution failed." in repr(result.content)
    assert "secret Athena/provider failure" not in repr(result.content)
