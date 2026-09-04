"""Bounded Amazon Bedrock runtime for the frozen semantic-query planner contract."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, cast

from opslens.semantic_query.planner.bedrock import build_bedrock_converse_request
from opslens.semantic_query.planner.models import (
    PlannerContractError,
    PlannerOutcome,
    SemanticPlannerRequest,
)
from opslens.semantic_query.planner.parser import parse_planner_json


class BedrockPlannerRuntimeError(RuntimeError):
    """Raised when Bedrock cannot provide complete, auditable planner evidence."""


class BedrockConverseClient(Protocol):
    """Narrow client port containing only the Bedrock Converse operation."""

    def converse(self, **kwargs: object) -> Mapping[str, object]:
        """Invoke one non-streaming Converse request."""
        ...


@dataclass(frozen=True, slots=True)
class BedrockPlannerUsage:
    """Usage evidence returned directly by Amazon Bedrock."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: int

    def __post_init__(self) -> None:
        """Reject missing, negative, or internally inconsistent runtime evidence."""
        for field_name in ("input_tokens", "output_tokens", "total_tokens", "latency_ms"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer.")
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("total_tokens must equal input_tokens + output_tokens.")


@dataclass(frozen=True, slots=True)
class BedrockPlannerResult:
    """Deterministically parsed planner proposal plus Bedrock runtime evidence."""

    outcome: PlannerOutcome
    usage: BedrockPlannerUsage


class BedrockSemanticPlanner:
    """Invoke exactly the frozen Bedrock request and revalidate its proposal deterministically."""

    def __init__(self, client: BedrockConverseClient) -> None:
        """Store the narrow Bedrock client port."""
        self._client = client

    def plan(self, request: SemanticPlannerRequest) -> BedrockPlannerResult:
        """Invoke Bedrock once and accept content only through the frozen parser."""
        if type(request) is not SemanticPlannerRequest:
            raise TypeError("request must be SemanticPlannerRequest.")

        response = self._client.converse(**build_bedrock_converse_request(request))
        text = _extract_single_text(response)
        usage = _extract_usage(response)
        try:
            outcome = parse_planner_json(text)
        except PlannerContractError:
            raise
        return BedrockPlannerResult(outcome=outcome, usage=usage)


def _extract_single_text(response: Mapping[str, object]) -> str:
    """Require exactly one non-empty Bedrock text content block."""
    output = _mapping(response.get("output"), context="output")
    message = _mapping(output.get("message"), context="output.message")
    content = _sequence(message.get("content"), context="output.message.content")
    if len(content) != 1:
        raise BedrockPlannerRuntimeError("Bedrock planner must return exactly one content block.")
    block = _mapping(content[0], context="output.message.content[0]")
    if set(block) != {"text"}:
        raise BedrockPlannerRuntimeError("Bedrock planner content block must contain only text.")
    text = block.get("text")
    if not isinstance(text, str) or not text.strip():
        raise BedrockPlannerRuntimeError("Bedrock planner text must be non-empty.")
    return text


def _extract_usage(response: Mapping[str, object]) -> BedrockPlannerUsage:
    """Extract Bedrock token and latency evidence without estimating missing values."""
    usage = _mapping(response.get("usage"), context="usage")
    metrics = _mapping(response.get("metrics"), context="metrics")
    return BedrockPlannerUsage(
        input_tokens=_non_negative_int(usage.get("inputTokens"), field="usage.inputTokens"),
        output_tokens=_non_negative_int(usage.get("outputTokens"), field="usage.outputTokens"),
        total_tokens=_non_negative_int(usage.get("totalTokens"), field="usage.totalTokens"),
        latency_ms=_non_negative_int(metrics.get("latencyMs"), field="metrics.latencyMs"),
    )


def _mapping(value: object, *, context: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise BedrockPlannerRuntimeError(f"Bedrock response {context} must be an object.")
    return cast(Mapping[str, object], value)


def _sequence(value: object, *, context: str) -> tuple[object, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise BedrockPlannerRuntimeError(f"Bedrock response {context} must be an array.")
    return tuple(cast(Sequence[object], value))


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        message = f"Bedrock response {field} must be a non-negative integer."
        raise BedrockPlannerRuntimeError(message)
    return value
