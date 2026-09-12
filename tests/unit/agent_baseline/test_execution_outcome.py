"""Regression tests for the additive admitted-result execution outcome."""

from dataclasses import dataclass
from datetime import date

from opslens.agent_baseline.application import (
    AgentCapabilityExecutionOutcome,
    AgentCapabilityExecutors,
    authorize_agent_action,
    execute_authorized_capability,
    execute_authorized_capability_outcome,
)
from opslens.agent_baseline.domain import (
    AgentCapability,
    AgentDecision,
    AuthorizedAgentAction,
    HybridSecurityAnswerInvocation,
    KnowledgeGuidanceInvocation,
    PublicRepositoryAnalysisInvocation,
    StructuredSecurityQueryInvocation,
    StructuredSecurityQueryResultBinding,
    create_agent_action_proposal,
    create_single_agent_task,
)
from opslens.hybrid_retrieval.domain.synthesis import HybridSynthesisResult
from opslens.knowledge_retrieval.domain.synthesis import SynthesisResult
from opslens.public_analysis.domain.semantic_planning import PublicAnalysisAdmissionHandoff
from opslens.semantic_query.application.models import AthenaQueryResult
from opslens.semantic_query.domain import (
    EpssFilters,
    SemanticDimension,
    SemanticMetric,
    SemanticQuery,
)


def _structured_invocation() -> StructuredSecurityQueryInvocation:
    capability = AgentCapability.STRUCTURED_SECURITY_QUERY
    task = create_single_agent_task(
        text="Execute bounded structured query",
        allowed_capabilities=(capability,),
    )
    proposal = create_agent_action_proposal(
        task_id=task.task_id,
        decision=AgentDecision.ACT,
        capability=capability,
    )
    action = authorize_agent_action(task, proposal)
    assert type(action) is AuthorizedAgentAction
    query = SemanticQuery(
        metric=SemanticMetric.EPSS_SCORE,
        dimensions=(SemanticDimension.CVE,),
        filters=EpssFilters(snapshot_date=date(2026, 9, 8), minimum_score=0.7),
        limit=2,
    )
    return StructuredSecurityQueryInvocation.create(action=action, query=query)


@dataclass(slots=True)
class _StructuredExecutor:
    calls: int = 0

    def execute_structured_security_query(
        self,
        invocation: StructuredSecurityQueryInvocation,
    ) -> StructuredSecurityQueryResultBinding:
        self.calls += 1
        return StructuredSecurityQueryResultBinding.create(
            invocation=invocation,
            result=AthenaQueryResult(
                query_execution_id="execution-outcome-regression",
                columns=("cve", "epss"),
                rows=(("CVE-2026-0001", "0.91"),),
                data_scanned_bytes=64,
            ),
        )


class _UnusedKnowledgeExecutor:
    def execute_knowledge_guidance(
        self,
        invocation: KnowledgeGuidanceInvocation,
    ) -> SynthesisResult:
        del invocation
        raise AssertionError("knowledge executor must not be called")


class _UnusedHybridExecutor:
    def execute_hybrid_security_answer(
        self,
        invocation: HybridSecurityAnswerInvocation,
    ) -> HybridSynthesisResult:
        del invocation
        raise AssertionError("hybrid executor must not be called")


class _UnusedPublicExecutor:
    def execute_public_repository_analysis(
        self,
        invocation: PublicRepositoryAnalysisInvocation,
    ) -> PublicAnalysisAdmissionHandoff:
        del invocation
        raise AssertionError("public executor must not be called")


def _executors(structured: _StructuredExecutor) -> AgentCapabilityExecutors:
    return AgentCapabilityExecutors(
        structured_security_query=structured,
        knowledge_guidance=_UnusedKnowledgeExecutor(),
        hybrid_security_answer=_UnusedHybridExecutor(),
        public_repository_analysis=_UnusedPublicExecutor(),
    )


def test_execution_outcome_preserves_admitted_result_without_changing_execution_identity() -> None:
    """New API returns the admitted typed result while legacy API keeps the same evidence."""
    invocation = _structured_invocation()
    outcome_executor = _StructuredExecutor()
    outcome = execute_authorized_capability_outcome(
        invocation,
        _executors(outcome_executor),
    )

    legacy_executor = _StructuredExecutor()
    legacy_execution = execute_authorized_capability(
        invocation,
        _executors(legacy_executor),
    )

    assert type(outcome) is AgentCapabilityExecutionOutcome
    assert type(outcome.result) is StructuredSecurityQueryResultBinding
    assert outcome.execution.execution_id == legacy_execution.execution_id
    assert outcome.execution.execution_sha256 == legacy_execution.execution_sha256
    assert outcome.execution.downstream_result_sha256 == outcome.result.result_sha256
    assert outcome_executor.calls == 1
    assert legacy_executor.calls == 1
