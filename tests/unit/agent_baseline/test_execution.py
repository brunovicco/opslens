"""Tests for Gate 11.2 typed capability bindings and one-attempt offline execution."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from opslens.agent_baseline.application import (
    AgentCapabilityExecutionError,
    AgentCapabilityExecutionFailureCategory,
    AgentCapabilityExecutors,
    authorize_agent_action,
    execute_authorized_capability,
)
from opslens.agent_baseline.domain import (
    MAX_AGENT_EXECUTION_ADAPTIVE_FALLBACKS,
    MAX_AGENT_EXECUTION_RETRIES,
    MAX_AGENT_EXECUTIONS_PER_CALL,
    SINGLE_AGENT_EXECUTION_CONTRACT_VERSION,
    AgentActionProposal,
    AgentCapability,
    AgentCapabilityExecution,
    AgentCapabilityExecutionValidationError,
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
from opslens.hybrid_retrieval.application.assembly import assemble_hybrid_evidence
from opslens.hybrid_retrieval.application.evaluation import load_hybrid_evaluation_dataset
from opslens.hybrid_retrieval.application.routing import route_evidence_request
from opslens.hybrid_retrieval.application.synthesis import (
    build_hybrid_synthesis_request,
    parse_hybrid_synthesis_output,
)
from opslens.hybrid_retrieval.domain.evaluation import HybridEvaluationCaseType
from opslens.hybrid_retrieval.domain.models import HybridRoutingRequest
from opslens.hybrid_retrieval.domain.synthesis import (
    HybridSynthesisRequest,
    HybridSynthesisResult,
)
from opslens.knowledge_retrieval.application.context_assembly import assemble_retrieval_context
from opslens.knowledge_retrieval.application.synthesis_contract import build_synthesis_request
from opslens.knowledge_retrieval.domain import (
    KnowledgeSourceType,
    RetrievalBackend,
    RetrievalEvidence,
    RetrievalRequest,
    RetrievedChunk,
    SynthesisAuthorityDecision,
    SynthesisDecision,
    SynthesisRequest,
    SynthesisResult,
)
from opslens.public_analysis.application import (
    admit_public_analysis_request,
    build_public_repository_evidence,
    plan_public_analysis_handoff,
)
from opslens.public_analysis.domain import (
    PUBLIC_ANALYSIS_V1_REQUIRED_EVIDENCE_NEEDS,
    PublicAnalysisAdmissionHandoff,
    PublicAnalysisRequest,
    PublicRepositoryEvidenceExecution,
)
from opslens.repository_intelligence.domain import compute_git_blob_sha1
from opslens.semantic_query.application.models import AthenaQueryResult
from opslens.semantic_query.domain import (
    EpssFilters,
    SemanticDimension,
    SemanticMetric,
    SemanticQuery,
)

_HYBRID_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "hybrid_retrieval"
    / "golden_hybrid_v1.json"
)


def _authorized_action(capability: AgentCapability) -> AuthorizedAgentAction:
    """Create one real Gate 11.1 authorization for a single capability."""
    task = create_single_agent_task(
        text=f"Use {capability.value}",
        allowed_capabilities=(capability,),
    )
    proposal = create_agent_action_proposal(
        task_id=task.task_id,
        decision=AgentDecision.ACT,
        capability=capability,
    )
    result = authorize_agent_action(task, proposal)
    assert type(result) is AuthorizedAgentAction
    return result


def _semantic_query(*, limit: int = 3) -> SemanticQuery:
    """Return one real allowlisted SemanticQuery without arbitrary SQL."""
    return SemanticQuery(
        metric=SemanticMetric.EPSS_SCORE,
        dimensions=(SemanticDimension.CVE,),
        filters=EpssFilters(snapshot_date=date(2026, 9, 7), minimum_score=0.7),
        limit=limit,
    )


def _knowledge_request(
    *,
    question: str = "How should dependencies be installed safely?",
) -> SynthesisRequest:
    """Build one real admitted knowledge synthesis request from offline evidence."""
    chunk = RetrievedChunk.from_text(
        chunk_id="knowledge-chunk:test:agent-execution:v1",
        document_id="knowledge-doc:test:agent-execution:v1",
        source_id="source:test:agent-execution",
        source_type=KnowledgeSourceType.SECURITY_GUIDANCE,
        canonical_uri="https://example.com/security-guidance",
        document_content_sha256="2" * 64,
        text="Require hashes for every dependency artifact.",
        rank=1,
        relevance_score=0.9,
        title="Secure installs",
        section_path=("Hash-checking Mode",),
    )
    evidence = RetrievalEvidence(
        retrieval_id="retrieval:agent-execution-test",
        request=RetrievalRequest(query=question, top_k=1),
        chunks=(chunk,),
        backend=RetrievalBackend.OFFLINE_GOLDEN,
    )
    return build_synthesis_request(
        question=question,
        context=assemble_retrieval_context(evidence),
        authority_decision=SynthesisAuthorityDecision.SUPPORTED,
    )


def _hybrid_request(*, question_suffix: str = "") -> HybridSynthesisRequest:
    """Build one real semantic-only hybrid request from the frozen offline fixture."""
    dataset = load_hybrid_evaluation_dataset(_HYBRID_FIXTURE)
    case = next(
        item
        for item in dataset.cases
        if item.case_type is HybridEvaluationCaseType.SEMANTIC_ONLY_REMEDIATION
    )
    decision = route_evidence_request(
        HybridRoutingRequest(evidence_needs=case.evidence_needs)
    )
    envelope = assemble_hybrid_evidence(
        authority_decision=decision,
        structured_evidence=case.structured_evidence,
        semantic_evidence=case.semantic_evidence,
    )
    return build_hybrid_synthesis_request(
        question=f"{case.question}{question_suffix}",
        envelope=envelope,
    )


_REPOSITORY_ID = 1_333_092_779
_COMMIT_SHA = "3f75a4fc2bd22589df0a5ffe98a8442fda81c8d3"
_TREE_SHA = "01ac6fe03f1db867ef29c6652311ee43b1f63afb"


def _uv_lock_content() -> bytes:
    return (
        b"version = 1\n"
        b"revision = 3\n"
        b"[[package]]\n"
        b'name = "Requests"\n'
        b'version = "2.31.0"\n'
        b'source = { registry = "https://pypi.org/simple" }\n'
    )


@dataclass(slots=True)
class _FakeRepositorySource:
    """Provide deterministic public repository evidence without network calls."""

    def get_repository(self, owner: str, name: str) -> dict[str, object]:
        assert (owner, name) == ("brunovicco", "opslens")
        return {
            "id": _REPOSITORY_ID,
            "name": "opslens",
            "full_name": "brunovicco/opslens",
            "private": False,
            "visibility": "public",
            "default_branch": "main",
            "owner": {"login": "brunovicco"},
        }

    def get_commit(self, owner: str, name: str, ref: str) -> dict[str, object]:
        assert (owner, name, ref) == ("brunovicco", "opslens", "main")
        return {"sha": _COMMIT_SHA, "commit": {"tree": {"sha": _TREE_SHA}}}

    def get_uv_lock(
        self,
        owner: str,
        name: str,
        commit_sha: str,
    ) -> dict[str, object]:
        assert (owner, name, commit_sha) == ("brunovicco", "opslens", _COMMIT_SHA)
        content = _uv_lock_content()
        return {
            "type": "file",
            "path": "uv.lock",
            "name": "uv.lock",
            "encoding": "base64",
            "size": len(content),
            "sha": compute_git_blob_sha1(content),
            "content": base64.encodebytes(content).decode("ascii"),
        }


def _public_request_and_execution(
    *,
    requested_ref: str | None = None,
) -> tuple[PublicAnalysisRequest, PublicRepositoryEvidenceExecution]:
    """Build one real admitted public request and deterministic source execution."""
    ref_json = "null" if requested_ref is None else f'"{requested_ref}"'
    raw = (
        '{"repository_url":"https://github.com/brunovicco/opslens",'
        f'"requested_ref":{ref_json}}}'
    ).encode()
    request = admit_public_analysis_request(raw).request
    execution = build_public_repository_evidence(request, _FakeRepositorySource())
    return request, execution


@dataclass(slots=True)
class _FakeSemanticPlanner:
    """Return the exact fixed public-v1 evidence needs without a model call."""

    def plan(self, request_json: bytes) -> bytes:
        payload: dict[str, object] = {
            "planning_request_sha256": sha256(request_json).hexdigest(),
            "evidence_needs": [
                item.value for item in PUBLIC_ANALYSIS_V1_REQUIRED_EVIDENCE_NEEDS
            ],
        }
        return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


@dataclass(slots=True)
class _StructuredExecutor:
    calls: list[str] = field(default_factory=list[str])
    fail: bool = False
    mismatched_result: bool = False

    def execute_structured_security_query(
        self,
        invocation: StructuredSecurityQueryInvocation,
    ) -> StructuredSecurityQueryResultBinding:
        self.calls.append(invocation.invocation_id)
        if self.fail:
            raise RuntimeError("sensitive downstream failure")
        bound_invocation = invocation
        if self.mismatched_result:
            bound_invocation = StructuredSecurityQueryInvocation.create(
                action=invocation.action,
                query=_semantic_query(limit=4),
            )
        result = AthenaQueryResult(
            query_execution_id="offline-query-1",
            columns=("cve", "epss_score"),
            rows=(("CVE-2026-0001", "0.91"),),
            data_scanned_bytes=128,
        )
        return StructuredSecurityQueryResultBinding.create(
            invocation=bound_invocation,
            result=result,
        )


@dataclass(slots=True)
class _KnowledgeExecutor:
    calls: list[str] = field(default_factory=list[str])
    result_request: SynthesisRequest | None = None

    def execute_knowledge_guidance(
        self,
        invocation: KnowledgeGuidanceInvocation,
    ) -> SynthesisResult:
        self.calls.append(invocation.invocation_id)
        result_request = (
            self.result_request if self.result_request is not None else invocation.request
        )
        return SynthesisResult.create(
            request=result_request,
            decision=SynthesisDecision.INSUFFICIENT_EVIDENCE,
            answer=None,
        )


@dataclass(slots=True)
class _HybridExecutor:
    calls: list[str] = field(default_factory=list[str])
    result_request: HybridSynthesisRequest | None = None

    def execute_hybrid_security_answer(
        self,
        invocation: HybridSecurityAnswerInvocation,
    ) -> HybridSynthesisResult:
        self.calls.append(invocation.invocation_id)
        result_request = (
            self.result_request if self.result_request is not None else invocation.request
        )
        return parse_hybrid_synthesis_output(
            '{"claims":[],"decision":"insufficient_evidence"}',
            request=result_request,
        )


@dataclass(slots=True)
class _PublicExecutor:
    execution: PublicRepositoryEvidenceExecution
    calls: list[str] = field(default_factory=list[str])

    def execute_public_repository_analysis(
        self,
        invocation: PublicRepositoryAnalysisInvocation,
    ) -> PublicAnalysisAdmissionHandoff:
        self.calls.append(invocation.invocation_id)
        return plan_public_analysis_handoff(self.execution, _FakeSemanticPlanner())


def _executors(
    *,
    structured: _StructuredExecutor | None = None,
    knowledge: _KnowledgeExecutor | None = None,
    hybrid: _HybridExecutor | None = None,
    public_execution: PublicRepositoryEvidenceExecution | None = None,
) -> AgentCapabilityExecutors:
    """Build the closed executor set with deterministic in-memory fakes."""
    _, default_public_execution = _public_request_and_execution()
    return AgentCapabilityExecutors(
        structured_security_query=(
            structured if structured is not None else _StructuredExecutor()
        ),
        knowledge_guidance=(knowledge if knowledge is not None else _KnowledgeExecutor()),
        hybrid_security_answer=(hybrid if hybrid is not None else _HybridExecutor()),
        public_repository_analysis=_PublicExecutor(
            public_execution if public_execution is not None else default_public_execution
        ),
    )


def test_execution_contract_is_separate_and_bounded() -> None:
    """Execution gets a separate frozen contract with one attempt and no fallback."""
    assert SINGLE_AGENT_EXECUTION_CONTRACT_VERSION == "single-agent-execution:v1"
    assert MAX_AGENT_EXECUTIONS_PER_CALL == 1
    assert MAX_AGENT_EXECUTION_RETRIES == 0
    assert MAX_AGENT_EXECUTION_ADAPTIVE_FALLBACKS == 0


def test_structured_invocation_is_bound_to_authorization_and_query_semantics() -> None:
    """Equivalent typed inputs share identity while changed query semantics do not."""
    action = _authorized_action(AgentCapability.STRUCTURED_SECURITY_QUERY)
    first = StructuredSecurityQueryInvocation.create(
        action=action,
        query=_semantic_query(limit=3),
    )
    equivalent = StructuredSecurityQueryInvocation.create(
        action=action,
        query=_semantic_query(limit=3),
    )
    changed = StructuredSecurityQueryInvocation.create(
        action=action,
        query=_semantic_query(limit=4),
    )

    assert first.invocation_id == equivalent.invocation_id
    assert first.invocation_sha256 == equivalent.invocation_sha256
    assert first.invocation_id != changed.invocation_id


def test_typed_invocation_rejects_wrong_authorized_capability_before_execution() -> None:
    """A valid authorization for one capability cannot be rebound to another."""
    action = _authorized_action(AgentCapability.KNOWLEDGE_GUIDANCE)

    with pytest.raises(AgentCapabilityExecutionValidationError):
        StructuredSecurityQueryInvocation.create(action=action, query=_semantic_query())


def test_forged_invocation_and_execution_identities_fail_closed() -> None:
    """Caller-forged invocation or execution hashes cannot enter execution evidence."""
    action = _authorized_action(AgentCapability.STRUCTURED_SECURITY_QUERY)
    invocation = StructuredSecurityQueryInvocation.create(
        action=action,
        query=_semantic_query(),
    )

    with pytest.raises(AgentCapabilityExecutionValidationError):
        StructuredSecurityQueryInvocation(
            action=action,
            query=invocation.query,
            invocation_sha256="0" * 64,
            invocation_id=(
                f"{SINGLE_AGENT_EXECUTION_CONTRACT_VERSION}:invocation:{'0' * 64}"
            ),
        )

    with pytest.raises(AgentCapabilityExecutionValidationError):
        AgentCapabilityExecution(
            action_id=action.action_id,
            capability=action.capability,
            invocation_id=invocation.invocation_id,
            downstream_result_sha256="1" * 64,
            execution_sha256="0" * 64,
            execution_id=(
                f"{SINGLE_AGENT_EXECUTION_CONTRACT_VERSION}:execution:{'0' * 64}"
            ),
        )


def test_structured_execution_calls_exactly_once_and_binds_query_to_result() -> None:
    """Structured execution calls one port once and preserves action/invocation identity."""
    action = _authorized_action(AgentCapability.STRUCTURED_SECURITY_QUERY)
    invocation = StructuredSecurityQueryInvocation.create(
        action=action,
        query=_semantic_query(),
    )
    executor = _StructuredExecutor()

    execution = execute_authorized_capability(
        invocation,
        _executors(structured=executor),
    )

    assert executor.calls == [invocation.invocation_id]
    assert execution.action_id == action.action_id
    assert execution.capability is AgentCapability.STRUCTURED_SECURITY_QUERY
    assert execution.invocation_id == invocation.invocation_id


def test_executor_failure_is_content_free_and_has_zero_retry() -> None:
    """Downstream exceptions become bounded failures after exactly one attempted call."""
    action = _authorized_action(AgentCapability.STRUCTURED_SECURITY_QUERY)
    invocation = StructuredSecurityQueryInvocation.create(
        action=action,
        query=_semantic_query(),
    )
    executor = _StructuredExecutor(fail=True)

    with pytest.raises(AgentCapabilityExecutionError) as exc_info:
        execute_authorized_capability(invocation, _executors(structured=executor))

    assert executor.calls == [invocation.invocation_id]
    assert exc_info.value.category is AgentCapabilityExecutionFailureCategory.EXECUTOR_FAILURE
    assert "sensitive downstream failure" not in str(exc_info.value)


def test_structured_result_for_another_invocation_fails_result_admission() -> None:
    """A structured result bound to another query invocation cannot become evidence."""
    action = _authorized_action(AgentCapability.STRUCTURED_SECURITY_QUERY)
    invocation = StructuredSecurityQueryInvocation.create(
        action=action,
        query=_semantic_query(),
    )
    executor = _StructuredExecutor(mismatched_result=True)

    with pytest.raises(AgentCapabilityExecutionError) as exc_info:
        execute_authorized_capability(invocation, _executors(structured=executor))

    assert executor.calls == [invocation.invocation_id]
    assert exc_info.value.category is AgentCapabilityExecutionFailureCategory.RESULT_CONTRACT


def test_knowledge_guidance_executes_one_exact_admitted_request() -> None:
    """Knowledge guidance executes only the exact request bound to the invocation."""
    action = _authorized_action(AgentCapability.KNOWLEDGE_GUIDANCE)
    request = _knowledge_request()
    invocation = KnowledgeGuidanceInvocation.create(action=action, request=request)
    executors = _executors()

    execution = execute_authorized_capability(invocation, executors)

    assert execution.capability is AgentCapability.KNOWLEDGE_GUIDANCE
    assert execution.invocation_id == invocation.invocation_id


def test_knowledge_result_for_another_request_fails_result_admission() -> None:
    """Knowledge output from a different synthesis request cannot be admitted."""
    action = _authorized_action(AgentCapability.KNOWLEDGE_GUIDANCE)
    request = _knowledge_request()
    invocation = KnowledgeGuidanceInvocation.create(action=action, request=request)
    executor = _KnowledgeExecutor(
        result_request=_knowledge_request(question="Use a different evidence request.")
    )

    with pytest.raises(AgentCapabilityExecutionError) as exc_info:
        execute_authorized_capability(invocation, _executors(knowledge=executor))

    assert executor.calls == [invocation.invocation_id]
    assert exc_info.value.category is AgentCapabilityExecutionFailureCategory.RESULT_CONTRACT


def test_hybrid_security_answer_executes_one_exact_admitted_request() -> None:
    """Hybrid answering executes only an already-admitted hybrid synthesis request."""
    action = _authorized_action(AgentCapability.HYBRID_SECURITY_ANSWER)
    request = _hybrid_request()
    invocation = HybridSecurityAnswerInvocation.create(action=action, request=request)
    executors = _executors()

    execution = execute_authorized_capability(invocation, executors)

    assert execution.capability is AgentCapability.HYBRID_SECURITY_ANSWER
    assert execution.invocation_id == invocation.invocation_id


def test_hybrid_result_for_another_request_fails_result_admission() -> None:
    """Hybrid output from another synthesis request cannot be admitted."""
    action = _authorized_action(AgentCapability.HYBRID_SECURITY_ANSWER)
    request = _hybrid_request()
    invocation = HybridSecurityAnswerInvocation.create(action=action, request=request)
    executor = _HybridExecutor(result_request=_hybrid_request(question_suffix=" altered"))

    with pytest.raises(AgentCapabilityExecutionError) as exc_info:
        execute_authorized_capability(invocation, _executors(hybrid=executor))

    assert executor.calls == [invocation.invocation_id]
    assert exc_info.value.category is AgentCapabilityExecutionFailureCategory.RESULT_CONTRACT


def test_public_repository_analysis_executes_one_exact_admitted_request() -> None:
    """Public analysis result must remain bound to the exact admitted public request."""
    request, source_execution = _public_request_and_execution()
    action = _authorized_action(AgentCapability.PUBLIC_REPOSITORY_ANALYSIS)
    invocation = PublicRepositoryAnalysisInvocation.create(action=action, request=request)
    executors = _executors(public_execution=source_execution)

    execution = execute_authorized_capability(invocation, executors)

    assert execution.capability is AgentCapability.PUBLIC_REPOSITORY_ANALYSIS
    assert execution.invocation_id == invocation.invocation_id


def test_public_result_for_another_request_fails_result_admission() -> None:
    """A public handoff for another request cannot be rebound to this invocation."""
    request, _ = _public_request_and_execution()
    _, mismatched_execution = _public_request_and_execution(requested_ref="main")
    action = _authorized_action(AgentCapability.PUBLIC_REPOSITORY_ANALYSIS)
    invocation = PublicRepositoryAnalysisInvocation.create(action=action, request=request)

    with pytest.raises(AgentCapabilityExecutionError) as exc_info:
        execute_authorized_capability(
            invocation,
            _executors(public_execution=mismatched_execution),
        )

    assert exc_info.value.category is AgentCapabilityExecutionFailureCategory.RESULT_CONTRACT


def test_wrong_runtime_invocation_type_fails_closed() -> None:
    """An arbitrary object cannot enter the closed typed invocation dispatch."""
    invalid = cast(
        StructuredSecurityQueryInvocation
        | KnowledgeGuidanceInvocation
        | HybridSecurityAnswerInvocation
        | PublicRepositoryAnalysisInvocation,
        object(),
    )

    with pytest.raises(TypeError, match="recognized typed capability invocation"):
        execute_authorized_capability(invalid, _executors())


def test_proposal_contract_still_has_no_executable_argument_surface() -> None:
    """Gate 11.2 execution must not enlarge the frozen Gate 11.1 proposal surface."""
    assert set(AgentActionProposal.__dataclass_fields__) == {
        "task_id",
        "decision",
        "capability",
        "proposal_sha256",
        "proposal_id",
    }
    for forbidden in (
        "args",
        "kwargs",
        "tool_name",
        "url",
        "sql",
        "command",
        "provider",
        "model_id",
        "retry_policy",
    ):
        assert forbidden not in AgentActionProposal.__dataclass_fields__
