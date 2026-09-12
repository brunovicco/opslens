"""Tests for the Gate 19.2 representative public-workload composition boundary."""

import base64
import json
from dataclasses import dataclass, field
from hashlib import sha256

import pytest

from opslens.hybrid_retrieval.domain import EvidenceNeed
from opslens.hybrid_retrieval.domain.evidence import (
    SemanticEvidenceChunk,
    StructuredEvidenceAuthority,
    StructuredEvidenceField,
    StructuredEvidenceRow,
)
from opslens.hybrid_retrieval.domain.synthesis import (
    HybridSynthesisClaim,
    HybridSynthesisDecision,
    HybridSynthesisRequest,
    HybridSynthesisResult,
)
from opslens.public_analysis.application import (
    admit_public_analysis_request,
    build_public_repository_evidence,
    plan_public_analysis_handoff,
)
from opslens.public_analysis.application.representative_workload import (
    PublicAnalysisWorkloadExecutionError,
    PublicAnalysisWorkloadFailureCategory,
    PublicHandoffStageExecution,
    PublicSemanticEvidenceStageExecution,
    PublicStructuredEvidenceStageExecution,
    PublicSynthesisStageExecution,
    RepresentativePublicWorkloadExecutors,
    execute_representative_public_workload,
)
from opslens.public_analysis.domain import (
    PUBLIC_ANALYSIS_V1_REQUIRED_EVIDENCE_NEEDS,
    PublicAnalysisAdmissionHandoff,
)
from opslens.public_analysis.domain.product_result import (
    PUBLIC_ANALYSIS_PRODUCT_RESULT_CONTRACT_VERSION,
    PUBLIC_ANALYSIS_SYNTHESIS_QUESTION,
)
from opslens.public_analysis.domain.workload_measurement import (
    PUBLIC_ANALYSIS_WORKLOAD_ID,
    PublicAnalysisStageMeasurement,
    PublicAnalysisWorkloadStage,
)
from opslens.repository_intelligence.domain import compute_git_blob_sha1

_REPOSITORY_ID = 1_333_092_779
_COMMIT_SHA = "3f75a4fc2bd22589df0a5ffe98a8442fda81c8d3"
_TREE_SHA = "01ac6fe03f1db867ef29c6652311ee43b1f63afb"


def _uv_lock_content() -> bytes:
    """Return one inert dependency file that is parsed but never executed."""
    return (
        b"version = 1\n"
        b"revision = 3\n"
        b"[[package]]\n"
        b'name = "Requests"\n'
        b'version = "2.31.0"\n'
        b'source = { registry = "https://pypi.org/simple" }\n'
    )


@dataclass(slots=True)
class _RepositorySource:
    """Provide deterministic public repository evidence without network access."""

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


def _need_values() -> tuple[str, ...]:
    """Return the exact public-v1 semantic evidence-need values."""
    return tuple(need.value for need in PUBLIC_ANALYSIS_V1_REQUIRED_EVIDENCE_NEEDS)


