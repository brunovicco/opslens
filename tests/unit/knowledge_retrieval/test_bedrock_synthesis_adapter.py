"""Unit tests for the bounded Amazon Bedrock knowledge synthesis adapter."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import cast

import pytest

from opslens.knowledge_retrieval.adapters.bedrock_synthesis import (
    BedrockKnowledgeSynthesizer,
    BedrockSynthesisExecution,
    BedrockSynthesisFailureCategory,
    BedrockSynthesisInvocationEvidence,
    BedrockSynthesisRuntimeError,
)
from opslens.knowledge_retrieval.application.bedrock_synthesis import (
    BEDROCK_SYNTHESIS_MODEL_ID,
    BEDROCK_SYNTHESIS_REGION,
)
from opslens.knowledge_retrieval.application.context_assembly import assemble_retrieval_context
from opslens.knowledge_retrieval.application.synthesis_contract import (
    build_synthesis_prompt,
    build_synthesis_request,
)
from opslens.knowledge_retrieval.domain import (
    KnowledgeSourceType,
    RetrievalBackend,
    RetrievalEvidence,
    RetrievalRequest,
    RetrievedChunk,
    SynthesisAuthorityDecision,
    SynthesisDecision,
    SynthesisRequest,
)

QUESTION = "How should I make dependency installation safer?"


class _FakeBedrockClient:
    """Record Converse requests and return one fixed response."""

    def __init__(self, response: Mapping[str, object]) -> None:
        self._response = response
        self.requests: list[dict[str, object]] = []

    def converse(self, **request: object) -> Mapping[str, object]:
        """Record one request and return the configured response."""
        self.requests.append(dict(request))
        return self._response


class _FailingBedrockClient:
    """Record one request and raise a configured provider failure."""

    def __init__(self, error: Exception) -> None:
        self._error = error
        self.requests: list[dict[str, object]] = []

    def converse(self, **request: object) -> Mapping[str, object]:
        """Record one request before raising the provider error."""
        self.requests.append(dict(request))
        raise self._error


class _ProviderError(RuntimeError):
    """Minimal botocore-like error exposing a content-free provider code."""

    def __init__(self, code: str) -> None:
        self.response: Mapping[str, object] = {"Error": {"Code": code}}
        super().__init__("sensitive provider text must not cross the adapter")


def _clock(*values: float) -> Callable[[], float]:
    """Return a deterministic monotonic clock over supplied values."""
    iterator = iter(values)
    return lambda: next(iterator)


def _request() -> SynthesisRequest:
    """Build one valid synthesis request over already-admitted offline evidence."""
    chunk = RetrievedChunk.from_text(
        chunk_id="knowledge-chunk:test:synthesis-adapter:v1",
        document_id="knowledge-doc:test:synthesis-adapter:v1",
        source_id="source:test:synthesis-adapter",
        source_type=KnowledgeSourceType.SECURITY_GUIDANCE,
        canonical_uri="https://example.com/secure-installs",
        document_content_sha256="3" * 64,
        text="Require hashes for every dependency artifact.",
        rank=1,
        relevance_score=0.88,
        title="Secure installs",
        section_path=("Hash-checking Mode",),
    )
    retrieval = RetrievalEvidence(
        retrieval_id="retrieval:gate-7-6d-test",
        request=RetrievalRequest(query=QUESTION, top_k=1),
        chunks=(chunk,),
        backend=RetrievalBackend.OFFLINE_GOLDEN,
    )
    context = assemble_retrieval_context(retrieval)
    return build_synthesis_request(
        question=QUESTION,
        context=context,
        authority_decision=SynthesisAuthorityDecision.SUPPORTED,
    )


def _response(
    *,
    decision: str = "answer",
    answer: str | None = "Use hash-checking mode for every dependency artifact.",
    stop_reason: str = "end_turn",
) -> dict[str, object]:
    """Build one representative Converse response."""
    model_output = {"decision": decision, "answer": answer}
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": json.dumps(model_output)}],
            }
        },
        "stopReason": stop_reason,
        "usage": {
            "inputTokens": 1200,
            "outputTokens": 80,
            "totalTokens": 1280,
            "cacheReadInputTokens": 0,
            "cacheWriteInputTokens": 0,
        },
        "metrics": {"latencyMs": 620},
        "ResponseMetadata": {
            "RequestId": "synthesis-request-123",
            "RetryAttempts": 0,
        },
    }


def test_adapter_returns_typed_answer_and_content_free_runtime_evidence() -> None:
    """One valid end-turn response becomes typed synthesis plus operational evidence."""
    request = _request()
    expected_prompt = build_synthesis_prompt(request)
    client = _FakeBedrockClient(_response())
    synthesizer = BedrockKnowledgeSynthesizer(client, clock=_clock(5.0, 5.75))

    execution = synthesizer.synthesize(request)

    assert execution.result.decision is SynthesisDecision.ANSWER
    assert execution.result.answer == "Use hash-checking mode for every dependency artifact."
    assert execution.evidence == BedrockSynthesisInvocationEvidence(
        model_id=BEDROCK_SYNTHESIS_MODEL_ID,
        region=BEDROCK_SYNTHESIS_REGION,
        request_id="synthesis-request-123",
        stop_reason="end_turn",
        input_tokens=1200,
        output_tokens=80,
        total_tokens=1280,
        cache_read_input_tokens=0,
        cache_write_input_tokens=0,
        bedrock_latency_ms=620,
        client_elapsed_ms=750,
        retry_attempts=0,
        request_sha256=request.request_sha256,
        prompt_sha256=expected_prompt.prompt_sha256,
        context_sha256=request.context.context_sha256,
    )
    assert len(client.requests) == 1
    assert client.requests[0]["modelId"] == BEDROCK_SYNTHESIS_MODEL_ID
    assert QUESTION not in str(client.requests[0]["requestMetadata"])


def test_insufficient_evidence_is_a_valid_model_abstention_not_runtime_failure() -> None:
    """Authorized synthesis may abstain without being misclassified as provider failure."""
    execution = BedrockKnowledgeSynthesizer(
        _FakeBedrockClient(_response(decision="insufficient_evidence", answer=None)),
        clock=_clock(1.0, 1.2),
    ).synthesize(_request())

    assert execution.result.decision is SynthesisDecision.INSUFFICIENT_EVIDENCE
    assert execution.result.answer is None


def test_provider_failure_is_content_free_and_preserves_cause() -> None:
    """Credential/provider errors remain distinct from model abstention and hide raw text."""
    provider_error = _ProviderError("AccessDeniedException")
    client = _FailingBedrockClient(provider_error)
    synthesizer = BedrockKnowledgeSynthesizer(client, clock=_clock(1.0))

    with pytest.raises(BedrockSynthesisRuntimeError) as exc_info:
        synthesizer.synthesize(_request())

    error = exc_info.value
    assert error.category is BedrockSynthesisFailureCategory.PROVIDER_INVOCATION
    assert "provider_code=AccessDeniedException" in str(error)
    assert "sensitive provider text" not in str(error)
    assert error.__cause__ is provider_error
    assert len(client.requests) == 1


@pytest.mark.parametrize(
    "stop_reason",
    [
        "max_tokens",
        "tool_use",
        "stop_sequence",
        "guardrail_intervened",
        "content_filtered",
        "malformed_model_output",
        "malformed_tool_use",
        "model_context_window_exceeded",
    ],
)
def test_non_end_turn_stop_reasons_fail_closed_before_output_admission(
    stop_reason: str,
) -> None:
    """Truncation, filtering, tools, and malformed output cannot become synthesis results."""
    synthesizer = BedrockKnowledgeSynthesizer(
        _FakeBedrockClient(_response(stop_reason=stop_reason)),
        clock=_clock(1.0, 1.1),
    )

    with pytest.raises(BedrockSynthesisRuntimeError) as exc_info:
        synthesizer.synthesize(_request())

    assert exc_info.value.category is BedrockSynthesisFailureCategory.STOP_REASON
    assert exc_info.value.stop_reason == stop_reason
    assert exc_info.value.request_id == "synthesis-request-123"


def test_response_requires_one_assistant_text_block() -> None:
    """Unexpected role or multimodal/tool-shaped response content fails closed."""
    wrong_role = _response()
    output = cast(dict[str, object], wrong_role["output"])
    message = cast(dict[str, object], output["message"])
    message["role"] = "user"

    with pytest.raises(BedrockSynthesisRuntimeError) as role_error:
        BedrockKnowledgeSynthesizer(
            _FakeBedrockClient(wrong_role),
            clock=_clock(1.0, 1.1),
        ).synthesize(_request())
    assert role_error.value.category is BedrockSynthesisFailureCategory.RESPONSE_CONTRACT

    multiple = _response()
    multiple_output = cast(dict[str, object], multiple["output"])
    multiple_message = cast(dict[str, object], multiple_output["message"])
    multiple_message["content"] = [{"text": "{}"}, {"text": "{}"}]

    with pytest.raises(BedrockSynthesisRuntimeError) as content_error:
        BedrockKnowledgeSynthesizer(
            _FakeBedrockClient(multiple),
            clock=_clock(1.0, 1.1),
        ).synthesize(_request())
    assert content_error.value.category is BedrockSynthesisFailureCategory.RESPONSE_CONTRACT


def test_invalid_structured_text_is_output_contract_failure() -> None:
    """A provider-success response still fails closed when model JSON violates the app contract."""
    response = _response()
    output = cast(dict[str, object], response["output"])
    message = cast(dict[str, object], output["message"])
    content = cast(list[dict[str, object]], message["content"])
    content[0]["text"] = '{"decision":"unsupported_authority","answer":null}'

    with pytest.raises(BedrockSynthesisRuntimeError) as exc_info:
        BedrockKnowledgeSynthesizer(
            _FakeBedrockClient(response),
            clock=_clock(1.0, 1.1),
        ).synthesize(_request())

    assert exc_info.value.category is BedrockSynthesisFailureCategory.OUTPUT_CONTRACT
    assert exc_info.value.request_id == "synthesis-request-123"
    assert exc_info.value.stop_reason == "end_turn"


def test_missing_or_inconsistent_runtime_evidence_fails_closed() -> None:
    """A valid model answer is not returned without complete trustworthy usage evidence."""
    missing = _response()
    del missing["metrics"]
    with pytest.raises(BedrockSynthesisRuntimeError) as missing_error:
        BedrockKnowledgeSynthesizer(
            _FakeBedrockClient(missing),
            clock=_clock(1.0, 1.1),
        ).synthesize(_request())
    assert missing_error.value.category is BedrockSynthesisFailureCategory.RESPONSE_CONTRACT

    inconsistent = _response()
    usage = cast(dict[str, object], inconsistent["usage"])
    usage["totalTokens"] = 999
    with pytest.raises(ValueError, match="total_tokens"):
        BedrockKnowledgeSynthesizer(
            _FakeBedrockClient(inconsistent),
            clock=_clock(1.0, 1.1),
        ).synthesize(_request())


def test_non_monotonic_clock_cannot_create_misleading_latency_evidence() -> None:
    """Negative local elapsed time is a distinct runtime failure category."""
    with pytest.raises(BedrockSynthesisRuntimeError) as exc_info:
        BedrockKnowledgeSynthesizer(
            _FakeBedrockClient(_response()),
            clock=_clock(2.0, 1.0),
        ).synthesize(_request())

    assert exc_info.value.category is BedrockSynthesisFailureCategory.CLOCK


def test_execution_contract_rejects_result_evidence_request_mismatch() -> None:
    """A synthesis result cannot be paired with invocation evidence from another request."""
    execution = BedrockKnowledgeSynthesizer(
        _FakeBedrockClient(_response()),
        clock=_clock(1.0, 1.1),
    ).synthesize(_request())
    evidence = execution.evidence
    forged = BedrockSynthesisInvocationEvidence(
        model_id=evidence.model_id,
        region=evidence.region,
        request_id=evidence.request_id,
        stop_reason=evidence.stop_reason,
        input_tokens=evidence.input_tokens,
        output_tokens=evidence.output_tokens,
        total_tokens=evidence.total_tokens,
        cache_read_input_tokens=evidence.cache_read_input_tokens,
        cache_write_input_tokens=evidence.cache_write_input_tokens,
        bedrock_latency_ms=evidence.bedrock_latency_ms,
        client_elapsed_ms=evidence.client_elapsed_ms,
        retry_attempts=evidence.retry_attempts,
        request_sha256="0" * 64,
        prompt_sha256=evidence.prompt_sha256,
        context_sha256=evidence.context_sha256,
    )

    with pytest.raises(ValueError, match="same request"):
        BedrockSynthesisExecution(result=execution.result, evidence=forged)
