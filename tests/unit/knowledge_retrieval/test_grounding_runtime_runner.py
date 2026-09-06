"""Tests for the frozen Gate 7.7 real-runtime orchestration."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from opslens.knowledge_retrieval.adapters.bedrock_grounded_synthesis import (
    BedrockGroundedSynthesisExecution,
    BedrockGroundedSynthesisInvocationEvidence,
)
from opslens.knowledge_retrieval.adapters.bedrock_synthesis import (
    BedrockSynthesisFailureCategory,
    BedrockSynthesisRuntimeError,
)
from opslens.knowledge_retrieval.application.bedrock_retrieval import (
    BedrockRetrieveInvocationEvidence,
    BedrockRetrieveResult,
)
from opslens.knowledge_retrieval.application.bedrock_synthesis import (
    BEDROCK_SYNTHESIS_MODEL_ID,
    BEDROCK_SYNTHESIS_REGION,
)
from opslens.knowledge_retrieval.application.corpus_config import load_corpus_manifest
from opslens.knowledge_retrieval.application.grounded_synthesis_prompt import (
    build_grounded_synthesis_prompt,
)
from opslens.knowledge_retrieval.application.grounding_contract import (
    parse_grounded_synthesis_output,
)
from opslens.knowledge_retrieval.application.grounding_evaluation import (
    load_golden_grounding_dataset,
)
from opslens.knowledge_retrieval.application.grounding_runtime_runner import (
    run_grounding_runtime_evaluation,
)
from opslens.knowledge_retrieval.application.retrieval_catalog import (
    build_retrieval_catalog,
)
from opslens.knowledge_retrieval.domain import (
    DEFAULT_RETRIEVAL_TOP_K,
    GroundedSynthesisRequest,
    KnowledgeSourceType,
    RetrievalBackend,
    RetrievalEvidence,
    RetrievalRequest,
    RetrievedChunk,
    SynthesisDecision,
)

_REPO_ROOT = Path(__file__).parents[3]
_FIXTURE = (
    _REPO_ROOT
    / "tests"
    / "fixtures"
    / "knowledge_retrieval"
    / "golden_grounding_v1.json"
)
_MANIFEST = _REPO_ROOT / "knowledge" / "corpus" / "v1" / "manifest.json"
_TEST_KB_ID = "TESTKB1234"


def _retrieval_result(request: RetrievalRequest, *, index: int) -> BedrockRetrieveResult:
    """Return one typed already-admitted Bedrock retrieval result for runner tests."""
    text = "Synthetic admitted evidence for grounded runtime evaluation."
    chunk = RetrievedChunk.from_text(
        chunk_id=f"knowledge-chunk:test:grounding-runtime:{index}:v1",
        document_id=f"knowledge-doc:test:grounding-runtime:{index}:v1",
        source_id=f"source:test:grounding-runtime:{index}",
        source_type=KnowledgeSourceType.SECURITY_GUIDANCE,
        canonical_uri=f"https://example.com/grounding-runtime/{index}",
        document_content_sha256=f"{index}" * 64,
        text=text,
        rank=1,
        relevance_score=0.9,
        title="Grounded runtime evidence",
        section_path=("Runtime",),
    )
    evidence = RetrievalEvidence(
        retrieval_id=f"retrieval:grounding-runtime:{index}",
        request=request,
        chunks=(chunk,),
        backend=RetrievalBackend.BEDROCK_KNOWLEDGE_BASE,
        backend_reference=_TEST_KB_ID,
    )
    invocation = BedrockRetrieveInvocationEvidence(
        knowledge_base_id=_TEST_KB_ID,
        provider_request_id=f"retrieve-request-{index}",
        retry_attempts=0,
        client_elapsed_ms=100 + index,
        returned_result_count=1,
    )
    return BedrockRetrieveResult(evidence=evidence, invocation=invocation)


def _synthesis_execution(
    request: GroundedSynthesisRequest,
    *,
    index: int,
) -> BedrockGroundedSynthesisExecution:
    """Return one valid grounded answer or abstention for a frozen case."""
    payload: dict[str, object]
    if "TLS cipher suite" in request.synthesis_request.question:
        payload = {"decision": "insufficient_evidence", "claims": []}
    else:
        payload = {
            "decision": "answer",
            "claims": [
                {
                    "text": "Use the admitted remediation evidence for this step.",
                    "citation_ids": ["C1"],
                }
            ],
        }
    result = parse_grounded_synthesis_output(
        json.dumps(payload),
        request=request,
    )
    prompt = build_grounded_synthesis_prompt(request)
    evidence = BedrockGroundedSynthesisInvocationEvidence(
        model_id=BEDROCK_SYNTHESIS_MODEL_ID,
        region=BEDROCK_SYNTHESIS_REGION,
        request_id=f"grounded-request-{index}",
        stop_reason="end_turn",
        input_tokens=100,
        output_tokens=20,
        total_tokens=120,
        cache_read_input_tokens=0,
        cache_write_input_tokens=0,
        bedrock_latency_ms=250 + index,
        client_elapsed_ms=300 + index,
        retry_attempts=0,
        grounded_request_sha256=request.grounded_request_sha256,
        prompt_sha256=prompt.prompt_sha256,
        context_sha256=request.synthesis_request.context.context_sha256,
        citation_catalog_sha256=request.citation_catalog.catalog_sha256,
    )
    return BedrockGroundedSynthesisExecution(result=result, evidence=evidence)


def test_runtime_runner_executes_each_frozen_case_once_with_default_top_k() -> None:
    """The first-run harness keeps one Retrieve and one grounded synthesis per case."""
    dataset = load_golden_grounding_dataset(_FIXTURE)
    catalog = build_retrieval_catalog(load_corpus_manifest(_MANIFEST))
    retrieval_requests: list[RetrievalRequest] = []
    synthesis_requests: list[GroundedSynthesisRequest] = []

    def retrieve(request: RetrievalRequest) -> BedrockRetrieveResult:
        retrieval_requests.append(request)
        return _retrieval_result(request, index=len(retrieval_requests))

    def synthesize(request: GroundedSynthesisRequest) -> BedrockGroundedSynthesisExecution:
        synthesis_requests.append(request)
        return _synthesis_execution(request, index=len(synthesis_requests))

    execution = run_grounding_runtime_evaluation(
        retrieve,
        synthesize,
        dataset=dataset,
        catalog=catalog,
    )

    assert execution.complete is True
    assert execution.dataset_id == "knowledge-grounding-golden:v1"
    assert execution.planned_case_count == 4
    assert len(execution.attempts) == 4
    assert len(retrieval_requests) == 4
    assert len(synthesis_requests) == 4
    assert all(request.top_k == DEFAULT_RETRIEVAL_TOP_K for request in retrieval_requests)
    assert execution.attempts[-1].synthesis is not None
    assert (
        execution.attempts[-1].synthesis.result.decision
        is SynthesisDecision.INSUFFICIENT_EVIDENCE
    )


def test_runtime_runner_stops_after_first_synthesis_failure_and_preserves_prefix() -> None:
    """A failed provider attempt is preserved and later cases are not replayed or attempted."""
    dataset = load_golden_grounding_dataset(_FIXTURE)
    catalog = build_retrieval_catalog(load_corpus_manifest(_MANIFEST))
    retrieval_count = 0

    def retrieve(request: RetrievalRequest) -> BedrockRetrieveResult:
        nonlocal retrieval_count
        retrieval_count += 1
        return _retrieval_result(request, index=retrieval_count)

    def synthesize(_: GroundedSynthesisRequest) -> BedrockGroundedSynthesisExecution:
        raise BedrockSynthesisRuntimeError(
            "provider failure",
            category=BedrockSynthesisFailureCategory.PROVIDER_INVOCATION,
        )

    execution = run_grounding_runtime_evaluation(
        retrieve,
        synthesize,
        dataset=dataset,
        catalog=catalog,
    )

    assert execution.complete is False
    assert retrieval_count == 1
    assert len(execution.attempts) == 1
    attempt = execution.attempts[0]
    assert attempt.retrieval is not None
    assert attempt.context is not None
    assert attempt.citation_catalog is not None
    assert attempt.synthesis is None
    assert attempt.failure_category == "BedrockSynthesisRuntimeError"


def test_runtime_runner_detects_retrieval_request_identity_mismatch() -> None:
    """Typed provider evidence for another request cannot enter grounded evaluation."""
    dataset = load_golden_grounding_dataset(_FIXTURE)
    catalog = build_retrieval_catalog(load_corpus_manifest(_MANIFEST))

    def retrieve(request: RetrievalRequest) -> BedrockRetrieveResult:
        mismatched = RetrievalRequest(
            query=f"{request.query} different",
            top_k=request.top_k,
        )
        return _retrieval_result(mismatched, index=1)

    execution = run_grounding_runtime_evaluation(
        retrieve,
        lambda request: _synthesis_execution(request, index=1),
        dataset=dataset,
        catalog=catalog,
    )

    assert execution.complete is False
    assert len(execution.attempts) == 1
    assert execution.attempts[0].failure_category == "BedrockRetrievalValidationError"


def test_fixture_questions_have_stable_content_identity_for_runtime_evidence() -> None:
    """Question evidence can be persisted by digest without raw retrieval source bodies."""
    dataset = load_golden_grounding_dataset(_FIXTURE)

    digests = tuple(sha256(case.question.encode("utf-8")).hexdigest() for case in dataset.cases)

    assert len(digests) == 4
    assert len(set(digests)) == 4
    assert all(len(digest) == 64 for digest in digests)