@dataclass(slots=True)
class _Planner:
    """Return the fixed public-v1 evidence need proposal."""

    def plan(self, request_json: bytes) -> bytes:
        return json.dumps(
            {
                "evidence_needs": list(_need_values()),
                "planning_request_sha256": sha256(request_json).hexdigest(),
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode()


def _handoff() -> PublicAnalysisAdmissionHandoff:
    """Build one real admitted public-analysis handoff over inert fake source evidence."""
    raw = (
        b'{"repository_url":"https://github.com/brunovicco/opslens",'
        b'"requested_ref":null}'
    )
    request = admit_public_analysis_request(raw).request
    execution = build_public_repository_evidence(request, _RepositorySource())
    return plan_public_analysis_handoff(execution, _Planner())


def _structured_evidence(
    handoff: PublicAnalysisAdmissionHandoff,
) -> tuple[StructuredEvidenceRow, ...]:
    """Build exact structured evidence for the two public structured needs."""
    source = handoff.source_execution
    vulnerability = StructuredEvidenceRow(
        evidence_need=EvidenceNeed.VULNERABILITY_FACTS,
        authority=StructuredEvidenceAuthority.REPOSITORY_ANALYSIS,
        source_artifact_id=source.execution_id,
        source_artifact_sha256=source.evidence_sha256,
        row_key="finding-1",
        fields=(
            StructuredEvidenceField(name="cve", value="CVE-2026-0001"),
            StructuredEvidenceField(name="package", value="requests"),
        ),
    )
    risk = StructuredEvidenceRow(
        evidence_need=EvidenceNeed.RISK_PRIORITY,
        authority=StructuredEvidenceAuthority.RISK_POLICY,
        source_artifact_id="risk-policy:v1:test",
        source_artifact_sha256="b" * 64,
        row_key="finding-1",
        fields=(StructuredEvidenceField(name="priority", value="high"),),
    )
    return (vulnerability, risk)


def _semantic_evidence() -> tuple[SemanticEvidenceChunk, ...]:
    """Build one admitted remediation-guidance chunk with complete provenance."""
    text = "Upgrade the affected package to the first fixed version after validation."
    return (
        SemanticEvidenceChunk(
            retrieval_id="retrieval-test-1",
            chunk_id="chunk-test-1",
            document_id="document-test-1",
            source_id="source-test-1",
            source_type="official_advisory",
            canonical_uri="https://example.com/security/advisory",
            document_content_sha256="c" * 64,
            chunk_content_sha256=sha256(text.encode()).hexdigest(),
            text=text,
            rank=1,
            relevance_score=0.91,
            title="Security advisory",
            section_path=("Remediation",),
        ),
    )


@dataclass(slots=True)
class _HandoffExecutor:
    handoff: PublicAnalysisAdmissionHandoff

    def execute_public_handoff(self, raw_body: bytes) -> PublicHandoffStageExecution:
        assert raw_body.startswith(b"{")
        return PublicHandoffStageExecution(
            handoff=self.handoff,
            measurement=PublicAnalysisStageMeasurement(
                stage=PublicAnalysisWorkloadStage.PUBLIC_HANDOFF,
                duration_ms=10,
                github_http_request_count=3,
                retry_count=0,
                throttle_count=0,
            ),
        )


@dataclass(slots=True)
class _StructuredExecutor:
    rows: tuple[StructuredEvidenceRow, ...]
    handoff_ids: list[str] = field(default_factory=lambda: list[str]())

    def acquire_structured_evidence(
        self,
        handoff: PublicAnalysisAdmissionHandoff,
    ) -> PublicStructuredEvidenceStageExecution:
        self.handoff_ids.append(handoff.handoff_id)
        return PublicStructuredEvidenceStageExecution(
            evidence=self.rows,
            measurement=PublicAnalysisStageMeasurement(
                stage=PublicAnalysisWorkloadStage.STRUCTURED_EVIDENCE,
                duration_ms=15,
                athena_query_count=1,
                athena_bytes_scanned=1024,
                retry_count=0,
                throttle_count=0,
            ),
        )


@dataclass(slots=True)
class _SemanticExecutor:
    chunks: tuple[SemanticEvidenceChunk, ...]

    def acquire_semantic_evidence(
        self,
        handoff: PublicAnalysisAdmissionHandoff,
    ) -> PublicSemanticEvidenceStageExecution:
        assert handoff.handoff_id
        return PublicSemanticEvidenceStageExecution(
            evidence=self.chunks,
            measurement=PublicAnalysisStageMeasurement(
                stage=PublicAnalysisWorkloadStage.SEMANTIC_EVIDENCE,
                duration_ms=10,
                bedrock_retrieve_call_count=1,
                bedrock_retrieve_latency_ms=8,
                retry_count=0,
                throttle_count=0,
            ),
        )


@dataclass(slots=True)
class _SynthesisExecutor:
    fail: bool = False
    request_sha256: str | None = None

    def synthesize_public_analysis(
        self,
        request: HybridSynthesisRequest,
    ) -> PublicSynthesisStageExecution:
        if self.fail:
            raise RuntimeError("provider output must not escape")
        self.request_sha256 = request.request_sha256
        claim = HybridSynthesisClaim.create(
            request=request,
            claim_index=1,
            text="Prioritize the admitted affected package and apply the cited remediation.",
            semantic_citation_ids=("S1",),
            structured_fact_ids=("F1", "F2", "F3"),
        )
        result = HybridSynthesisResult.create(
            request=request,
            decision=HybridSynthesisDecision.ANSWER,
            claims=(claim,),
        )
        return PublicSynthesisStageExecution(
            result=result,
            measurement=PublicAnalysisStageMeasurement(
                stage=PublicAnalysisWorkloadStage.SYNTHESIS,
                duration_ms=5,
                bedrock_model_call_count=1,
                bedrock_input_tokens=120,
                bedrock_output_tokens=40,
                bedrock_model_latency_ms=4,
                retry_count=0,
                throttle_count=0,
            ),
        )


@dataclass(slots=True)
class _Clock:
    values: list[int]

    def monotonic_ns(self) -> int:
        if not self.values:
            raise AssertionError("clock exhausted")
        return self.values.pop(0)


def _executors(
    *,
    synthesis: _SynthesisExecutor | None = None,
) -> tuple[PublicAnalysisAdmissionHandoff, RepresentativePublicWorkloadExecutors]:
    """Build one closed fake executor set around a real admitted public handoff."""
    handoff = _handoff()
    return handoff, RepresentativePublicWorkloadExecutors(
        public_handoff=_HandoffExecutor(handoff),
        structured_evidence=_StructuredExecutor(_structured_evidence(handoff)),
        semantic_evidence=_SemanticExecutor(_semantic_evidence()),
        synthesis=synthesis or _SynthesisExecutor(),
    )


def test_representative_workload_binds_result_and_measurement_without_public_transport() -> None:
    """The composed workload reaches one evidence-bound result and exact stage accounting."""
    handoff, executors = _executors()
    clock = _Clock(
        [
            0,
            50_000_000,
            55_000_000,
            80_000_000,
            81_000_000,
            100_000_000,
        ]
    )

    execution = execute_representative_public_workload(
        b'{"repository_url":"https://github.com/brunovicco/opslens"}',
        executors,
        clock=clock,
    )

    assert execution.result.handoff is handoff
    assert execution.result.synthesis_request.question == PUBLIC_ANALYSIS_SYNTHESIS_QUESTION
    assert execution.result.result_id.startswith(
        f"{PUBLIC_ANALYSIS_PRODUCT_RESULT_CONTRACT_VERSION}@sha256:"
    )
    assert execution.measurement.workload_id == PUBLIC_ANALYSIS_WORKLOAD_ID
    assert execution.measurement.result_sha256 == execution.result.result_sha256
    assert execution.measurement.result_size_bytes == len(execution.result.canonical_json)
    assert execution.measurement.end_to_end_duration_ms == 100
    assert tuple(item.stage for item in execution.measurement.stages) == tuple(
        PublicAnalysisWorkloadStage
    )
    assert execution.measurement.stages[0].github_http_request_count == 3
    assert execution.measurement.stages[1].athena_bytes_scanned == 1024
    assert execution.measurement.stages[2].bedrock_retrieve_call_count == 1
    assert execution.measurement.stages[4].bedrock_model_call_count == 1

    decoded = json.loads(execution.result.canonical_json)
    assert decoded["repository"]["commit_sha"] == _COMMIT_SHA
    assert decoded["evidence"]["semantic_citations"][0]["canonical_uri"] == (
        "https://example.com/security/advisory"
    )
    assert "text" not in decoded["evidence"]["semantic_citations"][0]
    assert decoded["synthesis"]["decision"] == "answer"


def test_missing_required_semantic_evidence_fails_before_model_execution() -> None:
    """ALL_REQUIRED completeness fails closed before synthesis receives authority."""
    handoff = _handoff()
    synthesis = _SynthesisExecutor()
    executors = RepresentativePublicWorkloadExecutors(
        public_handoff=_HandoffExecutor(handoff),
        structured_evidence=_StructuredExecutor(_structured_evidence(handoff)),
        semantic_evidence=_SemanticExecutor(()),
        synthesis=synthesis,
    )
    clock = _Clock([0, 1_000_000])

    with pytest.raises(PublicAnalysisWorkloadExecutionError) as exc_info:
        execute_representative_public_workload(b"{}", executors, clock=clock)

    assert exc_info.value.category is PublicAnalysisWorkloadFailureCategory.EVIDENCE_ASSEMBLY
    assert synthesis.request_sha256 is None


def test_synthesis_failure_is_content_free_and_does_not_admit_a_result() -> None:
    """Provider exception text does not cross the representative workload boundary."""
    synthesis = _SynthesisExecutor(fail=True)
    _, executors = _executors(synthesis=synthesis)
    clock = _Clock([0, 1_000_000, 2_000_000])

    with pytest.raises(PublicAnalysisWorkloadExecutionError) as exc_info:
        execute_representative_public_workload(b"{}", executors, clock=clock)

    assert exc_info.value.category is PublicAnalysisWorkloadFailureCategory.SYNTHESIS
    assert "provider output" not in str(exc_info.value)
