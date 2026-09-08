"""Bounded provider-neutral execution of already-authorized agent capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from opslens.agent_baseline.domain.execution import (
    AgentCapabilityExecution,
    AgentCapabilityInvocation,
    HybridSecurityAnswerInvocation,
    KnowledgeGuidanceInvocation,
    PublicRepositoryAnalysisInvocation,
    StructuredSecurityQueryInvocation,
    StructuredSecurityQueryResultBinding,
)
from opslens.hybrid_retrieval.domain.synthesis import HybridSynthesisResult
from opslens.knowledge_retrieval.domain.synthesis import SynthesisResult
from opslens.public_analysis.domain import PublicAnalysisAdmissionHandoff


type AgentCapabilityExecutionResult = (
    StructuredSecurityQueryResultBinding
    | SynthesisResult
    | HybridSynthesisResult
    | PublicAnalysisAdmissionHandoff
)


class AgentCapabilityExecutionFailureCategory(StrEnum):
    """Content-free failure categories for the Gate 11.2 executor boundary."""

    EXECUTOR_FAILURE = "executor_failure"
    RESULT_CONTRACT = "result_contract"


class AgentCapabilityExecutionError(RuntimeError):
    """Bounded execution failure that never admits arbitrary downstream messages."""

    def __init__(self, category: AgentCapabilityExecutionFailureCategory) -> None:
        """Create one stable content-free execution failure."""
        self.category = category
        super().__init__(f"agent capability execution failed category={category.value}")


class StructuredSecurityQueryExecutor(Protocol):
    """Explicit executor port for the structured-security capability."""

    def execute_structured_security_query(
        self,
        invocation: StructuredSecurityQueryInvocation,
    ) -> StructuredSecurityQueryResultBinding:
        """Execute exactly one admitted structured query invocation."""
        ...


class KnowledgeGuidanceExecutor(Protocol):
    """Explicit executor port for one admitted knowledge synthesis request."""

    def execute_knowledge_guidance(
        self,
        invocation: KnowledgeGuidanceInvocation,
    ) -> SynthesisResult:
        """Execute exactly one admitted knowledge-guidance invocation."""
        ...


class HybridSecurityAnswerExecutor(Protocol):
    """Explicit executor port for one admitted hybrid synthesis request."""

    def execute_hybrid_security_answer(
        self,
        invocation: HybridSecurityAnswerInvocation,
    ) -> HybridSynthesisResult:
        """Execute exactly one admitted hybrid-security invocation."""
        ...


class PublicRepositoryAnalysisExecutor(Protocol):
    """Explicit executor port for one admitted public repository request."""

    def execute_public_repository_analysis(
        self,
        invocation: PublicRepositoryAnalysisInvocation,
    ) -> PublicAnalysisAdmissionHandoff:
        """Execute exactly one admitted public-repository invocation."""
        ...


@dataclass(frozen=True, slots=True)
class AgentCapabilityExecutors:
    """Closed executor set; there is no dynamic tool-name registry."""

    structured_security_query: StructuredSecurityQueryExecutor
    knowledge_guidance: KnowledgeGuidanceExecutor
    hybrid_security_answer: HybridSecurityAnswerExecutor
    public_repository_analysis: PublicRepositoryAnalysisExecutor


@dataclass(frozen=True, slots=True)
class AgentCapabilityExecutionOutcome:
    """Preserve one already-admitted typed result beside deterministic execution identity."""

    execution: AgentCapabilityExecution
    result: AgentCapabilityExecutionResult

    def __post_init__(self) -> None:
        """Keep the additive outcome bound to the existing deterministic execution evidence."""
        if type(self.execution) is not AgentCapabilityExecution:
            raise TypeError("execution must be one AgentCapabilityExecution value")
        if type(self.result) not in {
            StructuredSecurityQueryResultBinding,
            SynthesisResult,
            HybridSynthesisResult,
            PublicAnalysisAdmissionHandoff,
        }:
            raise TypeError("result must be one admitted typed capability result")


def _executor_failure() -> AgentCapabilityExecutionError:
    """Return one content-free downstream failure without retaining provider content."""
    return AgentCapabilityExecutionError(
        AgentCapabilityExecutionFailureCategory.EXECUTOR_FAILURE
    )


def _result_contract_failure() -> AgentCapabilityExecutionError:
    """Return one stable result-admission failure without downstream content."""
    return AgentCapabilityExecutionError(
        AgentCapabilityExecutionFailureCategory.RESULT_CONTRACT
    )


def execute_authorized_capability_outcome(
    invocation: AgentCapabilityInvocation,
    executors: AgentCapabilityExecutors,
) -> AgentCapabilityExecutionOutcome:
    """Execute one exact typed invocation once and preserve its admitted typed result."""
    if type(executors) is not AgentCapabilityExecutors:
        raise TypeError("executors must be one AgentCapabilityExecutors value")

    if type(invocation) is StructuredSecurityQueryInvocation:
        try:
            result = executors.structured_security_query.execute_structured_security_query(
                invocation
            )
        except Exception:
            raise _executor_failure() from None
        if type(result) is not StructuredSecurityQueryResultBinding:
            raise _result_contract_failure()
        if result.invocation_sha256 != invocation.invocation_sha256:
            raise _result_contract_failure()
        execution = AgentCapabilityExecution.create(
            invocation=invocation,
            downstream_result_sha256=result.result_sha256,
        )
        return AgentCapabilityExecutionOutcome(execution=execution, result=result)

    if type(invocation) is KnowledgeGuidanceInvocation:
        try:
            result = executors.knowledge_guidance.execute_knowledge_guidance(invocation)
        except Exception:
            raise _executor_failure() from None
        if type(result) is not SynthesisResult:
            raise _result_contract_failure()
        if result.request_sha256 != invocation.request.request_sha256:
            raise _result_contract_failure()
        execution = AgentCapabilityExecution.create(
            invocation=invocation,
            downstream_result_sha256=result.result_sha256,
        )
        return AgentCapabilityExecutionOutcome(execution=execution, result=result)

    if type(invocation) is HybridSecurityAnswerInvocation:
        try:
            result = executors.hybrid_security_answer.execute_hybrid_security_answer(
                invocation
            )
        except Exception:
            raise _executor_failure() from None
        if type(result) is not HybridSynthesisResult:
            raise _result_contract_failure()
        if result.request_sha256 != invocation.request.request_sha256:
            raise _result_contract_failure()
        execution = AgentCapabilityExecution.create(
            invocation=invocation,
            downstream_result_sha256=result.result_sha256,
        )
        return AgentCapabilityExecutionOutcome(execution=execution, result=result)

    if type(invocation) is PublicRepositoryAnalysisInvocation:
        try:
            result = executors.public_repository_analysis.execute_public_repository_analysis(
                invocation
            )
        except Exception:
            raise _executor_failure() from None
        if type(result) is not PublicAnalysisAdmissionHandoff:
            raise _result_contract_failure()
        result_request = result.source_execution.request
        if result_request.request_id != invocation.request.request_id:
            raise _result_contract_failure()
        if result_request.request_sha256 != invocation.request.request_sha256:
            raise _result_contract_failure()
        execution = AgentCapabilityExecution.create(
            invocation=invocation,
            downstream_result_sha256=result.handoff_sha256,
        )
        return AgentCapabilityExecutionOutcome(execution=execution, result=result)

    raise TypeError("invocation must be one recognized typed capability invocation")


def execute_authorized_capability(
    invocation: AgentCapabilityInvocation,
    executors: AgentCapabilityExecutors,
) -> AgentCapabilityExecution:
    """Execute one exact typed invocation once and return existing deterministic evidence."""
    return execute_authorized_capability_outcome(invocation, executors).execution


__all__ = [
    "AgentCapabilityExecutionError",
    "AgentCapabilityExecutionFailureCategory",
    "AgentCapabilityExecutionOutcome",
    "AgentCapabilityExecutionResult",
    "AgentCapabilityExecutors",
    "HybridSecurityAnswerExecutor",
    "KnowledgeGuidanceExecutor",
    "PublicRepositoryAnalysisExecutor",
    "StructuredSecurityQueryExecutor",
    "execute_authorized_capability",
    "execute_authorized_capability_outcome",
]
