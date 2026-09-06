"""Strict loader and offline evaluator for the frozen hybrid evaluation fixture."""

from __future__ import annotations

import json
import math
from enum import StrEnum
from hashlib import sha256
from json import JSONDecodeError
from pathlib import Path
from typing import cast

from opslens.hybrid_retrieval.application.assembly import assemble_hybrid_evidence
from opslens.hybrid_retrieval.application.routing import route_evidence_request
from opslens.hybrid_retrieval.domain.errors import HybridRetrievalValidationError
from opslens.hybrid_retrieval.domain.evaluation import (
    ExpectedStructuredFact,
    HybridEvaluationCase,
    HybridEvaluationCaseType,
    HybridEvaluationDataset,
    HybridExpectedAnswerBehavior,
    HybridExpectedEnvelope,
    HybridMeasurementStatus,
    HybridMetricDimension,
    HybridMetricMeasurement,
    HybridMetricSpec,
    HybridMetricStage,
    HybridMetricUnit,
    HybridOfflineBaseline,
    HybridOfflineCaseResult,
)
from opslens.hybrid_retrieval.domain.evidence import (
    SemanticEvidenceChunk,
    StructuredEvidenceAuthority,
    StructuredEvidenceField,
    StructuredEvidenceRow,
    StructuredScalar,
)
from opslens.hybrid_retrieval.domain.models import (
    EvidenceNeed,
    HybridRoute,
    HybridRoutingRequest,
)

_DATASET_KEYS = frozenset(
    {
        "dataset_id",
        "purpose",
        "authority_boundary",
        "metric_dimensions",
        "cases",
    }
)
_METRIC_KEYS = frozenset({"metric", "stage", "unit"})
_CASE_KEYS = frozenset(
    {
        "case_id",
        "case_type",
        "question",
        "evidence_needs",
        "expected_route",
        "expected_envelope",
        "expected_answer_behavior",
        "structured_evidence",
        "semantic_evidence",
        "expected_structured_facts",
        "expected_supported_chunk_ids",
        "expected_citation_chunk_ids",
    }
)
_STRUCTURED_ROW_KEYS = frozenset(
    {
        "evidence_need",
        "authority",
        "source_artifact_id",
        "source_artifact_sha256",
        "row_key",
        "fields",
    }
)
_FIELD_KEYS = frozenset({"name", "value"})
_SEMANTIC_CHUNK_KEYS = frozenset(
    {
        "retrieval_id",
        "chunk_id",
        "document_id",
        "source_id",
        "source_type",
        "canonical_uri",
        "document_content_sha256",
        "chunk_content_sha256",
        "text",
        "rank",
        "relevance_score",
        "title",
        "section_path",
    }
)


def _require_mapping(value: object, label: str) -> dict[str, object]:
    """Return one string-keyed JSON object or fail closed."""
    if not isinstance(value, dict):
        raise HybridRetrievalValidationError(f"{label} must be an object.")
    raw_mapping = cast(dict[object, object], value)
    if any(not isinstance(key, str) for key in raw_mapping):
        raise HybridRetrievalValidationError(f"{label} keys must be strings.")
    return cast(dict[str, object], raw_mapping)


def _require_exact_keys(
    mapping: dict[str, object],
    expected: frozenset[str],
    label: str,
) -> None:
    """Reject both missing and additional fixture fields."""
    actual = frozenset(mapping)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise HybridRetrievalValidationError(
            f"{label} fields do not match frozen schema; missing={missing}, extra={extra}."
        )


def _require_list(value: object, label: str) -> list[object]:
    """Return one JSON list."""
    if not isinstance(value, list):
        raise HybridRetrievalValidationError(f"{label} must be a list.")
    return cast(list[object], value)


def _require_string(value: object, label: str) -> str:
    """Return one non-empty string."""
    if not isinstance(value, str):
        raise HybridRetrievalValidationError(f"{label} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise HybridRetrievalValidationError(f"{label} cannot be blank.")
    return normalized


def _require_optional_string(value: object, label: str) -> str | None:
    """Return one optional non-empty string."""
    if value is None:
        return None
    return _require_string(value, label)


def _require_int(value: object, label: str) -> int:
    """Return an actual integer, rejecting booleans."""
    if type(value) is not int:
        raise HybridRetrievalValidationError(f"{label} must be an integer.")
    return cast(int, value)


def _require_optional_number(value: object, label: str) -> float | None:
    """Return one finite optional numeric provider observation."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HybridRetrievalValidationError(f"{label} must be numeric or null.")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise HybridRetrievalValidationError(f"{label} must be finite.")
    return normalized


def _parse_structured_scalar(value: object) -> StructuredScalar:
    """Admit only the scalar shape already frozen by Gate 8.2."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise HybridRetrievalValidationError(
        "structured fixture values must be stable JSON scalars."
    )


