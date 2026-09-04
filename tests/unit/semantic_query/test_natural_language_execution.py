"""Unit tests for bounded natural-language semantic-query composition."""

from __future__ import annotations

from datetime import date

from opslens.semantic_query.application import (
    AthenaQueryResult,
    ExecutedNaturalLanguageSemanticQuery,
    ExecuteNaturalLanguageSemanticQuery,
    ExecuteSemanticQuery,
    UnsupportedNaturalLanguageSemanticQuery,
)
from opslens.semantic_query.domain import (
    CompiledAthenaQuery,
    EpssFilters,
    SemanticDimension,
    SemanticMetric,
    SemanticQuery,
)
from opslens.semantic_query.planner import (
    BEDROCK_PLANNER_MODEL_ID,
    BEDROCK_PLANNER_REGION,
    BedrockPlannerInvocationEvidence,
    BedrockPlannerResult,
    PlannedSemanticQuery,
    SemanticPlannerRequest,
    UnsupportedPlannerDecision,
    UnsupportedReason,
)


class _FakePlanner:
    """Return one prevalidated planner result and record requests."""

    def __init__(self, result: BedrockPlannerResult) -> None:
        self._result = result
        self.requests: list[SemanticPlannerRequest] = []

    def plan(self, request: SemanticPlannerRequest) -> BedrockPlannerResult:
        """Record and return the configured planner result."""
        self.requests.append(request)
        return self._result


class _FakeCompiledExecutor:
    """Record compiler-owned queries and return fixed Athena evidence."""

    def __init__(self, result: AthenaQueryResult) -> None:
        self._result = result
        self.calls: list[tuple[CompiledAthenaQuery, int]] = []

    def execute(
        self,
        query: CompiledAthenaQuery,
        *,
        max_rows: int,
    ) -> AthenaQueryResult:
        """Record one compiled query and its explicit row bound."""
        self.calls.append((query, max_rows))
        return self._result


def _evidence() -> BedrockPlannerInvocationEvidence:
    """Return representative metadata-only planner evidence."""
    return BedrockPlannerInvocationEvidence(
        model_id=BEDROCK_PLANNER_MODEL_ID,
        region=BEDROCK_PLANNER_REGION,
        request_id="request-123",
        stop_reason="end_turn",
        input_tokens=942,
        output_tokens=79,
        total_tokens=1021,
        cache_read_input_tokens=0,
        cache_write_input_tokens=0,
        bedrock_latency_ms=1620,
        client_elapsed_ms=3535,
        retry_attempts=0,
    )


def _query() -> SemanticQuery:
    """Return the first bounded EPSS semantic query."""
    return SemanticQuery(
        metric=SemanticMetric.EPSS_SCORE,
        dimensions=(SemanticDimension.CVE,),
        filters=EpssFilters(
            snapshot_date=date(2026, 9, 3),
            minimum_score=0.7,
        ),
        limit=20,
    )


def _athena_result() -> AthenaQueryResult:
    """Return representative bounded Athena evidence."""
    return AthenaQueryResult(
        query_execution_id="athena-123",
        columns=("cve", "epss"),
        rows=(("CVE-2021-44228", "0.99999"),),
        data_scanned_bytes=3_785_003,
        engine_execution_time_ms=1198,
        total_execution_time_ms=1388,
    )


def test_supported_natural_language_query_reenters_compiler_owned_execution() -> None:
    """Supported model semantics compile deterministically before bounded execution."""
    query = _query()
    planner = _FakePlanner(BedrockPlannerResult(PlannedSemanticQuery(query), _evidence()))
    compiled_executor = _FakeCompiledExecutor(_athena_result())
    use_case = ExecuteNaturalLanguageSemanticQuery(
        planner,
        ExecuteSemanticQuery(compiled_executor),
    )
    request = SemanticPlannerRequest(
        "Which CVEs have EPSS of at least 0.7 on 2026-09-03?"
    )

    outcome = use_case.execute(request)

    assert isinstance(outcome, ExecutedNaturalLanguageSemanticQuery)
    assert outcome.planner_evidence == _evidence()
    assert outcome.semantic_query == query
    assert outcome.result == _athena_result()
    assert planner.requests == [request]
    assert len(compiled_executor.calls) == 1

    compiled, max_rows = compiled_executor.calls[0]
    assert compiled.sql == "\n".join(
        [
            'SELECT "cve", "epss"',
            'FROM "opslens_dev"."epss_scores"',
            'WHERE "snapshot_date" = ? AND "epss" >= ?',
            'ORDER BY "epss" DESC, "cve" ASC',
            "LIMIT 20",
        ]
    )
    assert compiled.execution_parameters == ("'2026-09-03'", "0.7")
    assert max_rows == 20


def test_unsupported_natural_language_query_never_reaches_compiler_or_athena() -> None:
    """Fail-closed planner decisions terminate before any execution capability is used."""
    planner = _FakePlanner(
        BedrockPlannerResult(
            UnsupportedPlannerDecision(
                UnsupportedReason.MISSING_EXPLICIT_SNAPSHOT_DATE
            ),
            _evidence(),
        )
    )
    compiled_executor = _FakeCompiledExecutor(_athena_result())
    use_case = ExecuteNaturalLanguageSemanticQuery(
        planner,
        ExecuteSemanticQuery(compiled_executor),
    )
    request = SemanticPlannerRequest("Which CVEs have EPSS of at least 0.7?")

    outcome = use_case.execute(request)

    assert outcome == UnsupportedNaturalLanguageSemanticQuery(
        planner_evidence=_evidence(),
        reason=UnsupportedReason.MISSING_EXPLICIT_SNAPSHOT_DATE,
    )
    assert planner.requests == [request]
    assert compiled_executor.calls == []
