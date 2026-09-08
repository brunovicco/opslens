"""Tests for the bounded AgentCore Runtime invocation contract."""

from __future__ import annotations

import json

import pytest

from opslens.agent_baseline.domain.models import (
    AgentCapability,
    SingleAgentTask,
    create_single_agent_task,
)
from opslens.agent_baseline.domain.reasoning import AgentReasoningInvocationEvidence
from opslens.agent_baseline.ports.reasoning import AgentReasoningModelResponse
from opslens.agentcore_runtime import (
    AGENTCORE_RUNTIME_INVOCATION_CONTRACT_VERSION,
    MAX_AGENTCORE_RUNTIME_CAPABILITY_EXECUTIONS,
    MAX_AGENTCORE_RUNTIME_REQUEST_UTF8_BYTES,
    AgentCoreRuntimeValidationError,
    admit_agentcore_runtime_request,
    handle_agentcore_runtime_invocation,
)


def _request(
    *,
    task_text: str = "Show the structured vulnerability facts.",
    allowed_capabilities: list[str] | None = None,
    extra: dict[str, object] | None = None,
) -> bytes:
    payload: dict[str, object] = {
        "task_text": task_text,
        "allowed_capabilities": allowed_capabilities
        if allowed_capabilities is not None
        else [AgentCapability.STRUCTURED_SECURITY_QUERY.value],
    }
    if extra is not None:
        payload.update(extra)
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


class _FakeReasoningModel:
    """Return one fixed bounded model response while recording invocation count."""

    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.invocation_count = 0

    def generate(self, task: SingleAgentTask) -> AgentReasoningModelResponse:
        """Create deterministic metadata-only evidence bound to the received task."""
        self.invocation_count += 1
        evidence = AgentReasoningInvocationEvidence.create(
            task_id=task.task_id,
            provider="amazon_bedrock",
            model_id="fixed-model",
            region="us-east-1",
            request_id="request-1",
            stop_reason="end_turn",
            input_tokens=10,
            output_tokens=2,
            total_tokens=12,
            cache_read_input_tokens=0,
            cache_write_input_tokens=0,
            provider_latency_ms=20,
            client_elapsed_ms=25,
            retry_attempts=0,
        )
        return AgentReasoningModelResponse(
            output_text=self.output_text,
            evidence=evidence,
        )


def test_admission_recomputes_existing_content_addressed_task_identity() -> None:
    raw_body = _request()

    admitted = admit_agentcore_runtime_request(raw_body)
    expected = create_single_agent_task(
        text="Show the structured vulnerability facts.",
        allowed_capabilities=(AgentCapability.STRUCTURED_SECURITY_QUERY,),
    )

    assert admitted == expected


@pytest.mark.parametrize(
    "raw_body",
    [
        b"[]",
        b"not-json",
        _request(extra={"task_id": "caller-controlled"}),
        _request(extra={"model_id": "caller-controlled"}),
        _request(extra={"sql": "SELECT *"}),
        _request(extra={"url": "https://example.invalid"}),
        _request(extra={"shell": "rm -rf /"}),
        _request(extra={"args": {"arbitrary": True}}),
    ],
)
def test_admission_refuses_malformed_or_authority_bearing_fields(raw_body: bytes) -> None:
    with pytest.raises(AgentCoreRuntimeValidationError):
        admit_agentcore_runtime_request(raw_body)


def test_admission_refuses_request_larger_than_runtime_bound() -> None:
    raw_body = b"{" + b"x" * MAX_AGENTCORE_RUNTIME_REQUEST_UTF8_BYTES + b"}"

    with pytest.raises(AgentCoreRuntimeValidationError, match="byte limit"):
        admit_agentcore_runtime_request(raw_body)


@pytest.mark.parametrize(
    "capabilities",
    [
        [],
        ["unknown"],
        [
            AgentCapability.STRUCTURED_SECURITY_QUERY.value,
            AgentCapability.STRUCTURED_SECURITY_QUERY.value,
        ],
        [
            AgentCapability.STRUCTURED_SECURITY_QUERY.value,
            AgentCapability.KNOWLEDGE_GUIDANCE.value,
            AgentCapability.HYBRID_SECURITY_ANSWER.value,
            AgentCapability.PUBLIC_REPOSITORY_ANALYSIS.value,
            AgentCapability.STRUCTURED_SECURITY_QUERY.value,
        ],
    ],
)
def test_admission_refuses_invalid_capability_allowlists(capabilities: list[str]) -> None:
    with pytest.raises(AgentCoreRuntimeValidationError):
        admit_agentcore_runtime_request(_request(allowed_capabilities=capabilities))


def test_authorized_runtime_projection_invokes_model_once_and_exposes_no_raw_output() -> None:
    model = _FakeReasoningModel(
        '{"decision":"act","capability":"structured_security_query"}'
    )

    projection = handle_agentcore_runtime_invocation(raw_body=_request(), model=model)
    payload = projection.to_payload()

    assert model.invocation_count == 1
    assert MAX_AGENTCORE_RUNTIME_CAPABILITY_EXECUTIONS == 0
    assert payload["contract_version"] == AGENTCORE_RUNTIME_INVOCATION_CONTRACT_VERSION
    assert payload["authorization_outcome"] == "authorized"
    assert payload["decision"] == "act"
    assert payload["capability"] == "structured_security_query"
    assert "output_text" not in payload
    assert "result" not in payload
    assert "sql" not in payload


def test_abstained_runtime_projection_remains_non_executable() -> None:
    model = _FakeReasoningModel('{"decision":"abstain","capability":null}')

    projection = handle_agentcore_runtime_invocation(raw_body=_request(), model=model)
    payload = projection.to_payload()

    assert model.invocation_count == 1
    assert payload["authorization_outcome"] == "abstained"
    assert payload["decision"] == "abstain"
    assert payload["capability"] is None
    assert payload["failure_category"] is None


def test_unauthorized_model_capability_is_projected_as_deterministic_rejection() -> None:
    model = _FakeReasoningModel(
        '{"decision":"act","capability":"hybrid_security_answer"}'
    )

    projection = handle_agentcore_runtime_invocation(raw_body=_request(), model=model)
    payload = projection.to_payload()

    assert model.invocation_count == 1
    assert payload["authorization_outcome"] == "rejected"
    assert payload["decision"] == "act"
    assert payload["capability"] == "hybrid_security_answer"
    assert payload["authorization_evidence_id"] is None
    assert payload["failure_category"] == "capability_authorization"


def test_projection_contains_only_bounded_metadata_evidence() -> None:
    model = _FakeReasoningModel(
        '{"decision":"act","capability":"structured_security_query"}'
    )

    payload = handle_agentcore_runtime_invocation(
        raw_body=_request(),
        model=model,
    ).to_payload()
    evidence = payload["invocation_evidence"]

    assert isinstance(evidence, dict)
    assert set(evidence) == {
        "cache_read_input_tokens",
        "cache_write_input_tokens",
        "client_elapsed_ms",
        "evidence_id",
        "evidence_sha256",
        "input_tokens",
        "model_id",
        "output_tokens",
        "provider",
        "provider_latency_ms",
        "region",
        "request_id",
        "retry_attempts",
        "stop_reason",
        "total_tokens",
    }
    assert "output_text" not in evidence
    assert "credentials" not in evidence
