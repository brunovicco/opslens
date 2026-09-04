"""Unit tests for the bounded real-Bedrock planner runtime boundary."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from opslens.semantic_query.adapters.outbound.bedrock_planner import (
    BedrockPlannerRuntimeError,
    BedrockSemanticPlanner,
)
from opslens.semantic_query.planner.models import (
    PlannerContractError,
    PlannerDecision,
    SemanticPlannerRequest,
    UnsupportedPlannerDecision,
)


class FakeBedrockClient:
    """Capture the frozen Converse request and return one deterministic response."""

    def __init__(self, response: Mapping[str, object]) -> None:
        """Store one deterministic response and an empty observed-request record."""
        self.response = response
        self.observed: dict[str, object] = {}

    def converse(self, **kwargs: object) -> Mapping[str, object]:
        """Capture one call without retrying or mutating its request."""
        self.observed = kwargs
        return self.response


def _response(text: str) -> Mapping[str, object]:
    return {
        "output": {"message": {"role": "assistant", "content": [{"text": text}]}},
        "usage": {"inputTokens": 101, "outputTokens": 19, "totalTokens": 120},
        "metrics": {"latencyMs": 345},
        "stopReason": "end_turn",
    }


def test_bedrock_runtime_preserves_frozen_request_and_runtime_evidence() -> None:
    """Invoke exactly once and retain only runtime-returned tokens and latency."""
    client = FakeBedrockClient(
        _response('{"decision":"unsupported","reason":"ambiguous"}')
    )
    result = BedrockSemanticPlanner(client).plan(
        SemanticPlannerRequest("show me the latest EPSS scores")
    )

    assert isinstance(result.outcome, UnsupportedPlannerDecision)
    assert result.outcome.decision is PlannerDecision.UNSUPPORTED
    assert result.usage.input_tokens == 101
    assert result.usage.output_tokens == 19
    assert result.usage.total_tokens == 120
    assert result.usage.latency_ms == 345
    assert client.observed["modelId"] == "anthropic.claude-haiku-4-5-20251001-v1:0"
    assert client.observed["inferenceConfig"] == {"maxTokens": 256, "temperature": 0.0}
    assert "toolConfig" not in client.observed


def test_bedrock_runtime_keeps_deterministic_parser_as_final_authority() -> None:
    """Reject schema-shaped but incomplete model proposals through deterministic code."""
    client = FakeBedrockClient(
        _response('{"decision":"semantic_query","metric":"epss_score"}')
    )

    with pytest.raises(PlannerContractError, match="must match the frozen contract"):
        BedrockSemanticPlanner(client).plan(
            SemanticPlannerRequest("show EPSS for 2026-09-01")
        )


def test_bedrock_runtime_rejects_missing_usage_instead_of_fabricating_it() -> None:
    """Fail when Bedrock omits token evidence rather than manufacturing zeros."""
    response = dict(_response('{"decision":"unsupported","reason":"ambiguous"}'))
    del response["usage"]

    with pytest.raises(BedrockPlannerRuntimeError, match="usage must be an object"):
        BedrockSemanticPlanner(FakeBedrockClient(response)).plan(
            SemanticPlannerRequest("show EPSS for 2026-09-01")
        )


def test_bedrock_runtime_rejects_missing_latency_instead_of_estimating_it() -> None:
    """Fail when Bedrock omits latency evidence rather than substituting local timing."""
    response = dict(_response('{"decision":"unsupported","reason":"ambiguous"}'))
    response["metrics"] = {}

    with pytest.raises(BedrockPlannerRuntimeError, match=r"metrics\.latencyMs"):
        BedrockSemanticPlanner(FakeBedrockClient(response)).plan(
            SemanticPlannerRequest("show EPSS for 2026-09-01")
        )


def test_bedrock_runtime_rejects_multiple_content_blocks() -> None:
    """Keep the first real invocation contract to exactly one textual proposal."""
    response = dict(_response('{"decision":"unsupported","reason":"ambiguous"}'))
    response["output"] = {
        "message": {
            "role": "assistant",
            "content": [
                {"text": '{"decision":"unsupported","reason":"ambiguous"}'},
                {"text": "unexpected"},
            ],
        }
    }

    with pytest.raises(BedrockPlannerRuntimeError, match="exactly one content block"):
        BedrockSemanticPlanner(FakeBedrockClient(response)).plan(
            SemanticPlannerRequest("show EPSS for 2026-09-01")
        )


def test_bedrock_usage_requires_consistent_total_tokens() -> None:
    """Reject internally contradictory Bedrock usage evidence."""
    response = dict(_response('{"decision":"unsupported","reason":"ambiguous"}'))
    response["usage"] = {"inputTokens": 101, "outputTokens": 19, "totalTokens": 999}

    with pytest.raises(ValueError, match="total_tokens"):
        BedrockSemanticPlanner(FakeBedrockClient(response)).plan(
            SemanticPlannerRequest("show EPSS for 2026-09-01")
        )