def _parse_enum[T: StrEnum](enum_type: type[T], value: object, label: str) -> T:
    """Parse one strict string enum value."""
    raw = _require_string(value, label)
    try:
        return enum_type(raw)
    except ValueError as exc:
        raise HybridRetrievalValidationError(
            f"{label} is not recognized by the frozen contract."
        ) from exc


def _parse_string_tuple(value: object, label: str) -> tuple[str, ...]:
    """Parse one duplicate-free list of strings into an immutable tuple."""
    raw = _require_list(value, label)
    normalized = tuple(_require_string(item, f"{label} item") for item in raw)
    if len(set(normalized)) != len(normalized):
        raise HybridRetrievalValidationError(f"{label} cannot contain duplicates.")
    return normalized


def _parse_evidence_needs(value: object) -> tuple[EvidenceNeed, ...]:
    """Parse recognized evidence needs without broadening routing authority."""
    raw = _require_list(value, "evidence_needs")
    needs = tuple(_parse_enum(EvidenceNeed, item, "evidence_need") for item in raw)
    if not needs:
        raise HybridRetrievalValidationError("evidence_needs cannot be empty.")
    if len(set(needs)) != len(needs):
        raise HybridRetrievalValidationError("evidence_needs cannot contain duplicates.")
    return needs


def _parse_field(value: object, label: str) -> StructuredEvidenceField:
    """Parse one canonical structured fixture field."""
    mapping = _require_mapping(value, label)
    _require_exact_keys(mapping, _FIELD_KEYS, label)
    return StructuredEvidenceField(
        name=_require_string(mapping["name"], f"{label}.name"),
        value=_parse_structured_scalar(mapping["value"]),
    )


def _parse_structured_row(value: object, label: str) -> StructuredEvidenceRow:
    """Parse one already-validated structured evidence fixture row."""
    mapping = _require_mapping(value, label)
    _require_exact_keys(mapping, _STRUCTURED_ROW_KEYS, label)
    fields_raw = _require_list(mapping["fields"], f"{label}.fields")
    return StructuredEvidenceRow(
        evidence_need=_parse_enum(
            EvidenceNeed,
            mapping["evidence_need"],
            f"{label}.evidence_need",
        ),
        authority=_parse_enum(
            StructuredEvidenceAuthority,
            mapping["authority"],
            f"{label}.authority",
        ),
        source_artifact_id=_require_string(
            mapping["source_artifact_id"],
            f"{label}.source_artifact_id",
        ),
        source_artifact_sha256=_require_string(
            mapping["source_artifact_sha256"],
            f"{label}.source_artifact_sha256",
        ),
        row_key=_require_string(mapping["row_key"], f"{label}.row_key"),
        fields=tuple(
            _parse_field(item, f"{label}.fields[{index}]")
            for index, item in enumerate(fields_raw)
        ),
    )


def _parse_semantic_chunk(value: object, label: str) -> SemanticEvidenceChunk:
    """Parse one already-admitted semantic fixture chunk."""
    mapping = _require_mapping(value, label)
    _require_exact_keys(mapping, _SEMANTIC_CHUNK_KEYS, label)
    return SemanticEvidenceChunk(
        retrieval_id=_require_string(
            mapping["retrieval_id"],
            f"{label}.retrieval_id",
        ),
        chunk_id=_require_string(mapping["chunk_id"], f"{label}.chunk_id"),
        document_id=_require_string(
            mapping["document_id"],
            f"{label}.document_id",
        ),
        source_id=_require_string(mapping["source_id"], f"{label}.source_id"),
        source_type=_require_string(
            mapping["source_type"],
            f"{label}.source_type",
        ),
        canonical_uri=_require_string(
            mapping["canonical_uri"],
            f"{label}.canonical_uri",
        ),
        document_content_sha256=_require_string(
            mapping["document_content_sha256"],
            f"{label}.document_content_sha256",
        ),
        chunk_content_sha256=_require_string(
            mapping["chunk_content_sha256"],
            f"{label}.chunk_content_sha256",
        ),
        text=_require_string(mapping["text"], f"{label}.text"),
        rank=_require_int(mapping["rank"], f"{label}.rank"),
        relevance_score=_require_optional_number(
            mapping["relevance_score"],
            f"{label}.relevance_score",
        ),
        title=_require_optional_string(mapping["title"], f"{label}.title"),
        section_path=_parse_string_tuple(
            mapping["section_path"],
            f"{label}.section_path",
        ),
    )


