"""Strict loading and deterministic scoring for the Gate 12.2 comparison corpus."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import cast

from opslens.agent_baseline.domain.errors import AgentAuthorityValidationError
from opslens.agent_baseline.domain.models import AgentCapability, create_single_agent_task
from opslens.multi_agent.application.handoff import admit_multi_agent_handoff
from opslens.multi_agent.domain.comparison import (
    MULTI_AGENT_COMPARISON_CONTRACT_VERSION,
    PHASE11_REFERENCE_CORPUS_SHA256,
    PHASE11_REFERENCE_REPORT_SHA256,
    MultiAgentComparisonAdmissionOutcome,
    MultiAgentComparisonCase,
    MultiAgentComparisonCaseScore,
    MultiAgentComparisonDataset,
    MultiAgentComparisonExpectation,
    MultiAgentComparisonReport,
    create_multi_agent_comparison_case,
    create_multi_agent_comparison_dataset,
)
from opslens.multi_agent.domain.errors import (
    MultiAgentComparisonValidationError,
    MultiAgentHandoffAuthorizationError,
)
from opslens.multi_agent.domain.handoff import (
    MAX_SPECIALIST_CAPABILITIES,
    AgentSpecialization,
    MultiAgentHandoffAbstention,
    MultiAgentHandoffDecision,
    SpecialistAgentTask,
    create_multi_agent_handoff_proposal,
    create_triage_agent_task,
)


def _canonical_sha256(value: object) -> str:
    """Hash one canonical payload using the comparison identity encoding."""
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _mapping(value: object, *, label: str) -> dict[str, object]:
    """Require one JSON object with string keys."""
    if type(value) is not dict:
        raise MultiAgentComparisonValidationError(f"{label} must be an object")
    mapping = cast(dict[object, object], value)
    if any(type(key) is not str for key in mapping):
        raise MultiAgentComparisonValidationError(f"{label} keys must be strings")
    return cast(dict[str, object], mapping)


def _list(value: object, *, label: str) -> list[object]:
    """Require one JSON array."""
    if type(value) is not list:
        raise MultiAgentComparisonValidationError(f"{label} must be an array")
    return cast(list[object], value)


def _string(value: object, *, label: str) -> str:
    """Require one JSON string."""
    if type(value) is not str:
        raise MultiAgentComparisonValidationError(f"{label} must be a string")
    return value


def _optional_string(value: object, *, label: str) -> str | None:
    """Require one nullable JSON string."""
    if value is None:
        return None
    return _string(value, label=label)


def _exact_fields(
    mapping: dict[str, object],
    *,
    label: str,
    fields: frozenset[str],
) -> None:
    """Reject missing and unknown fixture fields so schema drift fails closed."""
    if frozenset(mapping) != fields:
        raise MultiAgentComparisonValidationError(
            f"{label} fields do not match the v1 comparison schema"
        )


def _capability(value: object, *, label: str) -> AgentCapability:
    """Parse one closed capability value."""
    raw = _string(value, label=label)
    try:
        return AgentCapability(raw)
    except ValueError:
        raise MultiAgentComparisonValidationError(f"{label} is unsupported") from None


def _capability_tuple(value: object, *, label: str) -> tuple[AgentCapability, ...]:
    """Parse one capability array and return canonical capability ordering."""
    raw = _list(value, label=label)
    capabilities = tuple(
        _capability(item, label=f"{label}[{index}]")
        for index, item in enumerate(raw)
    )
    return tuple(sorted(capabilities, key=lambda item: item.value))


def _decision(value: object, *, label: str) -> MultiAgentHandoffDecision:
    """Parse one closed handoff decision."""
    try:
        return MultiAgentHandoffDecision(_string(value, label=label))
    except ValueError:
        raise MultiAgentComparisonValidationError(f"{label} is unsupported") from None


def _specialization(value: object, *, label: str) -> AgentSpecialization | None:
    """Parse one nullable closed specialization value."""
    raw = _optional_string(value, label=label)
    if raw is None:
        return None
    try:
        return AgentSpecialization(raw)
    except ValueError:
        raise MultiAgentComparisonValidationError(f"{label} is unsupported") from None


def _admission_outcome(
    value: object,
    *,
    label: str,
) -> MultiAgentComparisonAdmissionOutcome:
    """Parse one closed expected admission outcome."""
    try:
        return MultiAgentComparisonAdmissionOutcome(_string(value, label=label))
    except ValueError:
        raise MultiAgentComparisonValidationError(f"{label} is unsupported") from None


def _case_from_json(value: object, *, index: int) -> MultiAgentComparisonCase:
    """Build one typed content-addressed comparison case from strict JSON."""
    label = f"cases[{index}]"
    case_raw = _mapping(value, label=label)
    _exact_fields(
        case_raw,
        label=label,
        fields=frozenset({"case_key", "expected", "proposal", "task"}),
    )

    task_raw = _mapping(case_raw["task"], label=f"{label}.task")
    _exact_fields(
        task_raw,
        label=f"{label}.task",
        fields=frozenset({"allowed_capabilities", "text"}),
    )
    allowed_capabilities = _capability_tuple(
        task_raw["allowed_capabilities"],
        label=f"{label}.task.allowed_capabilities",
    )
    try:
        task = create_single_agent_task(
            text=_string(task_raw["text"], label=f"{label}.task.text"),
            allowed_capabilities=allowed_capabilities,
        )
    except AgentAuthorityValidationError:
        raise MultiAgentComparisonValidationError(f"{label}.task is invalid") from None

    proposal_raw = _mapping(case_raw["proposal"], label=f"{label}.proposal")
    _exact_fields(
        proposal_raw,
        label=f"{label}.proposal",
        fields=frozenset({"decision", "target_specialization"}),
    )
    proposal = create_multi_agent_handoff_proposal(
        source_task_id=task.task_id,
        decision=_decision(proposal_raw["decision"], label=f"{label}.proposal.decision"),
        target_specialization=_specialization(
            proposal_raw["target_specialization"],
            label=f"{label}.proposal.target_specialization",
        ),
    )

    expected_raw = _mapping(case_raw["expected"], label=f"{label}.expected")
    _exact_fields(
        expected_raw,
        label=f"{label}.expected",
        fields=frozenset(
            {
                "admission_outcome",
                "decision",
                "target_capabilities",
                "target_specialization",
            }
        ),
    )
    expected = MultiAgentComparisonExpectation(
        decision=_decision(expected_raw["decision"], label=f"{label}.expected.decision"),
        target_specialization=_specialization(
            expected_raw["target_specialization"],
            label=f"{label}.expected.target_specialization",
        ),
        admission_outcome=_admission_outcome(
            expected_raw["admission_outcome"],
            label=f"{label}.expected.admission_outcome",
        ),
        target_capabilities=_capability_tuple(
            expected_raw["target_capabilities"],
            label=f"{label}.expected.target_capabilities",
        ),
    )
    return create_multi_agent_comparison_case(
        case_key=_string(case_raw["case_key"], label=f"{label}.case_key"),
        task=task,
        proposal=proposal,
        expected=expected,
    )


def load_multi_agent_comparison_dataset(path: Path) -> MultiAgentComparisonDataset:
    """Load the exact-schema frozen comparison fixture."""
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise MultiAgentComparisonValidationError(
            "multi-agent comparison dataset could not be loaded"
        ) from None
    root = _mapping(raw, label="dataset")
    _exact_fields(
        root,
        label="dataset",
        fields=frozenset({"cases", "contract_version", "phase11_reference"}),
    )
    contract_version = _string(root["contract_version"], label="dataset.contract_version")
    if contract_version != MULTI_AGENT_COMPARISON_CONTRACT_VERSION:
        raise MultiAgentComparisonValidationError(
            "comparison dataset contract_version is unsupported"
        )

    reference = _mapping(root["phase11_reference"], label="dataset.phase11_reference")
    _exact_fields(
        reference,
        label="dataset.phase11_reference",
        fields=frozenset({"corpus_sha256", "report_sha256"}),
    )
    corpus_sha256 = _string(
        reference["corpus_sha256"],
        label="dataset.phase11_reference.corpus_sha256",
    )
    report_sha256 = _string(
        reference["report_sha256"],
        label="dataset.phase11_reference.report_sha256",
    )
    if corpus_sha256 != PHASE11_REFERENCE_CORPUS_SHA256:
        raise MultiAgentComparisonValidationError("comparison fixture Phase 11 corpus drifted")
    if report_sha256 != PHASE11_REFERENCE_REPORT_SHA256:
        raise MultiAgentComparisonValidationError("comparison fixture Phase 11 report drifted")

    cases_raw = _list(root["cases"], label="dataset.cases")
    cases = tuple(
        _case_from_json(case_raw, index=index)
        for index, case_raw in enumerate(cases_raw)
    )
    return create_multi_agent_comparison_dataset(
        phase11_reference_corpus_sha256=corpus_sha256,
        phase11_reference_report_sha256=report_sha256,
        cases=cases,
    )


def _score_payload(
    *,
    case: MultiAgentComparisonCase,
    observed_decision: MultiAgentHandoffDecision,
    observed_specialization: AgentSpecialization | None,
    observed_admission_outcome: MultiAgentComparisonAdmissionOutcome,
    observed_target_capabilities: tuple[AgentCapability, ...],
    decision_match: bool,
    specialization_match: bool,
    admission_match: bool,
    target_scope_match: bool,
    non_broadening: bool,
    bounds_compliant: bool,
    passed: bool,
    source_capability_slots: int,
    specialist_capability_slots: int,
) -> dict[str, object]:
    """Return exact canonical semantics validated by the case-score domain contract."""
    return {
        "admission_match": admission_match,
        "bounds_compliant": bounds_compliant,
        "case_id": case.case_id,
        "case_key": case.case_key,
        "contract_version": MULTI_AGENT_COMPARISON_CONTRACT_VERSION,
        "decision_match": decision_match,
        "non_broadening": non_broadening,
        "observed_admission_outcome": observed_admission_outcome.value,
        "observed_decision": observed_decision.value,
        "observed_specialization": (
            observed_specialization.value if observed_specialization is not None else None
        ),
        "observed_target_capabilities": [
            item.value for item in observed_target_capabilities
        ],
        "passed": passed,
        "source_capability_slots": source_capability_slots,
        "specialist_capability_slots": specialist_capability_slots,
        "specialization_match": specialization_match,
        "target_scope_match": target_scope_match,
    }


def _score_case(case: MultiAgentComparisonCase) -> MultiAgentComparisonCaseScore:
    """Admit one synthetic proposal and score each deterministic dimension separately."""
    if type(case) is not MultiAgentComparisonCase:
        raise MultiAgentComparisonValidationError(
            "comparison scorer requires MultiAgentComparisonCase"
        )
    observed_decision = case.proposal.decision
    observed_specialization = case.proposal.target_specialization
    try:
        admitted = admit_multi_agent_handoff(
            source=create_triage_agent_task(task=case.task),
            proposal=case.proposal,
        )
    except MultiAgentHandoffAuthorizationError:
        observed_admission = MultiAgentComparisonAdmissionOutcome.REJECTED
        observed_target_capabilities: tuple[AgentCapability, ...] = ()
    else:
        if type(admitted) is SpecialistAgentTask:
            observed_admission = MultiAgentComparisonAdmissionOutcome.HANDOFF
            observed_target_capabilities = admitted.task.allowed_capabilities
        elif type(admitted) is MultiAgentHandoffAbstention:
            observed_admission = MultiAgentComparisonAdmissionOutcome.ABSTAINED
            observed_target_capabilities = ()
        else:
            raise MultiAgentComparisonValidationError(
                "handoff evaluator returned an unsupported admission result"
            )

    decision_match = observed_decision is case.expected.decision
    specialization_match = observed_specialization is case.expected.target_specialization
    admission_match = observed_admission is case.expected.admission_outcome
    target_scope_match = observed_target_capabilities == case.expected.target_capabilities
    non_broadening = set(observed_target_capabilities).issubset(case.task.allowed_capabilities)
    bounds_compliant = (
        len(observed_target_capabilities) <= MAX_SPECIALIST_CAPABILITIES
        and observed_admission
        in (
            MultiAgentComparisonAdmissionOutcome.HANDOFF,
            MultiAgentComparisonAdmissionOutcome.ABSTAINED,
            MultiAgentComparisonAdmissionOutcome.REJECTED,
        )
    )
    passed = all(
        (
            decision_match,
            specialization_match,
            admission_match,
            target_scope_match,
            non_broadening,
            bounds_compliant,
        )
    )
    source_slots = len(case.task.allowed_capabilities)
    specialist_slots = len(observed_target_capabilities)
    payload = _score_payload(
        case=case,
        observed_decision=observed_decision,
        observed_specialization=observed_specialization,
        observed_admission_outcome=observed_admission,
        observed_target_capabilities=observed_target_capabilities,
        decision_match=decision_match,
        specialization_match=specialization_match,
        admission_match=admission_match,
        target_scope_match=target_scope_match,
        non_broadening=non_broadening,
        bounds_compliant=bounds_compliant,
        passed=passed,
        source_capability_slots=source_slots,
        specialist_capability_slots=specialist_slots,
    )
    digest = _canonical_sha256(payload)
    return MultiAgentComparisonCaseScore(
        case_key=case.case_key,
        case_id=case.case_id,
        observed_decision=observed_decision,
        observed_specialization=observed_specialization,
        observed_admission_outcome=observed_admission,
        observed_target_capabilities=observed_target_capabilities,
        decision_match=decision_match,
        specialization_match=specialization_match,
        admission_match=admission_match,
        target_scope_match=target_scope_match,
        non_broadening=non_broadening,
        bounds_compliant=bounds_compliant,
        passed=passed,
        source_capability_slots=source_slots,
        specialist_capability_slots=specialist_slots,
        score_sha256=digest,
        score_id=f"{MULTI_AGENT_COMPARISON_CONTRACT_VERSION}:score:{digest}",
    )


def _report_payload(
    *,
    dataset: MultiAgentComparisonDataset,
    scores: tuple[MultiAgentComparisonCaseScore, ...],
    total_cases: int,
    passed_cases: int,
    decision_matches: int,
    specialization_matches: int,
    admission_matches: int,
    target_scope_matches: int,
    non_broadening_cases: int,
    bounds_compliant_cases: int,
    handoff_cases: int,
    abstention_cases: int,
    source_capability_slots_for_handoffs: int,
    specialist_capability_slots: int,
    capability_slots_removed: int,
) -> dict[str, object]:
    """Return exact canonical semantics validated by the report domain contract."""
    return {
        "abstention_cases": abstention_cases,
        "admission_matches": admission_matches,
        "bounds_compliant_cases": bounds_compliant_cases,
        "capability_slots_removed": capability_slots_removed,
        "case_score_ids": [score.score_id for score in scores],
        "client_elapsed_ms": None,
        "contract_version": MULTI_AGENT_COMPARISON_CONTRACT_VERSION,
        "dataset_id": dataset.dataset_id,
        "decision_matches": decision_matches,
        "handoff_cases": handoff_cases,
        "inference_cost_usd": None,
        "input_tokens": None,
        "model_invocation_count": None,
        "non_broadening_cases": non_broadening_cases,
        "offline_capability_executions": 0,
        "output_tokens": None,
        "passed_cases": passed_cases,
        "phase11_reference_corpus_sha256": dataset.phase11_reference_corpus_sha256,
        "phase11_reference_report_sha256": dataset.phase11_reference_report_sha256,
        "provider_latency_ms": None,
        "sdk_retries": None,
        "source_capability_slots_for_handoffs": source_capability_slots_for_handoffs,
        "specialist_capability_slots": specialist_capability_slots,
        "specialization_matches": specialization_matches,
        "target_scope_matches": target_scope_matches,
        "total_cases": total_cases,
        "total_tokens": None,
    }


def evaluate_multi_agent_comparison_dataset(
    dataset: MultiAgentComparisonDataset,
) -> MultiAgentComparisonReport:
    """Evaluate the frozen synthetic proposals without invoking any model or executor."""
    if type(dataset) is not MultiAgentComparisonDataset:
        raise MultiAgentComparisonValidationError(
            "dataset must be MultiAgentComparisonDataset"
        )
    scores = tuple(_score_case(case) for case in dataset.cases)
    total_cases = len(scores)
    passed_cases = sum(score.passed for score in scores)
    decision_matches = sum(score.decision_match for score in scores)
    specialization_matches = sum(score.specialization_match for score in scores)
    admission_matches = sum(score.admission_match for score in scores)
    target_scope_matches = sum(score.target_scope_match for score in scores)
    non_broadening_cases = sum(score.non_broadening for score in scores)
    bounds_compliant_cases = sum(score.bounds_compliant for score in scores)
    handoff_scores = tuple(
        score
        for score in scores
        if score.observed_admission_outcome is MultiAgentComparisonAdmissionOutcome.HANDOFF
    )
    handoff_cases = len(handoff_scores)
    abstention_cases = sum(
        score.observed_admission_outcome is MultiAgentComparisonAdmissionOutcome.ABSTAINED
        for score in scores
    )
    source_capability_slots_for_handoffs = sum(
        score.source_capability_slots for score in handoff_scores
    )
    specialist_capability_slots = sum(
        score.specialist_capability_slots for score in handoff_scores
    )
    capability_slots_removed = (
        source_capability_slots_for_handoffs - specialist_capability_slots
    )
    payload = _report_payload(
        dataset=dataset,
        scores=scores,
        total_cases=total_cases,
        passed_cases=passed_cases,
        decision_matches=decision_matches,
        specialization_matches=specialization_matches,
        admission_matches=admission_matches,
        target_scope_matches=target_scope_matches,
        non_broadening_cases=non_broadening_cases,
        bounds_compliant_cases=bounds_compliant_cases,
        handoff_cases=handoff_cases,
        abstention_cases=abstention_cases,
        source_capability_slots_for_handoffs=source_capability_slots_for_handoffs,
        specialist_capability_slots=specialist_capability_slots,
        capability_slots_removed=capability_slots_removed,
    )
    digest = _canonical_sha256(payload)
    return MultiAgentComparisonReport(
        dataset_id=dataset.dataset_id,
        phase11_reference_corpus_sha256=dataset.phase11_reference_corpus_sha256,
        phase11_reference_report_sha256=dataset.phase11_reference_report_sha256,
        case_scores=scores,
        total_cases=total_cases,
        passed_cases=passed_cases,
        decision_matches=decision_matches,
        specialization_matches=specialization_matches,
        admission_matches=admission_matches,
        target_scope_matches=target_scope_matches,
        non_broadening_cases=non_broadening_cases,
        bounds_compliant_cases=bounds_compliant_cases,
        handoff_cases=handoff_cases,
        abstention_cases=abstention_cases,
        source_capability_slots_for_handoffs=source_capability_slots_for_handoffs,
        specialist_capability_slots=specialist_capability_slots,
        capability_slots_removed=capability_slots_removed,
        offline_capability_executions=0,
        model_invocation_count=None,
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
        provider_latency_ms=None,
        client_elapsed_ms=None,
        sdk_retries=None,
        inference_cost_usd=None,
        report_sha256=digest,
        report_id=f"{MULTI_AGENT_COMPARISON_CONTRACT_VERSION}:report:{digest}",
    )


__all__ = [
    "evaluate_multi_agent_comparison_dataset",
    "load_multi_agent_comparison_dataset",
]
