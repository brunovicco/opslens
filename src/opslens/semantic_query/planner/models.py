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
        if type(self.question) is not str:
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
        if type(self.query) is not SemanticQuery:
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
        if type(self.reason) is not UnsupportedReason:
            raise PlannerContractError("Unknown unsupported planner reason.")

    @property
    def decision(self) -> PlannerDecision:
        """Return the stable planner decision discriminator."""
        return PlannerDecision.UNSUPPORTED


type PlannerOutcome = PlannedSemanticQuery | UnsupportedPlannerDecision


@dataclass(frozen=True, slots=True)
class BedrockPlannerInvocationEvidence:
    """Metadata-only evidence for one bounded Amazon Bedrock planner invocation."""

    model_id: str
    region: str
    request_id: str
    stop_reason: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cache_read_input_tokens: int
    cache_write_input_tokens: int
    bedrock_latency_ms: int
    client_elapsed_ms: int
    retry_attempts: int

    def __post_init__(self) -> None:
        """Reject malformed runtime evidence instead of silently normalizing it."""
        for field_name, value in (
            ("model_id", self.model_id),
            ("region", self.region),
            ("request_id", self.request_id),
            ("stop_reason", self.stop_reason),
        ):
            if type(value) is not str or not value.strip() or value.strip() != value:
                raise PlannerContractError(
                    f"Bedrock planner {field_name} must be a normalized non-empty string."
                )

        for field_name, value in (
            ("input_tokens", self.input_tokens),
            ("output_tokens", self.output_tokens),
            ("total_tokens", self.total_tokens),
            ("cache_read_input_tokens", self.cache_read_input_tokens),
            ("cache_write_input_tokens", self.cache_write_input_tokens),
            ("bedrock_latency_ms", self.bedrock_latency_ms),
            ("client_elapsed_ms", self.client_elapsed_ms),
            ("retry_attempts", self.retry_attempts),
        ):
            if type(value) is not int or value < 0:
                raise PlannerContractError(
                    f"Bedrock planner {field_name} must be a non-negative integer."
                )

        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise PlannerContractError(
                "Bedrock planner total_tokens must equal input_tokens plus output_tokens."
            )


@dataclass(frozen=True, slots=True)
class BedrockPlannerResult:
    """Bind a validated planner outcome to metadata-only Bedrock invocation evidence."""

    outcome: PlannerOutcome
    evidence: BedrockPlannerInvocationEvidence

    def __post_init__(self) -> None:
        """Keep model semantics and invocation evidence explicit and independently typed."""
        if not isinstance(
            self.outcome,
            (PlannedSemanticQuery, UnsupportedPlannerDecision),
        ):
            raise PlannerContractError("Unknown planner outcome type.")
        if type(self.evidence) is not BedrockPlannerInvocationEvidence:
            raise PlannerContractError("Planner result evidence must be Bedrock invocation evidence.")
