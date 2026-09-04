"""Contract tests for the governed semantic-planner transport."""

from __future__ import annotations

from types import TracebackType
from typing import ClassVar

import pytest
from governed_llm_gateway_contracts import (
    ExecutionStatus,
    Message,
    MessageRole,
    ProviderExecution,
    StructuredOutputSchema,
    WorkloadRequirements,
)

from opslens.semantic_query.adapters.outbound import governed_gateway as gateway_module
from opslens.semantic_query.adapters.outbound.governed_gateway import (
    GovernedGatewayPlannerConfig,
    GovernedGatewaySemanticPlanner,
    SemanticPlannerUnavailableError,
)
from opslens.semantic_query.planner.models import (
    PlannerContractError,
    PlannerDecision,
    SemanticPlannerRequest,
    UnsupportedPlannerDecision,
    UnsupportedReason,
)
from opslens.semantic_query.planner.prompt import PLANNER_MAX_TOKENS, PLANNER_SYSTEM_PROMPT
from opslens.semantic_query.planner.schema import PLANNER_OUTPUT_SCHEMA, PLANNER_SCHEMA_NAME


def _successful_execution() -> ProviderExecution:
    return ProviderExecution(
        provider="bedrock",
        model="anthropic.claude-haiku-4-5-20251001-v1:0",
        deployment="opslens-semantic-planner",
        status=ExecutionStatus.SUCCEEDED,
        latency_ms=42,
    )


class _FakeResponse:
    def __init__(
        self,
        *,
        content: str | None,
        status: ExecutionStatus,
        execution: ProviderExecution | None,
    ) -> None:
        self.content = content
        self.status = status
        self.execution = execution


class _FakeGatewayClient:
    observed: ClassVar[dict[str, object]] = {}
    content: ClassVar[str | None] = '{"decision":"unsupported","reason":"ambiguous"}'
    status: ClassVar[ExecutionStatus] = ExecutionStatus.SUCCEEDED
    execution: ClassVar[ProviderExecution | None] = _successful_execution()

    def __init__(self, config: object) -> None:
        self.config = config

    async def __aenter__(self) -> _FakeGatewayClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def generate(self, **kwargs: object) -> _FakeResponse:
        type(self).observed = kwargs
        return _FakeResponse(
            content=type(self).content,
            status=type(self).status,
            execution=type(self).execution,
        )


def _planner() -> GovernedGatewaySemanticPlanner:
    return GovernedGatewaySemanticPlanner(
        GovernedGatewayPlannerConfig(
            base_url="https://gateway.example.com",
            api_key="test-key",
        )
    )


def _reset_success() -> None:
    _FakeGatewayClient.content = '{"decision":"unsupported","reason":"ambiguous"}'
    _FakeGatewayClient.status = ExecutionStatus.SUCCEEDED
    _FakeGatewayClient.execution = _successful_execution()


def test_gateway_planner_preserves_bounded_structured_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep the gateway request provider-neutral and schema-bounded."""
    monkeypatch.setattr(gateway_module, "GatewayClient", _FakeGatewayClient)
    _reset_success()

    outcome = _planner().plan(SemanticPlannerRequest("show me the latest EPSS values"))

    assert isinstance(outcome, UnsupportedPlannerDecision)
    assert outcome.decision is PlannerDecision.UNSUPPORTED
    assert outcome.reason is UnsupportedReason.AMBIGUOUS
    assert _FakeGatewayClient.observed["workload"] == "opslens.semantic-query.plan"
    assert _FakeGatewayClient.observed["max_output_tokens"] == PLANNER_MAX_TOKENS
    assert _FakeGatewayClient.observed["provider_timeout_seconds"] == 10.0

    messages = _FakeGatewayClient.observed["messages"]
    assert isinstance(messages, tuple)
    assert messages == (
        Message(role=MessageRole.SYSTEM, content=PLANNER_SYSTEM_PROMPT),
        Message(role=MessageRole.USER, content="show me the latest EPSS values"),
    )

    requirements = _FakeGatewayClient.observed["requirements"]
    assert isinstance(requirements, WorkloadRequirements)
    assert requirements.structured_output is True
    structured_output = _FakeGatewayClient.observed["structured_output"]
    assert isinstance(structured_output, StructuredOutputSchema)
    assert structured_output.name == PLANNER_SCHEMA_NAME
    assert structured_output.schema == PLANNER_OUTPUT_SCHEMA
    assert "tools" not in _FakeGatewayClient.observed
    assert "provider" not in _FakeGatewayClient.observed
    assert "model" not in _FakeGatewayClient.observed


def test_gateway_planner_rejects_failed_partial_content(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject partial output whenever gateway execution is terminally failed."""
    monkeypatch.setattr(gateway_module, "GatewayClient", _FakeGatewayClient)
    _FakeGatewayClient.content = '{"decision":"unsupported","reason":"ambiguous"}'
    _FakeGatewayClient.status = ExecutionStatus.FAILED
    _FakeGatewayClient.execution = ProviderExecution(
        provider="bedrock",
        model="anthropic.claude-haiku-4-5-20251001-v1:0",
        deployment="opslens-semantic-planner",
        status=ExecutionStatus.FAILED,
        latency_ms=21,
    )

    with pytest.raises(SemanticPlannerUnavailableError, match="did not succeed"):
        _planner().plan(SemanticPlannerRequest("show EPSS for 2026-09-01"))


def test_gateway_planner_requires_terminal_execution_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject success-shaped responses that omit runtime execution evidence."""
    monkeypatch.setattr(gateway_module, "GatewayClient", _FakeGatewayClient)
    _reset_success()
    _FakeGatewayClient.execution = None

    with pytest.raises(SemanticPlannerUnavailableError, match="no terminal execution evidence"):
        _planner().plan(SemanticPlannerRequest("show EPSS for 2026-09-01"))


def test_gateway_planner_rejects_non_success_terminal_execution_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject contradictory terminal execution evidence before parsing model content."""
    monkeypatch.setattr(gateway_module, "GatewayClient", _FakeGatewayClient)
    _reset_success()
    _FakeGatewayClient.execution = ProviderExecution(
        provider="bedrock",
        model="anthropic.claude-haiku-4-5-20251001-v1:0",
        deployment="opslens-semantic-planner",
        status=ExecutionStatus.FAILED,
        latency_ms=21,
    )

    with pytest.raises(SemanticPlannerUnavailableError, match="terminal execution evidence"):
        _planner().plan(SemanticPlannerRequest("show EPSS for 2026-09-01"))


def test_gateway_planner_keeps_deterministic_parser_as_final_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject malformed model proposals through the existing deterministic parser."""
    monkeypatch.setattr(gateway_module, "GatewayClient", _FakeGatewayClient)
    _reset_success()
    _FakeGatewayClient.content = '{"decision":"semantic_query","metric":"epss_score"}'

    with pytest.raises(PlannerContractError, match="must match the frozen contract"):
        _planner().plan(SemanticPlannerRequest("show EPSS for 2026-09-01"))
