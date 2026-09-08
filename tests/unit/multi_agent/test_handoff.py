"""Tests for the Phase 12 bounded specialization handoff contract."""

from __future__ import annotations

from typing import cast

import pytest

from opslens.agent_baseline.domain.models import (
    AgentCapability,
    AuthorizedAgentAction,
    SingleAgentTask,
    create_single_agent_task,
)
from opslens.multi_agent.application.handoff import admit_multi_agent_handoff
from opslens.multi_agent.domain.errors import (
    MultiAgentHandoffAuthorizationError,
    MultiAgentHandoffValidationError,
)
from opslens.multi_agent.domain.handoff import (
    MAX_MULTI_AGENT_HANDOFFS_PER_TASK,
    MAX_SPECIALIST_CAPABILITIES,
    MULTI_AGENT_HANDOFF_CONTRACT_VERSION,
    AgentSpecialization,
    MultiAgentHandoffAbstention,
    MultiAgentHandoffDecision,
    MultiAgentHandoffProposal,
    SpecialistAgentTask,
    TriageAgentTask,
    capabilities_for_specialization,
    create_multi_agent_handoff_proposal,
    create_triage_agent_task,
)


def _all_capability_task() -> SingleAgentTask:
    """Return one task exposing the full frozen Phase 11 capability set."""
    return create_single_agent_task(
        text="Analyze the admitted security request through the bounded workflow.",
        allowed_capabilities=tuple(AgentCapability),
    )


def _handoff_proposal(
    task: SingleAgentTask,
    specialization: AgentSpecialization,
) -> MultiAgentHandoffProposal:
    """Create one HANDOFF proposal bound to the supplied source task."""
    return create_multi_agent_handoff_proposal(
        source_task_id=task.task_id,
        decision=MultiAgentHandoffDecision.HANDOFF,
        target_specialization=specialization,
    )


def test_contract_freezes_one_handoff_and_two_capability_specialist_limit() -> None:
    """Gate 12.1 must remain one-way and narrower than the Phase 11 maximum."""
    assert MULTI_AGENT_HANDOFF_CONTRACT_VERSION == "multi-agent-handoff:v1"
    assert MAX_MULTI_AGENT_HANDOFFS_PER_TASK == 1
    assert MAX_SPECIALIST_CAPABILITIES == 2


def test_specialization_mapping_is_closed_and_code_owned() -> None:
    """Each specialization must expose only its frozen two-capability scope."""
    assert capabilities_for_specialization(AgentSpecialization.EVIDENCE_ANALYSIS) == (
        AgentCapability.PUBLIC_REPOSITORY_ANALYSIS,
        AgentCapability.STRUCTURED_SECURITY_QUERY,
    )
    assert capabilities_for_specialization(AgentSpecialization.GUIDANCE_SYNTHESIS) == (
        AgentCapability.HYBRID_SECURITY_ANSWER,
        AgentCapability.KNOWLEDGE_GUIDANCE,
    )


def test_evidence_handoff_narrows_full_source_scope_to_two_capabilities() -> None:
    """Evidence specialization must narrow a four-capability source task to two."""
    source_task = _all_capability_task()
    result = admit_multi_agent_handoff(
        source=create_triage_agent_task(task=source_task),
        proposal=_handoff_proposal(source_task, AgentSpecialization.EVIDENCE_ANALYSIS),
    )

    assert type(result) is SpecialistAgentTask
    specialist = cast(SpecialistAgentTask, result)
    assert specialist.specialization is AgentSpecialization.EVIDENCE_ANALYSIS
    assert specialist.task.text == source_task.text
    assert specialist.task.allowed_capabilities == (
        AgentCapability.PUBLIC_REPOSITORY_ANALYSIS,
        AgentCapability.STRUCTURED_SECURITY_QUERY,
    )
    assert len(specialist.task.allowed_capabilities) <= MAX_SPECIALIST_CAPABILITIES
    assert specialist.handoff.source_task_id == source_task.task_id
    assert specialist.handoff.target_task_id == specialist.task.task_id
    assert specialist.handoff.target_capabilities == specialist.task.allowed_capabilities
    assert not isinstance(specialist, AuthorizedAgentAction)


def test_guidance_handoff_narrows_full_source_scope_to_two_capabilities() -> None:
    """Guidance specialization must narrow a four-capability source task to two."""
    source_task = _all_capability_task()
    result = admit_multi_agent_handoff(
        source=create_triage_agent_task(task=source_task),
        proposal=_handoff_proposal(source_task, AgentSpecialization.GUIDANCE_SYNTHESIS),
    )

    assert type(result) is SpecialistAgentTask
    specialist = cast(SpecialistAgentTask, result)
    assert specialist.task.allowed_capabilities == (
        AgentCapability.HYBRID_SECURITY_ANSWER,
        AgentCapability.KNOWLEDGE_GUIDANCE,
    )


