"""Public domain API for OpsLens semantic-query contracts."""

from opslens.semantic_query.domain.errors import (
    SemanticQueryError,
    SemanticQueryValidationError,
    UnsupportedSemanticQueryError,
)
from opslens.semantic_query.domain.models import (
    ALLOWED_DIMENSIONS,
    ALLOWED_METRICS,
    ALLOWED_ORDER_FIELDS,
    DEFAULT_QUERY_LIMIT,
    MAX_QUERY_LIMIT,
    CompiledAthenaQuery,
    EpssFilters,
    SemanticDimension,
    SemanticMetric,
    SemanticOrderField,
    SemanticQuery,
    SortDirection,
)

__all__ = [
    "ALLOWED_DIMENSIONS",
    "ALLOWED_METRICS",
    "ALLOWED_ORDER_FIELDS",
    "DEFAULT_QUERY_LIMIT",
    "MAX_QUERY_LIMIT",
    "CompiledAthenaQuery",
    "EpssFilters",
    "SemanticDimension",
    "SemanticMetric",
    "SemanticOrderField",
    "SemanticQuery",
    "SemanticQueryError",
    "SemanticQueryValidationError",
    "SortDirection",
    "UnsupportedSemanticQueryError",
]
