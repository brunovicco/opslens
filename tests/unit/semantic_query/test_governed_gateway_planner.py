"""Contract tests for the governed semantic-planner transport."""

from __future__ import annotations

from types import TracebackType
from typing import ClassVar

import pytest
from governed_llm_gateway_contracts import ExecutionStatus, StreamEventType

from opslens.semantic_query.adapters.outbound import governed_gateway as gateway_module
from opslens.semantic_query.adapters.outbound.governed_gateway import (
    GovernedGatewayPlannerConfig,
    GovernedGatewaySemanticPlanner,
    SemanticPlannerUnavailableError,
)
from opslens.semantic_query.planner.models import (
    PlannerDecision,
    SemanticPlannerRequest,
    UnsupportedPlannerDecision,
    UnsupportedReason,
)
from opslens.semantic_query.planner.schema import PLANNER_SCHEMA_NAME


class _FakeResponse:
    def __init__(self, *, content: str | None, status: ExecutionStatus) -> None:
        self.content = content
        self.status = status


class _FakeGatewayClient:
    observed: ClassVar[dict[str, object]] = {}
    content: ClassVar[str | None] = '{"decision":"unsupported","reason":"ambiguous"}'
    status: ClassVar[ExecutionStatus] = ExecutionStatus.SUCCEEDED

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
        return _FakeResponse(content=type(self).content, status=type(self).status)


def _planner() -> GovernedGatewaySemanticPlanner:
    return GovernedGatewaySemanticPlanner(
        GovernedGatewayPlannerConfig(
            base_url="https://gateway.example.com",
            api_key="test-key",
        )
    )


def test_gateway_planner_preserves_bounded_structured_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gateway_module, "GatewayClient", _FakeGatewayClient)
    _FakeGatewayClient.content = '{"decision":"unsupported","reason":"ambiguous"}'
    _FakeGatewayClient.status = ExecutionStatus.SUCCEEDED

    outcome = _planner().plan(SemanticPlannerRequest("show me the latest EPSS values"))

    assert isinstance(outcome, UnsupportedPlannerDecision)
    assert outcome.decision is PlannerDecision.UNSUPPORTED
    assert outcome.reason is UnsupportedReason.AMBIGUOUS
    assert _FakeGatewayClient.observed["workload"] == "opslens.semantic-query.plan"
    requirements = _FakeGatewayClient.observed["requirements"]
    assert getattr(requirements, "structured_output") is True
    structured_output = _FakeGatewayClient.observed["structured_output"]
    assert getattr(structured_output, "name") == PLANNER_SCHEMA_NAME


def test_gateway_planner_rejects_failed_partial_content(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gateway_module, "GatewayClient", _FakeGatewayClient)
    _FakeGatewayClient.content = '{"decision":"unsupported","reason":"ambiguous"}'
    _FakeGatewayClient.status = ExecutionStatus.FAILED

    with pytest.raises(SemanticPlannerUnavailableError, match="did not succeed"):
        _planner().plan(SemanticPlannerRequest("show EPSS for 2026-09-01"))


def test_gateway_planner_keeps_deterministic_parser_as_final_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gateway_module, "GatewayClient", _FakeGatewayClient)
    _FakeGatewayClient.content = '{"decision":"semantic_query","metric":"epss_score"}'
    _FakeGatewayClient.status = ExecutionStatus.SUCCEEDED

    with pytest.raises(ValueError, match="exact"):
        _planner().plan(SemanticPlannerRequest("show EPSS for 2026-09-01"))


def test_gateway_planner_does_not_use_streaming_or_tools() -> None:
    assert StreamEventType.RESPONSE_COMPLETED.value == "response.completed"