def _parse_expected_fact(value: object, label: str) -> ExpectedStructuredFact:
    """Parse one exact structured fact expected from future synthesis."""
    mapping = _require_mapping(value, label)
    _require_exact_keys(mapping, _FIELD_KEYS, label)
    return ExpectedStructuredFact(
        name=_require_string(mapping["name"], f"{label}.name"),
        value=_parse_structured_scalar(mapping["value"]),
    )


def _parse_metric(value: object, index: int) -> HybridMetricSpec:
    """Parse one frozen independent metric dimension."""
    label = f"metric_dimensions[{index}]"
    mapping = _require_mapping(value, label)
    _require_exact_keys(mapping, _METRIC_KEYS, label)
    return HybridMetricSpec(
        metric=_parse_enum(
            HybridMetricDimension,
            mapping["metric"],
            f"{label}.metric",
        ),
        stage=_parse_enum(
            HybridMetricStage,
            mapping["stage"],
            f"{label}.stage",
        ),
        unit=_parse_enum(
            HybridMetricUnit,
            mapping["unit"],
            f"{label}.unit",
        ),
    )


def _parse_case(value: object, index: int) -> HybridEvaluationCase:
    """Parse one frozen evaluation case with exact schema."""
    label = f"cases[{index}]"
    mapping = _require_mapping(value, label)
    _require_exact_keys(mapping, _CASE_KEYS, label)

    structured_raw = _require_list(
        mapping["structured_evidence"],
        f"{label}.structured_evidence",
    )
    semantic_raw = _require_list(
        mapping["semantic_evidence"],
        f"{label}.semantic_evidence",
    )
    facts_raw = _require_list(
        mapping["expected_structured_facts"],
        f"{label}.expected_structured_facts",
    )

    return HybridEvaluationCase(
        case_id=_require_string(mapping["case_id"], f"{label}.case_id"),
        case_type=_parse_enum(
            HybridEvaluationCaseType,
            mapping["case_type"],
            f"{label}.case_type",
        ),
        question=_require_string(mapping["question"], f"{label}.question"),
        evidence_needs=_parse_evidence_needs(mapping["evidence_needs"]),
        expected_route=_parse_enum(
            HybridRoute,
            mapping["expected_route"],
            f"{label}.expected_route",
        ),
        expected_envelope=_parse_enum(
            HybridExpectedEnvelope,
            mapping["expected_envelope"],
            f"{label}.expected_envelope",
        ),
        expected_answer_behavior=_parse_enum(
            HybridExpectedAnswerBehavior,
            mapping["expected_answer_behavior"],
            f"{label}.expected_answer_behavior",
        ),
        structured_evidence=tuple(
            _parse_structured_row(
                item,
                f"{label}.structured_evidence[{item_index}]",
            )
            for item_index, item in enumerate(structured_raw)
        ),
        semantic_evidence=tuple(
            _parse_semantic_chunk(
                item,
                f"{label}.semantic_evidence[{item_index}]",
            )
            for item_index, item in enumerate(semantic_raw)
        ),
        expected_structured_facts=tuple(
            _parse_expected_fact(
                item,
                f"{label}.expected_structured_facts[{item_index}]",
            )
            for item_index, item in enumerate(facts_raw)
        ),
        expected_supported_chunk_ids=_parse_string_tuple(
            mapping["expected_supported_chunk_ids"],
            f"{label}.expected_supported_chunk_ids",
        ),
        expected_citation_chunk_ids=_parse_string_tuple(
            mapping["expected_citation_chunk_ids"],
            f"{label}.expected_citation_chunk_ids",
        ),
    )


def _admit_text(value: object) -> str:
    """Keep runtime text admission explicit under strict static typing."""
    if not isinstance(value, str):
        raise HybridRetrievalValidationError("evaluation fixture text must be a string.")
    return value


