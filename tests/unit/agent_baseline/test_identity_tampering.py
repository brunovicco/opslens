"""Tamper-resistance tests for Gate 11.1 authorization result identities."""

import pytest

from opslens.agent_baseline.application import authorize_agent_action
from opslens.agent_baseline.domain import (
    AgentAbstention,
    AgentAuthorityValidationError,
    AgentCapability,
    AgentDecision,
    AuthorizedAgentAction,
    create_agent_action_proposal,
    create_single_agent_task,
)


def test_forged_authorized_action_identity_is_rejected() -> None:
    """Reject direct construction that tampers with authorized-action identity."""
    task = create_single_agent_task(
        text="Use the bounded hybrid capability.",
        allowed_capabilities=(AgentCapability.HYBRID_SECURITY_ANSWER,),
    )
    proposal = create_agent_action_proposal(
        task_id=task.task_id,
        decision=AgentDecision.ACT,
        capability=AgentCapability.HYBRID_SECURITY_ANSWER,
    )
    admitted = authorize_agent_action(task, proposal)
    assert isinstance(admitted, AuthorizedAgentAction)

    with pytest.raises(AgentAuthorityValidationError, match="action_sha256"):
        AuthorizedAgentAction(
            task_id=admitted.task_id,
            proposal_id=admitted.proposal_id,
            capability=admitted.capability,
            action_sha256="0" * 64,
            action_id=admitted.action_id,
        )


def test_forged_abstention_identity_is_rejected() -> None:
    """Reject direct construction that tampers with explicit abstention identity."""
    task = create_single_agent_task(
        text="Abstain when no capability should be selected.",
        allowed_capabilities=(AgentCapability.KNOWLEDGE_GUIDANCE,),
    )
    proposal = create_agent_action_proposal(
        task_id=task.task_id,
        decision=AgentDecision.ABSTAIN,
        capability=None,
    )
    admitted = authorize_agent_action(task, proposal)
    assert isinstance(admitted, AgentAbstention)

    with pytest.raises(AgentAuthorityValidationError, match="abstention_sha256"):
        AgentAbstention(
            task_id=admitted.task_id,
            proposal_id=admitted.proposal_id,
            abstention_sha256="0" * 64,
            abstention_id=admitted.abstention_id,
        )
