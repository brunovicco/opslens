"""Typed allowlisted contracts for the first OpsLens semantic-query slice."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from opslens.semantic_query.domain.errors import SemanticQueryValidationError

MAX_QUERY_LIMIT = 100
DEFAULT_QUERY_LIMIT = 20


class SemanticMetric(StrEnum):
    """Metrics exposed by the current semantic-query contract."""

    EPSS_SCORE = "epss_score"


class SemanticDimension(StrEnum):
    """Dimensions exposed by the current semantic-query contract."""

    CVE = "cve"


class SemanticOrderField(StrEnum):
    """Fields that may control deterministic result ordering."""

    EPSS_SCORE = "epss_score"


class SortDirection(StrEnum):
    """Supported deterministic sort directions."""

    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True, slots=True)
class EpssFilters:
    """Strongly typed filters for the first EPSS semantic-query slice."""

    snapshot_date: date
    minimum_score: float | None = None

    def __post_init__(self) -> None:
        """Reject missing, ambiguous, or out-of-range EPSS filter values."""
        if type(self.snapshot_date) is not date:
            raise SemanticQueryValidationError(
                "EPSS snapshot_date must be an explicit calendar date."
            )

        score = self.minimum_score
        if score is None:
            return
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise SemanticQueryValidationError("EPSS minimum_score must be numeric.")

        normalized_score = float(score)
        if not math.isfinite(normalized_score) or not 0.0 <= normalized_score <= 1.0:
            raise SemanticQueryValidationError(
                "EPSS minimum_score must be finite and between 0.0 and 1.0."
            )
        object.__setattr__(self, "minimum_score", normalized_score)


@dataclass(frozen=True, slots=True)
class SemanticQuery:
    """Allowlisted semantic query that contains no arbitrary SQL authority."""

    metric: SemanticMetric
    dimensions: tuple[SemanticDimension, ...]
    filters: EpssFilters
    order_by: SemanticOrderField = SemanticOrderField.EPSS_SCORE
    order_direction: SortDirection = SortDirection.DESC
    limit: int = DEFAULT_QUERY_LIMIT

    def __post_init__(self) -> None:
        """Validate the frozen Phase 6.1 semantic-query surface."""
        if not isinstance(self.metric, SemanticMetric):
            raise SemanticQueryValidationError("Unknown semantic metric.")
        if type(self.dimensions) is not tuple or any(
            not isinstance(dimension, SemanticDimension) for dimension in self.dimensions
        ):
            raise SemanticQueryValidationError("Unknown semantic dimension.")
        if len(set(self.dimensions)) != len(self.dimensions):
            raise SemanticQueryValidationError("Semantic dimensions cannot be duplicated.")
        if not isinstance(self.filters, EpssFilters):
            raise SemanticQueryValidationError("Unsupported semantic filter contract.")
        if not isinstance(self.order_by, SemanticOrderField):
            raise SemanticQueryValidationError("Unknown semantic order field.")
        if not isinstance(self.order_direction, SortDirection):
            raise SemanticQueryValidationError("Unknown semantic sort direction.")
        if type(self.limit) is not int or not 1 <= self.limit <= MAX_QUERY_LIMIT:
            raise SemanticQueryValidationError(
                f"Semantic query limit must be an integer from 1 to {MAX_QUERY_LIMIT}."
            )


@dataclass(frozen=True, slots=True)
class CompiledAthenaQuery:
    """Compiler-owned Athena SQL plus positional execution parameters."""

    sql: str
    execution_parameters: tuple[str, ...]

    def __post_init__(self) -> None:
        """Keep compiler output internally consistent and deterministic."""
        if not self.sql.strip():
            raise SemanticQueryValidationError("Compiled Athena SQL cannot be blank.")
        if self.sql.count("?") != len(self.execution_parameters):
            raise SemanticQueryValidationError(
                "Athena placeholder count must equal the execution-parameter count."
            )
        if any(not parameter.strip() for parameter in self.execution_parameters):
            raise SemanticQueryValidationError("Athena execution parameters cannot be blank.")


ALLOWED_METRICS = frozenset(SemanticMetric)
ALLOWED_DIMENSIONS = frozenset(SemanticDimension)
ALLOWED_ORDER_FIELDS = frozenset(SemanticOrderField)
