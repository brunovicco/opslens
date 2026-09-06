"""Evaluation result contracts for the first bounded hybrid synthesis baseline."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import cast

from opslens.hybrid_retrieval.domain.errors import HybridRetrievalValidationError
from opslens.hybrid_retrieval.domain.evaluation import (
    HYBRID_EVALUATION_DATASET_ID,
    HYBRID_EVALUATION_DATASET_SHA256,
    HybridExpectedAnswerBehavior,
    HybridMeasurementStatus,
    HybridMetricDimension,
    HybridMetricMeasurement,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _require_runtime_instance(
    value: object,
    expected_type: type[object],
    label: str,
) -> None:
    """Validate runtime values without weakening public annotations."""
    if not isinstance(value, expected_type):
        raise HybridRetrievalValidationError(f"{label} has an unsupported value.")


def _normalize_required_text(value: object, label: str) -> str:
    """Return one normalized non-empty string."""
    if not isinstance(value, str):
        raise HybridRetrievalValidationError(f"{label} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise HybridRetrievalValidationError(f"{label} cannot be blank.")
    return normalized


def _normalize_sha256(value: object, label: str) -> str:
    """Return one lowercase SHA-256 digest."""
    normalized = _normalize_required_text(value, label)
    if _SHA256_PATTERN.fullmatch(normalized) is None:
        raise HybridRetrievalValidationError(f"{label} must be a lowercase SHA-256 digest.")
    return normalized


def _normalize_string_tuple(value: object, label: str) -> tuple[str, ...]:
    """Validate one immutable duplicate-free string tuple."""
    if not isinstance(value, tuple):
        raise HybridRetrievalValidationError(f"{label} must be a tuple.")
    raw = cast(tuple[object, ...], value)
    normalized = tuple(_normalize_required_text(item, f"{label} item") for item in raw)
    if len(set(normalized)) != len(normalized):
        raise HybridRetrievalValidationError(f"{label} cannot contain duplicates.")
    return tuple(sorted(normalized))


def _normalize_case_results(
    value: object,
) -> tuple[HybridSynthesisCaseEvaluation, ...]:
    """Validate runtime case evaluations without weakening public annotations."""
    if not isinstance(value, tuple):
        raise HybridRetrievalValidationError("case_results must be a tuple.")
    raw = cast(tuple[object, ...], value)
    if any(not isinstance(item, HybridSynthesisCaseEvaluation) for item in raw):
        raise HybridRetrievalValidationError(
            "case_results must contain only HybridSynthesisCaseEvaluation values."
        )
    return cast(tuple[HybridSynthesisCaseEvaluation, ...], raw)


def _normalize_measurements(
    value: object,
) -> tuple[HybridMetricMeasurement, ...]:
    """Validate immutable metric measurements at the runtime boundary."""
    if not isinstance(value, tuple):
        raise HybridRetrievalValidationError("measurements must be a tuple.")
    raw = cast(tuple[object, ...], value)
    if any(not isinstance(item, HybridMetricMeasurement) for item in raw):
        raise HybridRetrievalValidationError(
            "measurements must contain only HybridMetricMeasurement values."
        )
    return cast(tuple[HybridMetricMeasurement, ...], raw)


@dataclass(frozen=True, slots=True)
class HybridSynthesisCaseEvaluation:
    """One case-level system observation after bounded synthesis is available."""

    case_id: str
    expected_behavior: HybridExpectedAnswerBehavior
    observed_behavior: HybridExpectedAnswerBehavior
    behavior_correct: bool
    model_required: bool
    model_result_sha256: str | None
    request_sha256: str | None
    structured_fact_correct: bool | None
    semantic_groundedness_correct: bool | None
    citation_correct: bool | None
    cited_chunk_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject internally inconsistent case-level quality observations."""
        object.__setattr__(
            self,
            "case_id",
            _normalize_required_text(self.case_id, "case_id"),
        )
        _require_runtime_instance(
            self.expected_behavior,
            HybridExpectedAnswerBehavior,
            "expected_behavior",
        )
        _require_runtime_instance(
            self.observed_behavior,
            HybridExpectedAnswerBehavior,
            "observed_behavior",
        )
        if self.behavior_correct != (self.expected_behavior is self.observed_behavior):
            raise HybridRetrievalValidationError("behavior_correct is inconsistent.")
        cited = _normalize_string_tuple(self.cited_chunk_ids, "cited_chunk_ids")
        object.__setattr__(self, "cited_chunk_ids", cited)
        if self.model_required:
            if self.model_result_sha256 is None or self.request_sha256 is None:
                raise HybridRetrievalValidationError(
                    "model-required cases must carry request and result identities."
                )
            object.__setattr__(
                self,
                "model_result_sha256",
                _normalize_sha256(self.model_result_sha256, "model_result_sha256"),
            )
            object.__setattr__(
                self,
                "request_sha256",
                _normalize_sha256(self.request_sha256, "request_sha256"),
            )
            if self.semantic_groundedness_correct is None or self.citation_correct is None:
                raise HybridRetrievalValidationError(
                    "model-required cases must expose semantic and citation correctness."
                )
        elif self.model_result_sha256 is not None or self.request_sha256 is not None:
            raise HybridRetrievalValidationError(
                "model-free cases cannot carry model request/result identities."
            )
        if self.semantic_groundedness_correct is None and cited:
            raise HybridRetrievalValidationError(
                "unscored semantic cases cannot carry cited chunk IDs."
            )
        if self.citation_correct is None and cited:
            raise HybridRetrievalValidationError(
                "unscored citation cases cannot carry cited chunk IDs."
            )