def test_source_allowlist_is_preserved_by_deterministic_intersection() -> None:
    """Handoff admission must never reintroduce a capability absent from source authority."""
    source_task = create_single_agent_task(
        text="Use the admitted structured evidence path.",
        allowed_capabilities=(AgentCapability.STRUCTURED_SECURITY_QUERY,),
    )
    result = admit_multi_agent_handoff(
        source=create_triage_agent_task(task=source_task),
        proposal=_handoff_proposal(source_task, AgentSpecialization.EVIDENCE_ANALYSIS),
    )

    assert type(result) is SpecialistAgentTask
    specialist = cast(SpecialistAgentTask, result)
    assert specialist.task.allowed_capabilities == (
        AgentCapability.STRUCTURED_SECURITY_QUERY,
    )


def test_empty_specialization_intersection_fails_closed() -> None:
    """A specialization with no source-authorized capability must be rejected."""
    source_task = create_single_agent_task(
        text="Explain admitted remediation guidance.",
        allowed_capabilities=(AgentCapability.KNOWLEDGE_GUIDANCE,),
    )

    with pytest.raises(
        MultiAgentHandoffAuthorizationError,
        match="no capability authorized by the source task",
    ):
        admit_multi_agent_handoff(
            source=create_triage_agent_task(task=source_task),
            proposal=_handoff_proposal(
                source_task,
                AgentSpecialization.EVIDENCE_ANALYSIS,
            ),
        )


def test_mismatched_source_task_identity_fails_closed() -> None:
    """Proposal identity must bind exactly to the admitted triage source task."""
    admitted_task = create_single_agent_task(
        text="Analyze structured security evidence.",
        allowed_capabilities=(AgentCapability.STRUCTURED_SECURITY_QUERY,),
    )
    other_task = create_single_agent_task(
        text="Explain controlled guidance.",
        allowed_capabilities=(AgentCapability.KNOWLEDGE_GUIDANCE,),
    )

    with pytest.raises(
        MultiAgentHandoffValidationError,
        match="does not match the admitted triage task",
    ):
        admit_multi_agent_handoff(
            source=create_triage_agent_task(task=admitted_task),
            proposal=_handoff_proposal(
                other_task,
                AgentSpecialization.GUIDANCE_SYNTHESIS,
            ),
        )


def test_explicit_handoff_abstention_creates_no_specialist_task() -> None:
    """Triage abstention must stop without creating a target task or capability authority."""
    source_task = _all_capability_task()
    proposal = create_multi_agent_handoff_proposal(
        source_task_id=source_task.task_id,
        decision=MultiAgentHandoffDecision.ABSTAIN,
        target_specialization=None,
    )

    result = admit_multi_agent_handoff(
        source=create_triage_agent_task(task=source_task),
        proposal=proposal,
    )

    assert type(result) is MultiAgentHandoffAbstention
    abstention = cast(MultiAgentHandoffAbstention, result)
    assert abstention.source_task_id == source_task.task_id
    assert abstention.proposal_id == proposal.proposal_id


def test_forged_handoff_proposal_identity_is_rejected() -> None:
    """Directly constructed proposals cannot forge their content-addressed identity."""
    source_task = _all_capability_task()
    forged_digest = "0" * 64

    with pytest.raises(
        MultiAgentHandoffValidationError,
        match="proposal_sha256 must match canonical semantics",
    ):
        MultiAgentHandoffProposal(
            source_task_id=source_task.task_id,
            decision=MultiAgentHandoffDecision.HANDOFF,
            target_specialization=AgentSpecialization.EVIDENCE_ANALYSIS,
            proposal_sha256=forged_digest,
            proposal_id=(
                f"{MULTI_AGENT_HANDOFF_CONTRACT_VERSION}:proposal:{forged_digest}"
            ),
        )


def test_specialist_task_cannot_be_reused_as_a_handoff_source() -> None:
    """The v1 API accepts only TriageAgentTask, structurally preventing handoff chains."""
    source_task = _all_capability_task()
    result = admit_multi_agent_handoff(
        source=create_triage_agent_task(task=source_task),
        proposal=_handoff_proposal(source_task, AgentSpecialization.EVIDENCE_ANALYSIS),
    )
    assert type(result) is SpecialistAgentTask
    specialist = cast(SpecialistAgentTask, result)
    second_proposal = _handoff_proposal(
        specialist.task,
        AgentSpecialization.EVIDENCE_ANALYSIS,
    )

    with pytest.raises(
        MultiAgentHandoffValidationError,
        match="source must be one admitted TriageAgentTask",
    ):
        admit_multi_agent_handoff(
            source=cast(TriageAgentTask, specialist),
            proposal=second_proposal,
        )
