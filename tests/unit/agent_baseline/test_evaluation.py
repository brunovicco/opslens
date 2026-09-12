"""Tests for Gate 11.3 deterministic offline single-agent evaluation."""

import json
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path
from typing import cast

import pytest

from opslens.agent_baseline.application import AgentCapabilityExecutors
from opslens.agent_baseline.application.evaluation import (
    AgentEvaluationInvocationBuilder,
    evaluate_agent_case,
    evaluate_agent_dataset,
)
from opslens.agent_baseline.application.evaluation_dataset import (
    load_agent_evaluation_dataset,
)
from opslens.agent_baseline.domain import (
    MAX_AGENT_EXECUTIONS_PER_CALL,
    AgentCapability,
    HybridSecurityAnswerInvocation,
    KnowledgeGuidanceInvocation,
    PublicRepositoryAnalysisInvocation,
    StructuredSecurityQueryInvocation,
    StructuredSecurityQueryResultBinding,
)
from opslens.agent_baseline.domain.errors import AgentEvaluationValidationError
from opslens.agent_baseline.domain.evaluation import (
    SINGLE_AGENT_EVALUATION_CONTRACT_VERSION,
    AgentEvaluationAuthorizationOutcome,
    AgentEvaluationCase,
    AgentEvaluationDataset,
    AgentEvaluationExecutionMode,
    AgentEvaluationExecutionOutcome,
    AgentEvaluationExpectation,
    AgentEvaluationFailureCategory,
    AgentEvaluationReport,
)
from opslens.agent_baseline.domain.models import AuthorizedAgentAction
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

_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "agent_baseline"
    / "golden_single_agent_evaluation_v1.json"
)


def _semantic_query(*, limit: int = 3) -> SemanticQuery:
    """Return one real allowlisted structured query for typed offline execution."""
    return SemanticQuery(
        metric=SemanticMetric.EPSS_SCORE,
        dimensions=(SemanticDimension.CVE,),
        filters=EpssFilters(snapshot_date=date(2026, 9, 7), minimum_score=0.7),
        limit=limit,
    )


@dataclass(slots=True)
class _StructuredInvocationBuilder(AgentEvaluationInvocationBuilder):
    """Bind fixture cases to the real structured-query invocation contract."""

    calls: list[str] = field(default_factory=list[str])

    def build_invocation(
        self,
        case: AgentEvaluationCase,
        action: AuthorizedAgentAction,
    ) -> StructuredSecurityQueryInvocation:
        self.calls.append(case.case_key)
        return StructuredSecurityQueryInvocation.create(
            action=action,
            query=_semantic_query(),
        )


@dataclass(slots=True)
class _EvaluationStructuredExecutor:
    """Produce admitted, executor-failure, or wrong-binding results by task identity."""

    executor_failure_task_ids: frozenset[str]
    result_contract_failure_task_ids: frozenset[str]
    calls: list[str] = field(default_factory=list[str])

    def execute_structured_security_query(
        self,
        invocation: StructuredSecurityQueryInvocation,
    ) -> StructuredSecurityQueryResultBinding:
        self.calls.append(invocation.invocation_id)
        task_id = invocation.action.task_id
        if task_id in self.executor_failure_task_ids:
            raise RuntimeError("sensitive downstream executor payload")
        bound_invocation = invocation
        if task_id in self.result_contract_failure_task_ids:
            bound_invocation = StructuredSecurityQueryInvocation.create(
                action=invocation.action,
                query=_semantic_query(limit=4),
            )
        result = AthenaQueryResult(
            query_execution_id="gate-11-3-offline-query",
            columns=("cve", "epss_score"),
            rows=(("CVE-2026-0001", "0.91"),),
            data_scanned_bytes=128,
        )
        return StructuredSecurityQueryResultBinding.create(
            invocation=bound_invocation,
            result=result,
        )