@dataclass(frozen=True, slots=True)
class HybridSynthesisBaseline:
    """Independent Gate 8.4 system metrics over the immutable Gate 8.3 dataset."""

    dataset_id: str
    dataset_sha256: str
    case_results: tuple[HybridSynthesisCaseEvaluation, ...]
    measurements: tuple[HybridMetricMeasurement, ...]

    def __post_init__(self) -> None:
        """Preserve independent dimensions and explicit unmeasured semantics."""
        if self.dataset_id != HYBRID_EVALUATION_DATASET_ID:
            raise HybridRetrievalValidationError("synthesis baseline dataset ID is invalid.")
        if self.dataset_sha256 != HYBRID_EVALUATION_DATASET_SHA256:
            raise HybridRetrievalValidationError(
                "synthesis baseline dataset SHA-256 is invalid."
            )
        results = _normalize_case_results(self.case_results)
        if len(results) != 6 or len({item.case_id for item in results}) != 6:
            raise HybridRetrievalValidationError(
                "synthesis baseline requires exactly six unique case results."
            )
        object.__setattr__(self, "case_results", results)
        measurements = _normalize_measurements(self.measurements)
        by_metric = {item.metric: item for item in measurements}
        if len(measurements) != len(HybridMetricDimension) or set(by_metric) != set(
            HybridMetricDimension
        ):
            raise HybridRetrievalValidationError(
                "synthesis baseline must expose every frozen metric exactly once."
            )
        object.__setattr__(self, "measurements", measurements)
        route = by_metric[HybridMetricDimension.ROUTE_ACCURACY]
        if route.status is not HybridMeasurementStatus.MEASURED or route.value is None:
            raise HybridRetrievalValidationError(
                "route_accuracy must remain measured from the frozen offline contract."
            )
        if not math.isfinite(route.value) or not 0.0 <= route.value <= 1.0:
            raise HybridRetrievalValidationError("route_accuracy must be a ratio.")

    def measurement(self, metric: HybridMetricDimension) -> HybridMetricMeasurement:
        """Return one named independent metric without computing a composite score."""
        for item in self.measurements:
            if item.metric is metric:
                return item
        raise HybridRetrievalValidationError(f"metric {metric.value!r} is absent.")
