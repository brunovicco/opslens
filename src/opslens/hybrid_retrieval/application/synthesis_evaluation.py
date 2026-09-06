"""Gate 8.4 runtime orchestration and metric computation over the frozen fixture."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from opslens.hybrid_retrieval.adapters.bedrock_synthesis import (
    BedrockHybridSynthesisExecution,
    BedrockHybridSynthesisRuntimeError,
)
from opslens.hybrid_retrieval.application.assembly import assemble_hybrid_evidence
from opslens.hybrid_retrieval.application.evaluation import evaluate_hybrid_offline
from opslens.hybrid_retrieval.application.routing import route_evidence_request
from opslens.hybrid_retrieval.application.synthesis import (
    HybridSynthesisOutputError,
    build_hybrid_synthesis_request,
    project_deterministic_structured_answer,
)
from opslens.hybrid_retrieval.domain.errors import HybridRetrievalValidationError
from opslens.hybrid_retrieval.domain.evaluation import (
    HybridEvaluationCase,
    HybridEvaluationDataset,
    HybridExpectedAnswerBehavior,
    HybridMeasurementStatus,
    HybridMetricDimension,
    HybridMetricMeasurement,
    HybridMetricUnit,
)
from opslens.hybrid_retrieval.domain.evidence import HybridEvidenceEnvelope
from opslens.hybrid_retrieval.domain.models import (
    HybridRoute,
    HybridRouteDecision,
    HybridRoutingRequest,
)
from opslens.hybrid_retrieval.domain.synthesis import (
    HybridStructuredFactProjection,
    HybridSynthesisDecision,
    HybridSynthesisRequest,
)
from opslens.hybrid_retrieval.domain.synthesis_evaluation import (
    HybridSynthesisBaseline,
    HybridSynthesisCaseEvaluation,
)

HybridEvaluationSynthesizer = Callable[
    [HybridSynthesisRequest],
    BedrockHybridSynthesisExecution,
]


@dataclass(frozen=True, slots=True)
class HybridRuntimeCaseExecution:
    """One Gate 8.4 case attempt with deterministic and provider evidence separated."""

    case: HybridEvaluationCase
    route_decision: HybridRouteDecision
    envelope: HybridEvidenceEnvelope | None
    structured_facts: tuple[HybridStructuredFactProjection, ...]
    request: HybridSynthesisRequest | None
    synthesis: BedrockHybridSynthesisExecution | None
    observed_behavior: HybridExpectedAnswerBehavior | None
    failure_category: str | None = None

    @property
    def complete(self) -> bool:
        """Return whether the case reached one valid bounded system outcome."""
        return self.failure_category is None and self.observed_behavior is not None


@dataclass(frozen=True, slots=True)
class HybridRuntimeExecution:
    """First-run Gate 8.4 observations before any optimization is authorized."""

    dataset_id: str
    dataset_sha256: str
    attempts: tuple[HybridRuntimeCaseExecution, ...]
    planned_case_count: int

    @property
    def complete(self) -> bool:
        """Require all six frozen cases to reach one bounded outcome exactly once."""
        return (
            len(self.attempts) == self.planned_case_count
            and all(attempt.complete for attempt in self.attempts)
        )


def _failure_category(exc: Exception) -> str:
    """Return one content-free runtime/application failure category."""
    return type(exc).__name__


def _observed_model_behavior(
    synthesis: BedrockHybridSynthesisExecution,
) -> HybridExpectedAnswerBehavior:
    """Translate admitted model decision into the frozen system behavior vocabulary."""
    if synthesis.result.decision is HybridSynthesisDecision.ANSWER:
        return HybridExpectedAnswerBehavior.ANSWER
    return HybridExpectedAnswerBehavior.ABSTAIN


def run_hybrid_synthesis_runtime_evaluation(
    synthesize: HybridEvaluationSynthesizer,
    *,
    dataset: HybridEvaluationDataset,
) -> HybridRuntimeExecution:
    """Run the frozen cases once; stop after the first model/application failure."""
    attempts: list[HybridRuntimeCaseExecution] = []

    for case in dataset.cases:
        decision = route_evidence_request(
            HybridRoutingRequest(evidence_needs=case.evidence_needs)
        )
        envelope: HybridEvidenceEnvelope | None = None
        structured_facts: tuple[HybridStructuredFactProjection, ...] = ()
        request: HybridSynthesisRequest | None = None
        synthesis: BedrockHybridSynthesisExecution | None = None

        if decision.route is HybridRoute.UNSUPPORTED:
            attempts.append(
                HybridRuntimeCaseExecution(
                    case=case,
                    route_decision=decision,
                    envelope=None,
                    structured_facts=(),
                    request=None,
                    synthesis=None,
                    observed_behavior=HybridExpectedAnswerBehavior.ABSTAIN,
                )
            )
            continue

        try:
            envelope = assemble_hybrid_evidence(
                authority_decision=decision,
                structured_evidence=case.structured_evidence,
                semantic_evidence=case.semantic_evidence,
            )
        except HybridRetrievalValidationError:
            attempts.append(
                HybridRuntimeCaseExecution(
                    case=case,
                    route_decision=decision,
                    envelope=None,
                    structured_facts=(),
                    request=None,
                    synthesis=None,
                    observed_behavior=(
                        HybridExpectedAnswerBehavior.REJECT_BEFORE_SYNTHESIS
                    ),
                )
            )
            continue

        structured_facts = project_deterministic_structured_answer(envelope)
        if decision.route is HybridRoute.STRUCTURED:
            attempts.append(
                HybridRuntimeCaseExecution(
                    case=case,
                    route_decision=decision,
                    envelope=envelope,
                    structured_facts=structured_facts,
                    request=None,
                    synthesis=None,
                    observed_behavior=HybridExpectedAnswerBehavior.ANSWER,
                )
            )
            continue

        try:
            request = build_hybrid_synthesis_request(
                question=case.question,
                envelope=envelope,
            )
            synthesis = synthesize(request)
            if synthesis.result.request_sha256 != request.request_sha256:
                raise HybridSynthesisOutputError(
                    "runtime evaluator received synthesis for a different request"
                )
        except (
            BedrockHybridSynthesisRuntimeError,
            HybridRetrievalValidationError,
            HybridSynthesisOutputError,
        ) as exc:
            attempts.append(
                HybridRuntimeCaseExecution(
                    case=case,
                    route_decision=decision,
                    envelope=envelope,
                    structured_facts=structured_facts,
                    request=request,
                    synthesis=synthesis,
                    observed_behavior=None,
                    failure_category=_failure_category(exc),
                )
            )
            break

        attempts.append(
            HybridRuntimeCaseExecution(
                case=case,
                route_decision=decision,
                envelope=envelope,
                structured_facts=structured_facts,
                request=request,
                synthesis=synthesis,
                observed_behavior=_observed_model_behavior(synthesis),
            )
        )

    return HybridRuntimeExecution(
        dataset_id=dataset.dataset_id,
        dataset_sha256=dataset.content_sha256,
        attempts=tuple(attempts),
        planned_case_count=len(dataset.cases),
    )


def _structured_fact_correct(attempt: HybridRuntimeCaseExecution) -> bool | None:
    """Score deterministic structured targets only for answer cases that define them."""
    case = attempt.case
    if (
        case.expected_answer_behavior is not HybridExpectedAnswerBehavior.ANSWER
        or not case.expected_structured_facts
    ):
        return None
    actual = {
        (item.field_name, type(item.value).__name__, item.value)
        for item in attempt.structured_facts
    }
    expected = {
        (item.name, type(item.value).__name__, item.value)
        for item in case.expected_structured_facts
    }
    return expected.issubset(actual)


def _cited_chunk_ids(attempt: HybridRuntimeCaseExecution) -> tuple[str, ...]:
    """Resolve model-selected S IDs back to canonical chunk IDs."""
    if attempt.request is None or attempt.synthesis is None:
        return ()
    by_id = {
        item.citation_id: item.chunk_id for item in attempt.request.semantic_citations
    }
    cited = {
        by_id[citation_id]
        for claim in attempt.synthesis.result.claims
        for citation_id in claim.semantic_citation_ids
    }
    return tuple(sorted(cited))


def _semantic_groundedness_correct(
    attempt: HybridRuntimeCaseExecution,
) -> bool | None:
    """Score whether every model claim cites only fixture-adjudicated supporting chunks."""
    if attempt.synthesis is None or attempt.request is None:
        return None
    if attempt.synthesis.result.decision is not HybridSynthesisDecision.ANSWER:
        return False
    supported = set(attempt.case.expected_supported_chunk_ids)
    if not supported:
        return False
    by_id = {
        item.citation_id: item.chunk_id for item in attempt.request.semantic_citations
    }
    for claim in attempt.synthesis.result.claims:
        claim_chunks = {by_id[item] for item in claim.semantic_citation_ids}
        if not claim_chunks or not claim_chunks.issubset(supported):
            return False
    return True


def _citation_correct(attempt: HybridRuntimeCaseExecution) -> bool | None:
    """Score exact canonical citation targets independently from semantic support."""
    if attempt.synthesis is None:
        return None
    return set(_cited_chunk_ids(attempt)) == set(
        attempt.case.expected_citation_chunk_ids
    )


def _ratio(values: list[bool], label: str) -> float:
    """Return one deterministic ratio over a non-empty metric population."""
    if not values:
        raise HybridRetrievalValidationError(f"{label} has no scorable cases.")
    return sum(values) / len(values)


def evaluate_hybrid_synthesis_runtime(
    execution: HybridRuntimeExecution,
    *,
    dataset: HybridEvaluationDataset,
) -> HybridSynthesisBaseline:
    """Compute independent Gate 8.4 metrics without a composite quality score."""
    if not execution.complete:
        raise HybridRetrievalValidationError(
            "runtime execution must complete before synthesis metrics are computed."
        )
    if execution.dataset_id != dataset.dataset_id:
        raise HybridRetrievalValidationError("runtime execution dataset ID is inconsistent.")
    if execution.dataset_sha256 != dataset.content_sha256:
        raise HybridRetrievalValidationError(
            "runtime execution dataset SHA-256 is inconsistent."
        )

    offline = evaluate_hybrid_offline(dataset)
    case_results: list[HybridSynthesisCaseEvaluation] = []
    structured_scores: list[bool] = []
    semantic_scores: list[bool] = []
    citation_scores: list[bool] = []
    abstention_scores: list[bool] = []
    latencies: list[int] = []

    for attempt in execution.attempts:
        observed = attempt.observed_behavior
        if observed is None:
            raise HybridRetrievalValidationError(
                "complete runtime attempt unexpectedly lacks observed behavior."
            )
        structured_correct = _structured_fact_correct(attempt)
        semantic_correct = _semantic_groundedness_correct(attempt)
        citation_correct = _citation_correct(attempt)
        cited_chunk_ids = _cited_chunk_ids(attempt)

        if structured_correct is not None:
            structured_scores.append(structured_correct)
        if semantic_correct is not None:
            semantic_scores.append(semantic_correct)
        if citation_correct is not None:
            citation_scores.append(citation_correct)
        if attempt.case.expected_answer_behavior is not HybridExpectedAnswerBehavior.ANSWER:
            abstention_scores.append(
                observed is attempt.case.expected_answer_behavior
            )
        if attempt.synthesis is not None:
            latencies.append(attempt.synthesis.evidence.client_elapsed_ms)

        case_results.append(
            HybridSynthesisCaseEvaluation(
                case_id=attempt.case.case_id,
                expected_behavior=attempt.case.expected_answer_behavior,
                observed_behavior=observed,
                behavior_correct=observed is attempt.case.expected_answer_behavior,
                model_required=attempt.synthesis is not None,
                model_result_sha256=(
                    attempt.synthesis.result.result_sha256
                    if attempt.synthesis is not None
                    else None
                ),
                request_sha256=(
                    attempt.request.request_sha256
                    if attempt.request is not None and attempt.synthesis is not None
                    else None
                ),
                structured_fact_correct=structured_correct,
                semantic_groundedness_correct=semantic_correct,
                citation_correct=citation_correct,
                cited_chunk_ids=cited_chunk_ids,
            )
        )

    measurements = (
        HybridMetricMeasurement(
            metric=HybridMetricDimension.ROUTE_ACCURACY,
            unit=HybridMetricUnit.RATIO,
            status=HybridMeasurementStatus.MEASURED,
            value=offline.route_accuracy,
        ),
        HybridMetricMeasurement(
            metric=HybridMetricDimension.STRUCTURED_FACT_CORRECTNESS,
            unit=HybridMetricUnit.RATIO,
            status=HybridMeasurementStatus.MEASURED,
            value=_ratio(structured_scores, "structured_fact_correctness"),
        ),
        HybridMetricMeasurement(
            metric=HybridMetricDimension.SEMANTIC_GROUNDEDNESS,
            unit=HybridMetricUnit.RATIO,
            status=HybridMeasurementStatus.MEASURED,
            value=_ratio(semantic_scores, "semantic_groundedness"),
        ),
        HybridMetricMeasurement(
            metric=HybridMetricDimension.CITATION_CORRECTNESS,
            unit=HybridMetricUnit.RATIO,
            status=HybridMeasurementStatus.MEASURED,
            value=_ratio(citation_scores, "citation_correctness"),
        ),
        HybridMetricMeasurement(
            metric=HybridMetricDimension.ABSTENTION,
            unit=HybridMetricUnit.RATIO,
            status=HybridMeasurementStatus.MEASURED,
            value=_ratio(abstention_scores, "abstention"),
        ),
        HybridMetricMeasurement(
            metric=HybridMetricDimension.LATENCY,
            unit=HybridMetricUnit.MILLISECONDS,
            status=HybridMeasurementStatus.MEASURED,
            value=sum(latencies) / len(latencies),
        ),
        HybridMetricMeasurement(
            metric=HybridMetricDimension.COST,
            unit=HybridMetricUnit.USD,
            status=HybridMeasurementStatus.UNMEASURED,
            value=None,
        ),
    )

    return HybridSynthesisBaseline(
        dataset_id=dataset.dataset_id,
        dataset_sha256=dataset.content_sha256,
        case_results=tuple(case_results),
        measurements=measurements,
    )
