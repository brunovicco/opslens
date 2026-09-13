"""Shared fixtures for the bounded A2A reference interoperability tests."""

import pytest

from opslens.agent_baseline.domain.models import (
    AgentCapability,
    create_single_agent_task,
)
from opslens.multi_agent.application.handoff import admit_multi_agent_handoff
from opslens.multi_agent.domain.handoff import (
    AgentSpecialization,
    MultiAgentHandoffDecision,
    SpecialistAgentTask,
    create_multi_agent_handoff_proposal,
    create_triage_agent_task,
)


@pytest.fixture
def specialist_task() -> SpecialistAgentTask:
    """Return one deterministically admitted evidence-analysis specialist task."""
    source_task = create_single_agent_task(
        text="Which admitted security capability should analyze this evidence?",
        allowed_capabilities=(
            AgentCapability.PUBLIC_REPOSITORY_ANALYSIS,
            AgentCapability.STRUCTURED_SECURITY_QUERY,
        ),
    )
    triage = create_triage_agent_task(task=source_task)
    proposal = create_multi_agent_handoff_proposal(
        source_task_id=source_task.task_id,
        decision=MultiAgentHandoffDecision.HANDOFF,
        target_specialization=AgentSpecialization.EVIDENCE_ANALYSIS,
    )
    admitted = admit_multi_agent_handoff(source=triage, proposal=proposal)
    if not isinstance(admitted, SpecialistAgentTask):
        raise AssertionError("fixture must produce one admitted SpecialistAgentTask")
    return admitted


@pytest.fixture
def second_specialist_task() -> SpecialistAgentTask:
    """Return a second valid specialist task for unknown-reference tests."""
    source_task = create_single_agent_task(
        text="Analyze a different bounded security evidence request.",
        allowed_capabilities=(AgentCapability.STRUCTURED_SECURITY_QUERY,),
    )
    triage = create_triage_agent_task(task=source_task)
    proposal = create_multi_agent_handoff_proposal(
        source_task_id=source_task.task_id,
        decision=MultiAgentHandoffDecision.HANDOFF,
        target_specialization=AgentSpecialization.EVIDENCE_ANALYSIS,
    )
    admitted = admit_multi_agent_handoff(source=triage, proposal=proposal)
    if not isinstance(admitted, SpecialistAgentTask):
        raise AssertionError("fixture must produce one admitted SpecialistAgentTask")
    return admitted
