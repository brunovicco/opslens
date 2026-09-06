"""Unit tests for the frozen Phase 8 hybrid evaluation contract."""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from opslens.hybrid_retrieval.application.evaluation import (
    evaluate_hybrid_offline,
    load_hybrid_evaluation_dataset,
    parse_hybrid_evaluation_dataset,
)
from opslens.hybrid_retrieval.domain.errors import HybridRetrievalValidationError
from opslens.hybrid_retrieval.domain.evaluation import (
    HYBRID_EVALUATION_DATASET_ID,
    HYBRID_EVALUATION_DATASET_SHA256,
    HybridEvaluationCaseType,
    HybridExpectedAnswerBehavior,
    HybridExpectedEnvelope,
    HybridMeasurementStatus,
    HybridMetricDimension,
    HybridMetricMeasurement,
    HybridMetricStage,
    HybridMetricUnit,
)
from opslens.hybrid_retrieval.domain.models import HybridRoute

_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "hybrid_retrieval"
    / "golden_hybrid_v1.json"
)


def _dataset():
    """Load the frozen Gate 8.3 fixture through its strict admission boundary."""
    return load_hybrid_evaluation_dataset(_FIXTURE)


def test_frozen_dataset_has_exact_identity_and_required_case_types() -> None:
    """The pre-synthesis dataset cannot drift silently after it is frozen."""
    dataset = _dataset()

    assert dataset.dataset_id == HYBRID_EVALUATION_DATASET_ID
    assert dataset.content_sha256 == HYBRID_EVALUATION_DATASET_SHA256
    assert dataset.dataset_identity == (
        f"{HYBRID_EVALUATION_DATASET_ID}@sha256:{HYBRID_EVALUATION_DATASET_SHA256}"
    )
    assert re.fullmatch(r"[0-9a-f]{64}", dataset.content_sha256)
    assert {case.case_type for case in dataset.cases} == set(HybridEvaluationCaseType)
    assert len(dataset.cases) == 6


def test_metric_dimensions_remain_independent_and_stage_bounded() -> None:
    """No aggregate quality score may hide distinct authority/runtime dimensions."""
    dataset = _dataset()
    specs = {spec.metric: spec for spec in dataset.metric_specs}

    assert set(specs) == set(HybridMetricDimension)
    assert specs[HybridMetricDimension.ROUTE_ACCURACY].stage is (
        HybridMetricStage.GATE_8_3_OFFLINE
    )
    assert specs[HybridMetricDimension.ROUTE_ACCURACY].unit is HybridMetricUnit.RATIO
    assert specs[HybridMetricDimension.STRUCTURED_FACT_CORRECTNESS].stage is (
        HybridMetricStage.GATE_8_4_SYNTHESIS
    )
    assert specs[HybridMetricDimension.SEMANTIC_GROUNDEDNESS].stage is (
        HybridMetricStage.GATE_8_4_SYNTHESIS
    )
    assert specs[HybridMetricDimension.CITATION_CORRECTNESS].stage is (
        HybridMetricStage.GATE_8_4_SYNTHESIS
    )
    assert specs[HybridMetricDimension.ABSTENTION].stage is (
        HybridMetricStage.GATE_8_4_SYNTHESIS
    )
    assert specs[HybridMetricDimension.LATENCY].stage is HybridMetricStage.RUNTIME
    assert specs[HybridMetricDimension.LATENCY].unit is HybridMetricUnit.MILLISECONDS
    assert specs[HybridMetricDimension.COST].stage is HybridMetricStage.RUNTIME
    assert specs[HybridMetricDimension.COST].unit is HybridMetricUnit.USD


def test_offline_baseline_measures_only_legitimate_gate_83_dimensions() -> None:
    """Gate 8.3 measures routing/admission without fabricating synthesis/runtime quality."""
    baseline = evaluate_hybrid_offline(_dataset())
    measurements = {item.metric: item for item in baseline.measurements}

    assert baseline.route_accuracy == 1.0
    assert baseline.evidence_admission_accuracy == 1.0
    assert re.fullmatch(r"[0-9a-f]{64}", baseline.baseline_sha256)

    route = measurements[HybridMetricDimension.ROUTE_ACCURACY]
    assert route.status is HybridMeasurementStatus.MEASURED
    assert route.value == 1.0

    for metric in (
        HybridMetricDimension.STRUCTURED_FACT_CORRECTNESS,
        HybridMetricDimension.SEMANTIC_GROUNDEDNESS,
        HybridMetricDimension.CITATION_CORRECTNESS,
        HybridMetricDimension.ABSTENTION,
        HybridMetricDimension.LATENCY,
        HybridMetricDimension.COST,
    ):
        assert measurements[metric].status is HybridMeasurementStatus.UNMEASURED
        assert measurements[metric].value is None


