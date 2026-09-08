"""Offline tests for the Phase 13 Gate 13.3 MCP capability execution bridge."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from typing import cast

import pytest
from mcp import Client, MCPError
from mcp_types import INVALID_PARAMS

from opslens.agent_baseline.application import (
    AgentCapabilityExecutors,
    authorize_agent_action,
    execute_authorized_capability,
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
    MCP_CAPABILITY_EXECUTION_CONTRACT_VERSION,
    InMemoryMcpInvocationResolver,
    McpBoundaryValidationError,
    McpCapabilityExecutionBridge,
    McpToolName,
    admit_mcp_tool_call,
    build_offline_mcp_execution_server,
    execute_mcp_invocation_reference,
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
    """Create one real authorization for the structured-security capability."""
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


def _structured_invocation(*, minimum_score: float = 0.7) -> StructuredSecurityQueryInvocation:
    """Create one exact typed invocation without executing it."""
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


def _empty_structured_calls() -> list[StructuredSecurityQueryInvocation]:
    """Return a fully typed empty call recorder for strict Pyright."""
    return []


@dataclass(slots=True)
class _StructuredExecutor:
    """Record exact invocation objects and return deterministic bound result evidence."""

    calls: list[StructuredSecurityQueryInvocation] = field(
        default_factory=_empty_structured_calls
    )
    fail: bool = False
    wrong_result_type: bool = False
    mismatched_result: bool = False

    def execute_structured_security_query(
        self,
        invocation: StructuredSecurityQueryInvocation,
    ) -> StructuredSecurityQueryResultBinding:
        self.calls.append(invocation)
        if self.fail:
            raise RuntimeError("secret downstream provider detail")
        if self.wrong_result_type:
            return cast(StructuredSecurityQueryResultBinding, object())

        bound_invocation = invocation
        if self.mismatched_result:
            bound_invocation = _structured_invocation(minimum_score=0.8)
        result = AthenaQueryResult(
            query_execution_id="offline-mcp-execution-1",
            columns=("cve", "epss_score"),
            rows=(("CVE-2026-0001", "0.91"),),
            data_scanned_bytes=128,
        )
        return StructuredSecurityQueryResultBinding.create(
            invocation=bound_invocation,
            result=result,
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
    """Build the existing closed executor set with only structured execution enabled."""
    return AgentCapabilityExecutors(
        structured_security_query=structured,
        knowledge_guidance=_UnusedKnowledgeExecutor(),
        hybrid_security_answer=_UnusedHybridExecutor(),
        public_repository_analysis=_UnusedPublicExecutor(),
    )


def test_mcp_execution_bridge_contract_binds_admission_and_execution_identity() -> None:
    """Bridge evidence content-addresses the exact admission and typed execution."""
    invocation = _structured_invocation()
    admission = admit_mcp_tool_call(
        tool_name=McpToolName.STRUCTURED_SECURITY_QUERY,
        invocation=invocation,
    )
    executor = _StructuredExecutor()
    execution = execute_authorized_capability(invocation, _executors(executor))

    bridge = McpCapabilityExecutionBridge.create(
        admission=admission,
        invocation=invocation,
        execution=execution,
    )

    assert MCP_CAPABILITY_EXECUTION_CONTRACT_VERSION == "mcp-capability-execution:v1"
    assert bridge.tool_name is McpToolName.STRUCTURED_SECURITY_QUERY
    assert bridge.action_id == invocation.action.action_id
    assert bridge.invocation_id == invocation.invocation_id
    assert bridge.invocation_sha256 == invocation.invocation_sha256
    assert bridge.admission_id == admission.admission_id
    assert bridge.execution_id == execution.execution_id
    assert executor.calls == [invocation]


def test_mcp_execution_bridge_rejects_internally_mismatched_content_ids() -> None:
    """Standalone bridge evidence rejects an execution ID paired with another digest."""
    invocation = _structured_invocation()
    admission = admit_mcp_tool_call(
        tool_name=McpToolName.STRUCTURED_SECURITY_QUERY,
        invocation=invocation,
    )
    execution = execute_authorized_capability(
        invocation,
        _executors(_StructuredExecutor()),
    )
    bridge = McpCapabilityExecutionBridge.create(
        admission=admission,
        invocation=invocation,
        execution=execution,
    )

    with pytest.raises(McpBoundaryValidationError, match="execution id and digest"):
        replace(
            bridge,
            execution_id=f"single-agent-execution:v1:execution:{'0' * 64}",
        )


def test_execution_application_service_executes_exact_resolved_invocation_once() -> None:
    """Application wiring preserves exact invocation identity and one-attempt cardinality."""
    invocation = _structured_invocation()
    executor = _StructuredExecutor()

    projection = execute_mcp_invocation_reference(
        tool_name=McpToolName.STRUCTURED_SECURITY_QUERY,
        invocation_id=invocation.invocation_id,
        invocation_sha256=invocation.invocation_sha256,
        resolver=InMemoryMcpInvocationResolver((invocation,)),
        executors=_executors(executor),
    )

    assert len(executor.calls) == 1
    assert executor.calls[0] is invocation
    assert projection.contract_version == MCP_CAPABILITY_EXECUTION_CONTRACT_VERSION
    assert projection.invocation_id == invocation.invocation_id
    assert projection.action_id == invocation.action.action_id


@pytest.mark.anyio
async def test_official_sdk_execution_bridge_returns_identity_evidence_only() -> None:
    """Real MCP transport executes once while withholding business result content."""
    invocation = _structured_invocation()
    executor = _StructuredExecutor()
    server = build_offline_mcp_execution_server(
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
    assert len(executor.calls) == 1
    assert executor.calls[0] is invocation
    assert result.structured_content is not None
    assert set(result.structured_content) == {
        "contract_version",
        "tool_name",
        "capability",
        "action_id",
        "invocation_id",
        "invocation_sha256",
        "admission_id",
        "admission_sha256",
        "execution_id",
        "execution_sha256",
        "downstream_result_sha256",
        "bridge_id",
        "bridge_sha256",
    }
    serialized = repr(result.structured_content)
    assert "CVE-2026-0001" not in serialized
    assert "offline-mcp-execution-1" not in serialized
    assert "0.91" not in serialized


@pytest.mark.anyio
async def test_official_sdk_tool_mismatch_fails_before_execution() -> None:
    """A valid structured invocation cannot execute through another MCP tool identity."""
    invocation = _structured_invocation()
    executor = _StructuredExecutor()
    server = build_offline_mcp_execution_server(
        resolver=InMemoryMcpInvocationResolver((invocation,)),
        executors=_executors(executor),
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
    assert executor.calls == []
    assert "MCP capability execution rejected." in repr(result.content)
    assert invocation.invocation_id not in repr(result.content)


@pytest.mark.anyio
async def test_official_sdk_executor_failure_is_content_minimized() -> None:
    """Downstream exception content is replaced by one stable protocol failure."""
    invocation = _structured_invocation()
    executor = _StructuredExecutor(fail=True)
    server = build_offline_mcp_execution_server(
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
    assert len(executor.calls) == 1
    assert "MCP capability execution failed." in repr(result.content)
    assert "secret downstream provider detail" not in repr(result.content)


@pytest.mark.anyio
@pytest.mark.parametrize("failure_mode", ["wrong_type", "mismatched_result"])
async def test_official_sdk_invalid_executor_result_fails_closed(failure_mode: str) -> None:
    """Wrong result family or mismatched result identity cannot become MCP execution evidence."""
    invocation = _structured_invocation()
    executor = _StructuredExecutor(
        wrong_result_type=failure_mode == "wrong_type",
        mismatched_result=failure_mode == "mismatched_result",
    )
    server = build_offline_mcp_execution_server(
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
    assert len(executor.calls) == 1
    assert "MCP capability execution failed." in repr(result.content)


@pytest.mark.anyio
async def test_official_sdk_extra_argument_fails_before_execution() -> None:
    """The Gate 13.2 raw-argument refusal remains ahead of the execution bridge."""
    invocation = _structured_invocation()
    executor = _StructuredExecutor()
    server = build_offline_mcp_execution_server(
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
                    "sql": "DROP TABLE findings",
                },
            )

    assert exc_info.value.error.code == INVALID_PARAMS
    assert exc_info.value.error.message == "MCP tool arguments rejected."
    assert executor.calls == []
