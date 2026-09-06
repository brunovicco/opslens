"""Frozen evaluation contracts for Phase 8 hybrid retrieval."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import cast

from opslens.hybrid_retrieval.domain.errors import HybridRetrievalValidationError
from opslens.hybrid_retrieval.domain.evidence import (
    SemanticEvidenceChunk,
    StructuredEvidenceField,
    StructuredEvidenceRow,
    StructuredScalar,
)
from opslens.hybrid_retrieval.domain.models import EvidenceNeed, HybridRoute

HYBRID_EVALUATION_DATASET_ID = "hybrid-evaluation-golden:v1"
HYBRID_EVALUATION_DATASET_SHA256 = (
    "68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1"
)


class HybridEvaluationCaseType(StrEnum):
    """Required scenario classes frozen before hybrid synthesis exists."""

    STRUCTURED_ONLY_FACTUAL = "structured_only_factual"
    SEMANTIC_ONLY_REMEDIATION = "semantic_only_remediation"
    TRUE_HYBRID = "true_hybrid"
    UNSUPPORTED_OUT_OF_AUTHORITY = "unsupported_out_of_authority"
    PARTIAL_STRUCTURED_EVIDENCE = "partial_structured_evidence"
    SEMANTIC_RETRIEVAL_NOISE = "semantic_retrieval_noise"


class HybridExpectedEnvelope(StrEnum):
    """Expected deterministic evidence-envelope outcome for one fixture case."""

    ADMIT = "admit"
    REJECT = "reject"
    NOT_APPLICABLE = "not_applicable"


class HybridExpectedAnswerBehavior(StrEnum):
    """Expected downstream behavior frozen before Gate 8.4 synthesis."""

    ANSWER = "answer"
    ABSTAIN = "abstain"
    REJECT_BEFORE_SYNTHESIS = "reject_before_synthesis"


class HybridMetricDimension(StrEnum):
    """Independent quality/runtime dimensions frozen by Gate 8.3."""

    ROUTE_ACCURACY = "route_accuracy"
    STRUCTURED_FACT_CORRECTNESS = "structured_fact_correctness"
    SEMANTIC_GROUNDEDNESS = "semantic_groundedness"
    CITATION_CORRECTNESS = "citation_correctness"
    ABSTENTION = "abstention"
    LATENCY = "latency"
    COST = "cost"


class HybridMetricStage(StrEnum):
    """Earliest stage at which a frozen metric is legitimately measurable."""

    GATE_8_3_OFFLINE = "gate_8_3_offline"
    GATE_8_4_SYNTHESIS = "gate_8_4_synthesis"
    RUNTIME = "runtime"


class HybridMetricUnit(StrEnum):
    """Units kept separate so unlike metrics cannot be collapsed silently."""

    RATIO = "ratio"
    MILLISECONDS = "milliseconds"
    USD = "usd"


class HybridMeasurementStatus(StrEnum):
    """Whether one frozen metric has actually been measured."""

    MEASURED = "measured"
    UNMEASURED = "unmeasured"


_REQUIRED_CASE_TYPES = frozenset(HybridEvaluationCaseType)
_EXPECTED_METRIC_SHAPE: dict[
    HybridMetricDimension, tuple[HybridMetricStage, HybridMetricUnit]
] = {
    HybridMetricDimension.ROUTE_ACCURACY: (
        HybridMetricStage.GATE_8_3_OFFLINE,
        HybridMetricUnit.RATIO,
    ),
    HybridMetricDimension.STRUCTURED_FACT_CORRECTNESS: (
        HybridMetricStage.GATE_8_4_SYNTHESIS,
        HybridMetricUnit.RATIO,
    ),
    HybridMetricDimension.SEMANTIC_GROUNDEDNESS: (
        HybridMetricStage.GATE_8_4_SYNTHESIS,
        HybridMetricUnit.RATIO,
    ),
    HybridMetricDimension.CITATION_CORRECTNESS: (
        HybridMetricStage.GATE_8_4_SYNTHESIS,
        HybridMetricUnit.RATIO,
    ),
    HybridMetricDimension.ABSTENTION: (
        HybridMetricStage.GATE_8_4_SYNTHESIS,
        HybridMetricUnit.RATIO,
    ),
    HybridMetricDimension.LATENCY: (
        HybridMetricStage.RUNTIME,
        HybridMetricUnit.MILLISECONDS,
    ),
    HybridMetricDimension.COST: (
        HybridMetricStage.RUNTIME,
        HybridMetricUnit.USD,
    ),
}


def _require_runtime_instance(
    value: object,
    expected_type: type[object],
    label: str,
) -> None:
    """Validate runtime values without weakening public type annotations."""
    if not isinstance(value, expected_type):
        raise HybridRetrievalValidationError(f"{label} has an unsupported value.")


def _require_tuple_of[T](
    value: object,
    expected_type: type[T],
    label: str,
) -> tuple[T, ...]:
    """Return an immutable tuple whose members have one exact runtime contract."""
    if not isinstance(value, tuple):
        raise HybridRetrievalValidationError(f"{label} must be a tuple.")
    raw = cast(tuple[object, ...], value)
    if any(not isinstance(item, expected_type) for item in raw):
        raise HybridRetrievalValidationError(
            f"{label} contains a value outside its frozen contract."
        )
    return cast(tuple[T, ...], raw)


def _normalize_required_text(value: object, label: str) -> str:
    """Return one non-empty stripped string."""
    if not isinstance(value, str):
        raise HybridRetrievalValidationError(f"{label} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise HybridRetrievalValidationError(f"{label} cannot be blank.")
    return normalized


def _normalize_string_tuple(value: object, label: str) -> tuple[str, ...]:
    """Validate one duplicate-free tuple of non-empty strings."""
    raw = _require_tuple_of(value, str, label)
    normalized = tuple(_normalize_required_text(item, f"{label} item") for item in raw)
    if len(set(normalized)) != len(normalized):
        raise HybridRetrievalValidationError(f"{label} cannot contain duplicates.")
    return normalized


def _normalize_evidence_needs(value: object) -> tuple[EvidenceNeed, ...]:
    """Validate and canonically order one evidence-need tuple."""
    typed = _require_tuple_of(value, EvidenceNeed, "evidence_needs")
    if not typed:
        raise HybridRetrievalValidationError("evidence_needs cannot be empty.")
    if len(set(typed)) != len(typed):
        raise HybridRetrievalValidationError("evidence_needs cannot contain duplicates.")
    return tuple(sorted(typed, key=lambda item: item.value))


def _scalar_identity(value: StructuredScalar) -> tuple[str, StructuredScalar]:
    """Keep bool/int and other scalar identities distinct during fixture validation."""
    return (type(value).__name__, value)


def _canonical_sha256(payload: object) -> str:
    """Return SHA-256 for one canonical JSON payload."""
    canonical = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class HybridMetricSpec:
    """One frozen metric dimension with an explicit stage and unit."""

    metric: HybridMetricDimension
    stage: HybridMetricStage
    unit: HybridMetricUnit

    def __post_init__(self) -> None:
        """Reject metric/stage/unit combinations outside the frozen v1 contract."""
        _require_runtime_instance(self.metric, HybridMetricDimension, "metric")
        _require_runtime_instance(self.stage, HybridMetricStage, "stage")
        _require_runtime_instance(self.unit, HybridMetricUnit, "unit")
        if _EXPECTED_METRIC_SHAPE.get(self.metric) != (self.stage, self.unit):
            raise HybridRetrievalValidationError(
                "metric stage/unit does not match the frozen hybrid evaluation contract."
            )


@dataclass(frozen=True, slots=True)
class ExpectedStructuredFact:
    """One exact structured fact later synthesis must preserve."""

    name: str
    value: StructuredScalar

    def __post_init__(self) -> None:
        """Reuse the structured evidence scalar contract for expected facts."""
        normalized = StructuredEvidenceField(name=self.name, value=self.value)
        object.__setattr__(self, "name", normalized.name)
        object.__setattr__(self, "value", normalized.value)


@dataclass(frozen=True, slots=True)
class HybridEvaluationCase:
    """One frozen pre-synthesis hybrid evaluation case."""

    case_id: str
    case_type: HybridEvaluationCaseType
    question: str
    evidence_needs: tuple[EvidenceNeed, ...]
    expected_route: HybridRoute
    expected_envelope: HybridExpectedEnvelope
    expected_answer_behavior: HybridExpectedAnswerBehavior
    structured_evidence: tuple[StructuredEvidenceRow, ...]
    semantic_evidence: tuple[SemanticEvidenceChunk, ...]
    expected_structured_facts: tuple[ExpectedStructuredFact, ...]
    expected_supported_chunk_ids: tuple[str, ...]
    expected_citation_chunk_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """Freeze fixture invariants without evaluating implementation behavior."""
        object.__setattr__(
            self,
            "case_id",
            _normalize_required_text(self.case_id, "case_id"),
        )
        object.__setattr__(
            self,
            "question",
            _normalize_required_text(self.question, "question"),
        )
        _require_runtime_instance(self.case_type, HybridEvaluationCaseType, "case_type")
        _require_runtime_instance(self.expected_route, HybridRoute, "expected_route")
        _require_runtime_instance(
            self.expected_envelope,
            HybridExpectedEnvelope,
            "expected_envelope",
        )
        _require_runtime_instance(
            self.expected_answer_behavior,
            HybridExpectedAnswerBehavior,
            "expected_answer_behavior",
        )

        object.__setattr__(
            self,
            "evidence_needs",
            _normalize_evidence_needs(self.evidence_needs),
        )
        structured = _require_tuple_of(
            self.structured_evidence,
            StructuredEvidenceRow,
            "structured_evidence",
        )
        semantic = _require_tuple_of(
            self.semantic_evidence,
            SemanticEvidenceChunk,
            "semantic_evidence",
        )
        facts = _require_tuple_of(
            self.expected_structured_facts,
            ExpectedStructuredFact,
            "expected_structured_facts",
        )
        object.__setattr__(self, "structured_evidence", structured)
        object.__setattr__(self, "semantic_evidence", semantic)
        object.__setattr__(self, "expected_structured_facts", facts)

        supported_ids = _normalize_string_tuple(
            self.expected_supported_chunk_ids,
            "expected_supported_chunk_ids",
        )
        citation_ids = _normalize_string_tuple(
            self.expected_citation_chunk_ids,
            "expected_citation_chunk_ids",
        )
        object.__setattr__(self, "expected_supported_chunk_ids", supported_ids)
        object.__setattr__(self, "expected_citation_chunk_ids", citation_ids)

        semantic_chunk_ids = {item.chunk_id for item in semantic}
        if not set(supported_ids).issubset(semantic_chunk_ids):
            raise HybridRetrievalValidationError(
                "expected supported chunks must exist in semantic fixture evidence."
            )
        if not set(citation_ids).issubset(set(supported_ids)):
            raise HybridRetrievalValidationError(
                "expected citation chunks must be a subset of supported semantic chunks."
            )

        available_facts = {
            (field.name, _scalar_identity(field.value))
            for row in structured
            for field in row.fields
        }
        for expected_fact in facts:
            candidate = (expected_fact.name, _scalar_identity(expected_fact.value))
            if candidate not in available_facts:
                raise HybridRetrievalValidationError(
                    "expected structured fact must exist in fixture structured evidence."
                )

        self._validate_case_type_contract()

    def _validate_case_type_contract(self) -> None:
        """Enforce scenario semantics frozen for the six-case v1 dataset."""
        if self.case_type is HybridEvaluationCaseType.STRUCTURED_ONLY_FACTUAL and (
            self.expected_route is not HybridRoute.STRUCTURED
            or self.expected_envelope is not HybridExpectedEnvelope.ADMIT
            or self.expected_answer_behavior is not HybridExpectedAnswerBehavior.ANSWER
            or not self.structured_evidence
            or bool(self.semantic_evidence)
        ):
            raise HybridRetrievalValidationError(
                "structured-only case must admit structured evidence and answer."
            )

        if self.case_type is HybridEvaluationCaseType.SEMANTIC_ONLY_REMEDIATION and (
            self.expected_route is not HybridRoute.SEMANTIC
            or self.expected_envelope is not HybridExpectedEnvelope.ADMIT
            or self.expected_answer_behavior is not HybridExpectedAnswerBehavior.ANSWER
            or bool(self.structured_evidence)
            or not self.semantic_evidence
        ):
            raise HybridRetrievalValidationError(
                "semantic-only case must admit semantic evidence and answer."
            )

        if self.case_type is HybridEvaluationCaseType.TRUE_HYBRID and (
            self.expected_route is not HybridRoute.HYBRID
            or self.expected_envelope is not HybridExpectedEnvelope.ADMIT
            or self.expected_answer_behavior is not HybridExpectedAnswerBehavior.ANSWER
            or not self.structured_evidence
            or not self.semantic_evidence
        ):
            raise HybridRetrievalValidationError(
                "true-hybrid case must admit both evidence classes and answer."
            )

        if self.case_type is HybridEvaluationCaseType.UNSUPPORTED_OUT_OF_AUTHORITY and (
            self.expected_route is not HybridRoute.UNSUPPORTED
            or self.expected_envelope is not HybridExpectedEnvelope.NOT_APPLICABLE
            or self.expected_answer_behavior is not HybridExpectedAnswerBehavior.ABSTAIN
            or bool(self.structured_evidence)
            or bool(self.semantic_evidence)
        ):
            raise HybridRetrievalValidationError(
                "unsupported fixture case must abstain with no evidence envelope."
            )

        if self.case_type is HybridEvaluationCaseType.PARTIAL_STRUCTURED_EVIDENCE and (
            self.expected_route is not HybridRoute.STRUCTURED
            or self.expected_envelope is not HybridExpectedEnvelope.REJECT
            or self.expected_answer_behavior
            is not HybridExpectedAnswerBehavior.REJECT_BEFORE_SYNTHESIS
            or not self.structured_evidence
            or bool(self.semantic_evidence)
        ):
            raise HybridRetrievalValidationError(
                "partial structured case must reject before synthesis."
            )

        if self.case_type is HybridEvaluationCaseType.SEMANTIC_RETRIEVAL_NOISE:
            self._validate_semantic_noise_case()

    def _validate_semantic_noise_case(self) -> None:
        """Require admitted noise to remain distinct from support/citation targets."""
        if (
            self.expected_route is not HybridRoute.SEMANTIC
            or self.expected_envelope is not HybridExpectedEnvelope.ADMIT
            or self.expected_answer_behavior is not HybridExpectedAnswerBehavior.ANSWER
            or bool(self.structured_evidence)
            or len(self.semantic_evidence) < 2
            or not self.expected_supported_chunk_ids
        ):
            raise HybridRetrievalValidationError(
                "semantic-noise case must admit multiple semantic chunks and answer."
            )
        rank_one = min(self.semantic_evidence, key=lambda item: item.rank)
        if rank_one.chunk_id in self.expected_supported_chunk_ids:
            raise HybridRetrievalValidationError(
                "semantic-noise case must preserve a non-supporting rank-one chunk."
            )


@dataclass(frozen=True, slots=True)
class HybridEvaluationDataset:
    """Frozen typed dataset identity used before any Gate 8.4 tuning."""

    dataset_id: str
    purpose: str
    authority_boundary: str
    content_sha256: str
    metric_specs: tuple[HybridMetricSpec, ...]
    cases: tuple[HybridEvaluationCase, ...]

    def __post_init__(self) -> None:
        """Require exact v1 case/metric coverage and frozen content identity."""
        if self.dataset_id != HYBRID_EVALUATION_DATASET_ID:
            raise HybridRetrievalValidationError("unexpected hybrid evaluation dataset ID.")
        object.__setattr__(
            self,
            "purpose",
            _normalize_required_text(self.purpose, "purpose"),
        )
        object.__setattr__(
            self,
            "authority_boundary",
            _normalize_required_text(self.authority_boundary, "authority_boundary"),
        )
        if self.content_sha256 != HYBRID_EVALUATION_DATASET_SHA256:
            raise HybridRetrievalValidationError(
                "hybrid evaluation fixture content hash does not match frozen v1."
            )

        specs = _require_tuple_of(self.metric_specs, HybridMetricSpec, "metric_specs")
        object.__setattr__(self, "metric_specs", specs)
        metrics = tuple(item.metric for item in specs)
        if len(set(metrics)) != len(metrics) or set(metrics) != set(
            _EXPECTED_METRIC_SHAPE
        ):
            raise HybridRetrievalValidationError(
                "hybrid evaluation dataset must contain every frozen metric exactly once."
            )

        cases = _require_tuple_of(self.cases, HybridEvaluationCase, "cases")
        object.__setattr__(self, "cases", cases)
        case_ids = tuple(item.case_id for item in cases)
        if len(set(case_ids)) != len(case_ids):
            raise HybridRetrievalValidationError(
                "hybrid evaluation case IDs must be unique."
            )
        case_types = tuple(item.case_type for item in cases)
        if (
            len(case_types) != len(_REQUIRED_CASE_TYPES)
            or len(set(case_types)) != len(case_types)
            or set(case_types) != set(_REQUIRED_CASE_TYPES)
        ):
            raise HybridRetrievalValidationError(
                "hybrid evaluation v1 requires exactly one case of each frozen case type."
            )

    @property
    def dataset_identity(self) -> str:
        """Return the content-addressed frozen dataset identifier."""
        return f"{self.dataset_id}@sha256:{self.content_sha256}"


@dataclass(frozen=True, slots=True)
class HybridMetricMeasurement:
    """One independent metric observation without composite-score laundering."""

    metric: HybridMetricDimension
    unit: HybridMetricUnit
    status: HybridMeasurementStatus
    value: float | None

    def __post_init__(self) -> None:
        """Reject unit drift and fabricated values for unmeasured metrics."""
        _require_runtime_instance(self.metric, HybridMetricDimension, "metric")
        _require_runtime_instance(self.unit, HybridMetricUnit, "unit")
        _require_runtime_instance(self.status, HybridMeasurementStatus, "status")
        if self.unit is not _EXPECTED_METRIC_SHAPE[self.metric][1]:
            raise HybridRetrievalValidationError("metric measurement unit is inconsistent.")
        if self.status is HybridMeasurementStatus.UNMEASURED:
            if self.value is not None:
                raise HybridRetrievalValidationError(
                    "unmeasured metrics cannot carry fabricated values."
                )
            return
        if self.value is None or not math.isfinite(self.value):
            raise HybridRetrievalValidationError(
                "measured metrics require one finite numeric value."
            )
        if self.unit is HybridMetricUnit.RATIO and not 0.0 <= self.value <= 1.0:
            raise HybridRetrievalValidationError(
                "ratio measurements must be between zero and one."
            )
        if self.unit is not HybridMetricUnit.RATIO and self.value < 0.0:
            raise HybridRetrievalValidationError(
                "latency/cost measurements cannot be negative."
            )


@dataclass(frozen=True, slots=True)
class HybridOfflineCaseResult:
    """Deterministic Gate 8.3 observation for routing and envelope admission."""

    case_id: str
    expected_route: HybridRoute
    observed_route: HybridRoute
    route_correct: bool
    expected_envelope: HybridExpectedEnvelope
    observed_envelope: HybridExpectedEnvelope
    envelope_correct: bool
    envelope_id: str | None

    def __post_init__(self) -> None:
        """Validate result consistency without interpreting model behavior."""
        object.__setattr__(
            self,
            "case_id",
            _normalize_required_text(self.case_id, "case_id"),
        )
        _require_runtime_instance(self.expected_route, HybridRoute, "expected_route")
        _require_runtime_instance(self.observed_route, HybridRoute, "observed_route")
        _require_runtime_instance(
            self.expected_envelope,
            HybridExpectedEnvelope,
            "expected_envelope",
        )
        _require_runtime_instance(
            self.observed_envelope,
            HybridExpectedEnvelope,
            "observed_envelope",
        )
        if self.route_correct != (self.expected_route is self.observed_route):
            raise HybridRetrievalValidationError("route_correct is inconsistent.")
        if self.envelope_correct != (
            self.expected_envelope is self.observed_envelope
        ):
            raise HybridRetrievalValidationError("envelope_correct is inconsistent.")
        if self.observed_envelope is HybridExpectedEnvelope.ADMIT:
            if self.envelope_id is None:
                raise HybridRetrievalValidationError(
                    "admitted envelope results require an envelope ID."
                )
        elif self.envelope_id is not None:
            raise HybridRetrievalValidationError(
                "rejected/not-applicable results cannot carry an envelope ID."
            )


@dataclass(frozen=True, slots=True)
class HybridOfflineBaseline:
    """Offline pre-synthesis baseline over the frozen Gate 8.3 dataset."""

    dataset_id: str
    dataset_sha256: str
    case_results: tuple[HybridOfflineCaseResult, ...]
    measurements: tuple[HybridMetricMeasurement, ...]
    evidence_admission_accuracy: float

    def __post_init__(self) -> None:
        """Keep measured and intentionally unmeasured dimensions explicit."""
        if self.dataset_id != HYBRID_EVALUATION_DATASET_ID:
            raise HybridRetrievalValidationError("offline baseline dataset ID is invalid.")
        if self.dataset_sha256 != HYBRID_EVALUATION_DATASET_SHA256:
            raise HybridRetrievalValidationError("offline baseline dataset hash is invalid.")

        results = _require_tuple_of(
            self.case_results,
            HybridOfflineCaseResult,
            "case_results",
        )
        object.__setattr__(self, "case_results", results)
        if not results:
            raise HybridRetrievalValidationError("offline baseline requires case results.")
        if len({item.case_id for item in results}) != len(results):
            raise HybridRetrievalValidationError(
                "offline baseline case results must be unique."
            )
        if not math.isfinite(self.evidence_admission_accuracy) or not (
            0.0 <= self.evidence_admission_accuracy <= 1.0
        ):
            raise HybridRetrievalValidationError(
                "evidence_admission_accuracy must be between zero and one."
            )

        measurements = _require_tuple_of(
            self.measurements,
            HybridMetricMeasurement,
            "measurements",
        )
        object.__setattr__(self, "measurements", measurements)
        by_metric = {item.metric: item for item in measurements}
        if (
            len(measurements) != len(_EXPECTED_METRIC_SHAPE)
            or set(by_metric) != set(_EXPECTED_METRIC_SHAPE)
        ):
            raise HybridRetrievalValidationError(
                "offline baseline must expose every frozen metric exactly once."
            )

        route = by_metric[HybridMetricDimension.ROUTE_ACCURACY]
        if route.status is not HybridMeasurementStatus.MEASURED or route.value is None:
            raise HybridRetrievalValidationError(
                "route_accuracy must be measured in Gate 8.3."
            )
        expected_route_accuracy = sum(item.route_correct for item in results) / len(results)
        if route.value != expected_route_accuracy:
            raise HybridRetrievalValidationError(
                "route_accuracy must equal the deterministic case-result ratio."
            )
        expected_admission_accuracy = sum(item.envelope_correct for item in results) / len(
            results
        )
        if self.evidence_admission_accuracy != expected_admission_accuracy:
            raise HybridRetrievalValidationError(
                "evidence_admission_accuracy must equal the case-result ratio."
            )

        for metric, measurement in by_metric.items():
            if metric is HybridMetricDimension.ROUTE_ACCURACY:
                continue
            if (
                measurement.status is not HybridMeasurementStatus.UNMEASURED
                or measurement.value is not None
            ):
                raise HybridRetrievalValidationError(
                    "pre-synthesis quality/runtime metrics must remain explicitly unmeasured."
                )

    @property
    def route_accuracy(self) -> float:
        """Return the one response metric legitimately measured in Gate 8.3."""
        for measurement in self.measurements:
            if measurement.metric is HybridMetricDimension.ROUTE_ACCURACY:
                if measurement.value is None:
                    raise HybridRetrievalValidationError(
                        "route_accuracy measurement unexpectedly missing."
                    )
                return measurement.value
        raise HybridRetrievalValidationError("route_accuracy measurement is absent.")

    @property
    def baseline_sha256(self) -> str:
        """Return deterministic identity for this offline evaluation observation."""
        return _canonical_sha256(
            {
                "case_results": [
                    {
                        "case_id": item.case_id,
                        "envelope_correct": item.envelope_correct,
                        "envelope_id": item.envelope_id,
                        "expected_envelope": item.expected_envelope.value,
                        "expected_route": item.expected_route.value,
                        "observed_envelope": item.observed_envelope.value,
                        "observed_route": item.observed_route.value,
                        "route_correct": item.route_correct,
                    }
                    for item in self.case_results
                ],
                "dataset_id": self.dataset_id,
                "dataset_sha256": self.dataset_sha256,
                "evidence_admission_accuracy": self.evidence_admission_accuracy,
                "measurements": [
                    {
                        "metric": item.metric.value,
                        "status": item.status.value,
                        "unit": item.unit.value,
                        "value": item.value,
                    }
                    for item in self.measurements
                ],
            }
        )