def test_true_hybrid_case_requires_and_admits_both_evidence_classes() -> None:
    """The positive hybrid fixture crosses both authorities without flattening them."""
    dataset = _dataset()
    case = next(
        item
        for item in dataset.cases
        if item.case_type is HybridEvaluationCaseType.TRUE_HYBRID
    )
    result = next(
        item
        for item in evaluate_hybrid_offline(dataset).case_results
        if item.case_id == case.case_id
    )

    assert case.expected_route is HybridRoute.HYBRID
    assert case.expected_envelope is HybridExpectedEnvelope.ADMIT
    assert case.structured_evidence
    assert case.semantic_evidence
    assert result.observed_route is HybridRoute.HYBRID
    assert result.observed_envelope is HybridExpectedEnvelope.ADMIT
    assert result.envelope_id is not None


def test_partial_structured_case_rejects_before_synthesis() -> None:
    """Class presence cannot hide missing need-level Risk Policy evidence."""
    dataset = _dataset()
    case = next(
        item
        for item in dataset.cases
        if item.case_type is HybridEvaluationCaseType.PARTIAL_STRUCTURED_EVIDENCE
    )
    result = next(
        item
        for item in evaluate_hybrid_offline(dataset).case_results
        if item.case_id == case.case_id
    )

    assert case.expected_route is HybridRoute.STRUCTURED
    assert case.expected_envelope is HybridExpectedEnvelope.REJECT
    assert case.expected_answer_behavior is (
        HybridExpectedAnswerBehavior.REJECT_BEFORE_SYNTHESIS
    )
    assert result.observed_route is HybridRoute.STRUCTURED
    assert result.observed_envelope is HybridExpectedEnvelope.REJECT
    assert result.envelope_id is None


def test_runtime_exposure_case_stays_unsupported_and_abstains() -> None:
    """Repository evidence cannot be relabeled into unavailable runtime authority."""
    dataset = _dataset()
    case = next(
        item
        for item in dataset.cases
        if item.case_type is HybridEvaluationCaseType.UNSUPPORTED_OUT_OF_AUTHORITY
    )
    result = next(
        item
        for item in evaluate_hybrid_offline(dataset).case_results
        if item.case_id == case.case_id
    )

    assert case.expected_route is HybridRoute.UNSUPPORTED
    assert case.expected_envelope is HybridExpectedEnvelope.NOT_APPLICABLE
    assert case.expected_answer_behavior is HybridExpectedAnswerBehavior.ABSTAIN
    assert result.observed_route is HybridRoute.UNSUPPORTED
    assert result.observed_envelope is HybridExpectedEnvelope.NOT_APPLICABLE
    assert result.envelope_id is None


def test_semantic_noise_proves_admission_is_not_groundedness() -> None:
    """A rank-one retrieved neighbor can be admitted yet remain an unsupported target."""
    dataset = _dataset()
    case = next(
        item
        for item in dataset.cases
        if item.case_type is HybridEvaluationCaseType.SEMANTIC_RETRIEVAL_NOISE
    )
    result = next(
        item
        for item in evaluate_hybrid_offline(dataset).case_results
        if item.case_id == case.case_id
    )

    rank_one = min(case.semantic_evidence, key=lambda item: item.rank)
    rank_two = max(case.semantic_evidence, key=lambda item: item.rank)

    assert rank_one.chunk_id not in case.expected_supported_chunk_ids
    assert rank_two.chunk_id in case.expected_supported_chunk_ids
    assert case.expected_citation_chunk_ids == (rank_two.chunk_id,)
    assert result.observed_envelope is HybridExpectedEnvelope.ADMIT


def test_valid_schema_content_tampering_fails_frozen_content_hash() -> None:
    """Even semantically valid edits require a new dataset version/hash."""
    text = _FIXTURE.read_text(encoding="utf-8")
    tampered = text.replace(
        "Which advisory is deterministically confirmed",
        "What advisory is deterministically confirmed",
        1,
    )

    with pytest.raises(
        HybridRetrievalValidationError,
        match="content hash does not match frozen v1",
    ):
        parse_hybrid_evaluation_dataset(tampered)


def test_unknown_root_field_fails_closed_before_evaluation() -> None:
    """The fixture loader rejects silent schema expansion."""
    text = _FIXTURE.read_text(encoding="utf-8")
    tampered = text.replace(
        '"dataset_id":"hybrid-evaluation-golden:v1",',
        '"dataset_id":"hybrid-evaluation-golden:v1","unexpected":true,',
        1,
    )

    with pytest.raises(
        HybridRetrievalValidationError,
        match="fields do not match frozen schema",
    ):
        parse_hybrid_evaluation_dataset(tampered)


def test_unmeasured_cost_cannot_be_fabricated_as_zero() -> None:
    """Absence of runtime execution is UNMEASURED, never a zero-dollar observation."""
    with pytest.raises(
        HybridRetrievalValidationError,
        match="unmeasured metrics cannot carry fabricated values",
    ):
        HybridMetricMeasurement(
            metric=HybridMetricDimension.COST,
            unit=HybridMetricUnit.USD,
            status=HybridMeasurementStatus.UNMEASURED,
            value=0.0,
        )
