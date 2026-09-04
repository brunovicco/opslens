"""Typed contracts for the bounded Phase 6 semantic-query planner."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from opslens.semantic_query.domain import SemanticQuery

MAX_PLANNER_QUESTION_CHARS = 1000


class PlannerContractError(ValueError):
    """Raised when planner input or output violates the frozen planner contract."""


class PlannerDecision(StrEnum):
    """Planner decisions allowed by the first semantic-query slice."""

    SEMANTIC_QUERY = "semantic_query"
    UNSUPPORTED = "unsupported"


class UnsupportedReason(StrEnum):
    """Fail-closed reasons exposed by the first planner contract."""

    MISSING_EXPLICIT_SNAPSHOT_DATE = "missing_explicit_snapshot_date"
    UNSUPPORTED_SEMANTICS = "unsupported_semantics"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class SemanticPlannerRequest:
    """One bounded natural-language question for the semantic planner."""

    question: str

    def __post_init__(self) -> None:
        """Normalize and bound planner input before it reaches a model."""
        if not isinstance(self.question, str):
            raise PlannerContractError("Planner question must be a string.")

        normalized = self.question.strip()
        if not normalized:
            raise PlannerContractError("Planner question cannot be blank.")
        if len(normalized) > MAX_PLANNER_QUESTION_CHARS:
            raise PlannerContractError(
                f"Planner question cannot exceed {MAX_PLANNER_QUESTION_CHARS} characters."
            )

        object.__setattr__(self, "question", normalized)


@dataclass(frozen=True, slots=True)
class PlannedSemanticQuery:
    """A model proposal that survived deterministic SemanticQuery construction."""

    query: SemanticQuery

    def __post_init__(self) -> None:
        """Reject forged outcomes that do not contain the deterministic domain type."""
        if not isinstance(self.query, SemanticQuery):
            raise PlannerContractError("Planned semantic query must contain SemanticQuery.")

    @property
    def decision(self) -> PlannerDecision:
        """Return the stable planner decision discriminator."""
        return PlannerDecision.SEMANTIC_QUERY


@dataclass(frozen=True, slots=True)
class UnsupportedPlannerDecision:
    """A fail-closed planner outcome for questions outside the current semantic surface."""

    reason: UnsupportedReason

    def __post_init__(self) -> None:
        """Reject unknown unsupported reasons at runtime."""
        if not isinstance(self.reason, UnsupportedReason):
            raise PlannerContractError("Unknown unsupported planner reason.")

    @property
    def decision(self) -> PlannerDecision:
        """Return the stable planner decision discriminator."""
        return PlannerDecision.UNSUPPORTED


type PlannerOutcome = PlannedSemanticQuery | UnsupportedPlannerDecision
