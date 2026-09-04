"""Offline evaluation primitives for semantic-query planner field accuracy."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from opslens.semantic_query.planner.models import (
    PlannedSemanticQuery,
    PlannerContractError,
    PlannerOutcome,
    SemanticPlannerRequest,
    UnsupportedPlannerDecision,
)
from opslens.semantic_query.planner.parser import parse_planner_payload


@dataclass(frozen=True, slots=True)
class PlannerEvalCase:
    """One golden planner question and expected typed outcome."""

    case_id: str
    request: SemanticPlannerRequest
    expected: PlannerOutcome

    def __post_init__(self) -> None:
        """Keep evaluation identities and expected outputs explicit."""
        if type(self.case_id) is not str or not self.case_id.strip():
            raise PlannerContractError("Planner eval case_id cannot be blank.")
        if type(self.request) is not SemanticPlannerRequest:
            raise PlannerContractError("Planner eval request has the wrong type.")
        if type(self.expected) not in {
            PlannedSemanticQuery,
            UnsupportedPlannerDecision,
        }:
            raise PlannerContractError("Planner eval expected outcome has the wrong type.")


@dataclass(frozen=True, slots=True)
class PlannerEvaluation:
    """Field-level accuracy evidence for one planner prediction set."""

    total_cases: int
    supported_cases: int
    unsupported_cases: int
    decision_correct: int
    metric_correct: int
    dimensions_correct: int
    snapshot_date_correct: int
    minimum_score_correct: int
    order_by_correct: int
    order_direction_correct: int
    limit_correct: int
    exact_semantic_query_correct: int
    unsupported_reason_correct: int

    @property
    def decision_accuracy(self) -> float:
        """Return decision accuracy across every evaluation case."""
        return _ratio(self.decision_correct, self.total_cases)

    @property
    def metric_accuracy(self) -> float:
        """Return metric accuracy across expected semantic-query cases."""
        return _ratio(self.metric_correct, self.supported_cases)

    @property
    def dimensions_accuracy(self) -> float:
        """Return dimension accuracy across expected semantic-query cases."""
        return _ratio(self.dimensions_correct, self.supported_cases)

    @property
    def snapshot_date_accuracy(self) -> float:
        """Return explicit-date filter accuracy."""
        return _ratio(self.snapshot_date_correct, self.supported_cases)

    @property
    def minimum_score_accuracy(self) -> float:
        """Return EPSS threshold filter accuracy."""
        return _ratio(self.minimum_score_correct, self.supported_cases)

    @property
    def order_by_accuracy(self) -> float:
        """Return order-field accuracy."""
        return _ratio(self.order_by_correct, self.supported_cases)

    @property
    def order_direction_accuracy(self) -> float:
        """Return sort-direction accuracy."""
        return _ratio(self.order_direction_correct, self.supported_cases)

    @property
    def limit_accuracy(self) -> float:
        """Return row-limit accuracy."""
        return _ratio(self.limit_correct, self.supported_cases)

    @property
    def exact_semantic_query_accuracy(self) -> float:
        """Return exact typed-query accuracy."""
        return _ratio(self.exact_semantic_query_correct, self.supported_cases)

    @property
    def unsupported_reason_accuracy(self) -> float:
        """Return unsupported-reason accuracy for expected fail-closed cases."""
        return _ratio(self.unsupported_reason_correct, self.unsupported_cases)

    def as_dict(self) -> dict[str, int | float]:
        """Project stable numeric metrics for later CLI/artifact persistence."""
        return {
            "total_cases": self.total_cases,
            "supported_cases": self.supported_cases,
            "unsupported_cases": self.unsupported_cases,
            "decision_accuracy": self.decision_accuracy,
            "metric_accuracy": self.metric_accuracy,
            "dimensions_accuracy": self.dimensions_accuracy,
            "snapshot_date_accuracy": self.snapshot_date_accuracy,
            "minimum_score_accuracy": self.minimum_score_accuracy,
            "order_by_accuracy": self.order_by_accuracy,
            "order_direction_accuracy": self.order_direction_accuracy,
            "limit_accuracy": self.limit_accuracy,
            "exact_semantic_query_accuracy": self.exact_semantic_query_accuracy,
            "unsupported_reason_accuracy": self.unsupported_reason_accuracy,
        }


def load_planner_eval_cases(path: object) -> tuple[PlannerEvalCase, ...]:
    """Load a bounded JSONL golden dataset through the same deterministic parser."""
    if not isinstance(path, Path):
        raise TypeError("path must be pathlib.Path.")

    cases: list[PlannerEvalCase] = []
    seen_ids: set[str] = set()
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PlannerContractError(
                f"Planner eval line {line_number} is not valid JSON."
            ) from exc

        mapping = _as_mapping(payload, context=f"Planner eval line {line_number}")
        if frozenset(mapping) != frozenset({"id", "question", "expected"}):
            raise PlannerContractError(
                f"Planner eval line {line_number} must contain id, question, expected."
            )

        case_id = mapping["id"]
        question = mapping["question"]
        if not isinstance(case_id, str) or not case_id.strip():
            raise PlannerContractError(f"Planner eval line {line_number} has invalid id.")
        if case_id in seen_ids:
            raise PlannerContractError(f"Duplicate planner eval case id {case_id!r}.")
        if not isinstance(question, str):
            raise PlannerContractError(
                f"Planner eval line {line_number} question must be a string."
            )

        seen_ids.add(case_id)
        cases.append(
            PlannerEvalCase(
                case_id=case_id,
                request=SemanticPlannerRequest(question),
                expected=parse_planner_payload(mapping["expected"]),
            )
        )

    if not cases:
        raise PlannerContractError("Planner evaluation dataset cannot be empty.")
    return tuple(cases)


def evaluate_planner_predictions(
    cases: Sequence[PlannerEvalCase],
    predictions: Mapping[str, PlannerOutcome],
) -> PlannerEvaluation:
    """Measure planner decision and semantic-field accuracy separately."""
    if not cases:
        raise PlannerContractError("Planner evaluation requires at least one case.")

    expected_ids = [case.case_id for case in cases]
    if len(expected_ids) != len(set(expected_ids)):
        raise PlannerContractError("Planner evaluation case ids must be unique.")
    if frozenset(predictions) != frozenset(expected_ids):
        raise PlannerContractError(
            "Planner prediction ids must exactly match evaluation case ids."
        )

    supported_cases = 0
    unsupported_cases = 0
    decision_correct = 0
    metric_correct = 0
    dimensions_correct = 0
    snapshot_date_correct = 0
    minimum_score_correct = 0
    order_by_correct = 0
    order_direction_correct = 0
    limit_correct = 0
    exact_semantic_query_correct = 0
    unsupported_reason_correct = 0

    for case in cases:
        predicted = predictions[case.case_id]
        expected = case.expected

        if isinstance(expected, PlannedSemanticQuery):
            supported_cases += 1
            if not isinstance(predicted, PlannedSemanticQuery):
                continue

            decision_correct += 1
            expected_query = expected.query
            predicted_query = predicted.query

            metric_correct += predicted_query.metric == expected_query.metric
            dimensions_correct += predicted_query.dimensions == expected_query.dimensions
            snapshot_date_correct += (
                predicted_query.filters.snapshot_date
                == expected_query.filters.snapshot_date
            )
            minimum_score_correct += (
                predicted_query.filters.minimum_score
                == expected_query.filters.minimum_score
            )
            order_by_correct += predicted_query.order_by == expected_query.order_by
            order_direction_correct += (
                predicted_query.order_direction == expected_query.order_direction
            )
            limit_correct += predicted_query.limit == expected_query.limit
            exact_semantic_query_correct += predicted_query == expected_query
            continue

        unsupported_cases += 1
        if not isinstance(predicted, UnsupportedPlannerDecision):
            continue
        decision_correct += 1
        unsupported_reason_correct += predicted.reason == expected.reason

    return PlannerEvaluation(
        total_cases=len(cases),
        supported_cases=supported_cases,
        unsupported_cases=unsupported_cases,
        decision_correct=decision_correct,
        metric_correct=metric_correct,
        dimensions_correct=dimensions_correct,
        snapshot_date_correct=snapshot_date_correct,
        minimum_score_correct=minimum_score_correct,
        order_by_correct=order_by_correct,
        order_direction_correct=order_direction_correct,
        limit_correct=limit_correct,
        exact_semantic_query_correct=exact_semantic_query_correct,
        unsupported_reason_correct=unsupported_reason_correct,
    )


def _as_mapping(value: object, *, context: str) -> Mapping[str, object]:
    """Validate one decoded JSON object in the evaluation fixture."""
    if not isinstance(value, Mapping):
        raise PlannerContractError(f"{context} must be an object.")
    return cast(Mapping[str, object], value)


def _ratio(numerator: int, denominator: int) -> float:
    """Return deterministic accuracy with zero for an empty denominator."""
    if denominator == 0:
        return 0.0
    return numerator / denominator
