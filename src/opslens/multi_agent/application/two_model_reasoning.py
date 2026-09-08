"""Compose triage reasoning, deterministic handoff admission, and specialist reasoning."""

from __future__ import annotations

from opslens.agent_baseline.application.reasoning import reason_about_task
from opslens.agent_baseline.domain.models import SingleAgentTask
from opslens.agent_baseline.ports.reasoning import AgentReasoningModel
from opslens.multi_agent.application.handoff import admit_multi_agent_handoff
from opslens.multi_agent.application.triage_reasoning import reason_about_triage_task
from opslens.multi_agent.domain.errors import MultiAgentHandoffAuthorizationError
from opslens.multi_agent.domain.handoff import (
    MultiAgentHandoffAbstention,
    SpecialistAgentTask,
    create_triage_agent_task,
)
from opslens.multi_agent.domain.two_model_reasoning import (
    MultiAgentTwoModelOutcome,
    MultiAgentTwoModelReasoningResult,
)
from opslens.multi_agent.ports.triage_reasoning import MultiAgentTriageReasoningModel


def run_two_model_reasoning(
    *,
    task: SingleAgentTask,
    triage_model: MultiAgentTriageReasoningModel,
    specialist_model: AgentReasoningModel,
) -> MultiAgentTwoModelReasoningResult:
    """Run at most one triage call and one specialist call, then stop before execution."""
    triage_result = reason_about_triage_task(task=task, model=triage_model)
    source = create_triage_agent_task(task=task)
    try:
        admitted = admit_multi_agent_handoff(
            source=source,
            proposal=triage_result.proposal,
        )
    except MultiAgentHandoffAuthorizationError:
        return MultiAgentTwoModelReasoningResult.create(
            source_task=task,
            triage_result=triage_result,
            outcome=MultiAgentTwoModelOutcome.HANDOFF_REJECTED,
            handoff_evidence_id=None,
            specialist_task_id=None,
            specialist_result=None,
            model_invocation_count=1,
        )

    if type(admitted) is MultiAgentHandoffAbstention:
        return MultiAgentTwoModelReasoningResult.create(
            source_task=task,
            triage_result=triage_result,
            outcome=MultiAgentTwoModelOutcome.TRIAGE_ABSTAINED,
            handoff_evidence_id=None,
            specialist_task_id=None,
            specialist_result=None,
            model_invocation_count=1,
        )
    if type(admitted) is SpecialistAgentTask:
        specialist_result = reason_about_task(
            task=admitted.task,
            model=specialist_model,
        )
        return MultiAgentTwoModelReasoningResult.create(
            source_task=task,
            triage_result=triage_result,
            outcome=MultiAgentTwoModelOutcome.SPECIALIST_REASONED,
            handoff_evidence_id=admitted.handoff.handoff_id,
            specialist_task_id=admitted.task.task_id,
            specialist_result=specialist_result,
            model_invocation_count=2,
        )
    raise TypeError("handoff admission returned an unsupported result type")


__all__ = ["run_two_model_reasoning"]
