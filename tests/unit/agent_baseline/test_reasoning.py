"""Regression tests for Gate 11.4 bounded single-agent model reasoning."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import cast

import pytest

from opslens.agent_baseline.adapters import (
    BEDROCK_AGENT_REASONING_MAX_TOKENS,
    BEDROCK_AGENT_REASONING_MODEL_ID,
    BEDROCK_AGENT_REASONING_PROVIDER,
    BEDROCK_AGENT_REASONING_REGION,
    BEDROCK_AGENT_REASONING_TEMPERATURE,
    BedrockAgentReasoningRuntimeError,
    BedrockSingleAgentReasoningModel,
    build_bedrock_agent_reasoning_request,
)
from opslens.agent_baseline.application import (
    parse_reasoning_model_output,
    reason_about_task,
)
from opslens.agent_baseline.domain import (
    MAX_AGENT_REASONING_ADAPTIVE_RETRIES,
    MAX_AGENT_REASONING_INVOCATIONS_PER_TASK,
    MAX_AGENT_REASONING_OUTPUT_UTF8_BYTES,
    SINGLE_AGENT_REASONING_CONTRACT_VERSION,
    AgentCapability,
    AgentDecision,
    AgentReasoningAuthorizationOutcome,
    AgentReasoningFailureCategory,
    AgentReasoningInvocationEvidence,
    AgentReasoningValidationError,
    SingleAgentTask,
    create_single_agent_task,
)
from opslens.agent_baseline.ports import AgentReasoningModelResponse


@dataclass(slots=True)
class _FakeReasoningModel:
    """Return one fixed model response and count application-level invocations."""

    response: AgentReasoningModelResponse
    calls: int = 0

    def generate(self, task: SingleAgentTask) -> AgentReasoningModelResponse:
        """Return the configured response exactly once per application call."""
        del task
        self.calls += 1
        return self.response


@dataclass(slots=True)
class _FakeBedrockClient:
    """Record Converse requests and return one fixed response or raise one failure."""

    response: Mapping[str, object] | None
    error: Exception | None = None
    requests: list[dict[str, object]] = field(default_factory=list)

    def converse(self, **request: object) -> Mapping[str, object]:
        """Record one request before returning or raising."""
        self.requests.append(dict(request))
        if self.error is not None:
            raise self.error
        if self.response is None:
            raise AssertionError("fake response is required")
        return self.response


@dataclass(slots=True)
class _Clock:
    """Return deterministic monotonic timestamps for adapter tests."""

    values: list[float]

    def __call__(self) -> float:
        """Pop the next configured timestamp."""
        if not self.values:
            raise AssertionError("clock exhausted")
        return self.values.pop(0)


def _task(
    *capabilities: AgentCapability,
    text: str = "Use structured facts to answer the admitted vulnerability question.",
) -> SingleAgentTask:
    """Create one admitted task for reasoning tests."""
    return create_single_agent_task(text=text, allowed_capabilities=capabilities)


def _evidence(
    task: SingleAgentTask,
    *,
    request_id: str = "request-1",
) -> AgentReasoningInvocationEvidence:
    """Create one deterministic provider-neutral invocation evidence object."""
    return AgentReasoningInvocationEvidence.create(
        task_id=task.task_id,
        provider=BEDROCK_AGENT_REASONING_PROVIDER,
        model_id=BEDROCK_AGENT_REASONING_MODEL_ID,
        region=BEDROCK_AGENT_REASONING_REGION,
        request_id=request_id,
        stop_reason="end_turn",
        input_tokens=100,
        output_tokens=10,
        total_tokens=110,
        cache_read_input_tokens=0,
        cache_write_input_tokens=0,
        provider_latency_ms=50,
        client_elapsed_ms=70,
        retry_attempts=0,
    )


def _bedrock_response(output_text: str) -> Mapping[str, object]:
    """Return the exact non-streaming Bedrock response shape admitted by the adapter."""
    return {
        "output": {"message": {"content": [{"text": output_text}]}},
        "stopReason": "end_turn",
        "usage": {
            "inputTokens": 100,
            "outputTokens": 10,
            "totalTokens": 110,
            "cacheReadInputTokens": 0,
            "cacheWriteInputTokens": 0,
        },
        "metrics": {"latencyMs": 50},
        "ResponseMetadata": {"RequestId": "request-1", "RetryAttempts": 0},
    }


def test_reasoning_contract_freezes_one_model_call_without_adaptive_retry() -> None:
    """Freeze the first model baseline as one bounded proposal invocation."""
    assert SINGLE_AGENT_REASONING_CONTRACT_VERSION == "single-agent-reasoning:v1"
    assert MAX_AGENT_REASONING_INVOCATIONS_PER_TASK == 1
    assert MAX_AGENT_REASONING_ADAPTIVE_RETRIES == 0
    assert MAX_AGENT_REASONING_OUTPUT_UTF8_BYTES == 512


def test_strict_model_output_becomes_existing_agent_action_proposal() -> None:
    """Convert only the closed decision/capability object into the Gate 11.1 proposal type."""
    task = _task(AgentCapability.STRUCTURED_SECURITY_QUERY)

    proposal = parse_reasoning_model_output(
        task=task,
        output_text='{"decision":"act","capability":"structured_security_query"}',
    )

    assert proposal.task_id == task.task_id
    assert proposal.decision is AgentDecision.ACT
    assert proposal.capability is AgentCapability.STRUCTURED_SECURITY_QUERY


def test_reasoning_output_rejects_unknown_extra_and_inconsistent_fields() -> None:
    """Fail closed before authorization when model JSON broadens or contradicts the contract."""
    task = _task(AgentCapability.KNOWLEDGE_GUIDANCE)

    with pytest.raises(AgentReasoningValidationError, match="exactly"):
        parse_reasoning_model_output(
            task=task,
            output_text=(
                '{"decision":"act","capability":"knowledge_guidance",'
                '"tool_args":{"url":"https://example.test"}}'
            ),
        )

    with pytest.raises(AgentReasoningValidationError, match="ABSTAIN"):
        parse_reasoning_model_output(
            task=task,
            output_text='{"decision":"abstain","capability":"knowledge_guidance"}',
        )

    with pytest.raises(AgentReasoningValidationError, match="ACT"):
        parse_reasoning_model_output(
            task=task,
            output_text='{"decision":"act","capability":null}',
        )


def test_reasoning_output_rejects_invalid_json_unknown_capability_and_byte_overflow() -> None:
    """Keep malformed or oversized model text outside the proposal boundary."""
    task = _task(AgentCapability.KNOWLEDGE_GUIDANCE)

    with pytest.raises(AgentReasoningValidationError, match="valid JSON"):
        parse_reasoning_model_output(task=task, output_text="not-json")

    with pytest.raises(AgentReasoningValidationError, match="not supported"):
        parse_reasoning_model_output(
            task=task,
            output_text='{"decision":"act","capability":"shell"}',
        )

    with pytest.raises(AgentReasoningValidationError, match="byte limit"):
        parse_reasoning_model_output(
            task=task,
            output_text=" " + ("x" * MAX_AGENT_REASONING_OUTPUT_UTF8_BYTES),
        )


def test_allowed_reasoning_proposal_is_authorized_after_exactly_one_model_call() -> None:
    """Let the model propose while deterministic code remains capability authority."""
    task = _task(AgentCapability.STRUCTURED_SECURITY_QUERY)
    model = _FakeReasoningModel(
        AgentReasoningModelResponse(
            output_text='{"decision":"act","capability":"structured_security_query"}',
            evidence=_evidence(task),
        )
    )

    result = reason_about_task(task=task, model=model)

    assert model.calls == 1
    assert result.invocation_count == 1
    assert result.authorization_outcome is AgentReasoningAuthorizationOutcome.AUTHORIZED
    assert result.proposal.capability is AgentCapability.STRUCTURED_SECURITY_QUERY
    assert result.authorization_evidence_id is not None
    assert result.failure_category is None
    assert result.result_id.startswith(f"{SINGLE_AGENT_REASONING_CONTRACT_VERSION}:result:")


def test_abstention_is_admitted_without_capability_authority() -> None:
    """Preserve explicit model abstention through deterministic Gate 11.1 authorization."""
    task = _task(AgentCapability.KNOWLEDGE_GUIDANCE)
    model = _FakeReasoningModel(
        AgentReasoningModelResponse(
            output_text='{"decision":"abstain","capability":null}',
            evidence=_evidence(task),
        )
    )

    result = reason_about_task(task=task, model=model)

    assert model.calls == 1
    assert result.authorization_outcome is AgentReasoningAuthorizationOutcome.ABSTAINED
    assert result.proposal.capability is None
    assert result.authorization_evidence_id is not None
    assert result.failure_category is None


def test_model_cannot_acquire_out_of_allowlist_capability_authority() -> None:
    """Score an unauthorized model selection as rejection rather than executing or repairing it."""
    task = _task(AgentCapability.KNOWLEDGE_GUIDANCE)
    model = _FakeReasoningModel(
        AgentReasoningModelResponse(
            output_text='{"decision":"act","capability":"structured_security_query"}',
            evidence=_evidence(task),
        )
    )

    result = reason_about_task(task=task, model=model)

    assert model.calls == 1
    assert result.authorization_outcome is AgentReasoningAuthorizationOutcome.REJECTED
    assert result.authorization_evidence_id is None
    assert result.failure_category is AgentReasoningFailureCategory.CAPABILITY_AUTHORIZATION
    assert result.proposal.capability is AgentCapability.STRUCTURED_SECURITY_QUERY


def test_cross_task_invocation_evidence_fails_before_model_output_is_admitted() -> None:
    """Reject provider evidence that is not bound to the exact admitted task."""
    task = _task(AgentCapability.KNOWLEDGE_GUIDANCE, text="first")
    other = _task(AgentCapability.KNOWLEDGE_GUIDANCE, text="second")
    model = _FakeReasoningModel(
        AgentReasoningModelResponse(
            output_text='{"decision":"act","capability":"knowledge_guidance"}',
            evidence=_evidence(other),
        )
    )

    with pytest.raises(AgentReasoningValidationError, match="not bound"):
        reason_about_task(task=task, model=model)

    assert model.calls == 1


def test_reasoning_result_does_not_persist_raw_model_output() -> None:
    """Keep arbitrary model/provider content transient instead of admitting it as evidence."""
    task = _task(AgentCapability.KNOWLEDGE_GUIDANCE)
    secret_marker = "synthetic-secret-never-persist"
    response_text = (
        '{"decision":"act","capability":"knowledge_guidance"}'
        + (" " * 2)
    )
    model = _FakeReasoningModel(
        AgentReasoningModelResponse(output_text=response_text, evidence=_evidence(task))
    )

    result = reason_about_task(task=task, model=model)

    assert secret_marker not in repr(result)
    assert not hasattr(result, "output_text")


def test_bedrock_request_is_fixed_non_streaming_tool_free_and_schema_bounded() -> None:
    """Freeze the first provider adapter without model/tool/runtime authority expansion."""
    task = _task(
        AgentCapability.KNOWLEDGE_GUIDANCE,
        AgentCapability.STRUCTURED_SECURITY_QUERY,
    )

    request = build_bedrock_agent_reasoning_request(task)

    assert request["modelId"] == BEDROCK_AGENT_REASONING_MODEL_ID
    assert request["inferenceConfig"] == {
        "maxTokens": BEDROCK_AGENT_REASONING_MAX_TOKENS,
        "temperature": BEDROCK_AGENT_REASONING_TEMPERATURE,
    }
    assert "toolConfig" not in request
    assert "guardrailConfig" not in request

    output_config = cast(dict[str, object], request["outputConfig"])
    text_format = cast(dict[str, object], output_config["textFormat"])
    structure = cast(dict[str, object], text_format["structure"])
    json_schema = cast(dict[str, object], structure["jsonSchema"])
    schema = json.loads(cast(str, json_schema["schema"]))
    assert isinstance(schema, dict)
    assert schema["additionalProperties"] is False

    messages = cast(list[dict[str, object]], request["messages"])
    content = cast(list[dict[str, str]], messages[0]["content"])
    user_text = content[0]["text"]
    assert AgentCapability.KNOWLEDGE_GUIDANCE.value in user_text
    assert AgentCapability.STRUCTURED_SECURITY_QUERY.value in user_text
    assert task.task_id in user_text


def test_bedrock_adapter_invokes_client_once_and_admits_metadata_only_evidence() -> None:
    """Parse one Converse response without retries, fallback, or raw output evidence."""
    task = _task(AgentCapability.STRUCTURED_SECURITY_QUERY)
    output_text = '{"decision":"act","capability":"structured_security_query"}'
    client = _FakeBedrockClient(response=_bedrock_response(output_text))
    model = BedrockSingleAgentReasoningModel(
        client,
        clock=_Clock([10.0, 10.07]),
    )

    response = model.generate(task)

    assert len(client.requests) == 1
    assert response.output_text == output_text
    assert response.evidence.task_id == task.task_id
    assert response.evidence.provider == BEDROCK_AGENT_REASONING_PROVIDER
    assert response.evidence.model_id == BEDROCK_AGENT_REASONING_MODEL_ID
    assert response.evidence.region == BEDROCK_AGENT_REASONING_REGION
    assert response.evidence.request_id == "request-1"
    assert response.evidence.client_elapsed_ms == 70
    assert response.evidence.retry_attempts == 0
    assert output_text not in repr(response.evidence)


def test_bedrock_provider_failure_is_wrapped_without_second_application_attempt() -> None:
    """Perform one client call and expose no adapter retry/fallback behavior."""
    task = _task(AgentCapability.KNOWLEDGE_GUIDANCE)
    provider_error = RuntimeError("synthetic-provider-secret")
    client = _FakeBedrockClient(response=None, error=provider_error)
    model = BedrockSingleAgentReasoningModel(client, clock=_Clock([1.0]))

    with pytest.raises(BedrockAgentReasoningRuntimeError, match="invocation failed") as exc_info:
        model.generate(task)

    assert len(client.requests) == 1
    assert exc_info.value.__cause__ is provider_error
    assert "synthetic-provider-secret" not in str(exc_info.value)


def test_bedrock_response_shape_and_runtime_evidence_fail_closed() -> None:
    """Reject ambiguous content blocks and inconsistent provider token evidence."""
    task = _task(AgentCapability.KNOWLEDGE_GUIDANCE)
    multi_content = cast(
        Mapping[str, object],
        {
            **dict(_bedrock_response('{"decision":"abstain","capability":null}')),
            "output": {
                "message": {
                    "content": [
                        {"text": '{"decision":"abstain","capability":null}'},
                        {"text": "extra"},
                    ]
                }
            },
        },
    )
    client = _FakeBedrockClient(response=multi_content)
    model = BedrockSingleAgentReasoningModel(client, clock=_Clock([1.0, 1.01]))

    with pytest.raises(BedrockAgentReasoningRuntimeError, match="exactly one"):
        model.generate(task)

    invalid_tokens = cast(
        Mapping[str, object],
        {
            **dict(_bedrock_response('{"decision":"abstain","capability":null}')),
            "usage": {"inputTokens": 100, "outputTokens": 10, "totalTokens": 999},
        },
    )
    second_client = _FakeBedrockClient(response=invalid_tokens)
    second_model = BedrockSingleAgentReasoningModel(
        second_client,
        clock=_Clock([2.0, 2.01]),
    )

    with pytest.raises(AgentReasoningValidationError, match="total_tokens"):
        second_model.generate(task)


def test_reasoning_invocation_evidence_identity_is_content_addressed() -> None:
    """Bind evidence identity to task and admitted runtime metadata without model text."""
    task = _task(AgentCapability.KNOWLEDGE_GUIDANCE)
    first = _evidence(task)
    second = _evidence(task)
    changed = _evidence(task, request_id="request-2")

    assert first == second
    assert first.evidence_id.startswith(
        f"{SINGLE_AGENT_REASONING_CONTRACT_VERSION}:invocation:"
    )
    assert first.evidence_id != changed.evidence_id
