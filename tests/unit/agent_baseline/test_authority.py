"""Regression tests for the Gate 11.1 single-agent authority contract."""

from typing import cast

import pytest

from opslens.agent_baseline.application import authorize_agent_action
from opslens.agent_baseline.domain import (
    MAX_AGENT_ADAPTIVE_RETRIES,
    MAX_AGENT_ALLOWED_CAPABILITIES,
    MAX_AGENT_AUTHORIZATION_STEPS,
    MAX_AGENT_CAPABILITY_EXECUTIONS,
    MAX_AGENT_PROPOSALS_PER_TASK,
    MAX_AGENT_TASK_UTF8_BYTES,
    SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION,
    AgentAbstention,
    AgentActionProposal,
    AgentAuthorityValidationError,
    AgentCapability,
    AgentCapabilityAuthorizationError,
    AgentDecision,
    AuthorizedAgentAction,
    SingleAgentTask,
    create_agent_action_proposal,
    create_single_agent_task,
)


def _task(
    *capabilities: AgentCapability,
    text: str = "Which governed capability should handle this security question?",
) -> SingleAgentTask:
    """Create one admitted bounded task for tests."""
    return create_single_agent_task(text=text, allowed_capabilities=capabilities)


def test_contract_limits_freeze_zero_execution_and_retry_authority() -> None:
    """Freeze Gate 11.1 as one proposal/authorization step with no execution."""
    assert SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION == "single-agent-authority:v1"
    assert MAX_AGENT_TASK_UTF8_BYTES == 2_048
    assert MAX_AGENT_ALLOWED_CAPABILITIES == 4
    assert MAX_AGENT_PROPOSALS_PER_TASK == 1
    assert MAX_AGENT_AUTHORIZATION_STEPS == 1
    assert MAX_AGENT_CAPABILITY_EXECUTIONS == 0
    assert MAX_AGENT_ADAPTIVE_RETRIES == 0


def test_task_capabilities_are_canonical_and_identity_is_order_independent() -> None:
    """Canonicalize the code-owned capability allowlist before hashing task identity."""
    first = _task(
        AgentCapability.PUBLIC_REPOSITORY_ANALYSIS,
        AgentCapability.STRUCTURED_SECURITY_QUERY,
    )
    second = _task(
        AgentCapability.STRUCTURED_SECURITY_QUERY,
        AgentCapability.PUBLIC_REPOSITORY_ANALYSIS,
    )

    assert first == second
    assert first.allowed_capabilities == (
        AgentCapability.PUBLIC_REPOSITORY_ANALYSIS,
        AgentCapability.STRUCTURED_SECURITY_QUERY,
    )
    assert first.task_id == second.task_id


def test_task_identity_changes_when_text_or_allowlist_changes() -> None:
    """Bind task identity to both untrusted text and deterministic capability authority."""
    baseline = _task(AgentCapability.HYBRID_SECURITY_ANSWER)
    changed_text = _task(
        AgentCapability.HYBRID_SECURITY_ANSWER,
        text="Use the governed hybrid path for this different question.",
    )
    changed_allowlist = _task(
        AgentCapability.HYBRID_SECURITY_ANSWER,
        AgentCapability.KNOWLEDGE_GUIDANCE,
    )

    assert baseline.task_id != changed_text.task_id
    assert baseline.task_id != changed_allowlist.task_id


