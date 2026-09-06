"""Bounded Gate 7.5 orchestration over the already-admitted Gate 7.4 runtime."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from opslens.knowledge_retrieval.application.bedrock_retrieval import (
    BedrockRetrievalProviderError,
    BedrockRetrievalValidationError,
    BedrockRetrieveResult,
)
from opslens.knowledge_retrieval.application.retrieval_catalog import (
    CanonicalRetrievalCatalog,
)
from opslens.knowledge_retrieval.application.retrieval_evaluation import (
    GoldenRetrievalDataset,
    RankedEvaluationChunk,
    RetrievalCaseObservation,
    RetrievalEvaluationIncompleteError,
    RetrievalEvaluationSummary,
    aggregate_retrieval_evaluation,
    validate_dataset_catalog,
)
from opslens.knowledge_retrieval.domain import RetrievalRequest

_EVALUATION_TOP_K = 10

EvaluationRetriever = Callable[[RetrievalRequest], BedrockRetrieveResult]


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationExecution:
    """All content-free case observations plus an optional complete summary."""

    observations: tuple[RetrievalCaseObservation, ...]
    summary: RetrievalEvaluationSummary | None

    @property
    def complete(self) -> bool:
        """Return whether every case produced admissible evidence and aggregate metrics."""
        return self.summary is not None


def _successful_observation(
    *,
    case_id: str,
    expected_request: RetrievalRequest,
    result: BedrockRetrieveResult,
) -> RetrievalCaseObservation:
    """Project one admitted Gate 7.4 result into content-free evaluation evidence."""
    if result.evidence.request != expected_request:
        raise BedrockRetrievalValidationError(
            "evaluation retriever returned evidence for a different request"
        )
    ranked = tuple(
        RankedEvaluationChunk(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            source_type=chunk.source_type.value,
            relevance_score=chunk.relevance_score,
        )
        for chunk in result.evidence.chunks
    )
    return RetrievalCaseObservation(
        case_id=case_id,
        returned_chunks=ranked,
        client_elapsed_ms=result.invocation.client_elapsed_ms,
        provider_request_id=result.invocation.provider_request_id,
        retry_attempts=result.invocation.retry_attempts,
    )


def _failed_observation(
    *,
    case_id: str,
    exc: BedrockRetrievalProviderError | BedrockRetrievalValidationError,
) -> RetrievalCaseObservation:
    """Preserve one safe bounded Gate 7.4 failure without turning it into a miss."""
    return RetrievalCaseObservation(
        case_id=case_id,
        returned_chunks=(),
        client_elapsed_ms=0,
        provider_request_id="",
        retry_attempts=0,
        failure_category=f"{type(exc).__name__}:{exc}",
    )


def run_retrieval_evaluation(
    retrieve: EvaluationRetriever,
    *,
    dataset: GoldenRetrievalDataset,
    catalog: CanonicalRetrievalCatalog,
) -> RetrievalEvaluationExecution:
    """Execute exactly one top-k=10 admitted retrieval attempt for every golden case."""
    validate_dataset_catalog(dataset, catalog)
    observations: list[RetrievalCaseObservation] = []

    for case in dataset.cases:
        request = RetrievalRequest(query=case.question, top_k=_EVALUATION_TOP_K)
        try:
            result = retrieve(request)
            observation = _successful_observation(
                case_id=case.case_id,
                expected_request=request,
                result=result,
            )
        except (BedrockRetrievalProviderError, BedrockRetrievalValidationError) as exc:
            observation = _failed_observation(case_id=case.case_id, exc=exc)
        observations.append(observation)

    frozen = tuple(observations)
    try:
        summary = aggregate_retrieval_evaluation(dataset, catalog, frozen)
    except RetrievalEvaluationIncompleteError:
        summary = None
    return RetrievalEvaluationExecution(observations=frozen, summary=summary)
