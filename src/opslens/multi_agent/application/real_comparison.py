"""Strict loading and deterministic execution for the first real two-model corpus."""

import json
from pathlib import Path
from typing import cast

from opslens.agent_baseline.domain.errors import AgentAuthorityValidationError
from opslens.agent_baseline.domain.models import (
    AgentCapability,
    create_single_agent_task,
)
from opslens.agent_baseline.ports.reasoning import AgentReasoningModel
from opslens.multi_agent.application.two_model_reasoning import run_two_model_reasoning
from opslens.multi_agent.domain.comparison import (
    PHASE11_REFERENCE_CORPUS_SHA256,
    PHASE11_REFERENCE_REPORT_SHA256,
    MultiAgentComparisonAdmissionOutcome,
)
from opslens.multi_agent.domain.errors import MultiAgentRealComparisonValidationError
from opslens.multi_agent.domain.handoff import (
    AgentSpecialization,
    MultiAgentHandoffDecision,
)
from opslens.multi_agent.domain.real_comparison import (
    GATE12_REFERENCE_DATASET_SHA256,
    GATE12_REFERENCE_REPORT_SHA256,
    MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION,
    MultiAgentRealComparisonCase,
    MultiAgentRealComparisonCaseScore,
    MultiAgentRealComparisonDataset,
    MultiAgentRealComparisonExpectation,
    MultiAgentRealComparisonReport,
)
from opslens.multi_agent.ports.triage_reasoning import MultiAgentTriageReasoningModel


def _mapping(value: object, *, label: str) -> dict[str, object]:
    """Require one JSON object with string keys."""
    if type(value) is not dict:
        raise MultiAgentRealComparisonValidationError(f"{label} must be an object")
    mapping = cast(dict[object, object], value)
    if any(type(key) is not str for key in mapping):
        raise MultiAgentRealComparisonValidationError(f"{label} keys must be strings")
    return cast(dict[str, object], mapping)


def _list(value: object, *, label: str) -> list[object]:
    """Require one JSON array."""
    if type(value) is not list:
        raise MultiAgentRealComparisonValidationError(f"{label} must be an array")
    return cast(list[object], value)


def _string(value: object, *, label: str) -> str:
    """Require one JSON string."""
    if type(value) is not str:
        raise MultiAgentRealComparisonValidationError(f"{label} must be a string")
    return value


def _exact_fields(
    mapping: dict[str, object],
    *,
    label: str,
    fields: frozenset[str],
) -> None:
    """Reject missing and unknown fixture fields."""
    if frozenset(mapping) != fields:
        raise MultiAgentRealComparisonValidationError(
            f"{label} fields do not match the v1 schema"
        )


def _capability(value: object, *, label: str) -> AgentCapability:
    """Parse one closed capability value."""
    raw = _string(value, label=label)
    try:
        return AgentCapability(raw)
    except ValueError:
        raise MultiAgentRealComparisonValidationError(
            f"{label} is unsupported"
        ) from None


def _optional_capability(value: object, *, label: str) -> AgentCapability | None:
    """Parse one nullable capability value."""
    if value is None:
        return None
    return _capability(value, label=label)


def _optional_specialization(
    value: object,
    *,
    label: str,
) -> AgentSpecialization | None:
    """Parse one nullable closed specialization value."""
    if value is None:
        return None
    raw = _string(value, label=label)
    try:
        return AgentSpecialization(raw)
    except ValueError:
        raise MultiAgentRealComparisonValidationError(
            f"{label} is unsupported"
        ) from None


