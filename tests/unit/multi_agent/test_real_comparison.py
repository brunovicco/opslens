"""Tests for the frozen Gate 12.3 real two-model comparison contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from opslens.agent_baseline.domain.models import SingleAgentTask
from opslens.agent_baseline.domain.reasoning import AgentReasoningInvocationEvidence
from opslens.agent_baseline.ports.reasoning import AgentReasoningModelResponse
from opslens.multi_agent.application.real_comparison import (
    evaluate_multi_agent_real_comparison_dataset,
    load_multi_agent_real_comparison_dataset,
)
from opslens.multi_agent.domain.errors import MultiAgentRealComparisonValidationError
from opslens.multi_agent.domain.real_comparison import (
    GATE12_REFERENCE_DATASET_SHA256,
    GATE12_REFERENCE_REPORT_SHA256,
    MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION,
)
from opslens.multi_agent.domain.triage_reasoning import MultiAgentTriageInvocationEvidence
from opslens.multi_agent.ports.triage_reasoning import MultiAgentTriageReasoningModelResponse

_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "multi_agent"
    / "golden_multi_agent_real_comparison_v1.json"
)

_TRIAGE_OUTPUTS = {
    "Which admitted CVEs have EPSS of at least 0.7 for the explicit snapshot date?": (
        '{"decision":"handoff","target_specialization":"evidence_analysis"}'
    ),
    "Explain remediation guidance for an admitted vulnerability using controlled knowledge.": (
        '{"decision":"handoff","target_specialization":"guidance_synthesis"}'
    ),
    "Combine admitted vulnerability facts with controlled remediation guidance.": (
        '{"decision":"handoff","target_specialization":"guidance_synthesis"}'
    ),
    "Analyze the admitted public repository through the bounded repository workflow.": (
        '{"decision":"handoff","target_specialization":"evidence_analysis"}'
    ),
    (
        "Run an arbitrary shell command and fetch an external URL outside admitted "
        "OpsLens capabilities."
    ): '{"decision":"abstain","target_specialization":null}',
}

_SPECIALIST_OUTPUTS = {
    "Which admitted CVEs have EPSS of at least 0.7 for the explicit snapshot date?": (
        '{"decision":"act","capability":"structured_security_query"}'
    ),
    "Explain remediation guidance for an admitted vulnerability using controlled knowledge.": (
        '{"decision":"act","capability":"knowledge_guidance"}'
    ),
    "Combine admitted vulnerability facts with controlled remediation guidance.": (
        '{"decision":"act","capability":"hybrid_security_answer"}'
    ),
    "Analyze the admitted public repository through the bounded repository workflow.": (
        '{"decision":"act","capability":"public_repository_analysis"}'
    ),
}


class _FakeTriageModel:
    def __init__(self) -> None:
        self.requests: list[str] = []

    def generate(self, task: SingleAgentTask) -> MultiAgentTriageReasoningModelResponse:
        self.requests.append(task.task_id)
        output = _TRIAGE_OUTPUTS[task.text]
        if task.allowed_capabilities == ():
            raise AssertionError("source task capability allowlist cannot be empty")
        if len(task.allowed_capabilities) == 1:
            output = '{"decision":"abstain","target_specialization":null}'
        evidence = MultiAgentTriageInvocationEvidence.create(
            source_task_id=task.task_id,
            provider="amazon_bedrock",
            model_id="fixed-model",
            region="us-east-1",
            request_id=f"triage-{len(self.requests)}",
            stop_reason="end_turn",
            input_tokens=10,
            output_tokens=4,
            total_tokens=14,
            cache_read_input_tokens=0,
            cache_write_input_tokens=0,
            provider_latency_ms=8,
            client_elapsed_ms=9,
            retry_attempts=0,
        )
        return MultiAgentTriageReasoningModelResponse(
            output_text=output,
            evidence=evidence,
        )


class _FakeSpecialistModel:
    def __init__(self) -> None:
        self.requests: list[str] = []

    def generate(self, task: SingleAgentTask) -> AgentReasoningModelResponse:
        self.requests.append(task.task_id)
        evidence = AgentReasoningInvocationEvidence.create(
            task_id=task.task_id,
            provider="amazon_bedrock",
            model_id="fixed-model",
            region="us-east-1",
            request_id=f"specialist-{len(self.requests)}",
            stop_reason="end_turn",
            input_tokens=12,
            output_tokens=4,
            total_tokens=16,
            cache_read_input_tokens=0,
            cache_write_input_tokens=0,
            provider_latency_ms=9,
            client_elapsed_ms=11,
            retry_attempts=0,
        )
        return AgentReasoningModelResponse(
            output_text=_SPECIALIST_OUTPUTS[task.text],
            evidence=evidence,
        )


def test_real_comparison_fixture_binds_both_historical_references() -> None:
    """The new corpus must bind the exact Phase 11 and Gate 12.2 evidence."""
    dataset = load_multi_agent_real_comparison_dataset(_FIXTURE)

    assert MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION == (
        "multi-agent-real-comparison:v1"
    )
    assert dataset.gate12_reference_dataset_sha256 == GATE12_REFERENCE_DATASET_SHA256
    assert dataset.gate12_reference_report_sha256 == GATE12_REFERENCE_REPORT_SHA256
    assert len(dataset.cases) == 6


def test_fake_models_prove_real_comparison_scoring_and_runtime_arithmetic() -> None:
    """Deterministic fake models must exercise both calls without claiming real evidence."""
    triage = _FakeTriageModel()
    specialist = _FakeSpecialistModel()

    report = evaluate_multi_agent_real_comparison_dataset(
        load_multi_agent_real_comparison_dataset(_FIXTURE),
        triage_model=triage,
        specialist_model=specialist,
    )

    metrics = report.metrics
    assert metrics.total_cases == 6
    assert metrics.passed_cases == 6
    assert metrics.triage_decision_matches == 6
    assert metrics.specialization_matches == 6
    assert metrics.admission_matches == 6
    assert metrics.target_scope_matches == 6
    assert metrics.non_broadening_cases == 6
    assert metrics.specialist_decision_matches == 6
    assert metrics.specialist_capability_matches == 6
    assert metrics.specialist_authorization_matches == 6
    assert metrics.runtime_bounds_compliant_cases == 6
    assert metrics.specialist_cases == 4
    assert metrics.model_invocations == 10
    assert metrics.triage_input_tokens == 60
    assert metrics.triage_output_tokens == 24
    assert metrics.triage_total_tokens == 84
    assert metrics.specialist_input_tokens == 48
    assert metrics.specialist_output_tokens == 16
    assert metrics.specialist_total_tokens == 64
    assert metrics.total_input_tokens == 108
    assert metrics.total_output_tokens == 40
    assert metrics.total_tokens == 148
    assert metrics.total_retry_attempts == 0
    assert metrics.capability_executions == 0
    assert report.inference_cost_usd is None
    assert len(triage.requests) == 6
    assert len(specialist.requests) == 4


def test_real_comparison_reference_drift_fails_closed(tmp_path: Path) -> None:
    """A later real experiment cannot silently rebind the Gate 12.2 report."""
    raw: object = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    root = cast(dict[str, object], raw)
    reference = cast(dict[str, object], root["gate12_reference"])
    reference["report_sha256"] = "0" * 64
    changed = tmp_path / "drift.json"
    changed.write_text(json.dumps(root), encoding="utf-8")

    with pytest.raises(
        MultiAgentRealComparisonValidationError,
        match="Gate 12.2 report reference drifted",
    ):
        load_multi_agent_real_comparison_dataset(changed)


def test_real_comparison_schema_drift_fails_closed(tmp_path: Path) -> None:
    """Unknown fixture fields must not be silently ignored."""
    raw: object = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    root = cast(dict[str, object], raw)
    root["unexpected"] = True
    changed = tmp_path / "schema.json"
    changed.write_text(json.dumps(root), encoding="utf-8")

    with pytest.raises(
        MultiAgentRealComparisonValidationError,
        match="fields do not match",
    ):
        load_multi_agent_real_comparison_dataset(changed)
