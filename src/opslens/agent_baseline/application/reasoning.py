"""Bounded single-agent reasoning orchestration over deterministic authorization."""

import json
from collections.abc import Mapping
from typing import cast

from opslens.agent_baseline.application.authorization import authorize_agent_action
from opslens.agent_baseline.domain.errors import (
    AgentCapabilityAuthorizationError,
    AgentReasoningValidationError,
)
from opslens.agent_baseline.domain.models import (
    AgentAbstention,
    AgentActionProposal,
    AgentCapability,
    AgentDecision,
    AuthorizedAgentAction,
    SingleAgentTask,
    create_agent_action_proposal,
)
from opslens.agent_baseline.domain.reasoning import (
    MAX_AGENT_REASONING_OUTPUT_UTF8_BYTES,
    AgentReasoningAuthorizationOutcome,
    AgentReasoningFailureCategory,
    AgentReasoningResult,
)
from opslens.agent_baseline.ports.reasoning import (
    AgentReasoningModel,
    AgentReasoningModelResponse,
)

_REASONING_OUTPUT_KEYS = frozenset({"decision", "capability"})


def parse_reasoning_model_output(
    *,
    task: SingleAgentTask,
    output_text: str,
) -> AgentActionProposal:
    """Parse one untrusted model response into the existing proposal contract."""
    if type(task) is not SingleAgentTask:
        raise AgentReasoningValidationError("task must be one admitted SingleAgentTask")
    if type(output_text) is not str:
        raise AgentReasoningValidationError("model output must be a string")
    if not output_text.strip():
        raise AgentReasoningValidationError("model output cannot be blank")
    if len(output_text.encode("utf-8")) > MAX_AGENT_REASONING_OUTPUT_UTF8_BYTES:
        raise AgentReasoningValidationError("model output exceeds the reasoning byte limit")

    try:
        loaded: object = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise AgentReasoningValidationError("model output is not valid JSON") from exc

    if not isinstance(loaded, Mapping):
        raise AgentReasoningValidationError("model output must be one JSON object")
    payload = cast(Mapping[object, object], loaded)
    if any(type(key) is not str for key in payload):
        raise AgentReasoningValidationError("model output keys must be strings")
    typed_payload = cast(Mapping[str, object], payload)
    if frozenset(typed_payload) != _REASONING_OUTPUT_KEYS:
        raise AgentReasoningValidationError(
            "model output must contain exactly decision and capability"
        )

    raw_decision = typed_payload["decision"]
    if type(raw_decision) is not str:
        raise AgentReasoningValidationError("decision must be a string")
    try:
        decision = AgentDecision(raw_decision)
    except ValueError as exc:
        raise AgentReasoningValidationError("decision is not supported") from exc

    raw_capability = typed_payload["capability"]
    capability: AgentCapability | None
    if raw_capability is None:
        capability = None
    elif type(raw_capability) is str:
        try:
            capability = AgentCapability(raw_capability)
        except ValueError as exc:
            raise AgentReasoningValidationError("capability is not supported") from exc
    else:
        raise AgentReasoningValidationError("capability must be a string or null")

    if decision is AgentDecision.ACT and capability is None:
        raise AgentReasoningValidationError("ACT reasoning output requires one capability")
    if decision is AgentDecision.ABSTAIN and capability is not None:
        raise AgentReasoningValidationError(
            "ABSTAIN reasoning output cannot carry a capability"
        )

    return create_agent_action_proposal(
        task_id=task.task_id,
        decision=decision,
        capability=capability,
    )


def reason_about_task(
    *,
    task: SingleAgentTask,
    model: AgentReasoningModel,
) -> AgentReasoningResult:
    """Invoke one model once, parse its proposal, then apply deterministic authorization."""
    if type(task) is not SingleAgentTask:
        raise AgentReasoningValidationError("task must be one admitted SingleAgentTask")

    response = model.generate(task)
    if type(response) is not AgentReasoningModelResponse:
        raise AgentReasoningValidationError(
            "reasoning model must return AgentReasoningModelResponse"
        )
    if response.evidence.task_id != task.task_id:
        raise AgentReasoningValidationError(
            "reasoning invocation evidence is not bound to the admitted task"
        )

    proposal = parse_reasoning_model_output(task=task, output_text=response.output_text)
    try:
        authorization = authorize_agent_action(task, proposal)
    except AgentCapabilityAuthorizationError:
        return AgentReasoningResult.create(
            task=task,
            proposal=proposal,
            invocation_evidence=response.evidence,
            authorization_outcome=AgentReasoningAuthorizationOutcome.REJECTED,
            authorization_evidence_id=None,
            failure_category=AgentReasoningFailureCategory.CAPABILITY_AUTHORIZATION,
        )

    if type(authorization) is AuthorizedAgentAction:
        return AgentReasoningResult.create(
            task=task,
            proposal=proposal,
            invocation_evidence=response.evidence,
            authorization_outcome=AgentReasoningAuthorizationOutcome.AUTHORIZED,
            authorization_evidence_id=authorization.action_id,
            failure_category=None,
        )
    if type(authorization) is AgentAbstention:
        return AgentReasoningResult.create(
            task=task,
            proposal=proposal,
            invocation_evidence=response.evidence,
            authorization_outcome=AgentReasoningAuthorizationOutcome.ABSTAINED,
            authorization_evidence_id=authorization.abstention_id,
            failure_category=None,
        )
    raise AgentReasoningValidationError("authorization returned an unsupported result type")


__all__ = ["parse_reasoning_model_output", "reason_about_task"]
