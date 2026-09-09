"""Tests for the bounded authenticated AgentCore Runtime replay contract."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from opslens.agent_baseline.application.reasoning_evaluation import (
    load_agent_reasoning_evaluation_dataset,
)
from opslens.agent_baseline.domain.reasoning_evaluation import AgentReasoningEvaluationDataset
from opslens.agentcore_runtime.replay import (
    PHASE11_REFERENCE_CORPUS_SHA256,
    AgentCoreRuntimeReplayError,
    execute_agentcore_runtime_replay,
)

_FIXTURE = (
    Path(__file__).parents[2]
    / "fixtures"
    / "agent_baseline"
    / "golden_single_agent_reasoning_v1.json"
)
_RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/test-abc"


class _ReplayClient:
    def __init__(
        self,
        dataset: AgentReasoningEvaluationDataset,
        *,
        wrong_session: bool = False,
        status_code: int = 200,
        mismatch_first_case: bool = False,
    ) -> None:
        self._expectations = {
            case.task.text: case.expectation for case in dataset.cases
        }
        self._wrong_session = wrong_session
        self._status_code = status_code
        self._mismatch_first_case = mismatch_first_case
        self.calls = 0

    def invoke_agent_runtime(
        self,
        *,
        agentRuntimeArn: str,
        runtimeSessionId: str,
        payload: bytes,
        contentType: str,
        accept: str,
    ) -> Mapping[str, object]:
        assert agentRuntimeArn == _RUNTIME_ARN
        assert contentType == "application/json"
        assert accept == "application/json"
        request = json.loads(payload)
        expectation = self._expectations[request["task_text"]]
        decision = expectation.decision.value
        if self._mismatch_first_case and self.calls == 0:
            decision = "abstain" if decision == "act" else "act"
        self.calls += 1
        body = json.dumps(
            {
                "authorization_outcome": expectation.authorization_outcome.value,
                "capability": (
                    expectation.capability.value
                    if expectation.capability is not None
                    else None
                ),
                "decision": decision,
                "invocation_evidence": {
                    "input_tokens": 10,
                    "output_tokens": 2,
                    "retry_attempts": 0,
                    "total_tokens": 12,
                },
            },
            sort_keys=True,
        ).encode()
        return {
            "contentType": "application/json",
            "response": body,
            "runtimeSessionId": (
                f"{runtimeSessionId}-wrong" if self._wrong_session else runtimeSessionId
            ),
            "statusCode": self._status_code,
        }


def _dataset() -> AgentReasoningEvaluationDataset:
    return load_agent_reasoning_evaluation_dataset(_FIXTURE)


def test_replay_preserves_phase11_corpus_and_bounds() -> None:
    """All six frozen cases should score through transport without capability execution."""
    dataset = _dataset()
    client = _ReplayClient(dataset)

    report = execute_agentcore_runtime_replay(
        client=client,
        runtime_arn=_RUNTIME_ARN,
        source_head_sha="a" * 40,
        replay_run_id="unit-test-run",
        dataset=dataset,
    )

    assert report["corpus_sha256"] == PHASE11_REFERENCE_CORPUS_SHA256
    assert report["capability_executions"] == 0
    metrics = report["metrics"]
    assert isinstance(metrics, dict)
    assert metrics["total_cases"] == 6
    assert metrics["passed_cases"] == 6
    assert metrics["total_tokens"] == 72
    assert metrics["sdk_retry_attempts_sum"] == 0
    assert client.calls == 6


def test_replay_reports_behavior_mismatch_without_hiding_it() -> None:
    """A model behavior mismatch must reduce the deterministic pass count."""
    dataset = _dataset()
    client = _ReplayClient(dataset, mismatch_first_case=True)

    report = execute_agentcore_runtime_replay(
        client=client,
        runtime_arn=_RUNTIME_ARN,
        source_head_sha="b" * 40,
        replay_run_id="mismatch-run",
        dataset=dataset,
    )

    metrics = report["metrics"]
    assert isinstance(metrics, dict)
    assert metrics["passed_cases"] == 5


def test_replay_fails_closed_on_runtime_session_identity_change() -> None:
    """Runtime transport must not silently replace the caller-bound session identity."""
    dataset = _dataset()
    client = _ReplayClient(dataset, wrong_session=True)

    with pytest.raises(AgentCoreRuntimeReplayError, match="different runtime session identity"):
        execute_agentcore_runtime_replay(
            client=client,
            runtime_arn=_RUNTIME_ARN,
            source_head_sha="c" * 40,
            replay_run_id="session-run",
            dataset=dataset,
        )


def test_replay_fails_closed_on_non_success_runtime_status() -> None:
    """Unexpected Runtime transport status must stop the replay."""
    dataset = _dataset()
    client = _ReplayClient(dataset, status_code=502)

    with pytest.raises(AgentCoreRuntimeReplayError, match="unexpected runtime status 502"):
        execute_agentcore_runtime_replay(
            client=client,
            runtime_arn=_RUNTIME_ARN,
            source_head_sha="d" * 40,
            replay_run_id="status-run",
            dataset=dataset,
        )
