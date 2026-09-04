"""Unit tests for the bounded Amazon Bedrock semantic planner adapter."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import date

import pytest

from opslens.semantic_query.adapters.outbound import (
    BedrockPlannerRuntimeError,
    BedrockSemanticPlanner,
)
from opslens.semantic_query.domain import (
    EpssFilters,
    SemanticDimension,
    SemanticMetric,
    SemanticOrderField,
    SemanticQuery,
    SortDirection,
)
from opslens.semantic_query.planner import (
    BEDROCK_PLANNER_MODEL_ID,
    BEDROCK_PLANNER_REGION,
    BedrockPlannerInvocationEvidence,
    PlannedSemanticQuery,
    SemanticPlannerRequest,
    UnsupportedPlannerDecision,
    UnsupportedReason,
)


class _FakeBedrockClient:
    """Record one or more Converse requests and return a fixed response."""

    def __init__(self, response: Mapping[str, object]) -> None:
        self._response = response
        self.requests: list[dict[str, object]] = []

    def converse(self, **request: object) -> Mapping[str, object]:
        """Record the request and return the configured fake response."""
        self.requests.append(dict(request))
        return self._response


def _clock(*values: float) -> Callable[[], float]:
    """Return a deterministic monotonic clock over the supplied values."""
    iterator = iter(values)
    return lambda: next(iterator)


def _response(model_output: Mapping[str, object]) -> dict[str, object]:
    """Build one representative successful Converse response."""
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": json.dumps(model_output)}],
            }
        },
        "stopReason": "end_turn",
        "usage": {
            "inputTokens": 942,
            "outputTokens": 79,
            "totalTokens": 1021,
            "cacheReadInputTokens": 0,
            "cacheWriteInputTokens": 0,
        },
        "metrics": {"latencyMs": 2064},
        "ResponseMetadata": {
            "RequestId": "request-123",
            "RetryAttempts": 0,
        },
    }


def _supported_output() -> dict[str, object]:
    """Return the first allowlisted EPSS semantic-query planner output."""
    return {
        "decision": "semantic_query",
        "dimensions": ["cve"],
        "filters": {
            "minimum_score": 0.7,
            "snapshot_date": "2026-09-03",
        },
        "limit": 20,
        "metric": "epss_score",
        "order_by": "epss_score",
        "order_direction": "desc",
    }


def test_bedrock_adapter_returns_typed_query_and_invocation_evidence() -> None:
    """A valid Converse response reenters deterministic semantics and preserves evidence."""
    client = _FakeBedrockClient(_response(_supported_output()))
    planner = BedrockSemanticPlanner(client, clock=_clock(10.0, 14.18))

    result = planner.plan(
        SemanticPlannerRequest(
            "Which CVEs have EPSS of at least 0.7 on 2026-09-03?"
        )
    )

    assert result.outcome == PlannedSemanticQuery(
        SemanticQuery(
            metric=SemanticMetric.EPSS_SCORE,
            dimensions=(SemanticDimension.CVE,),
            filters=EpssFilters(
                snapshot_date=date(2026, 9, 3),
                minimum_score=0.7,
            ),
            order_by=SemanticOrderField.EPSS_SCORE,
            order_direction=SortDirection.DESC,
            limit=20,
        )
    )
    assert result.evidence == BedrockPlannerInvocationEvidence(
        model_id=BEDROCK_PLANNER_MODEL_ID,
        region=BEDROCK_PLANNER_REGION,
        request_id="request-123",
        stop_reason="end_turn",
        input_tokens=942,
        output_tokens=79,
        total_tokens=1021,
        cache_read_input_tokens=0,
        cache_write_input_tokens=0,
        bedrock_latency_ms=2064,
        client_elapsed_ms=4180,
        retry_attempts=0,
    )

    assert len(client.requests) == 1
    assert client.requests[0]["modelId"] == BEDROCK_PLANNER_MODEL_ID
    inference_config = client.requests[0]["inferenceConfig"]
    assert isinstance(inference_config, dict)
    assert inference_config == {"maxTokens": 256, "temperature": 0.0}


def test_bedrock_adapter_preserves_typed_fail_closed_decision() -> None:
    """Unsupported model output remains a typed refusal and grants no query authority."""
    client = _FakeBedrockClient(
        _response(
            {
                "decision": "unsupported",
                "reason": "missing_explicit_snapshot_date",
            }
        )
    )
    planner = BedrockSemanticPlanner(client, clock=_clock(1.0, 1.87))

    result = planner.plan(
        SemanticPlannerRequest("Which CVEs have EPSS of at least 0.7?")
    )

    assert result.outcome == UnsupportedPlannerDecision(
        UnsupportedReason.MISSING_EXPLICIT_SNAPSHOT_DATE
    )
    assert result.evidence.client_elapsed_ms == 870


def test_bedrock_adapter_rejects_multiple_content_blocks() -> None:
    """Unexpected multimodal or partial content cannot cross the planner boundary."""
    response = _response(_supported_output())
    output = response["output"]
    assert isinstance(output, dict)
    message = output["message"]
    assert isinstance(message, dict)
    message["content"] = [
        {"text": json.dumps(_supported_output())},
        {"text": json.dumps(_supported_output())},
    ]
    planner = BedrockSemanticPlanner(
        _FakeBedrockClient(response),
        clock=_clock(1.0, 1.1),
    )

    with pytest.raises(BedrockPlannerRuntimeError, match="exactly one content block"):
        planner.plan(
            SemanticPlannerRequest(
                "Which CVEs have EPSS of at least 0.7 on 2026-09-03?"
            )
        )


def test_bedrock_adapter_rejects_missing_runtime_evidence() -> None:
    """Missing provider metadata fails closed rather than yielding partial evidence."""
    response = _response(_supported_output())
    del response["metrics"]
    planner = BedrockSemanticPlanner(
        _FakeBedrockClient(response),
        clock=_clock(1.0, 1.1),
    )

    with pytest.raises(BedrockPlannerRuntimeError, match=r"Converse response\.metrics"):
        planner.plan(
            SemanticPlannerRequest(
                "Which CVEs have EPSS of at least 0.7 on 2026-09-03?"
            )
        )


def test_bedrock_adapter_rejects_inconsistent_token_evidence() -> None:
    """Token metadata must satisfy the evidence contract before it is returned."""
    response = _response(_supported_output())
    usage = response["usage"]
    assert isinstance(usage, dict)
    usage["totalTokens"] = 999
    planner = BedrockSemanticPlanner(
        _FakeBedrockClient(response),
        clock=_clock(1.0, 1.1),
    )

    with pytest.raises(ValueError, match="total_tokens"):
        planner.plan(
            SemanticPlannerRequest(
                "Which CVEs have EPSS of at least 0.7 on 2026-09-03?"
            )
        )


def test_bedrock_adapter_rejects_non_monotonic_clock() -> None:
    """Invalid local timing cannot produce misleading latency evidence."""
    planner = BedrockSemanticPlanner(
        _FakeBedrockClient(_response(_supported_output())),
        clock=_clock(2.0, 1.0),
    )

    with pytest.raises(BedrockPlannerRuntimeError, match="clock moved backwards"):
        planner.plan(
            SemanticPlannerRequest(
                "Which CVEs have EPSS of at least 0.7 on 2026-09-03?"
            )
        )
