"""Unit tests for the bounded read-only Athena semantic-query executor."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date

import pytest

from opslens.semantic_query.adapters.outbound import (
    ATHENA_DATABASE,
    ATHENA_WORKGROUP,
    AthenaQueryExecutor,
)
from opslens.semantic_query.application import ExecuteSemanticQuery
from opslens.semantic_query.domain import (
    CompiledAthenaQuery,
    EpssFilters,
    SemanticDimension,
    SemanticMetric,
    SemanticQuery,
    SemanticQueryExecutionError,
    SemanticQueryResultError,
    SemanticQueryTimeoutError,
)


class _FakeAthenaClient:
    """Deterministic in-memory Athena API fake for adapter tests."""

    def __init__(
        self,
        *,
        states: Sequence[str] = ("SUCCEEDED",),
        state_reason: str | None = None,
        query_execution_id: str | None = "query-123",
        result_response: Mapping[str, object] | None = None,
        result_responses: Sequence[Mapping[str, object]] | None = None,
        statistics: Mapping[str, object] | None = None,
    ) -> None:
        if result_response is not None and result_responses is not None:
            raise ValueError("Provide either result_response or result_responses, not both.")

        self.states = list(states)
        self.state_reason = state_reason
        self.query_execution_id = query_execution_id
        if result_responses is not None:
            self.result_responses = list(result_responses)
        else:
            self.result_responses = [result_response or _result_response()]
        self.statistics = statistics or {
            "DataScannedInBytes": 4096,
            "EngineExecutionTimeInMillis": 25,
            "TotalExecutionTimeInMillis": 40,
        }
        self.start_calls: list[dict[str, object]] = []
        self.status_calls: list[str] = []
        self.result_calls: list[dict[str, object]] = []
        self.stop_calls: list[str] = []

    def start_query_execution(
        self,
        *,
        QueryString: str,
        QueryExecutionContext: Mapping[str, str],
        WorkGroup: str,
        ExecutionParameters: Sequence[str],
    ) -> Mapping[str, object]:
        self.start_calls.append(
            {
                "QueryString": QueryString,
                "QueryExecutionContext": dict(QueryExecutionContext),
                "WorkGroup": WorkGroup,
                "ExecutionParameters": ExecutionParameters,
            }
        )
        if self.query_execution_id is None:
            return {}
        return {"QueryExecutionId": self.query_execution_id}

    def get_query_execution(
        self,
        *,
        QueryExecutionId: str,
    ) -> Mapping[str, object]:
        self.status_calls.append(QueryExecutionId)
        state = self.states.pop(0) if self.states else "RUNNING"
        status: dict[str, object] = {"State": state}
        if self.state_reason is not None:
            status["StateChangeReason"] = self.state_reason
        return {
            "QueryExecution": {
                "Status": status,
                "Statistics": dict(self.statistics),
            }
        }

    def get_query_results(
        self,
        *,
        QueryExecutionId: str,
        MaxResults: int,
        NextToken: str | None = None,
    ) -> Mapping[str, object]:
        call: dict[str, object] = {
            "QueryExecutionId": QueryExecutionId,
            "MaxResults": MaxResults,
        }
        if NextToken is not None:
            call["NextToken"] = NextToken
        self.result_calls.append(call)

        if not self.result_responses:
            raise AssertionError("Athena fake received an unexpected result-page request.")
        return self.result_responses.pop(0)

    def stop_query_execution(
        self,
        *,
        QueryExecutionId: str,
    ) -> Mapping[str, object]:
        self.stop_calls.append(QueryExecutionId)
        return {}


def _semantic_query(*, limit: int = 20) -> SemanticQuery:
    """Build the first supported EPSS semantic query."""
    return SemanticQuery(
        metric=SemanticMetric.EPSS_SCORE,
        dimensions=(SemanticDimension.CVE,),
        filters=EpssFilters(snapshot_date=date(2026, 9, 3), minimum_score=0.7),
        limit=limit,
    )


def _compiled_query(
    *,
    where: str = 'WHERE "snapshot_date" = ? AND "epss" >= ?',
    order: str = 'ORDER BY "epss" DESC, "cve" ASC',
    limit: int = 20,
    parameters: tuple[str, ...] = ("'2026-09-03'", "0.7"),
) -> CompiledAthenaQuery:
    """Build the exact Gate 6.1 compiler shape for direct-adapter hardening tests."""
    return CompiledAthenaQuery(
        sql="\n".join(
            [
                'SELECT "cve", "epss"',
                'FROM "opslens_dev"."epss_scores"',
                where,
                order,
                f"LIMIT {limit}",
            ]
        ),
        execution_parameters=parameters,
    )


def _result_response(
    *,
    rows: Sequence[Sequence[str | None]] | None = None,
    next_token: str | None = None,
) -> Mapping[str, object]:
    """Build the subset of GetQueryResults used by the adapter."""
    values = (
        (
            ("cve", "epss"),
            ("CVE-2026-0001", "0.91"),
            ("CVE-2026-0002", "0.72"),
        )
        if rows is None
        else rows
    )
    response: dict[str, object] = {
        "ResultSet": {
            "ResultSetMetadata": {
                "ColumnInfo": (
                    {"Name": "cve"},
                    {"Name": "epss"},
                )
            },
            "Rows": tuple(
                {
                    "Data": tuple(
                        {} if value is None else {"VarCharValue": value}
                        for value in row
                    )
                }
                for row in values
            ),
        }
    }
    if next_token is not None:
        response["NextToken"] = next_token
    return response


def _executor(client: _FakeAthenaClient, *, max_poll_attempts: int = 5) -> AthenaQueryExecutor:
    """Build an executor without real sleeping."""
    return AthenaQueryExecutor(
        client,
        poll_interval_seconds=0.0,
        max_poll_attempts=max_poll_attempts,
        sleeper=lambda _: None,
    )


def test_application_compiles_then_executes_in_fixed_dev_boundary() -> None:
    """The application never grants the caller arbitrary SQL/workgroup authority."""
    client = _FakeAthenaClient(states=("QUEUED", "RUNNING", "SUCCEEDED"))
    use_case = ExecuteSemanticQuery(_executor(client))

    result = use_case.execute(_semantic_query())

    assert len(client.start_calls) == 1
    start = client.start_calls[0]
    assert start["QueryExecutionContext"] == {"Database": ATHENA_DATABASE}
    assert start["WorkGroup"] == ATHENA_WORKGROUP
    assert start["ExecutionParameters"] == ["'2026-09-03'", "0.7"]
    assert start["QueryString"] == (
        'SELECT "cve", "epss"\n'
        'FROM "opslens_dev"."epss_scores"\n'
        'WHERE "snapshot_date" = ? AND "epss" >= ?\n'
        'ORDER BY "epss" DESC, "cve" ASC\n'
        "LIMIT 20"
    )
    assert client.status_calls == ["query-123", "query-123", "query-123"]
    assert client.result_calls == [{"QueryExecutionId": "query-123", "MaxResults": 21}]
    assert result.query_execution_id == "query-123"
    assert result.columns == ("cve", "epss")
    assert result.rows == (
        ("CVE-2026-0001", "0.91"),
        ("CVE-2026-0002", "0.72"),
    )
    assert result.data_scanned_bytes == 4096
    assert result.engine_execution_time_ms == 25
    assert result.total_execution_time_ms == 40


def test_sql_limit_controls_get_query_results_page_bound() -> None:
    """Each API result page is bounded by the semantic query limit plus header."""
    client = _FakeAthenaClient()
    use_case = ExecuteSemanticQuery(_executor(client))

    use_case.execute(_semantic_query(limit=100))

    assert client.result_calls == [{"QueryExecutionId": "query-123", "MaxResults": 101}]


def test_failed_query_surfaces_state_reason_without_fetching_results() -> None:
    """FAILED is terminal and never falls through to result retrieval."""
    client = _FakeAthenaClient(
        states=("FAILED",),
        state_reason="COLUMN_NOT_FOUND",
    )

    with pytest.raises(SemanticQueryExecutionError, match="COLUMN_NOT_FOUND"):
        ExecuteSemanticQuery(_executor(client)).execute(_semantic_query())

    assert client.result_calls == []
    assert client.stop_calls == []


def test_cancelled_query_fails_closed_without_fetching_results() -> None:
    """CANCELLED is terminal failure evidence for this synchronous use case."""
    client = _FakeAthenaClient(states=("CANCELLED",))

    with pytest.raises(SemanticQueryExecutionError, match="CANCELLED"):
        ExecuteSemanticQuery(_executor(client)).execute(_semantic_query())

    assert client.result_calls == []


def test_poll_timeout_requests_cancellation() -> None:
    """Queries cannot remain unbounded when Athena never reaches a terminal state."""
    client = _FakeAthenaClient(states=("QUEUED", "RUNNING", "RUNNING"))

    with pytest.raises(SemanticQueryTimeoutError, match="polling bound"):
        ExecuteSemanticQuery(_executor(client, max_poll_attempts=3)).execute(_semantic_query())

    assert client.stop_calls == ["query-123"]
    assert client.result_calls == []


def test_unknown_athena_state_requests_cancellation_and_fails_closed() -> None:
    """Future or malformed Athena states do not inherit implicit execution semantics."""
    client = _FakeAthenaClient(states=("MYSTERY",))

    with pytest.raises(SemanticQueryExecutionError, match="unsupported query state"):
        ExecuteSemanticQuery(_executor(client)).execute(_semantic_query())

    assert client.stop_calls == ["query-123"]


def test_missing_query_execution_id_is_rejected() -> None:
    """Malformed StartQueryExecution evidence cannot enter the application result."""
    client = _FakeAthenaClient(query_execution_id=None)

    with pytest.raises(SemanticQueryResultError, match="QueryExecutionId"):
        ExecuteSemanticQuery(_executor(client)).execute(_semantic_query())


def test_bounded_result_pagination_is_followed() -> None:
    """Athena pagination is transport behavior, not broader SQL authority."""
    client = _FakeAthenaClient(
        result_responses=(
            _result_response(
                rows=(
                    ("cve", "epss"),
                    ("CVE-2026-0001", "0.91"),
                ),
                next_token="page-2",
            ),
            _result_response(rows=(("CVE-2026-0002", "0.72"),)),
        )
    )

    result = ExecuteSemanticQuery(_executor(client)).execute(_semantic_query())

    assert result.rows == (
        ("CVE-2026-0001", "0.91"),
        ("CVE-2026-0002", "0.72"),
    )
    assert client.result_calls == [
        {"QueryExecutionId": "query-123", "MaxResults": 21},
        {
            "QueryExecutionId": "query-123",
            "MaxResults": 21,
            "NextToken": "page-2",
        },
    ]


def test_paginated_rows_still_cannot_exceed_semantic_limit() -> None:
    """Following a continuation token cannot increase the semantic row authority."""
    client = _FakeAthenaClient(
        result_responses=(
            _result_response(
                rows=(
                    ("cve", "epss"),
                    ("CVE-2026-0001", "0.91"),
                ),
                next_token="page-2",
            ),
            _result_response(rows=(("CVE-2026-0002", "0.72"),)),
        )
    )

    with pytest.raises(SemanticQueryResultError, match="more rows"):
        ExecuteSemanticQuery(_executor(client)).execute(_semantic_query(limit=1))


def test_repeated_result_pagination_token_is_rejected() -> None:
    """A malformed token cycle cannot cause unbounded result retrieval."""
    client = _FakeAthenaClient(
        result_responses=(
            _result_response(
                rows=(("cve", "epss"),),
                next_token="page-2",
            ),
            _result_response(rows=(), next_token="page-2"),
        )
    )

    with pytest.raises(SemanticQueryResultError, match="repeated"):
        ExecuteSemanticQuery(_executor(client)).execute(_semantic_query())


def test_result_row_width_must_match_metadata() -> None:
    """Malformed Athena rows are explicit failures rather than partially parsed data."""
    client = _FakeAthenaClient(
        result_response=_result_response(rows=(("cve", "epss"), ("CVE-2026-0001",))),
    )

    with pytest.raises(SemanticQueryResultError, match="row width"):
        ExecuteSemanticQuery(_executor(client)).execute(_semantic_query())


def test_null_result_value_is_preserved_explicitly() -> None:
    """The adapter preserves Athena nulls instead of inventing values."""
    client = _FakeAthenaClient(
        result_response=_result_response(
            rows=(("cve", "epss"), ("CVE-2026-0001", None)),
        )
    )

    result = ExecuteSemanticQuery(_executor(client)).execute(_semantic_query())

    assert result.rows == (("CVE-2026-0001", None),)


@pytest.mark.parametrize(
    "sql",
    [
        'DROP TABLE "opslens_dev"."epss_scores"',
        'SELECT "cve" FROM "opslens_dev"."epss_scores"; DROP TABLE x',
        'SELECT "cve" FROM "other"."table"',
        (
            'SELECT "cve", "epss"\n'
            'FROM "opslens_dev"."epss_scores"\n'
            'JOIN "other"."table" ON 1 = 1\n'
            'WHERE "snapshot_date" = ? AND "epss" >= ?\n'
            'ORDER BY "epss" DESC, "cve" ASC\n'
            'LIMIT 20'
        ),
        (
            'SELECT "cve", "epss"\n'
            'FROM "opslens_dev"."epss_scores"\n'
            'WHERE "snapshot_date" = ? AND "epss" >= ?\n'
            'ORDER BY "cve" ASC\n'
            'LIMIT 20'
        ),
    ],
)
def test_direct_adapter_call_cannot_bypass_compiler_sql_boundary(sql: str) -> None:
    """A forged compiled object cannot broaden the exact Gate 6.1 SQL grammar."""
    placeholder_count = sql.count("?")
    parameters = tuple("0.7" for _ in range(placeholder_count))
    if placeholder_count:
        parameters = ("'2026-09-03'", *parameters[1:])
    client = _FakeAthenaClient()
    forged = CompiledAthenaQuery(sql=sql, execution_parameters=parameters)

    with pytest.raises(SemanticQueryExecutionError):
        _executor(client).execute(forged, max_rows=20)

    assert client.start_calls == []


@pytest.mark.parametrize(
    "parameters",
    [
        ("'2026-09-03' OR 1=1", "0.7"),
        ("'2026-02-30'", "0.7"),
        ("'2026-09-03'", "0.7 OR 1=1"),
        ("'2026-09-03'", "nan"),
        ("'2026-09-03'", "1.01"),
    ],
)
def test_direct_adapter_call_rejects_forged_execution_parameters(
    parameters: tuple[str, str],
) -> None:
    """Execution parameters cannot inject semantics outside compiler-owned literals."""
    client = _FakeAthenaClient()
    forged = _compiled_query(parameters=parameters)

    with pytest.raises(SemanticQueryExecutionError):
        _executor(client).execute(forged, max_rows=20)

    assert client.start_calls == []


def test_direct_adapter_requires_sql_limit_to_match_result_bound() -> None:
    """A caller cannot decouple SQL authority from the validated result bound."""
    client = _FakeAthenaClient()
    forged = _compiled_query(limit=21)

    with pytest.raises(SemanticQueryExecutionError, match="must match"):
        _executor(client).execute(forged, max_rows=20)

    assert client.start_calls == []


def test_direct_adapter_accepts_compiler_shape_without_epss_threshold() -> None:
    """The exact no-threshold Gate 6.1 compiler variant remains supported."""
    client = _FakeAthenaClient()
    compiled = _compiled_query(
        where='WHERE "snapshot_date" = ?',
        parameters=("'2026-09-03'",),
    )

    result = _executor(client).execute(compiled, max_rows=20)

    assert result.query_execution_id == "query-123"
    assert client.start_calls[0]["ExecutionParameters"] == ["'2026-09-03'"]


@pytest.mark.parametrize("max_rows", [0, 101, -1])
def test_adapter_has_its_own_result_bound(max_rows: int) -> None:
    """Infrastructure execution remains bounded if called outside the application service."""
    client = _FakeAthenaClient()
    compiled = _compiled_query()

    with pytest.raises(SemanticQueryExecutionError, match="result bound"):
        _executor(client).execute(compiled, max_rows=max_rows)


def test_executor_configuration_must_be_bounded() -> None:
    """Polling controls cannot be disabled through invalid construction values."""
    client = _FakeAthenaClient()

    with pytest.raises(ValueError, match="poll interval"):
        AthenaQueryExecutor(client, poll_interval_seconds=-0.1)
    with pytest.raises(ValueError, match="max poll attempts"):
        AthenaQueryExecutor(client, max_poll_attempts=0)
