"""Strict loading and deterministic scoring for the Gate 11.4 reasoning corpus."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from opslens.agent_baseline.application.reasoning import reason_about_task
from opslens.agent_baseline.domain.errors import (
    AgentAuthorityValidationError,
    AgentEvaluationValidationError,
)
from opslens.agent_baseline.domain.models import (
    AgentCapability,
    AgentDecision,
    create_single_agent_task,
)
from opslens.agent_baseline.domain.reasoning import AgentReasoningAuthorizationOutcome
from opslens.agent_baseline.domain.reasoning_evaluation import (
    SINGLE_AGENT_REASONING_EVALUATION_CONTRACT_VERSION,
    AgentReasoningCaseScore,
    AgentReasoningEvaluationCase,
    AgentReasoningEvaluationDataset,
    AgentReasoningEvaluationReport,
    AgentReasoningExpectation,
)
from opslens.agent_baseline.ports.reasoning import AgentReasoningModel


def _mapping(value: object, *, label: str) -> dict[str, object]:
    """Require one JSON object with string keys."""
    if type(value) is not dict:
        raise AgentEvaluationValidationError(f"{label} must be an object")
    mapping = cast(dict[object, object], value)
    if any(type(key) is not str for key in mapping):
        raise AgentEvaluationValidationError(f"{label} keys must be strings")
    return cast(dict[str, object], mapping)


def _list(value: object, *, label: str) -> list[object]:
    """Require one JSON array."""
    if type(value) is not list:
        raise AgentEvaluationValidationError(f"{label} must be an array")
    return cast(list[object], value)


def _string(value: object, *, label: str) -> str:
    """Require one JSON string."""
    if type(value) is not str:
        raise AgentEvaluationValidationError(f"{label} must be a string")
    return value


def _exact_fields(
    mapping: dict[str, object],
    *,
    label: str,
    fields: frozenset[str],
) -> None:
    """Reject missing and unknown fixture fields so schema drift fails closed."""
    if frozenset(mapping) != fields:
        raise AgentEvaluationValidationError(f"{label} fields do not match the v1 schema")


def _capability(value: object, *, label: str) -> AgentCapability:
    """Parse one closed capability value."""
    raw = _string(value, label=label)
    try:
        return AgentCapability(raw)
    except ValueError:
        raise AgentEvaluationValidationError(f"{label} is unsupported") from None


def _optional_capability(value: object, *, label: str) -> AgentCapability | None:
    """Parse one nullable closed capability value."""
    if value is None:
        return None
    return _capability(value, label=label)


def _case_from_json(value: object, *, index: int) -> AgentReasoningEvaluationCase:
    """Build one typed content-addressed reasoning case from strict JSON."""
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
        _capability(item, label=f"{label}.task.allowed_capabilities[{item_index}]")
        for item_index, item in enumerate(capabilities_raw)
    )
    try:
        task = create_single_agent_task(
            text=_string(task_raw["text"], label=f"{label}.task.text"),
            allowed_capabilities=capabilities,
        )
    except AgentAuthorityValidationError:
        raise AgentEvaluationValidationError(f"{label}.task is invalid") from None

    expected_raw = _mapping(case_raw["expected"], label=f"{label}.expected")
    _exact_fields(
        expected_raw,
        label=f"{label}.expected",
        fields=frozenset({"authorization_outcome", "capability", "decision"}),
    )
    try:
        decision = AgentDecision(
            _string(expected_raw["decision"], label=f"{label}.expected.decision")
        )
        authorization_outcome = AgentReasoningAuthorizationOutcome(
            _string(
                expected_raw["authorization_outcome"],
                label=f"{label}.expected.authorization_outcome",
            )
        )
    except ValueError:
        raise AgentEvaluationValidationError(
            f"{label}.expected contains unsupported outcome"
        ) from None

    expectation = AgentReasoningExpectation(
        decision=decision,
        capability=_optional_capability(
            expected_raw["capability"],
            label=f"{label}.expected.capability",
        ),
        authorization_outcome=authorization_outcome,
    )
    return AgentReasoningEvaluationCase.create(
        case_key=_string(case_raw["case_key"], label=f"{label}.case_key"),
        task=task,
        expectation=expectation,
    )


def load_agent_reasoning_evaluation_dataset(
    path: Path,
) -> AgentReasoningEvaluationDataset:
    """Load one exact-schema reasoning corpus into typed content-addressed cases."""
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise AgentEvaluationValidationError(
            "reasoning evaluation dataset could not be loaded"
        ) from None
    root = _mapping(raw, label="dataset")
    _exact_fields(
        root,
        label="dataset",
        fields=frozenset({"cases", "contract_version"}),
    )
    contract_version = _string(root["contract_version"], label="dataset.contract_version")
    if contract_version != SINGLE_AGENT_REASONING_EVALUATION_CONTRACT_VERSION:
        raise AgentEvaluationValidationError(
            "reasoning evaluation dataset contract_version is unsupported"
        )
    cases_raw = _list(root["cases"], label="dataset.cases")
    cases = tuple(_case_from_json(value, index=index) for index, value in enumerate(cases_raw))
    return AgentReasoningEvaluationDataset.create(cases=cases)


def evaluate_agent_reasoning_dataset(
    dataset: AgentReasoningEvaluationDataset,
    *,
    model: AgentReasoningModel,
) -> AgentReasoningEvaluationReport:
    """Run each golden task once and compute deterministic decomposed proposal metrics."""
    if type(dataset) is not AgentReasoningEvaluationDataset:
        raise AgentEvaluationValidationError(
            "dataset must be AgentReasoningEvaluationDataset"
        )
    scores = tuple(
        AgentReasoningCaseScore.create(
            case=case,
            result=reason_about_task(task=case.task, model=model),
        )
        for case in dataset.cases
    )
    return AgentReasoningEvaluationReport.create(dataset=dataset, scores=scores)


__all__ = [
    "evaluate_agent_reasoning_dataset",
    "load_agent_reasoning_evaluation_dataset",
]
