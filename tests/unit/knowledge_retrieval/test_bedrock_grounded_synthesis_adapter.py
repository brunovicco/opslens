"""Unit tests for the bounded citation-aware Bedrock synthesis adapter."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping

import pytest

from opslens.knowledge_retrieval.adapters.bedrock_grounded_synthesis import (
    BedrockGroundedKnowledgeSynthesizer,
    BedrockGroundedSynthesisInvocationEvidence,
)
from opslens.knowledge_retrieval.adapters.bedrock_synthesis import (
    BedrockSynthesisFailureCategory,
    BedrockSynthesisRuntimeError,
)
from opslens.knowledge_retrieval.application.bedrock_synthesis import (
    BEDROCK_SYNTHESIS_MODEL_ID,
    BEDROCK_SYNTHESIS_REGION,
)
from opslens.knowledge_retrieval.application.citation_projection import (
    project_citation_catalog,
)
from opslens.knowledge_retrieval.application.context_assembly import (
    assemble_retrieval_context,
)
from opslens.knowledge_retrieval.application.grounded_synthesis_prompt import (
    build_grounded_synthesis_prompt,
)
from opslens.knowledge_retrieval.application.grounding_contract import (
    build_grounded_synthesis_request,
)
from opslens.knowledge_retrieval.application.synthesis_contract import (
    build_synthesis_request,
)
from opslens.knowledge_retrieval.domain import (
    GroundedSynthesisRequest,
    KnowledgeSourceType,
    RetrievalBackend,
    RetrievalEvidence,
    RetrievalRequest,
    RetrievedChunk,
    SynthesisAuthorityDecision,
    SynthesisDecision,
)

QUESTION = "How should I verify dependency artifacts?"


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
    """Raise one configured provider failure after recording the request."""

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


def _request() -> GroundedSynthesisRequest:
    """Build one grounded request over two already-admitted chunks."""
    chunks = (
        RetrievedChunk.from_text(
            chunk_id="knowledge-chunk:test:grounded-adapter:one:v1",
            document_id="knowledge-doc:test:grounded-adapter:one:v1",
            source_id="source:test:grounded-adapter:one",
            source_type=KnowledgeSourceType.SECURITY_GUIDANCE,
            canonical_uri="https://example.com/grounded-adapter/one",
            document_content_sha256="3" * 64,
            text="Require hashes for every dependency artifact.",
            rank=1,
            relevance_score=0.9,
            title="Hashes",
            section_path=("Hash-checking",),
        ),
        RetrievedChunk.from_text(
            chunk_id="knowledge-chunk:test:grounded-adapter:two:v1",
            document_id="knowledge-doc:test:grounded-adapter:two:v1",
            source_id="source:test:grounded-adapter:two",
            source_type=KnowledgeSourceType.MAINTAINER_DOCUMENTATION,
            canonical_uri="https://example.com/grounded-adapter/two",
            document_content_sha256="4" * 64,
            text="Pin dependency versions before installation.",
            rank=2,
            relevance_score=0.8,
            title="Pinning",
            section_path=("Versions",),
        ),
    )
    retrieval = RetrievalEvidence(
        retrieval_id="retrieval:gate-7-7d-adapter-test",
        request=RetrievalRequest(query=QUESTION, top_k=2),
        chunks=chunks,
        backend=RetrievalBackend.OFFLINE_GOLDEN,
    )
    context = assemble_retrieval_context(retrieval)
    synthesis = build_synthesis_request(
        question=QUESTION,
        context=context,
        authority_decision=SynthesisAuthorityDecision.SUPPORTED,
    )
    return build_grounded_synthesis_request(
        synthesis_request=synthesis,
        citation_catalog=project_citation_catalog(context),
    )


def _response(
    *,
    decision: str = "answer",
    claims: list[dict[str, object]] | None = None,
    stop_reason: str = "end_turn",
) -> dict[str, object]:
    """Build one representative structured Converse response."""
    if claims is None:
        claims = [
            {
                "text": "Require hashes for dependency artifacts.",
                "citation_ids": ["C1"],
            },
            {
                "text": "Pin dependency versions before installation.",
                "citation_ids": ["C2"],
            },
        ]
    model_output = {"decision": decision, "claims": claims}
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": json.dumps(model_output)}],
            }
        },
        "stopReason": stop_reason,
        "usage": {
            "inputTokens": 1400,
            "outputTokens": 120,
            "totalTokens": 1520,
            "cacheReadInputTokens": 0,
            "cacheWriteInputTokens": 0,
        },
        "metrics": {"latencyMs": 700},
        "ResponseMetadata": {
            "RequestId": "grounded-synthesis-request-123",
            "RetryAttempts": 0,
        },
    }


def test_adapter_returns_grounded_claims_and_content_free_evidence() -> None:
    """One valid response becomes deterministic claims plus grounded runtime evidence."""
    request = _request()
    prompt = build_grounded_synthesis_prompt(request)
    client = _FakeBedrockClient(_response())
    execution = BedrockGroundedKnowledgeSynthesizer(
        client,
        clock=_clock(5.0, 5.8),
    ).synthesize(request)

    assert execution.result.decision is SynthesisDecision.ANSWER
    assert tuple(claim.citation_ids for claim in execution.result.claims) == (
        ("C1",),
        ("C2",),
    )
    assert execution.evidence == BedrockGroundedSynthesisInvocationEvidence(
        model_id=BEDROCK_SYNTHESIS_MODEL_ID,
        region=BEDROCK_SYNTHESIS_REGION,
        request_id="grounded-synthesis-request-123",
        stop_reason="end_turn",
        input_tokens=1400,
        output_tokens=120,
        total_tokens=1520,
        cache_read_input_tokens=0,
        cache_write_input_tokens=0,
        bedrock_latency_ms=700,
        client_elapsed_ms=800,
        retry_attempts=0,
        grounded_request_sha256=request.grounded_request_sha256,
        prompt_sha256=prompt.prompt_sha256,
        context_sha256=request.synthesis_request.context.context_sha256,
        citation_catalog_sha256=request.citation_catalog.catalog_sha256,
    )
    assert len(client.requests) == 1
    assert QUESTION not in str(client.requests[0]["requestMetadata"])


def test_insufficient_evidence_is_a_valid_zero_claim_abstention() -> None:
    """Authorized grounded synthesis may abstain without runtime failure."""
    execution = BedrockGroundedKnowledgeSynthesizer(
        _FakeBedrockClient(
            _response(decision="insufficient_evidence", claims=[])
        ),
        clock=_clock(1.0, 1.2),
    ).synthesize(_request())

    assert execution.result.decision is SynthesisDecision.INSUFFICIENT_EVIDENCE
    assert execution.result.claims == ()
    assert execution.result.rendered_answer is None


def test_unknown_model_citation_id_is_output_contract_failure() -> None:
    """Provider success cannot promote a model-invented citation identity."""
    response = _response(
        claims=[
            {
                "text": "Invented citation target.",
                "citation_ids": ["C99"],
            }
        ]
    )

    with pytest.raises(BedrockSynthesisRuntimeError) as exc_info:
        BedrockGroundedKnowledgeSynthesizer(
            _FakeBedrockClient(response),
            clock=_clock(1.0, 1.1),
        ).synthesize(_request())

    assert exc_info.value.category is BedrockSynthesisFailureCategory.OUTPUT_CONTRACT
    assert exc_info.value.request_id == "grounded-synthesis-request-123"


def test_provider_failure_remains_content_free_and_preserves_cause() -> None:
    """Provider errors remain distinct from grounded abstention and hide raw text."""
    provider_error = _ProviderError("AccessDeniedException")
    client = _FailingBedrockClient(provider_error)

    with pytest.raises(BedrockSynthesisRuntimeError) as exc_info:
        BedrockGroundedKnowledgeSynthesizer(
            client,
            clock=_clock(1.0),
        ).synthesize(_request())

    error = exc_info.value
    assert error.category is BedrockSynthesisFailureCategory.PROVIDER_INVOCATION
    assert "provider_code=AccessDeniedException" in str(error)
    assert "sensitive provider text" not in str(error)
    assert error.__cause__ is provider_error
    assert len(client.requests) == 1


@pytest.mark.parametrize(
    "stop_reason",
    ["max_tokens", "tool_use", "guardrail_intervened", "content_filtered"],
)
def test_non_end_turn_stop_reason_fails_before_output_admission(
    stop_reason: str,
) -> None:
    """Truncation, tool use, filtering, or guardrail stops fail closed."""
    with pytest.raises(BedrockSynthesisRuntimeError) as exc_info:
        BedrockGroundedKnowledgeSynthesizer(
            _FakeBedrockClient(_response(stop_reason=stop_reason)),
            clock=_clock(1.0, 1.1),
        ).synthesize(_request())

    assert exc_info.value.category is BedrockSynthesisFailureCategory.STOP_REASON
    assert exc_info.value.stop_reason == stop_reason


def test_grounded_adapter_rejects_wrong_runtime_request_type() -> None:
    """Arbitrary callers cannot bypass the frozen grounded request contract."""
    with pytest.raises(TypeError, match="GroundedSynthesisRequest"):
        BedrockGroundedKnowledgeSynthesizer(
            _FakeBedrockClient(_response())
        ).synthesize(object())  # type: ignore[arg-type]
