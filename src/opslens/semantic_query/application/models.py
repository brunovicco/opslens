"""Application result models for bounded semantic-query execution."""

from __future__ import annotations

from dataclasses import dataclass

from opslens.semantic_query.domain import SemanticQueryResultError


@dataclass(frozen=True, slots=True)
class AthenaQueryResult:
    """Structured evidence returned by one successful bounded Athena execution."""

    query_execution_id: str
    columns: tuple[str, ...]
    rows: tuple[tuple[str | None, ...], ...]
    data_scanned_bytes: int
    engine_execution_time_ms: int | None = None
    total_execution_time_ms: int | None = None

    def __post_init__(self) -> None:
        """Reject malformed execution evidence instead of normalizing it silently."""
        if not self.query_execution_id.strip():
            raise SemanticQueryResultError("Athena query_execution_id cannot be blank.")
        if not self.columns or any(not column.strip() for column in self.columns):
            raise SemanticQueryResultError("Athena result columns must be explicit.")
        if len(set(self.columns)) != len(self.columns):
            raise SemanticQueryResultError("Athena result columns cannot be duplicated.")
        if any(len(row) != len(self.columns) for row in self.rows):
            raise SemanticQueryResultError(
                "Athena result rows must match the declared column width."
            )
        if type(self.data_scanned_bytes) is not int or self.data_scanned_bytes < 0:
            raise SemanticQueryResultError("Athena data_scanned_bytes must be non-negative.")
        for field_name, value in (
            ("engine_execution_time_ms", self.engine_execution_time_ms),
            ("total_execution_time_ms", self.total_execution_time_ms),
        ):
            if value is not None and (type(value) is not int or value < 0):
                raise SemanticQueryResultError(
                    f"Athena {field_name} must be a non-negative integer when present."
                )
