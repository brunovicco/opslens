"""Deterministic authorization of untrusted single-agent action proposals."""

from opslens.agent_baseline.domain.errors import (
    AgentAuthorityValidationError,
    AgentCapabilityAuthorizationError,
)
from opslens.agent_baseline.domain.models import (
    AgentAbstention,
    AgentActionProposal,
    AgentDecision,
    AuthorizedAgentAction,
    SingleAgentTask,
    create_agent_abstention,
    create_authorized_agent_action,
)


def authorize_agent_action(
    task: SingleAgentTask,
    proposal: AgentActionProposal,
) -> AuthorizedAgentAction | AgentAbstention:
    """Authorize one proposal without executing any capability."""
    if type(task) is not SingleAgentTask:
        raise AgentAuthorityValidationError("task must be one admitted SingleAgentTask")
    if type(proposal) is not AgentActionProposal:
        raise AgentAuthorityValidationError(
            "proposal must be one admitted AgentActionProposal"
        )
    if proposal.task_id != task.task_id:
        raise AgentCapabilityAuthorizationError(
            "agent proposal is not bound to the admitted task"
        )

    if proposal.decision is AgentDecision.ABSTAIN:
        return create_agent_abstention(
            task_id=task.task_id,
            proposal_id=proposal.proposal_id,
        )

    capability = proposal.capability
    if capability is None:
        raise AgentAuthorityValidationError(
            "ACT proposal reached authorization without a capability"
        )
    if capability not in task.allowed_capabilities:
        raise AgentCapabilityAuthorizationError(
            "proposed capability is not authorized for the admitted task"
        )

    return create_authorized_agent_action(
        task_id=task.task_id,
        proposal_id=proposal.proposal_id,
        capability=capability,
    )


__all__ = ["authorize_agent_action"]
