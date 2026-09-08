"""Deterministic admission for one bounded triage-to-specialist handoff."""

from __future__ import annotations

from opslens.agent_baseline.domain.models import create_single_agent_task
from opslens.multi_agent.domain.errors import (
    MultiAgentHandoffAuthorizationError,
    MultiAgentHandoffValidationError,
)
from opslens.multi_agent.domain.handoff import (
    MAX_SPECIALIST_CAPABILITIES,
    MultiAgentHandoffAbstention,
    MultiAgentHandoffDecision,
    MultiAgentHandoffProposal,
    SpecialistAgentTask,
    TriageAgentTask,
    capabilities_for_specialization,
    create_authorized_multi_agent_handoff,
    create_multi_agent_handoff_abstention,
)


def admit_multi_agent_handoff(
    *,
    source: TriageAgentTask,
    proposal: MultiAgentHandoffProposal,
) -> SpecialistAgentTask | MultiAgentHandoffAbstention:
    """Admit one handoff by deterministic source binding and capability narrowing."""
    if type(source) is not TriageAgentTask:
        raise MultiAgentHandoffValidationError(
            "source must be one admitted TriageAgentTask"
        )
    if type(proposal) is not MultiAgentHandoffProposal:
        raise MultiAgentHandoffValidationError(
            "proposal must be one MultiAgentHandoffProposal"
        )

    source_task = source.task
    if proposal.source_task_id != source_task.task_id:
        raise MultiAgentHandoffValidationError(
            "proposal source task identity does not match the admitted triage task"
        )

    if proposal.decision is MultiAgentHandoffDecision.ABSTAIN:
        return create_multi_agent_handoff_abstention(
            source_task=source_task,
            proposal=proposal,
        )

    specialization = proposal.target_specialization
    if specialization is None:
        raise MultiAgentHandoffValidationError(
            "HANDOFF proposal must contain one target specialization"
        )

    specialization_scope = capabilities_for_specialization(specialization)
    target_capabilities = tuple(
        capability
        for capability in source_task.allowed_capabilities
        if capability in specialization_scope
    )
    if not target_capabilities:
        raise MultiAgentHandoffAuthorizationError(
            "handoff specialization has no capability authorized by the source task"
        )
    if len(target_capabilities) > MAX_SPECIALIST_CAPABILITIES:
        raise MultiAgentHandoffAuthorizationError(
            "handoff target exceeds the specialist capability limit"
        )

    target_task = create_single_agent_task(
        text=source_task.text,
        allowed_capabilities=target_capabilities,
    )
    evidence = create_authorized_multi_agent_handoff(
        source_task=source_task,
        proposal=proposal,
        target_task=target_task,
    )
    return SpecialistAgentTask(
        task=target_task,
        specialization=specialization,
        handoff=evidence,
    )


__all__ = ["admit_multi_agent_handoff"]
