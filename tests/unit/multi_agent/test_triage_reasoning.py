"""Tests for bounded provider-neutral multi-agent triage reasoning."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from opslens.agent_baseline.domain.models import (
    AgentCapability,
    SingleAgentTask,
    create_single_agent_task,
)
from opslens.multi_agent.adapters.bedrock_triage_reasoning import (
    BEDROCK_TRIAGE_REASONING_MAX_TOKENS,
    BEDROCK_TRIAGE_REASONING_MODEL_ID,
    BEDROCK_TRIAGE_REASONING_OUTPUT_SCHEMA_JSON,
    build_bedrock_triage_reasoning_request,
)
from opslens.multi_agent.application.triage_reasoning import (
    parse_triage_model_output,
    reason_about_triage_task,
)
from opslens.multi_agent.domain.errors import MultiAgentTriageReasoningValidationError
from opslens.multi_agent.domain.handoff import (
    AgentSpecialization,
    MultiAgentHandoffDecision,
)
from opslens.multi_agent.domain.triage_reasoning import (
    MAX_MULTI_AGENT_TRIAGE_OUTPUT_UTF8_BYTES,
    MultiAgentTriageInvocationEvidence,
)
from opslens.multi_agent.ports.triage_reasoning import MultiAgentTriageReasoningModelResponse


def _task() -> SingleAgentTask:
    return create_single_agent_task(
        text="Which admitted CVEs have EPSS of at least 0.7?",
        allowed_capabilities=(
            AgentCapability.PUBLIC_REPOSITORY_ANALYSIS,
            AgentCapability.STRUCTURED_SECURITY_QUERY,
        ),
    )


def _evidence(task: SingleAgentTask, *, request_id: str = "request-1") -> MultiAgentTriageInvocationEvidence:
    return MultiAgentTriageInvocationEvidence.create(
        source_task_id=task.task_id,
        provider="amazon_bedrock",
        model_id=BEDROCK_TRIAGE_REASONING_MODEL_ID,
        region="us-east-1",
        request_id=request_id,
        stop_reason="end_turn",
        input_tokens=20,
        output_tokens=4,
        total_tokens=24,
        cache_read_input_tokens=0,
        cache_write_input_tokens=0,
        provider_latency_ms=10,
        client_elapsed_ms=12,
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
            evidence=_evidence(task),
        )


def test_triage_parser_creates_existing_handoff_proposal() -> None:
    task = _task()

    proposal = parse_triage_model_output(
        task=task,
        output_text=(
            '{"decision":"handoff","target_specialization":"evidence_analysis"}'
        ),
    )

    assert proposal.source_task_id == task.task_id
    assert proposal.decision is MultiAgentHandoffDecision.HANDOFF
    assert proposal.target_specialization is AgentSpecialization.EVIDENCE_ANALYSIS


def test_triage_parser_accepts_explicit_abstention() -> None:
    proposal = parse_triage_model_output(
        task=_task(),
        output_text='{"decision":"abstain","target_specialization":null}',
    )

    assert proposal.decision is MultiAgentHandoffDecision.ABSTAIN
    assert proposal.target_specialization is None


@pytest.mark.parametrize(
    "output_text, message",
    [
        (
            '{"decision":"handoff","target_specialization":null}',
            "requires one specialization",
        ),
        (
            '{"decision":"abstain","target_specialization":"evidence_analysis"}',
            "cannot carry a specialization",
        ),
        (
            '{"decision":"handoff","target_specialization":"evidence_analysis",'
            '"capability":"structured_security_query"}',
            "exactly decision and target_specialization",
        ),
    ],
)
def test_triage_parser_rejects_authority_broadening_shapes(
    output_text: str,
    message: str,
) -> None:
    with pytest.raises(MultiAgentTriageReasoningValidationError, match=message):
        parse_triage_model_output(task=_task(), output_text=output_text)


def test_triage_parser_rejects_oversized_output() -> None:
    with pytest.raises(
        MultiAgentTriageReasoningValidationError,
        match="byte limit",
    ):
        parse_triage_model_output(
            task=_task(),
            output_text="x" * (MAX_MULTI_AGENT_TRIAGE_OUTPUT_UTF8_BYTES + 1),
        )


def test_triage_reasoning_invokes_model_exactly_once() -> None:
    task = _task()
    model = _FakeTriageModel(
        '{"decision":"handoff","target_specialization":"evidence_analysis"}'
    )

    result = reason_about_triage_task(task=task, model=model)

    assert model.requests == [task.task_id]
    assert result.invocation_count == 1
    assert result.proposal.target_specialization is AgentSpecialization.EVIDENCE_ANALYSIS
    assert result.invocation_evidence.retry_attempts == 0
    assert result.result_id.startswith("multi-agent-triage-reasoning:v1:result:")


def test_bedrock_triage_request_is_fixed_and_has_no_tool_authority() -> None:
    request = build_bedrock_triage_reasoning_request(_task())

    assert request["modelId"] == BEDROCK_TRIAGE_REASONING_MODEL_ID
    assert request["inferenceConfig"] == {
        "maxTokens": BEDROCK_TRIAGE_REASONING_MAX_TOKENS,
        "temperature": 0.0,
    }
    assert "toolConfig" not in request
    assert "guardrailConfig" not in request
    assert "capability" not in BEDROCK_TRIAGE_REASONING_OUTPUT_SCHEMA_JSON
    assert "target_specialization" in BEDROCK_TRIAGE_REASONING_OUTPUT_SCHEMA_JSON
