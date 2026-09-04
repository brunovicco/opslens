"""Bounded Amazon Athena adapter for compiler-owned semantic queries."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from typing import Protocol, cast

from opslens.semantic_query.application.models import AthenaQueryResult
from opslens.semantic_query.domain import (
    CompiledAthenaQuery,
    SemanticQueryExecutionError,
    SemanticQueryResultError,
    SemanticQueryTimeoutError,
)

ATHENA_DATABASE = "opslens_dev"
ATHENA_WORKGROUP = "opslens-dev"
_EPSS_RELATION = '"opslens_dev"."epss_scores"'
_TERMINAL_STATES = frozenset({"SUCCEEDED", "FAILED", "CANCELLED"})
_ACTIVE_STATES = frozenset({"QUEUED", "RUNNING"})


class AthenaQueryClient(Protocol):
    """Define only the Athena API operations required by the first query slice."""

    def start_query_execution(
        self,
        *,
        QueryString: str,
        QueryExecutionContext: Mapping[str, str],
        WorkGroup: str,
        ExecutionParameters: Sequence[str],
    ) -> Mapping[str, object]:
        """Start one parameterized Athena query."""
        ...

    def get_query_execution(
        self,
        *,
        QueryExecutionId: str,
    ) -> Mapping[str, object]:
        """Return status and statistics for one Athena query execution."""
        ...

    def get_query_results(
        self,
        *,
        QueryExecutionId: str,
        MaxResults: int,
    ) -> Mapping[str, object]:
        """Return one bounded page of Athena query results."""
        ...

    def stop_query_execution(
        self,
        *,
        QueryExecutionId: str,
    ) -> Mapping[str, object]:
        """Request cancellation for an Athena query execution."""
        ...


class AthenaQueryExecutor:
    """Execute compiler-owned SELECT statements in the fixed OpsLens dev workgroup."""

    def __init__(
        self,
        client: AthenaQueryClient,
        *,
        poll_interval_seconds: float = 1.0,
        max_poll_attempts: int = 60,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        """Initialize a bounded synchronous Athena executor.

        Args:
            client: Minimal Athena client implementation.
            poll_interval_seconds: Delay between non-terminal status checks.
            max_poll_attempts: Maximum status checks before cancellation.
            sleeper: Injected sleep function for deterministic tests.
        """
        if poll_interval_seconds < 0:
            raise ValueError("Athena poll interval cannot be negative.")
        if max_poll_attempts < 1:
            raise ValueError("Athena max poll attempts must be at least 1.")

        self._client = client
        self._poll_interval_seconds = poll_interval_seconds
        self._max_poll_attempts = max_poll_attempts
        self._sleeper = sleeper

    def execute(
        self,
        query: CompiledAthenaQuery,
        *,
        max_rows: int,
    ) -> AthenaQueryResult:
        """Run one bounded, compiler-owned query and return execution evidence.

        The adapter fixes both the Glue database and Athena workgroup. It accepts no
        user/model-selected database, workgroup, table, column, or SQL fragment.
        """
        if type(max_rows) is not int or not 1 <= max_rows <= 100:
            raise SemanticQueryExecutionError(
                "Athena result bound must be an integer from 1 to 100."
            )
        self._assert_read_only_compiled_shape(query)

        start_response = self._client.start_query_execution(
            QueryString=query.sql,
            QueryExecutionContext={"Database": ATHENA_DATABASE},
            WorkGroup=ATHENA_WORKGROUP,
            ExecutionParameters=query.execution_parameters,
        )
        query_execution_id = _required_string(
            start_response,
            "QueryExecutionId",
            context="StartQueryExecution response",
        )

        execution = self._wait_for_terminal_state(query_execution_id)
        status = _required_mapping(execution, "Status", context="QueryExecution")
        state = _required_string(status, "State", context="QueryExecution.Status")

        if state != "SUCCEEDED":
            reason = _optional_string(status.get("StateChangeReason"))
            detail = f": {reason}" if reason else ""
            raise SemanticQueryExecutionError(
                f"Athena query {query_execution_id} ended in state {state}{detail}"
            )

        statistics = _optional_mapping(execution.get("Statistics"))
        data_scanned_bytes = _non_negative_int(
            statistics.get("DataScannedInBytes") if statistics else None,
            field="DataScannedInBytes",
            default=0,
        )
        engine_execution_time_ms = _optional_non_negative_int(
            statistics.get("EngineExecutionTimeInMillis") if statistics else None,
            field="EngineExecutionTimeInMillis",
        )
        total_execution_time_ms = _optional_non_negative_int(
            statistics.get("TotalExecutionTimeInMillis") if statistics else None,
            field="TotalExecutionTimeInMillis",
        )

        columns, rows = self._read_bounded_results(
            query_execution_id,
            max_rows=max_rows,
        )

        return AthenaQueryResult(
            query_execution_id=query_execution_id,
            columns=columns,
            rows=rows,
            data_scanned_bytes=data_scanned_bytes,
            engine_execution_time_ms=engine_execution_time_ms,
            total_execution_time_ms=total_execution_time_ms,
        )

    def _wait_for_terminal_state(self, query_execution_id: str) -> Mapping[str, object]:
        """Poll a query until terminal state or cancel after the configured bound."""
        for attempt in range(self._max_poll_attempts):
            response = self._client.get_query_execution(
                QueryExecutionId=query_execution_id,
            )
            execution = _required_mapping(
                response,
                "QueryExecution",
                context="GetQueryExecution response",
            )
            status = _required_mapping(execution, "Status", context="QueryExecution")
            state = _required_string(status, "State", context="QueryExecution.Status")

            if state in _TERMINAL_STATES:
                return execution
            if state not in _ACTIVE_STATES:
                self._cancel(query_execution_id)
                raise SemanticQueryExecutionError(
                    f"Athena returned unsupported query state {state!r}."
                )

            if attempt + 1 < self._max_poll_attempts:
                self._sleeper(self._poll_interval_seconds)

        self._cancel(query_execution_id)
        raise SemanticQueryTimeoutError(
            "Athena query did not reach a terminal state within the polling bound."
        )

    def _read_bounded_results(
        self,
        query_execution_id: str,
        *,
        max_rows: int,
    ) -> tuple[tuple[str, ...], tuple[tuple[str | None, ...], ...]]:
        """Read one bounded result page and reject unexpected pagination."""
        response = self._client.get_query_results(
            QueryExecutionId=query_execution_id,
            MaxResults=max_rows + 1,
        )

        if _optional_string(response.get("NextToken")) is not None:
            raise SemanticQueryResultError(
                "Athena returned pagination for a SQL query that is already row-bounded."
            )

        result_set = _required_mapping(response, "ResultSet", context="GetQueryResults")
        metadata = _required_mapping(
            result_set,
            "ResultSetMetadata",
            context="GetQueryResults.ResultSet",
        )
        column_info = _required_sequence(
            metadata,
            "ColumnInfo",
            context="ResultSetMetadata",
        )
        columns = tuple(
            _required_string(
                _as_mapping(item, context="ColumnInfo item"),
                "Name",
                context="ColumnInfo item",
            )
            for item in column_info
        )
        if not columns:
            raise SemanticQueryResultError("Athena result metadata contains no columns.")

        raw_rows = _required_sequence(result_set, "Rows", context="GetQueryResults.ResultSet")
        rows = tuple(self._parse_row(item, expected_columns=len(columns)) for item in raw_rows)

        if rows and rows[0] == columns:
            rows = rows[1:]
        if len(rows) > max_rows:
            raise SemanticQueryResultError(
                "Athena returned more rows than the semantic-query limit permits."
            )

        return columns, rows

    @staticmethod
    def _parse_row(
        raw_row: object,
        *,
        expected_columns: int,
    ) -> tuple[str | None, ...]:
        """Parse one Athena row without guessing missing or extra columns."""
        row = _as_mapping(raw_row, context="Athena row")
        data = _required_sequence(row, "Data", context="Athena row")
        if len(data) != expected_columns:
            raise SemanticQueryResultError(
                "Athena row width does not match result metadata."
            )

        values: list[str | None] = []
        for raw_value in data:
            value = _as_mapping(raw_value, context="Athena datum")
            varchar_value = value.get("VarCharValue")
            if varchar_value is None:
                values.append(None)
                continue
            if not isinstance(varchar_value, str):
                raise SemanticQueryResultError("Athena datum is not a string value.")
            values.append(varchar_value)

        return tuple(values)

    @staticmethod
    def _assert_read_only_compiled_shape(query: CompiledAthenaQuery) -> None:
        """Fail closed if a caller bypasses the compiler-owned SELECT boundary."""
        statement = query.sql.strip()
        if not statement.upper().startswith("SELECT "):
            raise SemanticQueryExecutionError("Athena executor accepts SELECT statements only.")
        if ";" in statement:
            raise SemanticQueryExecutionError(
                "Athena executor accepts exactly one compiler-owned SQL statement."
            )
        if _EPSS_RELATION not in statement:
            raise SemanticQueryExecutionError(
                "Athena executor is currently restricted to the EPSS Silver relation."
            )

    def _cancel(self, query_execution_id: str) -> None:
        """Best-effort cancellation for bounded failure paths."""
        self._client.stop_query_execution(QueryExecutionId=query_execution_id)


def _required_mapping(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> Mapping[str, object]:
    """Read one required nested mapping from an AWS response."""
    value = mapping.get(key)
    if not isinstance(value, Mapping):
        raise SemanticQueryResultError(f"{context} is missing mapping field {key!r}.")
    return cast(Mapping[str, object], value)


def _optional_mapping(value: object) -> Mapping[str, object] | None:
    """Normalize an optional AWS response mapping."""
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise SemanticQueryResultError("Athena response contains a malformed mapping value.")
    return cast(Mapping[str, object], value)


def _as_mapping(value: object, *, context: str) -> Mapping[str, object]:
    """Validate one untrusted AWS response value as a mapping."""
    if not isinstance(value, Mapping):
        raise SemanticQueryResultError(f"{context} must be a mapping.")
    return cast(Mapping[str, object], value)


def _required_sequence(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> tuple[object, ...]:
    """Read one required sequence without accepting strings as collections."""
    value = mapping.get(key)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise SemanticQueryResultError(f"{context} is missing sequence field {key!r}.")
    return tuple(cast(Sequence[object], value))


def _required_string(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> str:
    """Read one required non-empty string from an AWS response."""
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SemanticQueryResultError(f"{context} is missing string field {key!r}.")
    return value


def _optional_string(value: object) -> str | None:
    """Normalize one optional string from an AWS response."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise SemanticQueryResultError("Athena response contains a malformed string value.")
    normalized = value.strip()
    return normalized or None


def _non_negative_int(value: object, *, field: str, default: int) -> int:
    """Normalize a required-or-default non-negative integer statistic."""
    if value is None:
        return default
    if type(value) is not int or value < 0:
        raise SemanticQueryResultError(f"Athena statistic {field} must be non-negative.")
    return value


def _optional_non_negative_int(value: object, *, field: str) -> int | None:
    """Normalize one optional non-negative integer statistic."""
    if value is None:
        return None
    return _non_negative_int(value, field=field, default=0)