class _NeverCalledExecutor:
    """Fail the test if an unrelated capability is dispatched by the evaluator."""

    def execute_knowledge_guidance(
        self,
        invocation: KnowledgeGuidanceInvocation,
    ) -> SynthesisResult:
        raise AssertionError(f"unexpected knowledge execution {invocation.invocation_id}")

    def execute_hybrid_security_answer(
        self,
        invocation: HybridSecurityAnswerInvocation,
    ) -> HybridSynthesisResult:
        raise AssertionError(f"unexpected hybrid execution {invocation.invocation_id}")

    def execute_public_repository_analysis(
        self,
        invocation: PublicRepositoryAnalysisInvocation,
    ) -> PublicAnalysisAdmissionHandoff:
        raise AssertionError(f"unexpected public execution {invocation.invocation_id}")


def _case(dataset: AgentEvaluationDataset, case_key: str) -> AgentEvaluationCase:
    """Return one named golden case."""
    return next(case for case in dataset.cases if case.case_key == case_key)


def _dependencies(
    dataset: AgentEvaluationDataset,
) -> tuple[_StructuredInvocationBuilder, AgentCapabilityExecutors, _EvaluationStructuredExecutor]:
    """Build deterministic in-memory execution dependencies for the golden corpus."""
    structured = _EvaluationStructuredExecutor(
        executor_failure_task_ids=frozenset(
            {_case(dataset, "structured-executor-failure").task.task_id}
        ),
        result_contract_failure_task_ids=frozenset(
            {_case(dataset, "structured-result-contract-failure").task.task_id}
        ),
    )
    never = _NeverCalledExecutor()
    return (
        _StructuredInvocationBuilder(),
        AgentCapabilityExecutors(
            structured_security_query=structured,
            knowledge_guidance=never,
            hybrid_security_answer=never,
            public_repository_analysis=never,
        ),
        structured,
    )


def test_golden_dataset_freezes_decomposed_offline_cases() -> None:
    """The Gate 11.3 corpus covers authorization, abstention, and typed execution failures."""
    dataset = load_agent_evaluation_dataset(_FIXTURE)

    assert SINGLE_AGENT_EVALUATION_CONTRACT_VERSION == "single-agent-evaluation:v1"
    assert len(dataset.cases) == 6
    assert tuple(case.case_key for case in dataset.cases) == (
        "authorized-structured-no-execution",
        "explicit-abstention",
        "structured-execution-admitted",
        "structured-executor-failure",
        "structured-result-contract-failure",
        "unauthorized-capability",
    )
    assert len(dataset.corpus_sha256) == 64


def test_offline_evaluation_replays_frozen_authority_and_execution_contracts() -> None:
    """All golden cases replay exactly and expose decomposed deterministic metrics."""
    dataset = load_agent_evaluation_dataset(_FIXTURE)
    builder, executors, structured = _dependencies(dataset)

    report = evaluate_agent_dataset(
        dataset,
        invocation_builder=builder,
        executors=executors,
    )

    assert report.metrics.total_cases == 6
    assert report.metrics.passed_cases == 6
    assert report.metrics.authorization_matches == 6
    assert report.metrics.capability_matches == 6
    assert report.metrics.execution_matches == 6
    assert report.metrics.failure_category_matches == 6
    assert report.metrics.bounds_compliant_cases == 6
    assert builder.calls == [
        "structured-execution-admitted",
        "structured-executor-failure",
        "structured-result-contract-failure",
    ]
    assert len(structured.calls) == 3

    abstention = next(
        result for result in report.results if result.case.case_key == "explicit-abstention"
    )
    unauthorized = next(
        result for result in report.results if result.case.case_key == "unauthorized-capability"
    )
    executor_failure = next(
        result
        for result in report.results
        if result.case.case_key == "structured-executor-failure"
    )
    result_failure = next(
        result
        for result in report.results
        if result.case.case_key == "structured-result-contract-failure"
    )

    assert abstention.authorization_outcome is AgentEvaluationAuthorizationOutcome.ABSTAINED
    assert abstention.execution_attempts == 0
    assert unauthorized.failure_category is AgentEvaluationFailureCategory.CAPABILITY_AUTHORIZATION
    assert unauthorized.execution_attempts == 0
    assert executor_failure.failure_category is AgentEvaluationFailureCategory.EXECUTOR_FAILURE
    assert executor_failure.execution_attempts == MAX_AGENT_EXECUTIONS_PER_CALL
    assert result_failure.failure_category is AgentEvaluationFailureCategory.RESULT_CONTRACT
    assert result_failure.execution_attempts == MAX_AGENT_EXECUTIONS_PER_CALL


