"""Strict loader for the content-addressed Gate 11.3 offline evaluation corpus."""

import json
from pathlib import Path
from typing import cast

from opslens.agent_baseline.domain.errors import (
    AgentAuthorityValidationError,
    AgentEvaluationValidationError,
)
from opslens.agent_baseline.domain.evaluation import (
    SINGLE_AGENT_EVALUATION_CONTRACT_VERSION,
    AgentEvaluationAuthorizationOutcome,
    AgentEvaluationCase,
    AgentEvaluationDataset,
    AgentEvaluationExecutionMode,
    AgentEvaluationExecutionOutcome,
    AgentEvaluationExpectation,
    AgentEvaluationFailureCategory,
)
from opslens.agent_baseline.domain.models import (
    AgentCapability,
    AgentDecision,
    create_agent_action_proposal,
    create_single_agent_task,
)


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


def _failure_category(
    value: object,
    *,
    label: str,
) -> AgentEvaluationFailureCategory | None:
    """Parse one nullable stable evaluation failure category."""
    if value is None:
        return None
    raw = _string(value, label=label)
    try:
        return AgentEvaluationFailureCategory(raw)
    except ValueError:
        raise AgentEvaluationValidationError(f"{label} is unsupported") from None


def _case_from_json(value: object, *, index: int) -> AgentEvaluationCase:
    """Build one typed content-addressed evaluation case from strict JSON."""
    label = f"cases[{index}]"
    case_raw = _mapping(value, label=label)
    _exact_fields(
        case_raw,
        label=label,
        fields=frozenset({"case_key", "execution_mode", "expected", "proposal", "task"}),
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

    proposal_raw = _mapping(case_raw["proposal"], label=f"{label}.proposal")
    _exact_fields(
        proposal_raw,
        label=f"{label}.proposal",
        fields=frozenset({"capability", "decision"}),
    )
    decision_raw = _string(proposal_raw["decision"], label=f"{label}.proposal.decision")
    try:
        decision = AgentDecision(decision_raw)
    except ValueError:
        raise AgentEvaluationValidationError(
            f"{label}.proposal.decision is unsupported"
        ) from None
    try:
        proposal = create_agent_action_proposal(
            task_id=task.task_id,
            decision=decision,
            capability=_optional_capability(
                proposal_raw["capability"],
                label=f"{label}.proposal.capability",
            ),
        )
    except AgentAuthorityValidationError:
        raise AgentEvaluationValidationError(f"{label}.proposal is invalid") from None

    expected_raw = _mapping(case_raw["expected"], label=f"{label}.expected")
    _exact_fields(
        expected_raw,
        label=f"{label}.expected",
        fields=frozenset(
            {"authorization_outcome", "capability", "execution_outcome", "failure_category"}
        ),
    )
    try:
        authorization_outcome = AgentEvaluationAuthorizationOutcome(
            _string(
                expected_raw["authorization_outcome"],
                label=f"{label}.expected.authorization_outcome",
            )
        )
        execution_outcome = AgentEvaluationExecutionOutcome(
            _string(
                expected_raw["execution_outcome"],
                label=f"{label}.expected.execution_outcome",
            )
        )
    except ValueError:
        raise AgentEvaluationValidationError(
            f"{label}.expected contains unsupported outcome"
        ) from None
    expectation = AgentEvaluationExpectation(
        authorization_outcome=authorization_outcome,
        capability=_optional_capability(
            expected_raw["capability"],
            label=f"{label}.expected.capability",
        ),
        execution_outcome=execution_outcome,
        failure_category=_failure_category(
            expected_raw["failure_category"],
            label=f"{label}.expected.failure_category",
        ),
    )

    execution_mode_raw = _string(
        case_raw["execution_mode"],
        label=f"{label}.execution_mode",
    )
    try:
        execution_mode = AgentEvaluationExecutionMode(execution_mode_raw)
    except ValueError:
        raise AgentEvaluationValidationError(f"{label}.execution_mode is unsupported") from None

    return AgentEvaluationCase.create(
        case_key=_string(case_raw["case_key"], label=f"{label}.case_key"),
        task=task,
        proposal=proposal,
        execution_mode=execution_mode,
        expectation=expectation,
    )


def load_agent_evaluation_dataset(path: Path) -> AgentEvaluationDataset:
    """Load one exact-schema JSON corpus and return typed content-addressed cases."""
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise AgentEvaluationValidationError("evaluation dataset could not be loaded") from None
    root = _mapping(raw, label="dataset")
    _exact_fields(
        root,
        label="dataset",
        fields=frozenset({"cases", "contract_version"}),
    )
    contract_version = _string(root["contract_version"], label="dataset.contract_version")
    if contract_version != SINGLE_AGENT_EVALUATION_CONTRACT_VERSION:
        raise AgentEvaluationValidationError("evaluation dataset contract_version is unsupported")
    cases_raw = _list(root["cases"], label="dataset.cases")
    cases = tuple(_case_from_json(value, index=index) for index, value in enumerate(cases_raw))
    return AgentEvaluationDataset.create(cases=cases)


__all__ = ["load_agent_evaluation_dataset"]
