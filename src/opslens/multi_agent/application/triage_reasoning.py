"""Bounded triage reasoning orchestration before deterministic handoff admission."""

import json
from collections.abc import Mapping
from typing import cast

from opslens.agent_baseline.domain.models import SingleAgentTask
from opslens.multi_agent.domain.errors import MultiAgentTriageReasoningValidationError
from opslens.multi_agent.domain.handoff import (
    AgentSpecialization,
    MultiAgentHandoffDecision,
    MultiAgentHandoffProposal,
    create_multi_agent_handoff_proposal,
)
from opslens.multi_agent.domain.triage_reasoning import (
    MAX_MULTI_AGENT_TRIAGE_OUTPUT_UTF8_BYTES,
    MultiAgentTriageReasoningResult,
)
from opslens.multi_agent.ports.triage_reasoning import (
    MultiAgentTriageReasoningModel,
    MultiAgentTriageReasoningModelResponse,
)

_TRIAGE_OUTPUT_KEYS = frozenset({"decision", "target_specialization"})


def parse_triage_model_output(
    *,
    task: SingleAgentTask,
    output_text: str,
) -> MultiAgentHandoffProposal:
    """Parse untrusted triage output into the existing handoff proposal contract."""
    if type(task) is not SingleAgentTask:
        raise MultiAgentTriageReasoningValidationError(
            "task must be one admitted SingleAgentTask"
        )
    if type(output_text) is not str:
        raise MultiAgentTriageReasoningValidationError("model output must be a string")
    if not output_text.strip():
        raise MultiAgentTriageReasoningValidationError("model output cannot be blank")
    if len(output_text.encode("utf-8")) > MAX_MULTI_AGENT_TRIAGE_OUTPUT_UTF8_BYTES:
        raise MultiAgentTriageReasoningValidationError(
            "model output exceeds the triage byte limit"
        )

    try:
        loaded: object = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise MultiAgentTriageReasoningValidationError(
            "model output is not valid JSON"
        ) from exc
    if not isinstance(loaded, Mapping):
        raise MultiAgentTriageReasoningValidationError(
            "model output must be one JSON object"
        )
    payload = cast(Mapping[object, object], loaded)
    if any(type(key) is not str for key in payload):
        raise MultiAgentTriageReasoningValidationError(
            "model output keys must be strings"
        )
    typed_payload = cast(Mapping[str, object], payload)
    if frozenset(typed_payload) != _TRIAGE_OUTPUT_KEYS:
        raise MultiAgentTriageReasoningValidationError(
            "model output must contain exactly decision and target_specialization"
        )

    raw_decision = typed_payload["decision"]
    if type(raw_decision) is not str:
        raise MultiAgentTriageReasoningValidationError("decision must be a string")
    try:
        decision = MultiAgentHandoffDecision(raw_decision)
    except ValueError as exc:
        raise MultiAgentTriageReasoningValidationError(
            "decision is not supported"
        ) from exc

    raw_specialization = typed_payload["target_specialization"]
    specialization: AgentSpecialization | None
    if raw_specialization is None:
        specialization = None
    elif type(raw_specialization) is str:
        try:
            specialization = AgentSpecialization(raw_specialization)
        except ValueError as exc:
            raise MultiAgentTriageReasoningValidationError(
                "target_specialization is not supported"
            ) from exc
    else:
        raise MultiAgentTriageReasoningValidationError(
            "target_specialization must be a string or null"
        )

    if decision is MultiAgentHandoffDecision.HANDOFF and specialization is None:
        raise MultiAgentTriageReasoningValidationError(
            "HANDOFF triage output requires one specialization"
        )
    if decision is MultiAgentHandoffDecision.ABSTAIN and specialization is not None:
        raise MultiAgentTriageReasoningValidationError(
            "ABSTAIN triage output cannot carry a specialization"
        )

    return create_multi_agent_handoff_proposal(
        source_task_id=task.task_id,
        decision=decision,
        target_specialization=specialization,
    )


def reason_about_triage_task(
    *,
    task: SingleAgentTask,
    model: MultiAgentTriageReasoningModel,
) -> MultiAgentTriageReasoningResult:
    """Invoke one triage model once and deterministically parse its specialization proposal."""
    if type(task) is not SingleAgentTask:
        raise MultiAgentTriageReasoningValidationError(
            "task must be one admitted SingleAgentTask"
        )
    response = model.generate(task)
    if type(response) is not MultiAgentTriageReasoningModelResponse:
        raise MultiAgentTriageReasoningValidationError(
            "triage model must return MultiAgentTriageReasoningModelResponse"
        )
    if response.evidence.source_task_id != task.task_id:
        raise MultiAgentTriageReasoningValidationError(
            "triage invocation evidence is not bound to the admitted source task"
        )
    proposal = parse_triage_model_output(task=task, output_text=response.output_text)
    return MultiAgentTriageReasoningResult.create(
        source_task=task,
        proposal=proposal,
        invocation_evidence=response.evidence,
    )


__all__ = ["parse_triage_model_output", "reason_about_triage_task"]