def parse_hybrid_evaluation_dataset(text: str) -> HybridEvaluationDataset:
    """Parse and verify the exact content-addressed Gate 8.3 fixture."""
    admitted_text = _admit_text(text)
    try:
        decoded = cast(object, json.loads(admitted_text))
    except JSONDecodeError as exc:
        raise HybridRetrievalValidationError(
            "hybrid evaluation fixture must be valid JSON."
        ) from exc

    root = _require_mapping(decoded, "dataset")
    _require_exact_keys(root, _DATASET_KEYS, "dataset")
    metric_raw = _require_list(root["metric_dimensions"], "metric_dimensions")
    cases_raw = _require_list(root["cases"], "cases")

    canonical = json.dumps(
        root,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    content_sha256 = sha256(canonical.encode("utf-8")).hexdigest()

    return HybridEvaluationDataset(
        dataset_id=_require_string(root["dataset_id"], "dataset_id"),
        purpose=_require_string(root["purpose"], "purpose"),
        authority_boundary=_require_string(
            root["authority_boundary"],
            "authority_boundary",
        ),
        content_sha256=content_sha256,
        metric_specs=tuple(
            _parse_metric(item, index) for index, item in enumerate(metric_raw)
        ),
        cases=tuple(_parse_case(item, index) for index, item in enumerate(cases_raw)),
    )


def _admit_path(value: object) -> Path:
    """Keep runtime path admission explicit under strict static typing."""
    if not isinstance(value, Path):
        raise HybridRetrievalValidationError("evaluation fixture path must be a Path.")
    return value


def load_hybrid_evaluation_dataset(path: Path) -> HybridEvaluationDataset:
    """Load the frozen dataset from one explicit local path."""
    admitted_path = _admit_path(path)
    try:
        text = admitted_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HybridRetrievalValidationError(
            "hybrid evaluation fixture could not be read."
        ) from exc
    return parse_hybrid_evaluation_dataset(text)


def _evaluate_case(case: HybridEvaluationCase) -> HybridOfflineCaseResult:
    """Execute only deterministic routing and evidence admission for one case."""
    decision = route_evidence_request(
        HybridRoutingRequest(evidence_needs=case.evidence_needs)
    )

    envelope_id: str | None = None
    if decision.route is HybridRoute.UNSUPPORTED:
        observed_envelope = HybridExpectedEnvelope.NOT_APPLICABLE
    else:
        try:
            envelope = assemble_hybrid_evidence(
                authority_decision=decision,
                structured_evidence=case.structured_evidence,
                semantic_evidence=case.semantic_evidence,
            )
        except HybridRetrievalValidationError:
            observed_envelope = HybridExpectedEnvelope.REJECT
        else:
            observed_envelope = HybridExpectedEnvelope.ADMIT
            envelope_id = envelope.envelope_id

    return HybridOfflineCaseResult(
        case_id=case.case_id,
        expected_route=case.expected_route,
        observed_route=decision.route,
        route_correct=decision.route is case.expected_route,
        expected_envelope=case.expected_envelope,
        observed_envelope=observed_envelope,
        envelope_correct=observed_envelope is case.expected_envelope,
        envelope_id=envelope_id,
    )


def _admit_dataset(value: object) -> HybridEvaluationDataset:
    """Reject values that bypass the frozen dataset admission boundary."""
    if not isinstance(value, HybridEvaluationDataset):
        raise HybridRetrievalValidationError(
            "dataset must be an admitted HybridEvaluationDataset."
        )
    return value


def evaluate_hybrid_offline(
    dataset: HybridEvaluationDataset,
) -> HybridOfflineBaseline:
    """Measure only pre-synthesis dimensions that Gate 8.3 can actually observe."""
    admitted_dataset = _admit_dataset(dataset)
    results = tuple(_evaluate_case(case) for case in admitted_dataset.cases)
    route_accuracy = sum(item.route_correct for item in results) / len(results)
    evidence_admission_accuracy = (
        sum(item.envelope_correct for item in results) / len(results)
    )

    measurements = tuple(
        HybridMetricMeasurement(
            metric=spec.metric,
            unit=spec.unit,
            status=(
                HybridMeasurementStatus.MEASURED
                if spec.metric is HybridMetricDimension.ROUTE_ACCURACY
                else HybridMeasurementStatus.UNMEASURED
            ),
            value=route_accuracy
            if spec.metric is HybridMetricDimension.ROUTE_ACCURACY
            else None,
        )
        for spec in admitted_dataset.metric_specs
    )

    return HybridOfflineBaseline(
        dataset_id=admitted_dataset.dataset_id,
        dataset_sha256=admitted_dataset.content_sha256,
        case_results=results,
        measurements=measurements,
        evidence_admission_accuracy=evidence_admission_accuracy,
    )
