"""Deterministic parser from planner JSON into the existing SemanticQuery authority."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import date
from enum import StrEnum
from typing import TypeVar, cast

from opslens.semantic_query.domain import (
    EpssFilters,
    SemanticDimension,
    SemanticMetric,
    SemanticOrderField,
    SemanticQuery,
    SemanticQueryError,
    SortDirection,
)
from opslens.semantic_query.planner.models import (
    PlannedSemanticQuery,
    PlannerContractError,
    PlannerDecision,
    PlannerOutcome,
    UnsupportedPlannerDecision,
    UnsupportedReason,
)

_EnumT = TypeVar("_EnumT", bound=StrEnum)

_SEMANTIC_QUERY_KEYS = frozenset(
    {
        "decision",
        "metric",
        "dimensions",
        "filters",
        "order_by",
        "order_direction",
        "limit",
    }
)
_FILTER_KEYS = frozenset({"snapshot_date", "minimum_score"})
_UNSUPPORTED_KEYS = frozenset({"decision", "reason"})


def parse_planner_json(text: str) -> PlannerOutcome:
    """Parse one JSON model output and revalidate it through deterministic code."""
    if not isinstance(text, str) or not text.strip():
        raise PlannerContractError("Planner output must be non-empty JSON text.")

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PlannerContractError("Planner output is not valid JSON.") from exc

    return parse_planner_payload(payload)


def parse_planner_payload(payload: object) -> PlannerOutcome:
    """Parse one decoded planner payload and enforce exact cross-field semantics."""
    mapping = _as_mapping(payload, context="Planner output")
    decision = _enum_value(
        PlannerDecision,
        mapping.get("decision"),
        field="decision",
    )

    if decision is PlannerDecision.SEMANTIC_QUERY:
        return _parse_semantic_query(mapping)
    if decision is PlannerDecision.UNSUPPORTED:
        return _parse_unsupported(mapping)

    raise PlannerContractError("Unknown planner decision.")


def _parse_semantic_query(mapping: Mapping[str, object]) -> PlannedSemanticQuery:
    """Build the existing SemanticQuery type from one exact planner proposal."""
    _require_exact_keys(mapping, _SEMANTIC_QUERY_KEYS, context="semantic_query decision")

    metric = _enum_value(SemanticMetric, mapping["metric"], field="metric")
    dimensions_raw = _as_sequence(mapping["dimensions"], context="dimensions")
    dimensions = tuple(
        _enum_value(SemanticDimension, item, field="dimensions item")
        for item in dimensions_raw
    )
    if dimensions != (SemanticDimension.CVE,):
        raise PlannerContractError(
            "The first planner slice requires exactly the cve dimension."
        )

    filters_raw = _as_mapping(mapping["filters"], context="filters")
    _require_exact_keys(filters_raw, _FILTER_KEYS, context="filters")
    snapshot_date = _parse_explicit_date(filters_raw["snapshot_date"])

    minimum_score = filters_raw["minimum_score"]
    if minimum_score is not None and (
        isinstance(minimum_score, bool) or not isinstance(minimum_score, (int, float))
    ):
        raise PlannerContractError("minimum_score must be a number or null.")

    order_by = _enum_value(
        SemanticOrderField,
        mapping["order_by"],
        field="order_by",
    )
    order_direction = _enum_value(
        SortDirection,
        mapping["order_direction"],
        field="order_direction",
    )
    limit = mapping["limit"]
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise PlannerContractError("limit must be an integer.")

    try:
        query = SemanticQuery(
            metric=metric,
            dimensions=dimensions,
            filters=EpssFilters(
                snapshot_date=snapshot_date,
                minimum_score=minimum_score,
            ),
            order_by=order_by,
            order_direction=order_direction,
            limit=limit,
        )
    except SemanticQueryError as exc:
        raise PlannerContractError(
            f"Planner proposal violates SemanticQuery: {exc}"
        ) from exc

    return PlannedSemanticQuery(query=query)


def _parse_unsupported(mapping: Mapping[str, object]) -> UnsupportedPlannerDecision:
    """Parse one explicit fail-closed planner outcome."""
    _require_exact_keys(mapping, _UNSUPPORTED_KEYS, context="unsupported decision")
    reason = _enum_value(
        UnsupportedReason,
        mapping["reason"],
        field="reason",
    )
    return UnsupportedPlannerDecision(reason=reason)


def _parse_explicit_date(value: object) -> date:
    """Accept only canonical ISO calendar dates, never relative temporal language."""
    if not isinstance(value, str):
        raise PlannerContractError("snapshot_date must be an ISO calendar date.")

    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise PlannerContractError(
            "snapshot_date must be an explicit ISO calendar date."
        ) from exc

    if parsed.isoformat() != value:
        raise PlannerContractError("snapshot_date must use canonical YYYY-MM-DD form.")
    return parsed


def _enum_value(
    enum_type: type[_EnumT],
    value: object,
    *,
    field: str,
) -> _EnumT:
    """Convert one string to an allowlisted enum without leaking ValueError semantics."""
    if not isinstance(value, str):
        raise PlannerContractError(f"{field} must be a string.")
    try:
        return enum_type(value)
    except ValueError as exc:
        raise PlannerContractError(f"Unsupported planner value for {field}.") from exc


def _as_mapping(value: object, *, context: str) -> Mapping[str, object]:
    """Validate one decoded JSON object."""
    if not isinstance(value, Mapping):
        raise PlannerContractError(f"{context} must be an object.")
    return cast(Mapping[str, object], value)


def _as_sequence(value: object, *, context: str) -> tuple[object, ...]:
    """Validate one decoded JSON array without accepting strings."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise PlannerContractError(f"{context} must be an array.")
    return tuple(cast(Sequence[object], value))


def _require_exact_keys(
    mapping: Mapping[str, object],
    expected: frozenset[str],
    *,
    context: str,
) -> None:
    """Reject missing or additional fields even if an upstream schema is bypassed."""
    actual = frozenset(mapping)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise PlannerContractError(
            f"{context} fields must match the frozen contract; "
            f"missing={missing}, extra={extra}."
        )
