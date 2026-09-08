"""Tests for bounded triage-to-specialist reasoning without capability execution."""

from __future__ import annotations

from dataclasses import dataclass, field

from opslens.agent_baseline.domain.models import (
    AgentCapability,
    SingleAgentTask,
    create_single_agent_task,
)
from opslens.agent_baseline.domain.reasoning import AgentReasoningInvocationEvidence
from opslens.agent_baseline.ports.reasoning import AgentReasoningModelResponse
from opslens.multi_agent.application.two_model_reasoning import run_two_model_reasoning
from opslens.multi_agent.domain.triage_reasoning import MultiAgentTriageInvocationEvidence
from opslens.multi_agent.domain.two_model_reasoning import MultiAgentTwoModelOutcome
from opslens.multi_agent.ports.triage_reasoning import MultiAgentTriageReasoningModelResponse


def _source_task(*, restricted: bool = False) -> SingleAgentTask:
    capabilities = (
        (AgentCapability.KNOWLEDGE_GUIDANCE,)
        if restricted
        else (
            AgentCapability.HYBRID_SECURITY_ANSWER,
            AgentCapability.KNOWLEDGE_GUIDANCE,
            AgentCapability.PUBLIC_REPOSITORY_ANALYSIS,
            AgentCapability.STRUCTURED_SECURITY_QUERY,
        )
    )
    return create_single_agent_task(
        text="Which admitted CVEs have EPSS of at least 0.7?",
        allowed_capabilities=capabilities,
    )


def _triage_evidence(task: SingleAgentTask) -> MultiAgentTriageInvocationEvidence:
    return MultiAgentTriageInvocationEvidence.create(
        source_task_id=task.task_id,
        provider="amazon_bedrock",
        model_id="fixed-model",
        region="us-east-1",
        request_id=f"triage-{task.task_sha256[:8]}",
        stop_reason="end_turn",
        input_tokens=10,
        output_tokens=4,
        total_tokens=14,
        cache_read_input_tokens=0,
        cache_write_input_tokens=0,
        provider_latency_ms=8,
        client_elapsed_ms=9,
        retry_attempts=0,
    )


def _specialist_evidence(task: SingleAgentTask) -> AgentReasoningInvocationEvidence:
    return AgentReasoningInvocationEvidence.create(
        task_id=task.task_id,
        provider="amazon_bedrock",
        model_id="fixed-model",
        region="us-east-1",
        request_id=f"specialist-{task.task_sha256[:8]}",
        stop_reason="end_turn",
        input_tokens=12,
        output_tokens=4,
        total_tokens=16,
        cache_read_input_tokens=0,
        cache_write_input_tokens=0,
        provider_latency_ms=9,
        client_elapsed_ms=11,
        retry_attempts=0,
    )


@dataclass
class _FakeTriageModel:
    output_text: str
    requests: list[str] = field(default_factory=list)

    def generate(self, task: SingleAgentTask) -> MultiAgentTriageReasoningModelResponse:
        self.requests.append(task.task_id)
        return MultiAgentTriageReasoningModelResponse(
            output_text=self.output_text,
            evidence=_triage_evidence(task),
        )


@dataclass
class _FakeSpecialistModel:
    output_text: str
    requests: list[str] = field(default_factory=list)

    def generate(self, task: SingleAgentTask) -> AgentReasoningModelResponse:
        self.requests.append(task.task_id)
        return AgentReasoningModelResponse(
            output_text=self.output_text,
            evidence=_specialist_evidence(task),
        )


def test_handoff_runs_exactly_two_models_and_stops_before_execution() -> None:
    """An admitted handoff may invoke one specialist but never execute a capability."""
    task = _source_task()
    triage = _FakeTriageModel(
        '{"decision":"handoff","target_specialization":"evidence_analysis"}'
    )
    specialist = _FakeSpecialistModel(
        '{"decision":"act","capability":"structured_security_query"}'
    )

    result = run_two_model_reasoning(
        task=task,
        triage_model=triage,
        specialist_model=specialist,
    )

    assert result.outcome is MultiAgentTwoModelOutcome.SPECIALIST_REASONED
    assert result.model_invocation_count == 2
    assert result.capability_executions == 0
    assert len(triage.requests) == 1
    assert len(specialist.requests) == 1
    assert result.specialist_result is not None
    assert result.specialist_result.proposal.capability is (
        AgentCapability.STRUCTURED_SECURITY_QUERY
    )
    assert result.specialist_result.task.allowed_capabilities == (
        AgentCapability.PUBLIC_REPOSITORY_ANALYSIS,
        AgentCapability.STRUCTURED_SECURITY_QUERY,
    )


def test_triage_abstention_never_invokes_specialist() -> None:
    """Triage abstention must stop after the first model invocation."""
    task = _source_task()
    triage = _FakeTriageModel(
        '{"decision":"abstain","target_specialization":null}'
    )
    specialist = _FakeSpecialistModel(
        '{"decision":"act","capability":"structured_security_query"}'
    )

    result = run_two_model_reasoning(
        task=task,
        triage_model=triage,
        specialist_model=specialist,
    )

    assert result.outcome is MultiAgentTwoModelOutcome.TRIAGE_ABSTAINED
    assert result.model_invocation_count == 1
    assert result.capability_executions == 0
    assert specialist.requests == []
    assert result.specialist_result is None


def test_disjoint_handoff_fails_closed_before_specialist_call() -> None:
    """An empty specialization intersection must reject before specialist reasoning."""
    task = _source_task(restricted=True)
    triage = _FakeTriageModel(
        '{"decision":"handoff","target_specialization":"evidence_analysis"}'
    )
    specialist = _FakeSpecialistModel(
        '{"decision":"act","capability":"knowledge_guidance"}'
    )

    result = run_two_model_reasoning(
        task=task,
        triage_model=triage,
        specialist_model=specialist,
    )

    assert result.outcome is MultiAgentTwoModelOutcome.HANDOFF_REJECTED
    assert result.model_invocation_count == 1
    assert result.capability_executions == 0
    assert specialist.requests == []
    assert result.handoff_evidence_id is None
    assert result.specialist_task_id is None
