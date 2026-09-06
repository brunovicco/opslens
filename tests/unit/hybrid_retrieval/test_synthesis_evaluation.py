"""Unit tests for Gate 8.4 runtime orchestration and independent synthesis metrics."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from opslens.hybrid_retrieval.adapters.bedrock_synthesis import BedrockHybridSynthesizer
from opslens.hybrid_retrieval.application.evaluation import load_hybrid_evaluation_dataset
from opslens.hybrid_retrieval.application.synthesis_evaluation import (
    evaluate_hybrid_synthesis_runtime,
    run_hybrid_synthesis_runtime_evaluation,
)
from opslens.hybrid_retrieval.domain.evaluation import (
    HybridEvaluationDataset,
    HybridExpectedAnswerBehavior,
    HybridMeasurementStatus,
    HybridMetricDimension,
)

_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "hybrid_retrieval"
    / "golden_hybrid_v1.json"
)


def _dataset() -> HybridEvaluationDataset:
    """Load the exact frozen Gate 8.3 dataset."""
    return load_hybrid_evaluation_dataset(_FIXTURE)


def _provider_response(output: str, request_id: str) -> dict[str, object]:
    """Build one minimal valid fake Converse response."""
    return {
        "output": {"message": {"role": "assistant", "content": [{"text": output}]}},
        "stopReason": "end_turn",
        "usage": {
            "inputTokens": 100,
            "outputTokens": 20,
            "totalTokens": 120,
            "cacheReadInputTokens": 0,
            "cacheWriteInputTokens": 0,
        },
        "metrics": {"latencyMs": 40},
        "ResponseMetadata": {"RequestId": request_id, "RetryAttempts": 0},
    }


def _answer(semantic_id: str, structured_ids: list[str] | None = None) -> str:
    """Serialize one admitted explanatory answer for a fake model call."""
    return json.dumps(
        {
            "decision": "answer",
            "claims": [
                {
                    "text": "Use the cited remediation evidence before deployment.",
                    "semantic_citation_ids": [semantic_id],
                    "structured_fact_ids": structured_ids or [],
                }
            ],
        }
    )


class _SequenceConverseClient:
    """Return deterministic fake responses in model-call order."""

    def __init__(self, responses: tuple[Mapping[str, object], ...]) -> None:
        self._responses = iter(responses)
        self.calls: list[dict[str, object]] = []

    def converse(self, **request: object) -> Mapping[str, object]:
        """Record one request and return the next frozen fake response."""
        self.calls.append(request)
        return next(self._responses)


class _Clock:
    """Return deterministic monotonic values for three model calls."""

    def __init__(self, values: tuple[float, ...]) -> None:
        self._values = iter(values)

    def __call__(self) -> float:
        """Return the next fake monotonic-clock observation."""
        return next(self._values)


def _run(*, noisy_citation: str = "S2"):
    """Execute all six fixture cases with exactly three fake model calls."""
    client = _SequenceConverseClient(
        (
            _provider_response(_answer("S1"), "req-semantic"),
            _provider_response(_answer("S1", ["F2"]), "req-hybrid"),
            _provider_response(_answer(noisy_citation), "req-noise"),
        )
    )
    synthesizer = BedrockHybridSynthesizer(
        client,
        clock=_Clock((0.0, 0.1, 1.0, 1.2, 2.0, 2.3)),
    )
    execution = run_hybrid_synthesis_runtime_evaluation(
        synthesizer.synthesize,
        dataset=_dataset(),
    )
    return execution, client


def test_runtime_runner_uses_zero_or_one_model_call_by_authorized_route() -> None:
    """Only semantic and true hybrid cases may reach the provider boundary."""
    execution, client = _run()

    assert execution.complete
    assert len(execution.attempts) == 6
    assert len(client.calls) == 3

    by_id = {item.case.case_id: item for item in execution.attempts}
    assert by_id["hybrid-structured-factual-01"].request is None
    assert by_id["hybrid-unsupported-runtime-exposure-01"].request is None
    assert by_id["hybrid-partial-structured-01"].request is None
    assert by_id["hybrid-partial-structured-01"].observed_behavior is (
        HybridExpectedAnswerBehavior.REJECT_BEFORE_SYNTHESIS
    )
    assert by_id["hybrid-unsupported-runtime-exposure-01"].observed_behavior is (
        HybridExpectedAnswerBehavior.ABSTAIN
    )


def test_perfect_fake_baseline_populates_independent_gate_8_4_metrics() -> None:
    """A correct run measures synthesis dimensions without inventing cost."""
    execution, _ = _run()

    baseline = evaluate_hybrid_synthesis_runtime(execution, dataset=_dataset())

    assert baseline.measurement(HybridMetricDimension.ROUTE_ACCURACY).value == 1.0
    assert (
        baseline.measurement(HybridMetricDimension.STRUCTURED_FACT_CORRECTNESS).value
        == 1.0
    )
    assert baseline.measurement(HybridMetricDimension.SEMANTIC_GROUNDEDNESS).value == 1.0
    assert baseline.measurement(HybridMetricDimension.CITATION_CORRECTNESS).value == 1.0
    assert baseline.measurement(HybridMetricDimension.ABSTENTION).value == 1.0
    assert baseline.measurement(HybridMetricDimension.LATENCY).value == 200.0
    cost = baseline.measurement(HybridMetricDimension.COST)
    assert cost.status is HybridMeasurementStatus.UNMEASURED
    assert cost.value is None


def test_semantic_noise_wrong_rank_one_citation_degrades_only_semantic_dimensions() -> None:
    """Admitted rank-one noise is not automatically a supporting or correct citation."""
    execution, _ = _run(noisy_citation="S1")

    baseline = evaluate_hybrid_synthesis_runtime(execution, dataset=_dataset())

    assert baseline.measurement(HybridMetricDimension.ROUTE_ACCURACY).value == 1.0
    assert (
        baseline.measurement(HybridMetricDimension.STRUCTURED_FACT_CORRECTNESS).value
        == 1.0
    )
    assert baseline.measurement(HybridMetricDimension.ABSTENTION).value == 1.0
    assert baseline.measurement(HybridMetricDimension.SEMANTIC_GROUNDEDNESS).value == (
        2 / 3
    )
    assert baseline.measurement(HybridMetricDimension.CITATION_CORRECTNESS).value == (
        2 / 3
    )