def _case_from_json(value: object, *, index: int) -> MultiAgentRealComparisonCase:
    """Build one typed real-comparison case from strict JSON."""
    label = f"cases[{index}]"
    case_raw = _mapping(value, label=label)
    _exact_fields(
        case_raw,
        label=label,
        fields=frozenset({"case_key", "expected", "task"}),
    )

    task_raw = _mapping(case_raw["task"], label=f"{label}.task")
    _exact_fields(
        task_raw,
        label=f"{label}.task",
        fields=frozenset({"allowed_capabilities", "text"}),
    )
    capabilities_raw = _list(
        task_raw["allowed_capabilities"],
        label=f"{label}.task.allowed_capabilities",
    )
    capabilities = tuple(
        _capability(
            item,
            label=f"{label}.task.allowed_capabilities[{item_index}]",
        )
        for item_index, item in enumerate(capabilities_raw)
    )
    try:
        task = create_single_agent_task(
            text=_string(task_raw["text"], label=f"{label}.task.text"),
            allowed_capabilities=capabilities,
        )
    except AgentAuthorityValidationError:
        raise MultiAgentRealComparisonValidationError(
            f"{label}.task is invalid"
        ) from None

    expected_raw = _mapping(case_raw["expected"], label=f"{label}.expected")
    _exact_fields(
        expected_raw,
        label=f"{label}.expected",
        fields=frozenset(
            {
                "admission_outcome",
                "specialist_capability",
                "target_capabilities",
                "target_specialization",
                "triage_decision",
            }
        ),
    )
    try:
        triage_decision = MultiAgentHandoffDecision(
            _string(
                expected_raw["triage_decision"],
                label=f"{label}.expected.triage_decision",
            )
        )
        admission_outcome = MultiAgentComparisonAdmissionOutcome(
            _string(
                expected_raw["admission_outcome"],
                label=f"{label}.expected.admission_outcome",
            )
        )
    except ValueError:
        raise MultiAgentRealComparisonValidationError(
            f"{label}.expected contains an unsupported outcome"
        ) from None

    target_capabilities_raw = _list(
        expected_raw["target_capabilities"],
        label=f"{label}.expected.target_capabilities",
    )
    target_capabilities = tuple(
        sorted(
            (
                _capability(
                    item,
                    label=f"{label}.expected.target_capabilities[{item_index}]",
                )
                for item_index, item in enumerate(target_capabilities_raw)
            ),
            key=lambda item: item.value,
        )
    )
    expectation = MultiAgentRealComparisonExpectation(
        triage_decision=triage_decision,
        target_specialization=_optional_specialization(
            expected_raw["target_specialization"],
            label=f"{label}.expected.target_specialization",
        ),
        admission_outcome=admission_outcome,
        target_capabilities=target_capabilities,
        specialist_capability=_optional_capability(
            expected_raw["specialist_capability"],
            label=f"{label}.expected.specialist_capability",
        ),
    )
    return MultiAgentRealComparisonCase.create(
        case_key=_string(case_raw["case_key"], label=f"{label}.case_key"),
        task=task,
        expected=expectation,
    )


def load_multi_agent_real_comparison_dataset(
    path: Path,
) -> MultiAgentRealComparisonDataset:
    """Load the exact-schema real experiment corpus with frozen reference bindings."""
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise MultiAgentRealComparisonValidationError(
            "real comparison dataset could not be loaded"
        ) from None
    root = _mapping(raw, label="dataset")
    _exact_fields(
        root,
        label="dataset",
        fields=frozenset(
            {
                "cases",
                "contract_version",
                "gate12_reference",
                "phase11_reference",
            }
        ),
    )
    if _string(root["contract_version"], label="dataset.contract_version") != (
        MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION
    ):
        raise MultiAgentRealComparisonValidationError(
            "real comparison contract_version is unsupported"
        )

    phase11 = _mapping(root["phase11_reference"], label="dataset.phase11_reference")
    _exact_fields(
        phase11,
        label="dataset.phase11_reference",
        fields=frozenset({"corpus_sha256", "report_sha256"}),
    )
    if phase11["corpus_sha256"] != PHASE11_REFERENCE_CORPUS_SHA256:
        raise MultiAgentRealComparisonValidationError("Phase 11 corpus reference drifted")
    if phase11["report_sha256"] != PHASE11_REFERENCE_REPORT_SHA256:
        raise MultiAgentRealComparisonValidationError("Phase 11 report reference drifted")

    gate12 = _mapping(root["gate12_reference"], label="dataset.gate12_reference")
    _exact_fields(
        gate12,
        label="dataset.gate12_reference",
        fields=frozenset({"dataset_sha256", "report_sha256"}),
    )
    if gate12["dataset_sha256"] != GATE12_REFERENCE_DATASET_SHA256:
        raise MultiAgentRealComparisonValidationError(
            "Gate 12.2 dataset reference drifted"
        )
    if gate12["report_sha256"] != GATE12_REFERENCE_REPORT_SHA256:
        raise MultiAgentRealComparisonValidationError(
            "Gate 12.2 report reference drifted"
        )

    cases_raw = _list(root["cases"], label="dataset.cases")
    cases = tuple(
        _case_from_json(value, index=index)
        for index, value in enumerate(cases_raw)
    )
    return MultiAgentRealComparisonDataset.create(cases=cases)


def evaluate_multi_agent_real_comparison_dataset(
    dataset: MultiAgentRealComparisonDataset,
    *,
    triage_model: MultiAgentTriageReasoningModel,
    specialist_model: AgentReasoningModel,
) -> MultiAgentRealComparisonReport:
    """Run each frozen task through at most two models and score deterministically."""
    if type(dataset) is not MultiAgentRealComparisonDataset:
        raise MultiAgentRealComparisonValidationError(
            "dataset must be MultiAgentRealComparisonDataset"
        )
    scores = tuple(
        MultiAgentRealComparisonCaseScore.create(
            case=case,
            result=run_two_model_reasoning(
                task=case.task,
                triage_model=triage_model,
                specialist_model=specialist_model,
            ),
        )
        for case in dataset.cases
    )
    return MultiAgentRealComparisonReport.create(dataset=dataset, scores=scores)


__all__ = [
    "evaluate_multi_agent_real_comparison_dataset",
    "load_multi_agent_real_comparison_dataset",
]
