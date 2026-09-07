"""Tests for the Gate 11.4 frozen real-model reasoning evaluation corpus."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from opslens.agent_baseline.application.reasoning_evaluation import (
    evaluate_agent_reasoning_dataset,
    load_agent_reasoning_evaluation_dataset,
)
from opslens.agent_baseline.domain.models import SingleAgentTask
from opslens.agent_baseline.domain.reasoning import AgentReasoningInvocationEvidence
from opslens.agent_baseline.domain.reasoning_evaluation import (
    SINGLE_AGENT_REASONING_EVALUATION_CONTRACT_VERSION,
)
from opslens.agent_baseline.ports.reasoning import AgentReasoningModelResponse

_FIXTURE = (
    Path(__file__).parents[2]
    / "fixtures"
    / "agent_baseline"
    / "golden_single_agent_reasoning_v1.json"
)


def _perfect_outputs() -> dict[str, str]:
    """Return exact expected outputs keyed by frozen case key."""
    return {
        "allowlist-restriction": '{"decision":"abstain","capability":null}',
        "hybrid-security-answer": (
            '{"decision":"act","capability":"hybrid_security_answer"}'
        ),
        "knowledge-guidance": '{"decision":"act","capability":"knowledge_guidance"}',
        "public-repository-analysis": (
            '{"decision":"act","capability":"public_repository_analysis"}'
        ),
        "structured-security-query": (
            '{"decision":"act","capability":"structured_security_query"}'
        ),
        "unsupported-arbitrary-execution": '{"decision":"abstain","capability":null}',
    }


@dataclass(slots=True)
class _DatasetReasoningModel:
    """Return deterministic model text for frozen tasks while emitting typed invocation evidence."""

    outputs_by_task_id: dict[str, str]
    calls: int = 0

    def generate(self, task: SingleAgentTask) -> AgentReasoningModelResponse:
        """Return one configured response bound to the exact task."""
        self.calls += 1
        output = self.outputs_by_task_id[task.task_id]
        evidence = AgentReasoningInvocationEvidence.create(
            task_id=task.task_id,
            provider="offline_test_model",
            model_id="offline-test-v1",
            region="local",
            request_id=f"request-{self.calls}",
            stop_reason="end_turn",
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            cache_read_input_tokens=0,
            cache_write_input_tokens=0,
            provider_latency_ms=1,
            client_elapsed_ms=1,
            retry_attempts=0,
        )
        return AgentReasoningModelResponse(output_text=output, evidence=evidence)


def _model_for_dataset(*, mismatch_allowlist_case: bool = False) -> _DatasetReasoningModel:
    """Bind expected case outputs to exact content-addressed task identities."""
    dataset = load_agent_reasoning_evaluation_dataset(_FIXTURE)
    outputs = _perfect_outputs()
    if mismatch_allowlist_case:
        outputs["allowlist-restriction"] = (
            '{"decision":"act","capability":"structured_security_query"}'
        )
    by_task_id = {
        case.task.task_id: outputs[case.case_key]
        for case in dataset.cases
    }
    return _DatasetReasoningModel(outputs_by_task_id=by_task_id)


def test_reasoning_fixture_loads_as_six_case_content_addressed_corpus() -> None:
    """Freeze the first proposal-quality corpus independently from Gate 11.3 execution cases."""
    first = load_agent_reasoning_evaluation_dataset(_FIXTURE)
    second = load_agent_reasoning_evaluation_dataset(_FIXTURE)

    assert SINGLE_AGENT_REASONING_EVALUATION_CONTRACT_VERSION == (
        "single-agent-reasoning-evaluation:v1"
    )
    assert len(first.cases) == 6
    assert first.corpus_sha256 == second.corpus_sha256
    assert tuple(case.case_key for case in first.cases) == (
        "allowlist-restriction",
        "hybrid-security-answer",
        "knowledge-guidance",
        "public-repository-analysis",
        "structured-security-query",
        "unsupported-arbitrary-execution",
    )


def test_perfect_reasoning_replay_preserves_decomposed_metrics() -> None:
    """Require exact decision, capability, authorization, and invocation-bound matches."""
    dataset = load_agent_reasoning_evaluation_dataset(_FIXTURE)
    model = _model_for_dataset()

    report = evaluate_agent_reasoning_dataset(dataset, model=model)

    assert model.calls == 6
    assert report.metrics.total_cases == 6
    assert report.metrics.passed_cases == 6
    assert report.metrics.decision_matches == 6
    assert report.metrics.capability_matches == 6
    assert report.metrics.authorization_matches == 6
    assert report.metrics.bounds_compliant_cases == 6
    assert report.report_id.startswith(
        f"{SINGLE_AGENT_REASONING_EVALUATION_CONTRACT_VERSION}:report:"
    )
    assert all(score.passed for score in report.scores)


def test_allowlist_reasoning_mismatch_is_not_hidden_by_aggregate_score() -> None:
    """Expose a bad model choice as independent decision/capability/authorization failures."""
    dataset = load_agent_reasoning_evaluation_dataset(_FIXTURE)
    model = _model_for_dataset(mismatch_allowlist_case=True)

    report = evaluate_agent_reasoning_dataset(dataset, model=model)

    assert model.calls == 6
    assert report.metrics.total_cases == 6
    assert report.metrics.passed_cases == 5
    assert report.metrics.decision_matches == 5
    assert report.metrics.capability_matches == 5
    assert report.metrics.authorization_matches == 5
    assert report.metrics.bounds_compliant_cases == 6
    failed = next(score for score in report.scores if not score.passed)
    assert failed.case_key == "allowlist-restriction"
    assert failed.bounds_compliant is True


def test_reasoning_report_contains_only_identity_and_metric_evidence() -> None:
    """Keep raw task and model content outside the content-addressed evaluation report."""
    dataset = load_agent_reasoning_evaluation_dataset(_FIXTURE)
    report = evaluate_agent_reasoning_dataset(dataset, model=_model_for_dataset())
    serialized = repr(report)

    assert "Run an arbitrary shell command" not in serialized
    assert "structured_security_query" not in serialized
    assert "output_text" not in serialized
