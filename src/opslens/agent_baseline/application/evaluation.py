"""Offline deterministic replay and scoring for the Phase 11 single-agent baseline."""

from typing import Protocol

from opslens.agent_baseline.application.authorization import authorize_agent_action
from opslens.agent_baseline.application.execution import (
    AgentCapabilityExecutionError,
    AgentCapabilityExecutionFailureCategory,
    AgentCapabilityExecutors,
    execute_authorized_capability,
)
from opslens.agent_baseline.domain.errors import (
    AgentAuthorityValidationError,
    AgentCapabilityAuthorizationError,
    AgentCapabilityExecutionValidationError,
    AgentEvaluationValidationError,
)
from opslens.agent_baseline.domain.evaluation import (
    AgentEvaluationAuthorizationOutcome,
    AgentEvaluationCase,
    AgentEvaluationCaseResult,
    AgentEvaluationDataset,
    AgentEvaluationExecutionMode,
    AgentEvaluationExecutionOutcome,
    AgentEvaluationFailureCategory,
    AgentEvaluationReport,
)
from opslens.agent_baseline.domain.execution import (
    AgentCapabilityInvocation,
    action_for_invocation,
)
from opslens.agent_baseline.domain.models import AgentAbstention, AuthorizedAgentAction


class AgentEvaluationInvocationBuilder(Protocol):
    """Build one already-typed invocation for an authorized offline replay case."""

    def build_invocation(
        self,
        case: AgentEvaluationCase,
        action: AuthorizedAgentAction,
    ) -> AgentCapabilityInvocation:
        """Bind deterministic fixture inputs to one exact authorization."""
        ...


def _rejected_result(
    case: AgentEvaluationCase,
    category: AgentEvaluationFailureCategory,
) -> AgentEvaluationCaseResult:
    """Create one content-free rejected authorization observation."""
    return AgentEvaluationCaseResult.create(
        case=case,
        authorization_outcome=AgentEvaluationAuthorizationOutcome.REJECTED,
        capability=None,
        execution_outcome=AgentEvaluationExecutionOutcome.NOT_ATTEMPTED,
        failure_category=category,
        authorization_evidence_id=None,
        execution_id=None,
        execution_attempts=0,
    )


def _authorized_without_execution(
    case: AgentEvaluationCase,
    action: AuthorizedAgentAction,
) -> AgentEvaluationCaseResult:
    """Record an authorization-only replay without capability execution."""
    return AgentEvaluationCaseResult.create(
        case=case,
        authorization_outcome=AgentEvaluationAuthorizationOutcome.AUTHORIZED,
        capability=action.capability,
        execution_outcome=AgentEvaluationExecutionOutcome.NOT_ATTEMPTED,
        failure_category=None,
        authorization_evidence_id=action.action_id,
        execution_id=None,
        execution_attempts=0,
    )


def _execution_failure_result(
    *,
    case: AgentEvaluationCase,
    action: AuthorizedAgentAction,
    category: AgentEvaluationFailureCategory,
    execution_attempts: int,
) -> AgentEvaluationCaseResult:
    """Record one stable content-free typed execution failure."""
    return AgentEvaluationCaseResult.create(
        case=case,
        authorization_outcome=AgentEvaluationAuthorizationOutcome.AUTHORIZED,
        capability=action.capability,
        execution_outcome=AgentEvaluationExecutionOutcome.FAILED,
        failure_category=category,
        authorization_evidence_id=action.action_id,
        execution_id=None,
        execution_attempts=execution_attempts,
    )


