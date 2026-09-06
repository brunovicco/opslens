"""Deterministic Gate 7.5 golden retrieval evaluation contracts and metrics."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from opslens.knowledge_retrieval.application.retrieval_catalog import (
    CanonicalRetrievalCatalog,
)

_DATASET_ID = "knowledge-retrieval-golden:v1"
_EXPECTED_CASE_COUNT = 10
_EXPECTED_POSITIVE_CASE_COUNT = 8
_EXPECTED_NEGATIVE_CASE_COUNT = 2
_EVALUATION_CUTOFFS = (1, 3, 5, 10)


class RetrievalEvaluationError(ValueError):
    """Raised when frozen evaluation evidence cannot be admitted safely."""


class RetrievalEvaluationIncompleteError(RetrievalEvaluationError):
    """Raised when provider/runtime failures prevent a complete metric baseline."""


def _require_trimmed(value: object, *, field: str, max_length: int = 4096) -> str:
    """Require one trimmed non-empty bounded string."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise RetrievalEvaluationError(f"{field} must be one trimmed non-empty string")
    if len(value) > max_length:
        raise RetrievalEvaluationError(f"{field} must be at most {max_length} characters")
    return value


def _require_bool(value: object, *, field: str) -> bool:
    """Require an actual JSON boolean rather than truthy/falsy coercion."""
    if type(value) is not bool:
        raise RetrievalEvaluationError(f"{field} must be a boolean")
    return value


def _require_nonnegative_int(value: object, *, field: str) -> int:
    """Require one non-negative non-boolean integer."""
    if type(value) is not int or value < 0:
        raise RetrievalEvaluationError(f"{field} must be a non-negative integer")
    return value


