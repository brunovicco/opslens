"""Unit tests for the bounded Gate 7.6e retrieval-to-synthesis lab runner."""

from __future__ import annotations

import json

import pytest

from opslens.knowledge_retrieval.adapters.bedrock_synthesis import (
    BedrockSynthesisExecution,
    BedrockSynthesisInvocationEvidence,
)
from opslens.knowledge_retrieval.application.bedrock_retrieval import (
    BedrockRetrieveInvocationEvidence,
    BedrockRetrieveResult,
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
from opslens.knowledge_retrieval.cli import run_bedrock_synthesis as cli
from opslens.knowledge_retrieval.domain import (
    KnowledgeSourceType,
    RetrievalBackend,
    RetrievalEvidence,
    RetrievalRequest,
    RetrievedChunk,
    SynthesisAuthorityDecision,
    SynthesisDecision,
    SynthesisResult,
)

QUESTION = "How should I make dependency installation safer?"
CHUNK_TEXT = "Require hashes for every dependency artifact."


def _retrieval_result() -> BedrockRetrieveResult:
    """Build one admitted Bedrock retrieval result for serializer tests."""
    chunk = RetrievedChunk.from_text(
        chunk_id="knowledge-chunk:test:synthesis-cli:v1",
        document_id="knowledge-doc:test:synthesis-cli:v1",
        source_id="source:test:synthesis-cli",
        source_type=KnowledgeSourceType.SECURITY_GUIDANCE,
        canonical_uri="https://example.com/secure-installs",
        document_content_sha256="4" * 64,
        text=CHUNK_TEXT,
        rank=1,
        relevance_score=0.9,
        title="Secure installs",
        section_path=("Hash-checking Mode",),
    )
    evidence = RetrievalEvidence(
        retrieval_id="retrieval:gate-7-6e-test",
        request=RetrievalRequest(query=QUESTION, top_k=1),
        chunks=(chunk,),
        backend=RetrievalBackend.BEDROCK_KNOWLEDGE_BASE,
        backend_reference="KBTEST1234",
    )
    invocation = BedrockRetrieveInvocationEvidence(
        knowledge_base_id="KBTEST1234",
        provider_request_id="retrieve-request-123",
        retry_attempts=0,
        client_elapsed_ms=500,
        returned_result_count=1,
    )
    return BedrockRetrieveResult(evidence=evidence, invocation=invocation)


def _execution(retrieval: BedrockRetrieveResult) -> BedrockSynthesisExecution:
    """Build one valid typed synthesis execution linked to retrieval context."""
    context = assemble_retrieval_context(retrieval.evidence)
    request = build_synthesis_request(
        question=QUESTION,
        context=context,
        authority_decision=SynthesisAuthorityDecision.SUPPORTED,
    )
    prompt = build_synthesis_prompt(request)
    result = SynthesisResult.create(
        request=request,
        decision=SynthesisDecision.ANSWER,
        answer="Use hash checking so every downloaded artifact is verified.",
    )
    evidence = BedrockSynthesisInvocationEvidence(
        model_id=BEDROCK_SYNTHESIS_MODEL_ID,
        region=BEDROCK_SYNTHESIS_REGION,
        request_id="synthesis-request-123",
        stop_reason="end_turn",
        input_tokens=900,
        output_tokens=50,
        total_tokens=950,
        cache_read_input_tokens=0,
        cache_write_input_tokens=0,
        bedrock_latency_ms=700,
        client_elapsed_ms=800,
        retry_attempts=0,
        request_sha256=request.request_sha256,
        prompt_sha256=prompt.prompt_sha256,
        context_sha256=context.context_sha256,
    )
    return BedrockSynthesisExecution(result=result, evidence=evidence)


def test_supported_serialization_preserves_quality_and_content_addressed_evidence() -> None:
    """First-run output keeps the answer but does not echo query or retrieved source text."""
    retrieval = _retrieval_result()
    context = assemble_retrieval_context(retrieval.evidence)
    execution = _execution(retrieval)

    payload = json.loads(
        cli.serialize_synthesis_evidence(
            retrieval,
            context=context,
            execution=execution,
            region=BEDROCK_SYNTHESIS_REGION,
        )
    )

    assert payload["execution_complete"] is True
    assert payload["retrieval_invoked"] is True
    assert payload["model_invoked"] is True
    assert payload["synthesis"]["decision"] == "answer"
    assert payload["synthesis"]["answer"] == execution.result.answer
    assert payload["synthesis"]["input_tokens"] == 900
    assert payload["synthesis"]["output_tokens"] == 50
    assert payload["retrieval"]["returned_result_count"] == 1
    assert payload["context"]["selected_chunk_count"] == 1

    serialized = json.dumps(payload, sort_keys=True)
    assert QUESTION not in serialized
    assert CHUNK_TEXT not in serialized


def test_unsupported_authority_serialization_is_content_free_and_has_no_calls() -> None:
    """A pre-model authority refusal reports zero provider execution."""
    request = RetrievalRequest(query=QUESTION, top_k=1)

    payload = json.loads(
        cli.serialize_unsupported_authority(
            request,
            region=BEDROCK_SYNTHESIS_REGION,
        )
    )

    assert payload["authority_decision"] == "unsupported"
    assert payload["execution_complete"] is True
    assert payload["retrieval_invoked"] is False
    assert payload["model_invoked"] is False
    assert QUESTION not in json.dumps(payload, sort_keys=True)


def test_unsupported_authority_main_exits_before_any_aws_client_creation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The lab entrypoint cannot accidentally call AWS for unsupported authority."""

    def forbidden_session() -> object:
        raise AssertionError("AWS client creation must not occur")

    monkeypatch.setattr(cli, "get_session", forbidden_session)

    exit_code = cli.main(
        [
            "--query",
            QUESTION,
            "--authority-decision",
            "unsupported",
            "--knowledge-base-id",
            "KBTEST1234",
            "--data-source-id",
            "DSTEST1234",
            "--source-bucket",
            "opslens-test-bucket",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["status"] == "unsupported_authority"
    assert payload["retrieval_invoked"] is False
    assert payload["model_invoked"] is False


def test_synthesis_runner_rejects_region_drift() -> None:
    """The first real synthesis path cannot silently switch Regions."""
    with pytest.raises(cli.SynthesisCliError, match=r"frozen Gate 7.6 region"):
        cli.require_synthesis_region("us-west-2")
