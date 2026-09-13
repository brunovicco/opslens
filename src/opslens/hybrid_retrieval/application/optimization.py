"""Deterministic Gate 8.5 comparison against the immutable Gate 8.4 baseline."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from opslens.hybrid_retrieval.application.synthesis_evaluation import (
    HybridRuntimeExecution,
)
from opslens.hybrid_retrieval.domain.errors import HybridRetrievalValidationError
from opslens.hybrid_retrieval.domain.evaluation import (
    HYBRID_EVALUATION_DATASET_ID,
    HYBRID_EVALUATION_DATASET_SHA256,
    HybridMeasurementStatus,
    HybridMetricDimension,
)
from opslens.hybrid_retrieval.domain.synthesis_evaluation import HybridSynthesisBaseline

GATE_8_5_EXPERIMENT_ID: Final = "hybrid-optimization:h8.5-01-v1"
GATE_8_5_HYPOTHESIS_ID: Final = "H8.5-01"

GATE_8_4_BASELINE_ROUTE_ACCURACY: Final = 1.0
GATE_8_4_BASELINE_STRUCTURED_FACT_CORRECTNESS: Final = 1.0
GATE_8_4_BASELINE_SEMANTIC_GROUNDEDNESS: Final = 2.0 / 3.0
GATE_8_4_BASELINE_CITATION_CORRECTNESS: Final = 2.0 / 3.0
GATE_8_4_BASELINE_ABSTENTION: Final = 1.0
GATE_8_4_BASELINE_LATENCY_MS: Final = 2959.3333333333335
GATE_8_4_BASELINE_INPUT_TOKENS: Final = 4150
GATE_8_4_BASELINE_OUTPUT_TOKENS: Final = 289
GATE_8_4_BASELINE_TOTAL_TOKENS: Final = 4439

_REQUIRED_PLANNED_CASES: Final = 6
_REQUIRED_MODEL_EXECUTIONS: Final = 3
_REQUIRED_STOP_REASON: Final = "end_turn"
_REQUIRED_RETRY_ATTEMPTS: Final = 0
_QUALITY_TARGET: Final = 1.0


class HybridOptimizationDecision(StrEnum):
    """Measured outcome for one versioned optimization hypothesis."""

    ACCEPT = "accept"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class HybridOptimizationComparison:
    """Independent before/after evidence for H8.5-01 without a composite score."""

    experiment_id: str
    hypothesis_id: str
    decision: HybridOptimizationDecision
    rejection_reasons: tuple[str, ...]
    route_accuracy: float
    structured_fact_correctness: float
    semantic_groundedness: float
    citation_correctness: float
    abstention: float
    latency_ms: float
    latency_delta_ms: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_token_delta: int
    output_token_delta: int
    total_token_delta: int

    def __post_init__(self) -> None:
        """Reject comparison records that drift from the single Gate 8.5 hypothesis."""
        if self.experiment_id != GATE_8_5_EXPERIMENT_ID:
            raise HybridRetrievalValidationError("unexpected Gate 8.5 experiment ID.")
        if self.hypothesis_id != GATE_8_5_HYPOTHESIS_ID:
            raise HybridRetrievalValidationError("unexpected Gate 8.5 hypothesis ID.")
        if self.decision is HybridOptimizationDecision.ACCEPT and self.rejection_reasons:
            raise HybridRetrievalValidationError(
                "accepted optimization comparisons cannot carry rejection reasons."
            )
        if self.decision is HybridOptimizationDecision.REJECT and not self.rejection_reasons:
            raise HybridRetrievalValidationError(
                "rejected optimization comparisons require deterministic reasons."
            )
        if len(set(self.rejection_reasons)) != len(self.rejection_reasons):
            raise HybridRetrievalValidationError("rejection reasons cannot contain duplicates.")
        for value in (
            self.route_accuracy,
            self.structured_fact_correctness,
            self.semantic_groundedness,
            self.citation_correctness,
            self.abstention,
        ):
            if not 0.0 <= value <= 1.0:
                raise HybridRetrievalValidationError(
                    "optimization quality measurements must be ratios."
                )
        if self.latency_ms < 0.0:
            raise HybridRetrievalValidationError("candidate latency cannot be negative.")
        if min(self.input_tokens, self.output_tokens, self.total_tokens) < 0:
            raise HybridRetrievalValidationError("candidate token counts cannot be negative.")
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise HybridRetrievalValidationError(
                "candidate total tokens must equal input plus output tokens."
            )


def _measured_value(
    baseline: HybridSynthesisBaseline,
    metric: HybridMetricDimension,
) -> float:
    """Return one required measured candidate metric."""
    measurement = baseline.measurement(metric)
    if measurement.status is not HybridMeasurementStatus.MEASURED:
        raise HybridRetrievalValidationError(
            f"Gate 8.5 requires measured {metric.value}."
        )
    if measurement.value is None:
        raise HybridRetrievalValidationError(
            f"Gate 8.5 measured {metric.value} unexpectedly lacks a value."
        )
    return measurement.value


def _validate_candidate_identity(
    execution: HybridRuntimeExecution,
    baseline: HybridSynthesisBaseline,
) -> None:
    """Require the immutable fixture and one complete candidate execution."""
    if not execution.complete:
        raise HybridRetrievalValidationError(
            "Gate 8.5 comparison requires one complete candidate execution."
        )
    if execution.dataset_id != HYBRID_EVALUATION_DATASET_ID:
        raise HybridRetrievalValidationError("candidate execution dataset ID drifted.")
    if execution.dataset_sha256 != HYBRID_EVALUATION_DATASET_SHA256:
        raise HybridRetrievalValidationError("candidate execution dataset SHA-256 drifted.")
    if baseline.dataset_id != execution.dataset_id:
        raise HybridRetrievalValidationError("candidate baseline dataset ID is inconsistent.")
    if baseline.dataset_sha256 != execution.dataset_sha256:
        raise HybridRetrievalValidationError(
            "candidate baseline dataset SHA-256 is inconsistent."
        )


def evaluate_gate_8_5_hypothesis(
    execution: HybridRuntimeExecution,
    *,
    baseline: HybridSynthesisBaseline,
) -> HybridOptimizationComparison:
    """Evaluate H8.5-01 once using predeclared non-regression and quality targets."""
    _validate_candidate_identity(execution, baseline)

    route_accuracy = _measured_value(baseline, HybridMetricDimension.ROUTE_ACCURACY)
    structured_fact_correctness = _measured_value(
        baseline,
        HybridMetricDimension.STRUCTURED_FACT_CORRECTNESS,
    )
    semantic_groundedness = _measured_value(
        baseline,
        HybridMetricDimension.SEMANTIC_GROUNDEDNESS,
    )
    citation_correctness = _measured_value(
        baseline,
        HybridMetricDimension.CITATION_CORRECTNESS,
    )
    abstention = _measured_value(baseline, HybridMetricDimension.ABSTENTION)
    latency_ms = _measured_value(baseline, HybridMetricDimension.LATENCY)

    successful = tuple(
        attempt.synthesis
        for attempt in execution.attempts
        if attempt.synthesis is not None
    )
    input_tokens = sum(item.evidence.input_tokens for item in successful)
    output_tokens = sum(item.evidence.output_tokens for item in successful)
    total_tokens = sum(item.evidence.total_tokens for item in successful)

    rejection_reasons: list[str] = []
    if route_accuracy != GATE_8_4_BASELINE_ROUTE_ACCURACY:
        rejection_reasons.append("route_accuracy_regressed")
    if structured_fact_correctness != GATE_8_4_BASELINE_STRUCTURED_FACT_CORRECTNESS:
        rejection_reasons.append("structured_fact_correctness_regressed")
    if abstention != GATE_8_4_BASELINE_ABSTENTION:
        rejection_reasons.append("abstention_regressed")
    if execution.planned_case_count != _REQUIRED_PLANNED_CASES:
        rejection_reasons.append("planned_case_count_changed")
    if execution.synthesis_invocation_attempt_count != _REQUIRED_MODEL_EXECUTIONS:
        rejection_reasons.append("synthesis_invocation_attempt_count_changed")
    if execution.admitted_model_execution_count != _REQUIRED_MODEL_EXECUTIONS:
        rejection_reasons.append("admitted_model_execution_count_changed")
    if any(item.evidence.stop_reason != _REQUIRED_STOP_REASON for item in successful):
        rejection_reasons.append("stop_reason_regressed")
    if any(item.evidence.retry_attempts != _REQUIRED_RETRY_ATTEMPTS for item in successful):
        rejection_reasons.append("sdk_retry_regressed")

    cost = baseline.measurement(HybridMetricDimension.COST)
    if cost.status is not HybridMeasurementStatus.UNMEASURED or cost.value is not None:
        rejection_reasons.append("cost_measurement_contract_changed")

    if semantic_groundedness != _QUALITY_TARGET:
        rejection_reasons.append("semantic_groundedness_target_not_met")
    if citation_correctness != _QUALITY_TARGET:
        rejection_reasons.append("citation_correctness_target_not_met")

    reasons = tuple(rejection_reasons)
    decision = (
        HybridOptimizationDecision.ACCEPT
        if not reasons
        else HybridOptimizationDecision.REJECT
    )
    return HybridOptimizationComparison(
        experiment_id=GATE_8_5_EXPERIMENT_ID,
        hypothesis_id=GATE_8_5_HYPOTHESIS_ID,
        decision=decision,
        rejection_reasons=reasons,
        route_accuracy=route_accuracy,
        structured_fact_correctness=structured_fact_correctness,
        semantic_groundedness=semantic_groundedness,
        citation_correctness=citation_correctness,
        abstention=abstention,
        latency_ms=latency_ms,
        latency_delta_ms=latency_ms - GATE_8_4_BASELINE_LATENCY_MS,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        input_token_delta=input_tokens - GATE_8_4_BASELINE_INPUT_TOKENS,
        output_token_delta=output_tokens - GATE_8_4_BASELINE_OUTPUT_TOKENS,
        total_token_delta=total_tokens - GATE_8_4_BASELINE_TOTAL_TOKENS,
    )


__all__ = [
    "GATE_8_4_BASELINE_ABSTENTION",
    "GATE_8_4_BASELINE_CITATION_CORRECTNESS",
    "GATE_8_4_BASELINE_INPUT_TOKENS",
    "GATE_8_4_BASELINE_LATENCY_MS",
    "GATE_8_4_BASELINE_OUTPUT_TOKENS",
    "GATE_8_4_BASELINE_ROUTE_ACCURACY",
    "GATE_8_4_BASELINE_SEMANTIC_GROUNDEDNESS",
    "GATE_8_4_BASELINE_STRUCTURED_FACT_CORRECTNESS",
    "GATE_8_4_BASELINE_TOTAL_TOKENS",
    "GATE_8_5_EXPERIMENT_ID",
    "GATE_8_5_HYPOTHESIS_ID",
    "HybridOptimizationComparison",
    "HybridOptimizationDecision",
    "evaluate_gate_8_5_hypothesis",
]
