"""Tests for the bounded Gate 7.5 full-fixture evaluation runner."""

from __future__ import annotations

from pathlib import Path

import pytest

from opslens.knowledge_retrieval.application.bedrock_retrieval import (
    BedrockRetrievalProviderError,
    BedrockRetrieveInvocationEvidence,
    BedrockRetrieveResult,
)
from opslens.knowledge_retrieval.application.corpus_config import load_corpus_manifest
from opslens.knowledge_retrieval.application.retrieval_catalog import (
    CanonicalRetrievalCatalog,
    build_retrieval_catalog,
)
from opslens.knowledge_retrieval.application.retrieval_evaluation import (
    load_golden_retrieval_dataset,
)
from opslens.knowledge_retrieval.application.retrieval_evaluation_runner import (
    run_retrieval_evaluation,
)
from opslens.knowledge_retrieval.domain import (
    RetrievalBackend,
    RetrievalEvidence,
    RetrievalRequest,
    RetrievedChunk,
)

_REPO_ROOT = Path(__file__).parents[3]
_FIXTURE = _REPO_ROOT / "tests" / "fixtures" / "knowledge_retrieval" / "golden_retrieval_v1.json"
_MANIFEST = _REPO_ROOT / "knowledge" / "corpus" / "v1" / "manifest.json"
_KB_ID = "BTVJ2PBR2A"


def _catalog() -> CanonicalRetrievalCatalog:
    return build_retrieval_catalog(load_corpus_manifest(_MANIFEST))


def _result_for_request(
    request: RetrievalRequest,
    *,
    catalog: CanonicalRetrievalCatalog,
    chunk_id: str,
    request_number: int,
) -> BedrockRetrieveResult:
    canonical = next(chunk for chunk in catalog.chunks if chunk.chunk_id == chunk_id)
    chunk = RetrievedChunk.from_text(
        chunk_id=canonical.chunk_id,
        document_id=canonical.document_id,
        source_id=canonical.source_id,
        source_type=canonical.source_type,
        canonical_uri=canonical.canonical_uri,
        document_content_sha256=canonical.document_content_sha256,
        text=f"synthetic admitted evaluation text {request_number}",
        rank=1,
        relevance_score=0.9,
        title=canonical.title,
        section_path=canonical.section_path,
    )
    evidence = RetrievalEvidence(
        retrieval_id=f"bedrock-retrieve:req-{request_number}",
        request=request,
        chunks=(chunk,),
        backend=RetrievalBackend.BEDROCK_KNOWLEDGE_BASE,
        backend_reference=_KB_ID,
    )
    invocation = BedrockRetrieveInvocationEvidence(
        knowledge_base_id=_KB_ID,
        provider_request_id=f"req-{request_number}",
        retry_attempts=0,
        client_elapsed_ms=100 + request_number,
        returned_result_count=1,
    )
    return BedrockRetrieveResult(evidence=evidence, invocation=invocation)


def test_runner_makes_exactly_one_top_k_10_attempt_per_fixture_case() -> None:
    dataset = load_golden_retrieval_dataset(_FIXTURE)
    catalog = _catalog()
    calls: list[RetrievalRequest] = []
    case_by_question = {case.question: case for case in dataset.cases}

    def retrieve(request: RetrievalRequest) -> BedrockRetrieveResult:
        calls.append(request)
        case = case_by_question[request.query]
        chunk_id = (
            case.relevant_chunk_ids[0]
            if case.should_have_relevant_evidence
            else catalog.chunks[0].chunk_id
        )
        return _result_for_request(
            request,
            catalog=catalog,
            chunk_id=chunk_id,
            request_number=len(calls),
        )

    execution = run_retrieval_evaluation(
        retrieve,
        dataset=dataset,
        catalog=catalog,
    )

    assert len(calls) == 10
    assert all(request.top_k == 10 for request in calls)
    assert [request.query for request in calls] == [case.question for case in dataset.cases]
    assert execution.complete is True
    assert execution.summary is not None
    assert execution.summary.recall_at_1 == pytest.approx(1.0)
    assert execution.summary.mean_reciprocal_rank == pytest.approx(1.0)
    assert execution.summary.negative_nonempty_retrieval_rate == pytest.approx(1.0)


def test_runner_records_safe_case_failure_and_continues_remaining_cases() -> None:
    dataset = load_golden_retrieval_dataset(_FIXTURE)
    catalog = _catalog()
    calls: list[RetrievalRequest] = []
    case_by_question = {case.question: case for case in dataset.cases}

    def retrieve(request: RetrievalRequest) -> BedrockRetrieveResult:
        calls.append(request)
        if len(calls) == 3:
            raise BedrockRetrievalProviderError(
                "Bedrock Retrieve failed provider_code=ThrottlingException"
            )
        case = case_by_question[request.query]
        chunk_id = (
            case.relevant_chunk_ids[0]
            if case.should_have_relevant_evidence
            else catalog.chunks[0].chunk_id
        )
        return _result_for_request(
            request,
            catalog=catalog,
            chunk_id=chunk_id,
            request_number=len(calls),
        )

    execution = run_retrieval_evaluation(
        retrieve,
        dataset=dataset,
        catalog=catalog,
    )

    assert len(calls) == 10
    assert execution.complete is False
    assert execution.summary is None
    assert execution.observations[2].failure_category == (
        "BedrockRetrievalProviderError:Bedrock Retrieve failed "
        "provider_code=ThrottlingException"
    )
    assert execution.observations[2].returned_chunks == ()
