"""Tests for the bounded Phase 6 semantic-query planner contract."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import cast

import pytest

from opslens.semantic_query.domain import (
    EpssFilters,
    SemanticDimension,
    SemanticMetric,
    SemanticOrderField,
    SemanticQuery,
    SortDirection,
)
from opslens.semantic_query.planner import (
    BEDROCK_PLANNER_MAX_TOKENS,
    BEDROCK_PLANNER_MODEL_ID,
    BEDROCK_PLANNER_REGION,
    BEDROCK_PLANNER_TEMPERATURE,
    MAX_PLANNER_QUESTION_CHARS,
    PLANNER_OUTPUT_SCHEMA,
    PLANNER_OUTPUT_SCHEMA_JSON,
    PlannedSemanticQuery,
    PlannerContractError,
    PlannerDecision,
    SemanticPlannerRequest,
    UnsupportedPlannerDecision,
    UnsupportedReason,
    build_bedrock_converse_request,
    evaluate_planner_predictions,
    load_planner_eval_cases,
    parse_planner_json,
    parse_planner_payload,
)

_FIXTURE = (
    Path(__file__).parents[2]
    / "fixtures"
    / "semantic_query"
    / "planner_eval_v1.jsonl"
)


def _supported_payload(
    *,
    snapshot_date: str = "2026-09-03",
    minimum_score: float | None = 0.7,
    order_direction: str = "desc",
    limit: int = 20,
) -> dict[str, object]:
    """Build one exact planner payload for focused parser tests."""
    return {
        "decision": "semantic_query",
        "metric": "epss_score",
        "dimensions": ["cve"],
        "filters": {
            "snapshot_date": snapshot_date,
            "minimum_score": minimum_score,
        },
        "order_by": "epss_score",
        "order_direction": order_direction,
        "limit": limit,
    }


def test_planner_request_is_trimmed_and_bounded() -> None:
    """Natural-language input is normalized before any future model call."""
    request = SemanticPlannerRequest("  Which CVEs have EPSS >= 0.7 on 2026-09-03?  ")

    assert request.question == "Which CVEs have EPSS >= 0.7 on 2026-09-03?"

    with pytest.raises(PlannerContractError, match="blank"):
        SemanticPlannerRequest("   ")
    with pytest.raises(PlannerContractError, match="cannot exceed"):
        SemanticPlannerRequest("x" * (MAX_PLANNER_QUESTION_CHARS + 1))


def test_supported_planner_payload_reenters_semantic_query_authority() -> None:
    """A model proposal becomes authoritative only after deterministic construction."""
    outcome = parse_planner_payload(_supported_payload())

    assert isinstance(outcome, PlannedSemanticQuery)
    assert outcome.decision is PlannerDecision.SEMANTIC_QUERY
    assert outcome.query == SemanticQuery(
        metric=SemanticMetric.EPSS_SCORE,
        dimensions=(SemanticDimension.CVE,),
        filters=EpssFilters(
            snapshot_date=date(2026, 9, 3),
            minimum_score=0.7,
        ),
        order_by=SemanticOrderField.EPSS_SCORE,
        order_direction=SortDirection.DESC,
        limit=20,
    )


def test_unsupported_planner_payload_is_explicit_and_typed() -> None:
    """Unsupported questions do not become partial or guessed SemanticQuery objects."""
    outcome = parse_planner_payload(
        {
            "decision": "unsupported",
            "reason": "missing_explicit_snapshot_date",
        }
    )

    assert outcome == UnsupportedPlannerDecision(
        reason=UnsupportedReason.MISSING_EXPLICIT_SNAPSHOT_DATE
    )
    assert outcome.decision is PlannerDecision.UNSUPPORTED


def test_planner_json_parser_rejects_non_json_output() -> None:
    """Prompt-only prose cannot cross the planner boundary."""
    with pytest.raises(PlannerContractError, match="valid JSON"):
        parse_planner_json("not-json")


def test_planner_payload_rejects_extra_or_missing_fields() -> None:
    """Structured output is revalidated even if Bedrock schema enforcement is bypassed."""
    extra = _supported_payload()
    extra["sql"] = "SELECT * FROM anything"

    with pytest.raises(PlannerContractError, match="extra"):
        parse_planner_payload(extra)

    missing = _supported_payload()
    del missing["limit"]
    with pytest.raises(PlannerContractError, match="missing"):
        parse_planner_payload(missing)


@pytest.mark.parametrize("snapshot_date", ["latest", "2026-9-3", "2026-02-30"])
def test_planner_payload_requires_canonical_explicit_date(snapshot_date: str) -> None:
    """Relative, noncanonical, and impossible dates fail closed."""
    with pytest.raises(PlannerContractError, match="snapshot_date"):
        parse_planner_payload(_supported_payload(snapshot_date=snapshot_date))


@pytest.mark.parametrize("minimum_score", [-0.1, 1.01, True])
def test_planner_payload_reuses_epss_score_validation(minimum_score: object) -> None:
    """Bedrock schema cannot express numeric bounds, so application validation remains final."""
    payload = _supported_payload()
    filters = payload["filters"]
    assert isinstance(filters, dict)
    filters["minimum_score"] = minimum_score

    with pytest.raises(PlannerContractError, match=r"minimum_score|SemanticQuery"):
        parse_planner_payload(payload)


@pytest.mark.parametrize("limit", [0, 101, True])
def test_planner_payload_reuses_semantic_limit_validation(limit: object) -> None:
    """The planner cannot increase the already-frozen Athena row authority."""
    payload = _supported_payload()
    payload["limit"] = limit

    with pytest.raises(PlannerContractError, match=r"limit|SemanticQuery"):
        parse_planner_payload(payload)


def test_bedrock_request_builder_is_pure_and_bounded() -> None:
    """Gate 6.3 freezes the Converse request without making a network call."""
    request = SemanticPlannerRequest(
        "Which CVEs have EPSS of at least 0.7 on 2026-09-03?"
    )

    built = build_bedrock_converse_request(request)

    assert BEDROCK_PLANNER_REGION == "us-east-1"
    assert BEDROCK_PLANNER_MODEL_ID == "anthropic.claude-haiku-4-5-20251001-v1:0"
    assert built["modelId"] == BEDROCK_PLANNER_MODEL_ID
    assert built["inferenceConfig"] == {
        "maxTokens": BEDROCK_PLANNER_MAX_TOKENS,
        "temperature": BEDROCK_PLANNER_TEMPERATURE,
    }
    assert built["messages"] == [
        {
            "role": "user",
            "content": [{"text": request.question}],
        }
    ]

    output_config = cast(dict[str, object], built["outputConfig"])
    text_format = cast(dict[str, object], output_config["textFormat"])
    assert text_format["type"] == "json_schema"


def test_bedrock_schema_is_canonical_and_grants_no_sql_field() -> None:
    """The model can emit semantic intent only, never SQL text or identifiers."""
    assert json.dumps(
        PLANNER_OUTPUT_SCHEMA,
        sort_keys=True,
        separators=(",", ":"),
    ) == PLANNER_OUTPUT_SCHEMA_JSON
    assert '"sql"' not in PLANNER_OUTPUT_SCHEMA_JSON.lower()
    assert '"minimum"' not in PLANNER_OUTPUT_SCHEMA_JSON
    assert '"maximum"' not in PLANNER_OUTPUT_SCHEMA_JSON


def test_every_planner_object_schema_disallows_additional_properties() -> None:
    """Every object branch follows Bedrock structured-output restrictions."""
    object_nodes: list[dict[str, object]] = []

    def visit(value: object) -> None:
        if isinstance(value, dict):
            mapping = cast(dict[str, object], value)
            if mapping.get("type") == "object":
                object_nodes.append(mapping)
            for nested in mapping.values():
                visit(nested)
        elif isinstance(value, list):
            for nested in cast(list[object], value):
                visit(nested)

    visit(PLANNER_OUTPUT_SCHEMA)

    assert object_nodes
    assert all(node.get("additionalProperties") is False for node in object_nodes)


def test_golden_planner_dataset_covers_supported_and_fail_closed_cases() -> None:
    """The first evaluation corpus exercises both planning and refusal semantics."""
    cases = load_planner_eval_cases(_FIXTURE)

    assert len(cases) == 18
    assert sum(isinstance(case.expected, PlannedSemanticQuery) for case in cases) == 8
    assert sum(
        isinstance(case.expected, UnsupportedPlannerDecision) for case in cases
    ) == 10


def test_perfect_predictions_score_every_planner_field_separately() -> None:
    """The evaluator reports semantic-field accuracy instead of one opaque score."""
    cases = load_planner_eval_cases(_FIXTURE)
    predictions = {case.case_id: case.expected for case in cases}

    result = evaluate_planner_predictions(cases, predictions)

    assert result.as_dict() == {
        "total_cases": 18,
        "supported_cases": 8,
        "unsupported_cases": 10,
        "decision_accuracy": 1.0,
        "metric_accuracy": 1.0,
        "dimensions_accuracy": 1.0,
        "snapshot_date_accuracy": 1.0,
        "minimum_score_accuracy": 1.0,
        "order_by_accuracy": 1.0,
        "order_direction_accuracy": 1.0,
        "limit_accuracy": 1.0,
        "exact_semantic_query_accuracy": 1.0,
        "unsupported_reason_accuracy": 1.0,
    }


def test_field_mutation_degrades_only_relevant_planner_metrics() -> None:
    """A sort error is visible independently from otherwise-correct semantic fields."""
    cases = load_planner_eval_cases(_FIXTURE)
    predictions = {case.case_id: case.expected for case in cases}

    first_supported = next(
        case for case in cases if isinstance(case.expected, PlannedSemanticQuery)
    )
    expected_outcome = first_supported.expected
    assert isinstance(expected_outcome, PlannedSemanticQuery)
    expected_query = expected_outcome.query
    predictions[first_supported.case_id] = PlannedSemanticQuery(
        SemanticQuery(
            metric=expected_query.metric,
            dimensions=expected_query.dimensions,
            filters=expected_query.filters,
            order_by=expected_query.order_by,
            order_direction=SortDirection.ASC,
            limit=expected_query.limit,
        )
    )

    result = evaluate_planner_predictions(cases, predictions)

    assert result.decision_accuracy == 1.0
    assert result.metric_accuracy == 1.0
    assert result.dimensions_accuracy == 1.0
    assert result.snapshot_date_accuracy == 1.0
    assert result.minimum_score_accuracy == 1.0
    assert result.order_by_accuracy == 1.0
    assert result.limit_accuracy == 1.0
    assert result.order_direction_accuracy == 7 / 8
    assert result.exact_semantic_query_accuracy == 7 / 8


def test_unsupported_reason_accuracy_is_measured_separately() -> None:
    """Fail-closed decision accuracy does not hide a wrong unsupported reason."""
    cases = load_planner_eval_cases(_FIXTURE)
    predictions = {case.case_id: case.expected for case in cases}

    unsupported = next(
        case for case in cases
        if isinstance(case.expected, UnsupportedPlannerDecision)
    )
    predictions[unsupported.case_id] = UnsupportedPlannerDecision(
        UnsupportedReason.AMBIGUOUS
    )

    result = evaluate_planner_predictions(cases, predictions)

    assert result.decision_accuracy == 1.0
    assert result.unsupported_reason_accuracy == 9 / 10


def test_evaluator_requires_exact_prediction_ids() -> None:
    """Missing model observations cannot silently disappear from the evaluation."""
    cases = load_planner_eval_cases(_FIXTURE)
    predictions = {case.case_id: case.expected for case in cases[1:]}

    with pytest.raises(PlannerContractError, match="exactly match"):
        evaluate_planner_predictions(cases, predictions)
