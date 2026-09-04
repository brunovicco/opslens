"""Application service for bounded natural-language semantic-query execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from opslens.semantic_query.application.models import AthenaQueryResult
from opslens.semantic_query.domain import SemanticQuery
from opslens.semantic_query.planner import (
    BedrockPlannerInvocationEvidence,
    BedrockPlannerResult,
    PlannedSemanticQuery,
    SemanticPlannerRequest,
    UnsupportedPlannerDecision,
    UnsupportedReason,
)


class SemanticQueryPlanner(Protocol):
    """Define the bounded planner capability required by the application layer."""

    def plan(self, request: SemanticPlannerRequest) -> BedrockPlannerResult:
        """Plan one normalized natural-language request."""
        ...


class TypedSemanticQueryExecutor(Protocol):
    """Define execution of one already-validated semantic query."""

    def execute(self, query: SemanticQuery) -> AthenaQueryResult:
        """Execute one typed semantic query through the deterministic compiler boundary."""
        ...


@dataclass(frozen=True, slots=True)
class ExecutedNaturalLanguageSemanticQuery:
    """Successful bounded execution with planner and Athena evidence kept separate."""

    planner_evidence: BedrockPlannerInvocationEvidence
    semantic_query: SemanticQuery
    result: AthenaQueryResult


@dataclass(frozen=True, slots=True)
class UnsupportedNaturalLanguageSemanticQuery:
    """Fail-closed planner result that intentionally grants no Athena execution authority."""

    planner_evidence: BedrockPlannerInvocationEvidence
    reason: UnsupportedReason


type NaturalLanguageSemanticQueryResult = (
    ExecutedNaturalLanguageSemanticQuery | UnsupportedNaturalLanguageSemanticQuery
)


class ExecuteNaturalLanguageSemanticQuery:
    """Plan bounded semantics and execute only validated supported queries."""

    def __init__(
        self,
        planner: SemanticQueryPlanner,
        executor: TypedSemanticQueryExecutor,
    ) -> None:
        """Initialize the use case with explicit planner and typed-query capabilities."""
        self._planner = planner
        self._executor = executor

    def execute(
        self,
        request: SemanticPlannerRequest,
    ) -> NaturalLanguageSemanticQueryResult:
        """Plan one question and stop before Athena when the planner fails closed."""
        if type(request) is not SemanticPlannerRequest:
            raise TypeError("request must be SemanticPlannerRequest.")

        planned = self._planner.plan(request)
        outcome = planned.outcome

        if isinstance(outcome, UnsupportedPlannerDecision):
            return UnsupportedNaturalLanguageSemanticQuery(
                planner_evidence=planned.evidence,
                reason=outcome.reason,
            )

        if isinstance(outcome, PlannedSemanticQuery):
            result = self._executor.execute(outcome.query)
            return ExecutedNaturalLanguageSemanticQuery(
                planner_evidence=planned.evidence,
                semantic_query=outcome.query,
                result=result,
            )

        raise TypeError("Unknown planner outcome type.")
