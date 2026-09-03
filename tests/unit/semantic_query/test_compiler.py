"""Unit tests for the first deterministic semantic-query compiler slice."""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import cast

import pytest

from opslens.semantic_query.application import compile_semantic_query
from opslens.semantic_query.domain import (
    ALLOWED_DIMENSIONS,
    ALLOWED_METRICS,
    ALLOWED_ORDER_FIELDS,
    MAX_QUERY_LIMIT,
    EpssFilters,
    SemanticDimension,
    SemanticMetric,
    SemanticOrderField,
    SemanticQuery,
    SemanticQueryValidationError,
    SortDirection,
    UnsupportedSemanticQueryError,
)


def _query(
    *,
    snapshot_date: date = date(2026, 9, 3),
    minimum_score: float | None = 0.70,
    order_direction: SortDirection = SortDirection.DESC,
    limit: int = 20,
) -> SemanticQuery:
    """Build one valid query inside the frozen EPSS slice."""
    return SemanticQuery(
        metric=SemanticMetric.EPSS_SCORE,
        dimensions=(SemanticDimension.CVE,),
        filters=EpssFilters(snapshot_date=snapshot_date, minimum_score=minimum_score),
        order_by=SemanticOrderField.EPSS_SCORE,
        order_direction=order_direction,
        limit=limit,
    )


def test_phase_6_1_allowlists_are_deliberately_narrow() -> None:
    """The first contract exposes only the proven EPSS/CVE query surface."""
    assert ALLOWED_METRICS == {SemanticMetric.EPSS_SCORE}
    assert ALLOWED_DIMENSIONS == {SemanticDimension.CVE}
    assert ALLOWED_ORDER_FIELDS == {SemanticOrderField.EPSS_SCORE}
    assert MAX_QUERY_LIMIT == 100


def test_compiler_emits_only_owned_identifiers_and_positional_parameters() -> None:
    """The first factual question compiles to fixed SQL plus literal parameters."""
    compiled = compile_semantic_query(_query())

    assert compiled.sql == (
        'SELECT "cve", "epss"\n'
        'FROM "opslens_dev"."epss_scores"\n'
        'WHERE "snapshot_date" = ? AND "epss" >= ?\n'
        'ORDER BY "epss" DESC, "cve" ASC\n'
        "LIMIT 20"
    )
    assert compiled.execution_parameters == ("'2026-09-03'", "0.7")


def test_minimum_score_is_optional_but_snapshot_date_is_always_present() -> None:
    """A bounded snapshot query may omit the threshold without implying latest data."""
    compiled = compile_semantic_query(_query(minimum_score=None))

    assert compiled.sql == (
        'SELECT "cve", "epss"\n'
        'FROM "opslens_dev"."epss_scores"\n'
        'WHERE "snapshot_date" = ?\n'
        'ORDER BY "epss" DESC, "cve" ASC\n'
        "LIMIT 20"
    )
    assert compiled.execution_parameters == ("'2026-09-03'",)


def test_same_semantic_query_always_compiles_to_same_output() -> None:
    """Compiler output is reproducible for identical typed evidence."""
    first = compile_semantic_query(_query())
    second = compile_semantic_query(_query())

    assert first == second


def test_ascending_order_remains_allowlisted_and_has_stable_cve_tie_breaker() -> None:
    """Only the direction varies; the compiler still owns the order expression."""
    compiled = compile_semantic_query(_query(order_direction=SortDirection.ASC))

    assert 'ORDER BY "epss" ASC, "cve" ASC' in compiled.sql


@pytest.mark.parametrize("limit", [0, 101, -1])
def test_limit_outside_policy_bounds_fails_closed(limit: int) -> None:
    """Queries cannot expand beyond the Phase 6.1 row bound."""
    with pytest.raises(SemanticQueryValidationError, match="limit"):
        _query(limit=limit)


def test_boolean_or_text_limit_cannot_become_sql() -> None:
    """Runtime values that merely resemble integers are rejected."""
    for value in (cast(int, True), cast(int, "20; DROP TABLE epss_scores")):
        with pytest.raises(SemanticQueryValidationError, match="limit"):
            _query(limit=value)


@pytest.mark.parametrize("score", [-0.01, 1.01, math.inf, -math.inf, math.nan])
def test_invalid_epss_threshold_fails_closed(score: float) -> None:
    """EPSS thresholds must preserve the source score domain."""
    with pytest.raises(SemanticQueryValidationError, match="minimum_score"):
        EpssFilters(snapshot_date=date(2026, 9, 3), minimum_score=score)


def test_text_epss_threshold_cannot_become_an_execution_parameter() -> None:
    """A malicious threshold-shaped string is rejected before compilation."""
    with pytest.raises(SemanticQueryValidationError, match="minimum_score"):
        EpssFilters(
            snapshot_date=date(2026, 9, 3),
            minimum_score=cast(float, "0.7 OR 1=1"),
        )


def test_snapshot_date_requires_an_explicit_calendar_date() -> None:
    """Datetime/latest-style ambiguity does not enter the first contract."""
    with pytest.raises(SemanticQueryValidationError, match="snapshot_date"):
        EpssFilters(
            snapshot_date=cast(date, datetime(2026, 9, 3, 12, 0)),
            minimum_score=0.7,
        )


def test_unknown_metric_fails_before_sql_compilation() -> None:
    """Raw model text cannot create a metric or inject SQL syntax."""
    with pytest.raises(SemanticQueryValidationError, match="metric"):
        SemanticQuery(
            metric=cast(SemanticMetric, "epss_score; DROP TABLE epss_scores"),
            dimensions=(SemanticDimension.CVE,),
            filters=EpssFilters(snapshot_date=date(2026, 9, 3)),
        )


def test_unknown_dimension_fails_before_sql_compilation() -> None:
    """Raw identifiers are not accepted as semantic dimensions."""
    with pytest.raises(SemanticQueryValidationError, match="dimension"):
        SemanticQuery(
            metric=SemanticMetric.EPSS_SCORE,
            dimensions=cast(tuple[SemanticDimension, ...], ("cve, secret_column",)),
            filters=EpssFilters(snapshot_date=date(2026, 9, 3)),
        )


def test_valid_but_unsupported_dimension_shape_fails_closed_in_compiler() -> None:
    """A typed query still needs an explicitly implemented compiler branch."""
    query = SemanticQuery(
        metric=SemanticMetric.EPSS_SCORE,
        dimensions=(),
        filters=EpssFilters(snapshot_date=date(2026, 9, 3)),
    )

    with pytest.raises(UnsupportedSemanticQueryError, match="cve dimension"):
        compile_semantic_query(query)


def test_unknown_sort_direction_fails_before_sql_compilation() -> None:
    """ORDER BY never accepts free-form direction text."""
    with pytest.raises(SemanticQueryValidationError, match="sort direction"):
        SemanticQuery(
            metric=SemanticMetric.EPSS_SCORE,
            dimensions=(SemanticDimension.CVE,),
            filters=EpssFilters(snapshot_date=date(2026, 9, 3)),
            order_direction=cast(SortDirection, "DESC; DROP TABLE epss_scores"),
        )
