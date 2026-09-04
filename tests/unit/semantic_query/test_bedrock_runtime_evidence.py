"""Tests for Gate 6.4 Bedrock runtime evidence contracts."""

from __future__ import annotations

import pytest

from opslens.semantic_query.planner import (
    BEDROCK_PLANNER_MODEL_ID,
    BEDROCK_PLANNER_REGION,
    BedrockPlannerInvocationEvidence,
    BedrockPlannerResult,
    PlannerContractError,
    UnsupportedPlannerDecision,
    UnsupportedReason,
)


def _evidence(**overrides: object) -> BedrockPlannerInvocationEvidence:
    """Build one real-shaped invocation evidence object for focused validation tests."""
    values: dict[str, object] = {
        "model_id": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        "region": "us-east-1",
        "request_id": "63fbb3d8-44dd-4b7b-aa60-9e6a02db1b8e",
        "stop_reason": "end_turn",
        "input_tokens": 942,
        "output_tokens": 79,
        "total_tokens": 1021,
        "cache_read_input_tokens": 0,
        "cache_write_input_tokens": 0,
        "bedrock_latency_ms": 2064,
        "client_elapsed_ms": 4180,
        "retry_attempts": 0,
    }
    values.update(overrides)
    return BedrockPlannerInvocationEvidence(**values)  # type: ignore[arg-type]


def test_gate_6_4_uses_us_geographic_inference_profile() -> None:
    """Runtime planning uses the verified US inference profile rather than direct model ID."""
    assert BEDROCK_PLANNER_REGION == "us-east-1"
    assert BEDROCK_PLANNER_MODEL_ID == "us.anthropic.claude-haiku-4-5-20251001-v1:0"


def test_bedrock_invocation_evidence_accepts_real_observed_shape() -> None:
    """Metadata observed in the successful real smoke is representable without raw payloads."""
    evidence = _evidence()

    assert evidence.input_tokens == 942
    assert evidence.output_tokens == 79
    assert evidence.total_tokens == 1021
    assert evidence.retry_attempts == 0


def test_bedrock_invocation_evidence_rejects_invalid_numeric_metadata() -> None:
    """Negative or boolean counters cannot silently become runtime evidence."""
    with pytest.raises(PlannerContractError, match="retry_attempts"):
        _evidence(retry_attempts=-1)
    with pytest.raises(PlannerContractError, match="input_tokens"):
        _evidence(input_tokens=True)


def test_bedrock_invocation_evidence_requires_consistent_total_tokens() -> None:
    """Token accounting remains internally consistent before evidence is exposed."""
    with pytest.raises(PlannerContractError, match="total_tokens"):
        _evidence(total_tokens=1022)


def test_bedrock_planner_result_keeps_outcome_and_evidence_separate() -> None:
    """Planner semantics and invocation metadata remain independently typed boundaries."""
    outcome = UnsupportedPlannerDecision(
        reason=UnsupportedReason.MISSING_EXPLICIT_SNAPSHOT_DATE
    )
    evidence = _evidence(
        input_tokens=933,
        output_tokens=23,
        total_tokens=956,
        bedrock_latency_ms=870,
        client_elapsed_ms=2202,
        request_id="ad00f430-10ce-431c-984a-b2c00a83c920",
    )

    result = BedrockPlannerResult(outcome=outcome, evidence=evidence)

    assert result.outcome is outcome
    assert result.evidence is evidence
