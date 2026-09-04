"""Bounded Amazon Bedrock Converse adapter for the semantic-query planner."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from typing import Protocol, cast

from opslens.semantic_query.planner import (
    BEDROCK_PLANNER_MODEL_ID,
    BEDROCK_PLANNER_REGION,
    BedrockPlannerInvocationEvidence,
    BedrockPlannerResult,
    SemanticPlannerRequest,
    build_bedrock_converse_request,
    parse_planner_json,
)


class BedrockPlannerRuntimeError(RuntimeError):
    """Raised when Bedrock invocation or response violates the bounded adapter contract."""


class BedrockConverseClient(Protocol):
    """Define only the Bedrock Converse capability required by the planner adapter."""

    def converse(self, **request: object) -> Mapping[str, object]:
        """Invoke one non-streaming Converse request."""
        ...


class BedrockSemanticPlanner:
    """Invoke the frozen Bedrock planner and return typed semantics plus runtime evidence."""

    def __init__(
        self,
        client: BedrockConverseClient,
        *,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        """Initialize the adapter with an injected Converse client and monotonic clock."""
        self._client = client
        self._clock = clock

    def plan(self, request: SemanticPlannerRequest) -> BedrockPlannerResult:
        """Invoke Bedrock once, revalidate model output, and capture metadata-only evidence."""
        if type(request) is not SemanticPlannerRequest:
            raise TypeError("request must be SemanticPlannerRequest.")

        payload = build_bedrock_converse_request(request)
        started = self._clock()
        try:
            response = self._client.converse(**payload)
        except Exception as exc:
            raise BedrockPlannerRuntimeError("Bedrock Converse invocation failed.") from exc
        client_elapsed_ms = _elapsed_milliseconds(started, self._clock())

        model_output = _extract_single_text_output(response)
        outcome = parse_planner_json(model_output)
        evidence = _parse_invocation_evidence(
            response,
            client_elapsed_ms=client_elapsed_ms,
        )
        return BedrockPlannerResult(outcome=outcome, evidence=evidence)


def _extract_single_text_output(response: Mapping[str, object]) -> str:
    """Require the exact non-streaming text response shape used by the frozen planner."""
    output = _required_mapping(response, "output", context="Converse response")
    message = _required_mapping(output, "message", context="Converse response.output")
    content = _required_sequence(
        message,
        "content",
        context="Converse response.output.message",
    )
    if len(content) != 1:
        raise BedrockPlannerRuntimeError(
            "Converse planner response must contain exactly one content block."
        )

    block = content[0]
    if not isinstance(block, Mapping):
        raise BedrockPlannerRuntimeError(
            "Converse planner content block must be an object."
        )
    text = cast(Mapping[str, object], block).get("text")
    if type(text) is not str or not text.strip():
        raise BedrockPlannerRuntimeError(
            "Converse planner content block must contain non-empty text."
        )
    return text


def _parse_invocation_evidence(
    response: Mapping[str, object],
    *,
    client_elapsed_ms: int,
) -> BedrockPlannerInvocationEvidence:
    """Translate Bedrock metadata into the typed evidence contract."""
    usage = _required_mapping(response, "usage", context="Converse response")
    metrics = _required_mapping(response, "metrics", context="Converse response")
    metadata = _required_mapping(response, "ResponseMetadata", context="Converse response")

    return BedrockPlannerInvocationEvidence(
        model_id=BEDROCK_PLANNER_MODEL_ID,
        region=BEDROCK_PLANNER_REGION,
        request_id=_required_string(metadata, "RequestId", context="ResponseMetadata"),
        stop_reason=_required_string(response, "stopReason", context="Converse response"),
        input_tokens=_required_non_negative_int(
            usage,
            "inputTokens",
            context="Converse response.usage",
        ),
        output_tokens=_required_non_negative_int(
            usage,
            "outputTokens",
            context="Converse response.usage",
        ),
        total_tokens=_required_non_negative_int(
            usage,
            "totalTokens",
            context="Converse response.usage",
        ),
        cache_read_input_tokens=_optional_non_negative_int(
            usage,
            "cacheReadInputTokens",
            context="Converse response.usage",
            default=0,
        ),
        cache_write_input_tokens=_optional_non_negative_int(
            usage,
            "cacheWriteInputTokens",
            context="Converse response.usage",
            default=0,
        ),
        bedrock_latency_ms=_required_non_negative_int(
            metrics,
            "latencyMs",
            context="Converse response.metrics",
        ),
        client_elapsed_ms=client_elapsed_ms,
        retry_attempts=_optional_non_negative_int(
            metadata,
            "RetryAttempts",
            context="ResponseMetadata",
            default=0,
        ),
    )


def _elapsed_milliseconds(started: float, finished: float) -> int:
    """Convert one monotonic elapsed interval to a non-negative integer millisecond value."""
    elapsed = finished - started
    if elapsed < 0:
        raise BedrockPlannerRuntimeError("Planner clock moved backwards.")
    return round(elapsed * 1000)


def _required_mapping(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> Mapping[str, object]:
    """Read one required mapping field from an AWS response structure."""
    value = mapping.get(key)
    if not isinstance(value, Mapping):
        raise BedrockPlannerRuntimeError(f"{context}.{key} must be an object.")
    return cast(Mapping[str, object], value)


def _required_sequence(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> Sequence[object]:
    """Read one required non-string sequence field from an AWS response structure."""
    value = mapping.get(key)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise BedrockPlannerRuntimeError(f"{context}.{key} must be an array.")
    return cast(Sequence[object], value)


def _required_string(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> str:
    """Read one required normalized non-empty string field."""
    value = mapping.get(key)
    if type(value) is not str or not value.strip() or value.strip() != value:
        raise BedrockPlannerRuntimeError(
            f"{context}.{key} must be a normalized non-empty string."
        )
    return value


def _required_non_negative_int(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> int:
    """Read one required non-negative integer field."""
    value = mapping.get(key)
    if type(value) is not int or value < 0:
        raise BedrockPlannerRuntimeError(f"{context}.{key} must be a non-negative integer.")
    return value


def _optional_non_negative_int(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
    default: int,
) -> int:
    """Read one optional non-negative integer field with an explicit default."""
    value = mapping.get(key)
    if value is None:
        return default
    if type(value) is not int or value < 0:
        raise BedrockPlannerRuntimeError(f"{context}.{key} must be a non-negative integer.")
    return value