def test_report_identity_is_reproducible_and_does_not_admit_executor_messages() -> None:
    """Equivalent replays produce one identity and never persist arbitrary executor content."""
    first_dataset = load_agent_evaluation_dataset(_FIXTURE)
    first_builder, first_executors, _ = _dependencies(first_dataset)
    first = evaluate_agent_dataset(
        first_dataset,
        invocation_builder=first_builder,
        executors=first_executors,
    )

    second_dataset = load_agent_evaluation_dataset(_FIXTURE)
    second_builder, second_executors, _ = _dependencies(second_dataset)
    second = evaluate_agent_dataset(
        second_dataset,
        invocation_builder=second_builder,
        executors=second_executors,
    )

    assert first_dataset.corpus_sha256 == second_dataset.corpus_sha256
    assert first.report_sha256 == second.report_sha256
    assert first.report_id == second.report_id
    persisted = json.dumps(first.to_dict(), separators=(",", ":"), sort_keys=True)
    assert "sensitive downstream executor payload" not in persisted
    assert "provider" not in persisted
    assert "model_id" not in persisted


def test_wrong_golden_capability_is_scored_false_without_changing_observation() -> None:
    """A wrong golden capability fails its metric without changing the observation."""
    dataset = load_agent_evaluation_dataset(_FIXTURE)
    original = _case(dataset, "authorized-structured-no-execution")
    wrong_case = AgentEvaluationCase.create(
        case_key="wrong-capability-expectation",
        task=original.task,
        proposal=original.proposal,
        execution_mode=AgentEvaluationExecutionMode.AUTHORIZATION_ONLY,
        expectation=AgentEvaluationExpectation(
            authorization_outcome=AgentEvaluationAuthorizationOutcome.AUTHORIZED,
            capability=AgentCapability.KNOWLEDGE_GUIDANCE,
            execution_outcome=AgentEvaluationExecutionOutcome.NOT_ATTEMPTED,
            failure_category=None,
        ),
    )
    builder, executors, _ = _dependencies(dataset)

    result = evaluate_agent_case(
        wrong_case,
        invocation_builder=builder,
        executors=executors,
    )

    assert result.authorization_match is True
    assert result.capability is AgentCapability.STRUCTURED_SECURITY_QUERY
    assert result.capability_match is False
    assert result.execution_match is True
    assert result.failure_category_match is True
    assert result.bounds_compliant is True
    assert result.passed is False


def test_dataset_loader_rejects_unknown_schema_fields_fail_closed(tmp_path: Path) -> None:
    """Fixture schema drift is rejected before any authorization or execution replay."""
    raw: object = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    assert type(raw) is dict
    payload = dict(cast(dict[str, object], raw))
    payload["unexpected"] = True
    fixture = tmp_path / "invalid-evaluation.json"
    fixture.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        AgentEvaluationValidationError,
        match="dataset fields do not match the v1 schema",
    ):
        load_agent_evaluation_dataset(fixture)


def test_forged_report_identity_fails_closed() -> None:
    """A caller cannot rewrite content-addressed evaluation evidence after scoring."""
    dataset = load_agent_evaluation_dataset(_FIXTURE)
    builder, executors, _ = _dependencies(dataset)
    report = evaluate_agent_dataset(
        dataset,
        invocation_builder=builder,
        executors=executors,
    )

    with pytest.raises(AgentEvaluationValidationError, match="report_sha256"):
        replace(report, report_sha256="0" * 64)

    with pytest.raises(AgentEvaluationValidationError, match="results must correspond"):
        AgentEvaluationReport.create(
            dataset=dataset,
            results=report.results[:-1],
        )