def evaluate_agent_case(
    case: AgentEvaluationCase,
    *,
    invocation_builder: AgentEvaluationInvocationBuilder,
    executors: AgentCapabilityExecutors,
) -> AgentEvaluationCaseResult:
    """Replay one golden case through frozen authorization and execution boundaries."""
    if type(case) is not AgentEvaluationCase:
        raise AgentEvaluationValidationError("case must be one AgentEvaluationCase")
    if type(executors) is not AgentCapabilityExecutors:
        raise AgentEvaluationValidationError("executors must be one AgentCapabilityExecutors")

    try:
        authorization = authorize_agent_action(case.task, case.proposal)
    except AgentCapabilityAuthorizationError:
        return _rejected_result(
            case,
            AgentEvaluationFailureCategory.CAPABILITY_AUTHORIZATION,
        )
    except AgentAuthorityValidationError:
        return _rejected_result(case, AgentEvaluationFailureCategory.AUTHORITY_VALIDATION)

    if type(authorization) is AgentAbstention:
        return AgentEvaluationCaseResult.create(
            case=case,
            authorization_outcome=AgentEvaluationAuthorizationOutcome.ABSTAINED,
            capability=None,
            execution_outcome=AgentEvaluationExecutionOutcome.NOT_ATTEMPTED,
            failure_category=None,
            authorization_evidence_id=authorization.abstention_id,
            execution_id=None,
            execution_attempts=0,
        )

    if type(authorization) is not AuthorizedAgentAction:
        raise AgentEvaluationValidationError("authorization returned an unsupported outcome")

    if case.execution_mode is AgentEvaluationExecutionMode.AUTHORIZATION_ONLY:
        return _authorized_without_execution(case, authorization)

    try:
        invocation = invocation_builder.build_invocation(case, authorization)
        bound_action = action_for_invocation(invocation)
    except (AgentCapabilityExecutionValidationError, TypeError):
        return _execution_failure_result(
            case=case,
            action=authorization,
            category=AgentEvaluationFailureCategory.INVOCATION_CONTRACT,
            execution_attempts=0,
        )

    if bound_action.action_id != authorization.action_id:
        return _execution_failure_result(
            case=case,
            action=authorization,
            category=AgentEvaluationFailureCategory.INVOCATION_CONTRACT,
            execution_attempts=0,
        )

    try:
        execution = execute_authorized_capability(invocation, executors)
    except AgentCapabilityExecutionError as error:
        if error.category is AgentCapabilityExecutionFailureCategory.EXECUTOR_FAILURE:
            category = AgentEvaluationFailureCategory.EXECUTOR_FAILURE
        elif error.category is AgentCapabilityExecutionFailureCategory.RESULT_CONTRACT:
            category = AgentEvaluationFailureCategory.RESULT_CONTRACT
        else:
            raise AgentEvaluationValidationError(
                "execution returned an unsupported stable failure category"
            ) from None
        return _execution_failure_result(
            case=case,
            action=authorization,
            category=category,
            execution_attempts=1,
        )

    return AgentEvaluationCaseResult.create(
        case=case,
        authorization_outcome=AgentEvaluationAuthorizationOutcome.AUTHORIZED,
        capability=authorization.capability,
        execution_outcome=AgentEvaluationExecutionOutcome.ADMITTED,
        failure_category=None,
        authorization_evidence_id=authorization.action_id,
        execution_id=execution.execution_id,
        execution_attempts=1,
    )


def evaluate_agent_dataset(
    dataset: AgentEvaluationDataset,
    *,
    invocation_builder: AgentEvaluationInvocationBuilder,
    executors: AgentCapabilityExecutors,
) -> AgentEvaluationReport:
    """Replay one exact golden corpus and deterministically compute decomposed metrics."""
    if type(dataset) is not AgentEvaluationDataset:
        raise AgentEvaluationValidationError("dataset must be one AgentEvaluationDataset")
    results = tuple(
        evaluate_agent_case(
            case,
            invocation_builder=invocation_builder,
            executors=executors,
        )
        for case in dataset.cases
    )
    return AgentEvaluationReport.create(dataset=dataset, results=results)


__all__ = [
    "AgentEvaluationInvocationBuilder",
    "evaluate_agent_case",
    "evaluate_agent_dataset",
]