def _require_optional_score(value: object) -> float | None:
    """Require one absent or finite numeric provider relevance score."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RetrievalEvaluationError("relevance_score must be numeric")
    score = float(value)
    if not math.isfinite(score):
        raise RetrievalEvaluationError("relevance_score must be finite")
    return score


def _require_string_tuple(
    value: object,
    *,
    field: str,
    allow_empty: bool,
) -> tuple[str, ...]:
    """Require one JSON array containing unique trimmed strings."""
    if not isinstance(value, list):
        raise RetrievalEvaluationError(f"{field} must be a JSON array")
    raw = cast(list[object], value)
    items = tuple(_require_trimmed(item, field=field) for item in raw)
    if not allow_empty and not items:
        raise RetrievalEvaluationError(f"{field} must not be empty")
    if len(set(items)) != len(items):
        raise RetrievalEvaluationError(f"{field} values must be unique")
    return items


def _require_exact_keys(
    value: dict[str, object],
    *,
    expected: set[str],
    field: str,
) -> None:
    """Reject both missing and unreviewed fixture fields."""
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise RetrievalEvaluationError(
            f"{field} keys must match frozen schema; missing={missing}, unknown={unknown}"
        )


def _require_object(value: object, *, field: str) -> dict[str, object]:
    """Require one JSON object through an explicit typing boundary."""
    if not isinstance(value, dict):
        raise RetrievalEvaluationError(f"{field} must be a JSON object")
    raw = cast(dict[object, object], value)
    if any(not isinstance(key, str) for key in raw):
        raise RetrievalEvaluationError(f"{field} keys must be strings")
    return cast(dict[str, object], raw)


@dataclass(frozen=True, slots=True)
class GoldenRetrievalCase:
    """One frozen question and its explanatory/remediation relevance labels."""

    case_id: str
    question: str
    relevant_document_ids: tuple[str, ...]
    relevant_chunk_ids: tuple[str, ...]
    expected_source_types: tuple[str, ...]
    should_have_relevant_evidence: bool

    def __post_init__(self) -> None:
        """Enforce positive/negative label consistency."""
        object.__setattr__(self, "case_id", _require_trimmed(self.case_id, field="case_id"))
        object.__setattr__(
            self,
            "question",
            _require_trimmed(self.question, field="question", max_length=1000),
        )
        if self.should_have_relevant_evidence:
            if not self.relevant_document_ids or not self.relevant_chunk_ids:
                raise RetrievalEvaluationError(
                    "positive cases require document and chunk relevance labels"
                )
            if not self.expected_source_types:
                raise RetrievalEvaluationError(
                    "positive cases require expected source types"
                )
        elif (
            self.relevant_document_ids
            or self.relevant_chunk_ids
            or self.expected_source_types
        ):
            raise RetrievalEvaluationError(
                "negative cases must not contain relevance or source labels"
            )


def _require_golden_cases(value: object) -> tuple[GoldenRetrievalCase, ...]:
    """Require one tuple containing only typed golden retrieval cases."""
    if not isinstance(value, tuple):
        raise RetrievalEvaluationError("dataset cases must be a tuple")
    items = cast(tuple[object, ...], value)
    if any(not isinstance(item, GoldenRetrievalCase) for item in items):
        raise RetrievalEvaluationError(
            "dataset cases must contain only GoldenRetrievalCase values"
        )
    return cast(tuple[GoldenRetrievalCase, ...], items)


@dataclass(frozen=True, slots=True)
class GoldenRetrievalDataset:
    """Frozen Gate 7.5 evaluation dataset."""

    dataset_id: str
    cases: tuple[GoldenRetrievalCase, ...]

    def __post_init__(self) -> None:
        """Require the exact v1 case cardinality and unique identities."""
        if self.dataset_id != _DATASET_ID:
            raise RetrievalEvaluationError(f"dataset_id must equal {_DATASET_ID!r}")
        cases = _require_golden_cases(self.cases)
        object.__setattr__(self, "cases", cases)
        if len(cases) != _EXPECTED_CASE_COUNT:
            raise RetrievalEvaluationError(
                f"dataset must contain exactly {_EXPECTED_CASE_COUNT} cases"
            )
        ids = tuple(case.case_id for case in cases)
        if len(set(ids)) != len(ids):
            raise RetrievalEvaluationError("dataset case_id values must be unique")
        positive = sum(case.should_have_relevant_evidence for case in cases)
        if positive != _EXPECTED_POSITIVE_CASE_COUNT:
            raise RetrievalEvaluationError(
                f"dataset must contain exactly {_EXPECTED_POSITIVE_CASE_COUNT} positive cases"
            )
        if len(cases) - positive != _EXPECTED_NEGATIVE_CASE_COUNT:
            raise RetrievalEvaluationError(
                f"dataset must contain exactly {_EXPECTED_NEGATIVE_CASE_COUNT} negative cases"
            )


def load_golden_retrieval_dataset(path: Path) -> GoldenRetrievalDataset:
    """Load the exact checked Gate 7.1 golden fixture without silent schema drift."""
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RetrievalEvaluationError(f"could not read retrieval fixture {path}") from exc
    try:
        parsed = cast(object, json.loads(raw_text))
    except json.JSONDecodeError as exc:
        raise RetrievalEvaluationError("retrieval fixture must contain valid JSON") from exc
    root = _require_object(parsed, field="retrieval fixture")
    _require_exact_keys(
        root,
        expected={
            "dataset_id",
            "purpose",
            "authority_boundary",
            "corpus_status",
            "cases",
        },
        field="retrieval fixture",
    )
    dataset_id = _require_trimmed(root["dataset_id"], field="dataset_id")
    _require_trimmed(root["purpose"], field="purpose")
    _require_trimmed(root["authority_boundary"], field="authority_boundary")
    if root["corpus_status"] != "planned_for_gate_7_2":
        raise RetrievalEvaluationError(
            "corpus_status must match the frozen v1 fixture value"
        )
    raw_cases = root["cases"]
    if not isinstance(raw_cases, list):
        raise RetrievalEvaluationError("cases must be a JSON array")

    cases: list[GoldenRetrievalCase] = []
    for index, raw_case in enumerate(cast(list[object], raw_cases)):
        case = _require_object(raw_case, field=f"case {index}")
        _require_exact_keys(
            case,
            expected={
                "case_id",
                "question",
                "relevant_document_ids",
                "relevant_chunk_ids",
                "expected_source_types",
                "should_have_relevant_evidence",
            },
            field=f"case {index}",
        )
        positive = _require_bool(
            case["should_have_relevant_evidence"],
            field=f"case {index} should_have_relevant_evidence",
        )
        cases.append(
            GoldenRetrievalCase(
                case_id=_require_trimmed(case["case_id"], field=f"case {index} case_id"),
                question=_require_trimmed(
                    case["question"],
                    field=f"case {index} question",
                    max_length=1000,
                ),
                relevant_document_ids=_require_string_tuple(
                    case["relevant_document_ids"],
                    field=f"case {index} relevant_document_ids",
                    allow_empty=not positive,
                ),
                relevant_chunk_ids=_require_string_tuple(
                    case["relevant_chunk_ids"],
                    field=f"case {index} relevant_chunk_ids",
                    allow_empty=not positive,
                ),
                expected_source_types=_require_string_tuple(
                    case["expected_source_types"],
                    field=f"case {index} expected_source_types",
                    allow_empty=not positive,
                ),
                should_have_relevant_evidence=positive,
            )
        )
    return GoldenRetrievalDataset(dataset_id=dataset_id, cases=tuple(cases))


def validate_dataset_catalog(
    dataset: GoldenRetrievalDataset,
    catalog: CanonicalRetrievalCatalog,
) -> None:
    """Require every positive label to resolve to the checked canonical corpus."""
    catalog_by_id = {chunk.chunk_id: chunk for chunk in catalog.chunks}
    for case in dataset.cases:
        for chunk_id in case.relevant_chunk_ids:
            canonical = catalog_by_id.get(chunk_id)
            if canonical is None:
                raise RetrievalEvaluationError(
                    f"case {case.case_id!r} references an unknown canonical chunk"
                )
            if canonical.document_id not in case.relevant_document_ids:
                raise RetrievalEvaluationError(
                    f"case {case.case_id!r} chunk/document labels disagree"
                )
            if canonical.source_type.value not in case.expected_source_types:
                raise RetrievalEvaluationError(
                    f"case {case.case_id!r} chunk/source-type labels disagree"
                )


@dataclass(frozen=True, slots=True)
class RankedEvaluationChunk:
    """Content-free canonical evidence for one admitted ranked result."""

    chunk_id: str
    document_id: str
    source_type: str
    relevance_score: float | None = None

    def __post_init__(self) -> None:
        """Validate bounded ranked evidence primitives."""
        object.__setattr__(self, "chunk_id", _require_trimmed(self.chunk_id, field="chunk_id"))
        object.__setattr__(
            self,
            "document_id",
            _require_trimmed(self.document_id, field="document_id"),
        )
        object.__setattr__(
            self,
            "source_type",
            _require_trimmed(self.source_type, field="source_type"),
        )
        object.__setattr__(
            self,
            "relevance_score",
            _require_optional_score(self.relevance_score),
        )


def _require_ranked_chunks(value: object) -> tuple[RankedEvaluationChunk, ...]:
    """Require one bounded tuple of admitted ranked evaluation chunks."""
    if not isinstance(value, tuple):
        raise RetrievalEvaluationError("returned_chunks must be a tuple")
    items = cast(tuple[object, ...], value)
    if any(not isinstance(item, RankedEvaluationChunk) for item in items):
        raise RetrievalEvaluationError(
            "returned_chunks must contain only RankedEvaluationChunk values"
        )
    if len(items) > 10:
        raise RetrievalEvaluationError("returned_chunks must contain at most 10 results")
    return cast(tuple[RankedEvaluationChunk, ...], items)


@dataclass(frozen=True, slots=True)
class RetrievalCaseObservation:
    """Content-free evidence for exactly one real or synthetic fixture execution."""

    case_id: str
    returned_chunks: tuple[RankedEvaluationChunk, ...]
    client_elapsed_ms: int
    provider_request_id: str
    retry_attempts: int
    failure_category: str | None = None

    def __post_init__(self) -> None:
        """Require bounded unique ranked output or one explicit failure category."""
        object.__setattr__(self, "case_id", _require_trimmed(self.case_id, field="case_id"))
        returned_chunks = _require_ranked_chunks(self.returned_chunks)
        object.__setattr__(self, "returned_chunks", returned_chunks)
        object.__setattr__(
            self,
            "client_elapsed_ms",
            _require_nonnegative_int(self.client_elapsed_ms, field="client_elapsed_ms"),
        )
        object.__setattr__(
            self,
            "retry_attempts",
            _require_nonnegative_int(self.retry_attempts, field="retry_attempts"),
        )
        if self.failure_category is None:
            object.__setattr__(
                self,
                "provider_request_id",
                _require_trimmed(self.provider_request_id, field="provider_request_id"),
            )
        else:
            object.__setattr__(
                self,
                "failure_category",
                _require_trimmed(self.failure_category, field="failure_category"),
            )
            if returned_chunks:
                raise RetrievalEvaluationError(
                    "failed observations must not contain admitted returned chunks"
                )
        ids = tuple(chunk.chunk_id for chunk in returned_chunks)
        if len(set(ids)) != len(ids):
            raise RetrievalEvaluationError("returned chunk identities must be unique")


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationSummary:
    """Deterministic aggregate metrics over one complete golden dataset execution."""

    dataset_id: str
    case_count: int
    positive_case_count: int
    negative_case_count: int
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    recall_at_10: float
    mean_reciprocal_rank: float
    relevant_hit_count: int
    relevant_hit_provenance_correct_count: int
    relevant_hit_provenance_correct_rate: float
    negative_nonempty_retrieval_rate: float
    negative_rank1_scores: tuple[float, ...]
    latency_min_ms: int
    latency_max_ms: int
    latency_mean_ms: float
    latency_p50_ms: int
    latency_p95_ms: int
    total_retry_attempts: int


def _nearest_rank(values: tuple[int, ...], percentile: float) -> int:
    """Return the frozen nearest-rank percentile over non-empty integer evidence."""
    if not values:
        raise RetrievalEvaluationError("percentile evidence must not be empty")
    ordered = tuple(sorted(values))
    rank = math.ceil(percentile * len(ordered))
    return ordered[rank - 1]


def aggregate_retrieval_evaluation(
    dataset: GoldenRetrievalDataset,
    catalog: CanonicalRetrievalCatalog,
    observations: tuple[RetrievalCaseObservation, ...],
) -> RetrievalEvaluationSummary:
    """Compute Gate 7.5 metrics without converting runtime failures into misses."""
    validate_dataset_catalog(dataset, catalog)
    if len(observations) != len(dataset.cases):
        raise RetrievalEvaluationError("observation count must equal dataset case count")
    by_case = {observation.case_id: observation for observation in observations}
    if len(by_case) != len(observations):
        raise RetrievalEvaluationError("observations must contain unique case IDs")
    expected_ids = {case.case_id for case in dataset.cases}
    if set(by_case) != expected_ids:
        raise RetrievalEvaluationError("observation case IDs must exactly match the dataset")

    failed = tuple(
        observation
        for observation in observations
        if observation.failure_category is not None
    )
    if failed:
        raise RetrievalEvaluationIncompleteError(
            "runtime/provider failures prevent complete retrieval metric aggregation"
        )

    catalog_by_id = {chunk.chunk_id: chunk for chunk in catalog.chunks}
    recall_hits = dict.fromkeys(_EVALUATION_CUTOFFS, 0)
    reciprocal_ranks: list[float] = []
    relevant_hit_count = 0
    provenance_correct_count = 0
    negative_nonempty = 0
    negative_rank1_scores: list[float] = []

    positives = tuple(case for case in dataset.cases if case.should_have_relevant_evidence)
    negatives = tuple(case for case in dataset.cases if not case.should_have_relevant_evidence)

    for case in dataset.cases:
        observation = by_case[case.case_id]
        for result in observation.returned_chunks:
            canonical = catalog_by_id.get(result.chunk_id)
            if canonical is None:
                raise RetrievalEvaluationError(
                    "observation contains a chunk outside checked canonical corpus"
                )
            if (
                result.document_id != canonical.document_id
                or result.source_type != canonical.source_type.value
            ):
                raise RetrievalEvaluationError(
                    "observation provenance disagrees with checked canonical corpus"
                )

        if case.should_have_relevant_evidence:
            first_relevant_rank: int | None = None
            for rank, result in enumerate(observation.returned_chunks, start=1):
                if result.chunk_id not in case.relevant_chunk_ids:
                    continue
                relevant_hit_count += 1
                if (
                    result.document_id in case.relevant_document_ids
                    and result.source_type in case.expected_source_types
                ):
                    provenance_correct_count += 1
                if first_relevant_rank is None:
                    first_relevant_rank = rank
            for cutoff in _EVALUATION_CUTOFFS:
                if first_relevant_rank is not None and first_relevant_rank <= cutoff:
                    recall_hits[cutoff] += 1
            reciprocal_ranks.append(
                0.0 if first_relevant_rank is None else 1.0 / first_relevant_rank
            )
        elif observation.returned_chunks:
            negative_nonempty += 1
            rank1_score = observation.returned_chunks[0].relevance_score
            if rank1_score is not None:
                negative_rank1_scores.append(rank1_score)

    latencies = tuple(observation.client_elapsed_ms for observation in observations)
    return RetrievalEvaluationSummary(
        dataset_id=dataset.dataset_id,
        case_count=len(dataset.cases),
        positive_case_count=len(positives),
        negative_case_count=len(negatives),
        recall_at_1=recall_hits[1] / len(positives),
        recall_at_3=recall_hits[3] / len(positives),
        recall_at_5=recall_hits[5] / len(positives),
        recall_at_10=recall_hits[10] / len(positives),
        mean_reciprocal_rank=sum(reciprocal_ranks) / len(reciprocal_ranks),
        relevant_hit_count=relevant_hit_count,
        relevant_hit_provenance_correct_count=provenance_correct_count,
        relevant_hit_provenance_correct_rate=(
            1.0 if relevant_hit_count == 0 else provenance_correct_count / relevant_hit_count
        ),
        negative_nonempty_retrieval_rate=negative_nonempty / len(negatives),
        negative_rank1_scores=tuple(negative_rank1_scores),
        latency_min_ms=min(latencies),
        latency_max_ms=max(latencies),
        latency_mean_ms=sum(latencies) / len(latencies),
        latency_p50_ms=_nearest_rank(latencies, 0.50),
        latency_p95_ms=_nearest_rank(latencies, 0.95),
        total_retry_attempts=sum(observation.retry_attempts for observation in observations),
    )