def test_task_limit_counts_utf8_bytes_not_python_characters() -> None:
    """Reject multibyte task text that crosses the exact UTF-8 byte budget."""
    within_limit = "é" * (MAX_AGENT_TASK_UTF8_BYTES // 2)
    task = _task(AgentCapability.KNOWLEDGE_GUIDANCE, text=within_limit)
    assert len(task.text.encode("utf-8")) == MAX_AGENT_TASK_UTF8_BYTES

    with pytest.raises(AgentAuthorityValidationError, match="UTF-8 byte limit"):
        _task(
            AgentCapability.KNOWLEDGE_GUIDANCE,
            text=within_limit + "é",
        )


def test_empty_duplicate_and_untyped_capability_surfaces_fail_closed() -> None:
    """Reject missing, duplicate, or raw-string capability authority."""
    with pytest.raises(AgentAuthorityValidationError, match="cannot be empty"):
        create_single_agent_task(text="question", allowed_capabilities=())

    with pytest.raises(AgentAuthorityValidationError, match="duplicates"):
        _task(
            AgentCapability.KNOWLEDGE_GUIDANCE,
            AgentCapability.KNOWLEDGE_GUIDANCE,
        )

    with pytest.raises(AgentAuthorityValidationError, match="AgentCapability"):
        create_single_agent_task(
            text="question",
            allowed_capabilities=cast(
                tuple[AgentCapability, ...],
                ("knowledge_guidance",),
            ),
        )


def test_allowlisted_act_becomes_content_addressed_authority_not_execution() -> None:
    """Authorize exactly one selected capability without creating execution authority."""
    task = _task(
        AgentCapability.STRUCTURED_SECURITY_QUERY,
        AgentCapability.HYBRID_SECURITY_ANSWER,
    )
    proposal = create_agent_action_proposal(
        task_id=task.task_id,
        decision=AgentDecision.ACT,
        capability=AgentCapability.HYBRID_SECURITY_ANSWER,
    )

    first = authorize_agent_action(task, proposal)
    second = authorize_agent_action(task, proposal)

    assert isinstance(first, AuthorizedAgentAction)
    assert first == second
    assert first.capability is AgentCapability.HYBRID_SECURITY_ANSWER
    assert first.task_id == task.task_id
    assert first.proposal_id == proposal.proposal_id
    assert first.action_id.startswith(
        f"{SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION}:action:"
    )


def test_out_of_allowlist_act_is_valid_proposal_but_denied_authority() -> None:
    """Keep proposal validity separate from deterministic capability authorization."""
    task = _task(AgentCapability.STRUCTURED_SECURITY_QUERY)
    proposal = create_agent_action_proposal(
        task_id=task.task_id,
        decision=AgentDecision.ACT,
        capability=AgentCapability.PUBLIC_REPOSITORY_ANALYSIS,
    )

    with pytest.raises(
        AgentCapabilityAuthorizationError,
        match="not authorized",
    ):
        authorize_agent_action(task, proposal)


def test_abstention_is_valid_and_grants_no_capability_authority() -> None:
    """Represent abstention explicitly instead of fabricating a fallback capability."""
    task = _task(AgentCapability.KNOWLEDGE_GUIDANCE)
    proposal = create_agent_action_proposal(
        task_id=task.task_id,
        decision=AgentDecision.ABSTAIN,
        capability=None,
    )

    result = authorize_agent_action(task, proposal)

    assert isinstance(result, AgentAbstention)
    assert result.task_id == task.task_id
    assert result.proposal_id == proposal.proposal_id
    assert result.abstention_id.startswith(
        f"{SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION}:abstention:"
    )
    assert not hasattr(result, "capability")


def test_act_and_abstain_shape_mismatches_fail_before_authorization() -> None:
    """Reject inconsistent proposal decisions before they can reach authorization."""
    task = _task(AgentCapability.KNOWLEDGE_GUIDANCE)

    with pytest.raises(AgentAuthorityValidationError, match="ACT proposals require"):
        create_agent_action_proposal(
            task_id=task.task_id,
            decision=AgentDecision.ACT,
            capability=None,
        )

    with pytest.raises(AgentAuthorityValidationError, match="ABSTAIN proposals cannot"):
        create_agent_action_proposal(
            task_id=task.task_id,
            decision=AgentDecision.ABSTAIN,
            capability=AgentCapability.KNOWLEDGE_GUIDANCE,
        )


def test_raw_decision_value_is_rejected_at_runtime() -> None:
    """Reject raw strings masquerading as typed decision authority."""
    task = _task(AgentCapability.KNOWLEDGE_GUIDANCE)
    valid = create_agent_action_proposal(
        task_id=task.task_id,
        decision=AgentDecision.ACT,
        capability=AgentCapability.KNOWLEDGE_GUIDANCE,
    )

    with pytest.raises(AgentAuthorityValidationError, match="decision must be AgentDecision"):
        AgentActionProposal(
            task_id=valid.task_id,
            decision=cast(AgentDecision, "act"),
            capability=valid.capability,
            proposal_sha256=valid.proposal_sha256,
            proposal_id=valid.proposal_id,
        )


def test_mismatched_task_identity_is_denied_even_for_allowlisted_capability() -> None:
    """Bind authorization to the exact admitted task rather than capability name alone."""
    first = _task(AgentCapability.KNOWLEDGE_GUIDANCE, text="first task")
    second = _task(AgentCapability.KNOWLEDGE_GUIDANCE, text="second task")
    proposal = create_agent_action_proposal(
        task_id=first.task_id,
        decision=AgentDecision.ACT,
        capability=AgentCapability.KNOWLEDGE_GUIDANCE,
    )

    with pytest.raises(AgentCapabilityAuthorizationError, match="not bound"):
        authorize_agent_action(second, proposal)


def test_forged_task_identity_is_rejected() -> None:
    """Reject direct construction that tampers with content-addressed task identity."""
    admitted = _task(AgentCapability.PUBLIC_REPOSITORY_ANALYSIS)

    with pytest.raises(AgentAuthorityValidationError, match="task_sha256"):
        SingleAgentTask(
            text=admitted.text,
            allowed_capabilities=admitted.allowed_capabilities,
            task_sha256="0" * 64,
            task_id=admitted.task_id,
        )


def test_forged_proposal_identity_is_rejected() -> None:
    """Reject direct construction that tampers with proposal identity."""
    task = _task(AgentCapability.HYBRID_SECURITY_ANSWER)
    admitted = create_agent_action_proposal(
        task_id=task.task_id,
        decision=AgentDecision.ACT,
        capability=AgentCapability.HYBRID_SECURITY_ANSWER,
    )

    with pytest.raises(AgentAuthorityValidationError, match="proposal_sha256"):
        AgentActionProposal(
            task_id=admitted.task_id,
            decision=admitted.decision,
            capability=admitted.capability,
            proposal_sha256="0" * 64,
            proposal_id=admitted.proposal_id,
        )


def test_contract_has_no_generic_tool_or_argument_surface() -> None:
    """Keep model-authored arguments, tools, providers, SQL, and commands out of v1."""
    task = _task(AgentCapability.STRUCTURED_SECURITY_QUERY)
    proposal = create_agent_action_proposal(
        task_id=task.task_id,
        decision=AgentDecision.ACT,
        capability=AgentCapability.STRUCTURED_SECURITY_QUERY,
    )
    authorized = authorize_agent_action(task, proposal)

    forbidden = (
        "args",
        "arguments",
        "command",
        "kwargs",
        "model_id",
        "provider",
        "sql",
        "tool_name",
        "url",
    )
    for value in (task, proposal, authorized):
        assert all(not hasattr(value, name) for name in forbidden)
