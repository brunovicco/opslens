"""Deterministic SQL compiler for allowlisted semantic queries."""

from __future__ import annotations

from opslens.semantic_query.domain import (
    CompiledAthenaQuery,
    SemanticDimension,
    SemanticMetric,
    SemanticOrderField,
    SemanticQuery,
    SortDirection,
    UnsupportedSemanticQueryError,
)

_EPSS_TABLE = '"opslens_dev"."epss_scores"'


def compile_semantic_query(query: SemanticQuery) -> CompiledAthenaQuery:
    """Compile one supported semantic query into compiler-owned Athena SQL.

    User/model output never supplies SQL identifiers or SQL fragments. The compiler
    owns the database, table, selected columns, predicates, ordering, and LIMIT shape.
    Only already-validated literal filter values become positional Athena execution
    parameters.
    """
    if query.metric is not SemanticMetric.EPSS_SCORE:
        raise UnsupportedSemanticQueryError("Only the epss_score metric is supported.")
    if query.dimensions != (SemanticDimension.CVE,):
        raise UnsupportedSemanticQueryError(
            "The epss_score slice requires exactly the cve dimension."
        )
    if query.order_by is not SemanticOrderField.EPSS_SCORE:
        raise UnsupportedSemanticQueryError(
            "The epss_score slice can only order by epss_score."
        )

    direction = _compile_sort_direction(query.order_direction)
    predicates = ['"snapshot_date" = ?']
    execution_parameters = [_athena_string_literal(query.filters.snapshot_date.isoformat())]

    if query.filters.minimum_score is not None:
        predicates.append('"epss" >= ?')
        execution_parameters.append(_athena_numeric_literal(query.filters.minimum_score))

    sql = "\n".join(
        [
            'SELECT "cve", "epss"',
            f"FROM {_EPSS_TABLE}",
            f"WHERE {' AND '.join(predicates)}",
            f'ORDER BY "epss" {direction}, "cve" ASC',
            f"LIMIT {query.limit}",
        ]
    )

    return CompiledAthenaQuery(
        sql=sql,
        execution_parameters=tuple(execution_parameters),
    )


def _compile_sort_direction(direction: SortDirection) -> str:
    """Translate an allowlisted direction into a compiler-owned SQL keyword."""
    if direction is SortDirection.ASC:
        return "ASC"
    if direction is SortDirection.DESC:
        return "DESC"
    raise UnsupportedSemanticQueryError("Unsupported semantic sort direction.")


def _athena_string_literal(value: str) -> str:
    """Render one validated value as an Athena string execution parameter."""
    return "'" + value.replace("'", "''") + "'"


def _athena_numeric_literal(value: float) -> str:
    """Render one validated finite numeric value deterministically."""
    return repr(value)
