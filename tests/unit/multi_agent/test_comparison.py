"""Tests for the Gate 12.2 deterministic multi-agent comparison contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from opslens.agent_baseline.domain.models import (
    AgentCapability,
    create_single_agent_task,
)
from opslens.multi_agent.application.comparison import (
    evaluate_multi_agent_comparison_dataset,
    load_multi_agent_comparison_dataset,
)
from opslens.multi_agent.domain.comparison import (
    MULTI_AGENT_COMPARISON_CONTRACT_VERSION,
    PHASE11_REFERENCE_CORPUS_SHA256,
    PHASE11_REFERENCE_REPORT_SHA256,
    MultiAgentComparisonAdmissionOutcome,
    MultiAgentComparisonExpectation,
    create_multi_agent_comparison_case,
    create_multi_agent_comparison_dataset,
)
from opslens.multi_agent.domain.errors import MultiAgentComparisonValidationError
from opslens.multi_agent.domain.handoff import (
    AgentSpecialization,
    MultiAgentHandoffDecision,
    create_multi_agent_handoff_proposal,
)

_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "multi_agent"
    / "golden_multi_agent_comparison_v1.json"
)


def test_frozen_fixture_binds_exact_phase11_reference_and_contract() -> None:
    """The comparison corpus must remain bound to the exact Phase 11 evidence."""
    dataset = load_multi_agent_comparison_dataset(_FIXTURE)

    assert MULTI_AGENT_COMPARISON_CONTRACT_VERSION == "multi-agent-comparison:v1"
    assert dataset.phase11_reference_corpus_sha256 == PHASE11_REFERENCE_CORPUS_SHA256
    assert dataset.phase11_reference_report_sha256 == PHASE11_REFERENCE_REPORT_SHA256
    assert len(dataset.cases) == 6
    assert dataset.dataset_id.startswith("multi-agent-comparison:v1:dataset:")


def test_frozen_synthetic_fixture_has_full_deterministic_conformance() -> None:
    """Synthetic proposal conformance must score separately from future model quality."""
    dataset = load_multi_agent_comparison_dataset(_FIXTURE)
    report = evaluate_multi_agent_comparison_dataset(dataset)

    assert report.total_cases == 6
    assert report.passed_cases == 6
    assert report.decision_matches == 6
    assert report.specialization_matches == 6
    assert report.admission_matches == 6
    assert report.target_scope_matches == 6
    assert report.non_broadening_cases == 6
    assert report.bounds_compliant_cases == 6
    assert report.handoff_cases == 4
    assert report.abstention_cases == 2
    assert report.source_capability_slots_for_handoffs == 16
    assert report.specialist_capability_slots == 8
    assert report.capability_slots_removed == 8
    assert report.offline_capability_executions == 0
    assert report.report_id.startswith("multi-agent-comparison:v1:report:")


def test_offline_report_does_not_manufacture_runtime_measurements() -> None:
    """Gate 12.2 runtime metrics must remain null until a real experiment exists."""
    report = evaluate_multi_agent_comparison_dataset(
        load_multi_agent_comparison_dataset(_FIXTURE)
    )

    assert report.model_invocation_count is None
    assert report.input_tokens is None
    assert report.output_tokens is None
    assert report.total_tokens is None
    assert report.provider_latency_ms is None
    assert report.client_elapsed_ms is None
    assert report.sdk_retries is None
    assert report.inference_cost_usd is None


def test_wrong_synthetic_specialization_is_visible_without_hiding_bounds(
    tmp_path: Path,
) -> None:
    """A wrong route must fail quality dimensions while preserving independent bounds evidence."""
    raw: object = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    root = cast(dict[str, object], raw)
    cases = cast(list[object], root["cases"])
    first_case = cast(dict[str, object], cases[0])
    proposal = cast(dict[str, object], first_case["proposal"])
    proposal["target_specialization"] = "guidance_synthesis"
    changed = tmp_path / "wrong-specialization.json"
    changed.write_text(json.dumps(root), encoding="utf-8")

    report = evaluate_multi_agent_comparison_dataset(
        load_multi_agent_comparison_dataset(changed)
    )

    assert report.total_cases == 6
    assert report.passed_cases == 5
    assert report.decision_matches == 6
    assert report.specialization_matches == 5
    assert report.admission_matches == 6
    assert report.target_scope_matches == 5
    assert report.non_broadening_cases == 6
    assert report.bounds_compliant_cases == 6


def test_authorization_rejection_is_a_scored_fail_closed_outcome() -> None:
    """Disjoint specialization authority should be measurable without a specialist task."""
    task = create_single_agent_task(
        text="Use structured evidence even though only guidance authority is admitted.",
        allowed_capabilities=(AgentCapability.KNOWLEDGE_GUIDANCE,),
    )
    proposal = create_multi_agent_handoff_proposal(
        source_task_id=task.task_id,
        decision=MultiAgentHandoffDecision.HANDOFF,
        target_specialization=AgentSpecialization.EVIDENCE_ANALYSIS,
    )
    case = create_multi_agent_comparison_case(
        case_key="expected-rejection",
        task=task,
        proposal=proposal,
        expected=MultiAgentComparisonExpectation(
            decision=MultiAgentHandoffDecision.HANDOFF,
            target_specialization=AgentSpecialization.EVIDENCE_ANALYSIS,
            admission_outcome=MultiAgentComparisonAdmissionOutcome.REJECTED,
            target_capabilities=(),
        ),
    )
    dataset = create_multi_agent_comparison_dataset(
        phase11_reference_corpus_sha256=PHASE11_REFERENCE_CORPUS_SHA256,
        phase11_reference_report_sha256=PHASE11_REFERENCE_REPORT_SHA256,
        cases=(case,),
    )

    report = evaluate_multi_agent_comparison_dataset(dataset)

    assert report.passed_cases == 1
    assert report.handoff_cases == 0
    assert report.abstention_cases == 0
    assert report.case_scores[0].observed_admission_outcome is (
        MultiAgentComparisonAdmissionOutcome.REJECTED
    )
    assert report.case_scores[0].observed_target_capabilities == ()
    assert report.case_scores[0].non_broadening is True
    assert report.case_scores[0].bounds_compliant is True


def test_comparison_dataset_rejects_phase11_reference_drift(tmp_path: Path) -> None:
    """Historical single-agent evidence cannot be silently rebound by a later fixture."""
    raw: object = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    root = cast(dict[str, object], raw)
    reference = cast(dict[str, object], root["phase11_reference"])
    reference["report_sha256"] = "0" * 64
    changed = tmp_path / "reference-drift.json"
    changed.write_text(json.dumps(root), encoding="utf-8")

    with pytest.raises(
        MultiAgentComparisonValidationError,
        match="Phase 11 report drifted",
    ):
        load_multi_agent_comparison_dataset(changed)


def test_comparison_fixture_rejects_unknown_schema_fields(tmp_path: Path) -> None:
    """Fixture schema drift must fail closed instead of being ignored."""
    raw: object = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    root = cast(dict[str, object], raw)
    root["unexpected"] = True
    changed = tmp_path / "schema-drift.json"
    changed.write_text(json.dumps(root), encoding="utf-8")

    with pytest.raises(
        MultiAgentComparisonValidationError,
        match="fields do not match",
    ):
        load_multi_agent_comparison_dataset(changed)


def test_comparison_dataset_and_report_identities_are_repeatable() -> None:
    """Equivalent frozen inputs must produce identical content-addressed evidence."""
    first_dataset = load_multi_agent_comparison_dataset(_FIXTURE)
    second_dataset = load_multi_agent_comparison_dataset(_FIXTURE)
    first_report = evaluate_multi_agent_comparison_dataset(first_dataset)
    second_report = evaluate_multi_agent_comparison_dataset(second_dataset)

    assert first_dataset.dataset_sha256 == second_dataset.dataset_sha256
    assert first_dataset.dataset_id == second_dataset.dataset_id
    assert first_report.report_sha256 == second_report.report_sha256
    assert first_report.report_id == second_report.report_id
