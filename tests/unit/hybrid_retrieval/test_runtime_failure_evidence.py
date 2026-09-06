"""Regression tests for bounded Gate 8.4 runtime failure evidence."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from botocore.exceptions import ClientError

from opslens.hybrid_retrieval.adapters.bedrock_synthesis import BedrockHybridSynthesizer
from opslens.hybrid_retrieval.application.evaluation import load_hybrid_evaluation_dataset
from opslens.hybrid_retrieval.application.synthesis_evaluation import (
    run_hybrid_synthesis_runtime_evaluation,
)
from opslens.hybrid_retrieval.cli.run_bedrock_hybrid_synthesis_evaluation import (
    serialize_hybrid_runtime_execution,
)

_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "hybrid_retrieval"
    / "golden_hybrid_v1.json"
)


class _AccessDeniedConverseClient:
    """Raise a provider error containing a message that must never enter evidence."""

    def __init__(self) -> None:
        self.calls = 0

    def converse(self, **request: object) -> Mapping[str, object]:
        """Record one invocation and fail with a realistic Bedrock error envelope."""
        self.calls += 1
        raise ClientError(
            error_response={
                "Error": {
                    "Code": "AccessDeniedException",
                    "Message": "provider detail that must not be serialized",
                },
                "ResponseMetadata": {"RequestId": "provider-request-secret"},
            },
            operation_name="Converse",
        )


class _SingleClock:
    """Provide the one pre-invocation timestamp needed by a failing call."""

    def __call__(self) -> float:
        """Return a deterministic monotonic observation."""
        return 1.0


def test_provider_failure_preserves_category_without_provider_content() -> None:
    """A failed provider boundary remains distinguishable from zero-call execution."""
    dataset = load_hybrid_evaluation_dataset(_FIXTURE)
    client = _AccessDeniedConverseClient()
    synthesizer = BedrockHybridSynthesizer(client, clock=_SingleClock())

    execution = run_hybrid_synthesis_runtime_evaluation(
        synthesizer.synthesize,
        dataset=dataset,
    )

    assert not execution.complete
    assert len(execution.attempts) == 2
    assert client.calls == 1
    assert execution.synthesis_invocation_attempt_count == 1
    assert execution.admitted_model_execution_count == 0

    failure = execution.attempts[-1]
    assert failure.case.case_id == "hybrid-semantic-remediation-01"
    assert failure.failure_category == "provider_invocation"
    assert failure.failure_diagnostic == (
        "Bedrock hybrid Converse synthesis failed provider_code=AccessDeniedException"
    )
    assert failure.failure_request_id is None
    assert failure.failure_stop_reason is None
    assert failure.synthesis_invocation_attempted
    assert failure.synthesis is None

    serialized = serialize_hybrid_runtime_execution(
        execution,
        baseline=None,
        region="us-east-1",
    )
    payload = json.loads(serialized)
    assert payload["model_call_count"] == 0
    assert payload["model_call_count_semantics"] == "admitted_model_executions"
    assert payload["synthesis_invocation_attempt_count"] == 1
    assert payload["cases"][-1]["failure_category"] == "provider_invocation"
    assert payload["cases"][-1]["synthesis_invocation_attempted"] is True
    assert "provider detail that must not be serialized" not in serialized
    assert "provider-request-secret" not in serialized
