"""Compose and measure the complete non-public Gate 19.2 representative workload."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from opslens.public_analysis.application.evidence_orchestration import (
    PublicRepositoryEvidenceSource,
)
from opslens.public_analysis.application.representative_hybrid_evidence import (
    build_representative_hybrid_evidence,
)
from opslens.public_analysis.application.representative_measurement import (
    MeasurementClock,
    RepresentativeWorkloadPlan,
    measure_representative_workload,
)
from opslens.public_analysis.application.representative_model_reasoning import (
    RepresentativeHybridSynthesizer,
    RepresentativeModelReasoning,
    execute_representative_model_reasoning,
)
from opslens.public_analysis.application.representative_repository_analysis import (
    RepresentativeRepositoryAnalysis,
    RepresentativeRepositoryThreatEvidence,
    build_representative_repository_analysis,
)
from opslens.public_analysis.application.representative_semantic_evidence import (
    RepresentativeSemanticEvidence,
    RepresentativeSemanticRetriever,
    retrieve_representative_semantic_evidence,
)
from opslens.public_analysis.application.representative_structured_evidence import (
    build_representative_structured_evidence,
)
from opslens.public_analysis.application.request_admission import (
    PublicAnalysisRequestAdmission,
    admit_public_analysis_request,
)
from opslens.public_analysis.application.semantic_planning import (
    admit_public_semantic_plan,
    build_public_semantic_planning_request,
)
from opslens.public_analysis.domain import (
    PUBLIC_ANALYSIS_V1_REQUIRED_EVIDENCE_NEEDS,
    ProviderMeasurementCoverage,
    ProviderResourceMetric,
    ProviderResourceUsage,
    PublicAnalysisAdmissionHandoff,
    PublicRepositoryEvidenceExecution,
    PublicSemanticPlanProposal,
    RepresentativePublicAnalysisResult,
    RepresentativeWorkloadMeasurement,
    RepresentativeWorkloadStage,
    provider_measurement_coverage,
)
from opslens.repository_intelligence.application import (
    GitHubSnapshotResolutionEvidence,
    acquire_uv_lock_evidence,
    normalize_uv_lock_pypi_dependencies,
    resolve_github_repository_snapshot,
)
from opslens.repository_intelligence.parsers.uv_lock import parse_uv_lock_evidence
from opslens.risk_policy.application import prioritize_repository_analysis
from opslens.risk_policy.domain import RiskPrioritizationResult

type ProviderUsageSnapshot = Callable[[], ProviderResourceUsage]
type RepresentativeThreatEvidenceLoader = Callable[
    [PublicRepositoryEvidenceExecution], "RepresentativeThreatEvidenceLoad"
]

REPRESENTATIVE_DEFAULT_PROVIDER_COVERAGE = provider_measurement_coverage(
    measured=(
        ProviderResourceMetric.GITHUB_HTTP_REQUEST_COUNT,
        ProviderResourceMetric.BEDROCK_RETRIEVE_COUNT,
        ProviderResourceMetric.BEDROCK_RETRIEVE_CLIENT_ELAPSED_MS,
        ProviderResourceMetric.BEDROCK_MODEL_CALL_COUNT,
        ProviderResourceMetric.BEDROCK_INPUT_TOKENS,
        ProviderResourceMetric.BEDROCK_OUTPUT_TOKENS,
        ProviderResourceMetric.BEDROCK_MODEL_CLIENT_ELAPSED_MS,
        ProviderResourceMetric.BEDROCK_MODEL_LATENCY_MS,
        ProviderResourceMetric.RETRY_COUNT,
    ),
    not_applicable=(
        ProviderResourceMetric.ATHENA_QUERY_COUNT,
        ProviderResourceMetric.ATHENA_BYTES_SCANNED,
    ),
)


@dataclass(frozen=True, slots=True)
class RepresentativeThreatEvidenceLoad:
    """Pre-admitted threat evidence and exact request-time provider usage needed to load it."""

    evidence: RepresentativeRepositoryThreatEvidence
    usage: ProviderResourceUsage = field(default_factory=ProviderResourceUsage)

    def __post_init__(self) -> None:
        """Require one typed deterministic threat-evidence bundle."""
        if type(self.evidence) is not RepresentativeRepositoryThreatEvidence:
            raise TypeError("evidence must be RepresentativeRepositoryThreatEvidence")
        if type(self.usage) is not ProviderResourceUsage:
            raise TypeError("usage must be ProviderResourceUsage")


@dataclass(frozen=True, slots=True)
class RepresentativeWorkloadDependencies:
    """Injected request-time ports required to execute the representative workload."""

    repository_source: PublicRepositoryEvidenceSource
    repository_usage_snapshot: ProviderUsageSnapshot
    threat_evidence_loader: RepresentativeThreatEvidenceLoader
    semantic_retriever: RepresentativeSemanticRetriever
    synthesizer: RepresentativeHybridSynthesizer
    clock: MeasurementClock
    provider_coverage: ProviderMeasurementCoverage = REPRESENTATIVE_DEFAULT_PROVIDER_COVERAGE


@dataclass(frozen=True, slots=True)
class RepresentativeWorkloadExecution:
    """One complete admitted result paired with its exact nine-stage measurement."""

    result: RepresentativePublicAnalysisResult
    measurement: RepresentativeWorkloadMeasurement

    def __post_init__(self) -> None:
        """Keep result-size evidence bound to the exact serialized admitted result."""
        if self.measurement.serialized_result_bytes != len(self.result.serialize()):
            raise ValueError("measurement result bytes must match the admitted result")


@dataclass(slots=True)
class _ExecutionState:
    raw_body: bytes
    repository_source: PublicRepositoryEvidenceSource
    repository_usage_snapshot: ProviderUsageSnapshot
    threat_evidence_loader: RepresentativeThreatEvidenceLoader
    semantic_retriever: RepresentativeSemanticRetriever
    synthesizer: RepresentativeHybridSynthesizer
    repository_usage_previous: ProviderResourceUsage
    admission: PublicAnalysisRequestAdmission | None = None
    snapshot_resolution: GitHubSnapshotResolutionEvidence | None = None
    source_execution: PublicRepositoryEvidenceExecution | None = None
    handoff: PublicAnalysisAdmissionHandoff | None = None
    repository_analysis: RepresentativeRepositoryAnalysis | None = None
    prioritization: RiskPrioritizationResult | None = None
    semantic_evidence: RepresentativeSemanticEvidence | None = None
    model_reasoning: RepresentativeModelReasoning | None = None
    result: RepresentativePublicAnalysisResult | None = None

    def require_admission(self) -> PublicAnalysisRequestAdmission:
        """Return request admission only after its stage has succeeded."""
        if self.admission is None:
            raise RuntimeError("public request admission stage has not completed")
        return self.admission

    def require_snapshot(self) -> GitHubSnapshotResolutionEvidence:
        """Return immutable snapshot resolution only after repository acquisition."""
        if self.snapshot_resolution is None:
            raise RuntimeError("repository acquisition stage has not completed")
        return self.snapshot_resolution

    def require_execution(self) -> PublicRepositoryEvidenceExecution:
        """Return dependency evidence execution only after exact-commit parsing."""
        if self.source_execution is None:
            raise RuntimeError("dependency evidence stage has not completed")
        return self.source_execution

    def require_handoff(self) -> PublicAnalysisAdmissionHandoff:
        """Return deterministic public handoff only after dependency evidence."""
        if self.handoff is None:
            raise RuntimeError("public analysis handoff has not been created")
        return self.handoff

    def require_analysis(self) -> RepresentativeRepositoryAnalysis:
        """Return repository analysis only after vulnerability correlation."""
        if self.repository_analysis is None:
            raise RuntimeError("vulnerability correlation stage has not completed")
        return self.repository_analysis

    def require_prioritization(self) -> RiskPrioritizationResult:
        """Return risk prioritization only after deterministic policy execution."""
        if self.prioritization is None:
            raise RuntimeError("risk prioritization stage has not completed")
        return self.prioritization

    def require_semantic(self) -> RepresentativeSemanticEvidence:
        """Return semantic evidence only after bounded retrieval."""
        if self.semantic_evidence is None:
            raise RuntimeError("semantic evidence stage has not completed")
        return self.semantic_evidence

    def require_reasoning(self) -> RepresentativeModelReasoning:
        """Return admitted model reasoning only after bounded synthesis."""
        if self.model_reasoning is None:
            raise RuntimeError("model reasoning stage has not completed")
        return self.model_reasoning

    def require_result(self) -> RepresentativePublicAnalysisResult:
        """Return final result only after deterministic result admission."""
        if self.result is None:
            raise RuntimeError("result admission stage has not completed")
        return self.result


@dataclass(slots=True)
class _RequestAdmissionAction:
    state: _ExecutionState
    stage: RepresentativeWorkloadStage = RepresentativeWorkloadStage.REQUEST_ADMISSION

    def execute(self) -> ProviderResourceUsage:
        self.state.admission = admit_public_analysis_request(self.state.raw_body)
        return ProviderResourceUsage()


@dataclass(slots=True)
class _RepositoryAcquisitionAction:
    state: _ExecutionState
    stage: RepresentativeWorkloadStage = RepresentativeWorkloadStage.REPOSITORY_ACQUISITION

    def execute(self) -> ProviderResourceUsage:
        request = self.state.require_admission().request
        target = request.target
        self.state.snapshot_resolution = resolve_github_repository_snapshot(
            self.state.repository_source,
            owner=target.owner,
            name=target.name,
            requested_ref=target.requested_ref,
        )
        return _consume_repository_usage(self.state)


@dataclass(slots=True)
class _DependencyEvidenceAction:
    state: _ExecutionState
    stage: RepresentativeWorkloadStage = RepresentativeWorkloadStage.DEPENDENCY_EVIDENCE

    def execute(self) -> ProviderResourceUsage:
        admission = self.state.require_admission()
        resolution = self.state.require_snapshot()
        file_evidence = acquire_uv_lock_evidence(
            self.state.repository_source,
            snapshot=resolution.snapshot,
        )
        parsed_lock = parse_uv_lock_evidence(file_evidence)
        inventory = normalize_uv_lock_pypi_dependencies(parsed_lock)
        execution = PublicRepositoryEvidenceExecution(
            request=admission.request,
            snapshot_resolution=resolution,
            file_evidence=file_evidence,
            parsed_lock=parsed_lock,
            normalization_inventory=inventory,
        )
        planning_request = build_public_semantic_planning_request(execution)
        proposal = PublicSemanticPlanProposal(
            planning_request_sha256=planning_request.request_sha256,
            evidence_needs=PUBLIC_ANALYSIS_V1_REQUIRED_EVIDENCE_NEEDS,
        )
        self.state.source_execution = execution
        self.state.handoff = admit_public_semantic_plan(
            proposal,
            planning_request=planning_request,
            source_execution=execution,
        )
        return _consume_repository_usage(self.state)


@dataclass(slots=True)
class _VulnerabilityCorrelationAction:
    state: _ExecutionState
    stage: RepresentativeWorkloadStage = RepresentativeWorkloadStage.VULNERABILITY_CORRELATION

    def execute(self) -> ProviderResourceUsage:
        execution = self.state.require_execution()
        loaded = self.state.threat_evidence_loader(execution)
        if type(loaded) is not RepresentativeThreatEvidenceLoad:
            raise TypeError("threat loader must return RepresentativeThreatEvidenceLoad")
        self.state.repository_analysis = build_representative_repository_analysis(
            execution=execution,
            threat_evidence=loaded.evidence,
        )
        return loaded.usage


@dataclass(slots=True)
class _RiskPrioritizationAction:
    state: _ExecutionState
    stage: RepresentativeWorkloadStage = RepresentativeWorkloadStage.RISK_PRIORITIZATION

    def execute(self) -> ProviderResourceUsage:
        self.state.prioritization = prioritize_repository_analysis(
            self.state.require_analysis().analysis
        )
        return ProviderResourceUsage()


@dataclass(slots=True)
class _StructuredEvidenceAction:
    state: _ExecutionState
    stage: RepresentativeWorkloadStage = RepresentativeWorkloadStage.STRUCTURED_EVIDENCE

    def execute(self) -> ProviderResourceUsage:
        analysis = self.state.require_analysis().analysis
        prioritization = self.state.require_prioritization()
        build_representative_structured_evidence(
            analysis=analysis,
            prioritization=prioritization,
        )
        return ProviderResourceUsage()


@dataclass(slots=True)
class _SemanticEvidenceAction:
    state: _ExecutionState
    stage: RepresentativeWorkloadStage = RepresentativeWorkloadStage.SEMANTIC_EVIDENCE

    def execute(self) -> ProviderResourceUsage:
        analysis = self.state.require_analysis()
        prioritization = self.state.require_prioritization()
        semantic = retrieve_representative_semantic_evidence(
            analysis=analysis.analysis,
            prioritization=prioritization,
            retriever=self.state.semantic_retriever,
        )
        self.state.semantic_evidence = semantic
        return semantic.usage


@dataclass(slots=True)
class _ModelReasoningAction:
    state: _ExecutionState
    stage: RepresentativeWorkloadStage = RepresentativeWorkloadStage.MODEL_REASONING

    def execute(self) -> ProviderResourceUsage:
        envelope = build_representative_hybrid_evidence(
            handoff=self.state.require_handoff(),
            repository_analysis=self.state.require_analysis(),
            prioritization=self.state.require_prioritization(),
            semantic_evidence=self.state.require_semantic(),
        )
        reasoning = execute_representative_model_reasoning(
            envelope=envelope,
            synthesizer=self.state.synthesizer,
        )
        self.state.model_reasoning = reasoning
        return reasoning.usage


@dataclass(slots=True)
class _ResultAdmissionAction:
    state: _ExecutionState
    stage: RepresentativeWorkloadStage = RepresentativeWorkloadStage.RESULT_ADMISSION

    def execute(self) -> ProviderResourceUsage:
        analysis = self.state.require_analysis()
        prioritization = self.state.require_prioritization()
        reasoning = self.state.require_reasoning()
        self.state.result = RepresentativePublicAnalysisResult(
            handoff=self.state.require_handoff(),
            analysis=analysis.analysis,
            prioritization=prioritization,
            envelope=reasoning.request.envelope,
            synthesis_request=reasoning.request,
            synthesis_result=reasoning.execution.result,
        )
        return ProviderResourceUsage()


@dataclass(slots=True)
class _DeferredResultSerializer:
    state: _ExecutionState

    def serialize(self) -> bytes:
        """Serialize only after the result-admission action has succeeded."""
        return self.state.require_result().serialize()


def _usage_delta(
    current: ProviderResourceUsage,
    previous: ProviderResourceUsage,
) -> ProviderResourceUsage:
    """Return monotonic per-stage provider counter increments."""
    values = (
        current.github_http_request_count - previous.github_http_request_count,
        current.athena_query_count - previous.athena_query_count,
        current.athena_bytes_scanned - previous.athena_bytes_scanned,
        current.bedrock_retrieve_count - previous.bedrock_retrieve_count,
        current.bedrock_retrieve_client_elapsed_ms
        - previous.bedrock_retrieve_client_elapsed_ms,
        current.bedrock_model_call_count - previous.bedrock_model_call_count,
        current.bedrock_input_tokens - previous.bedrock_input_tokens,
        current.bedrock_output_tokens - previous.bedrock_output_tokens,
        current.bedrock_model_client_elapsed_ms
        - previous.bedrock_model_client_elapsed_ms,
        current.bedrock_model_latency_ms - previous.bedrock_model_latency_ms,
        current.retry_count - previous.retry_count,
        current.throttle_count - previous.throttle_count,
    )
    if any(value < 0 for value in values):
        raise ValueError("provider usage snapshot moved backwards")
    return ProviderResourceUsage(
        github_http_request_count=values[0],
        athena_query_count=values[1],
        athena_bytes_scanned=values[2],
        bedrock_retrieve_count=values[3],
        bedrock_retrieve_client_elapsed_ms=values[4],
        bedrock_model_call_count=values[5],
        bedrock_input_tokens=values[6],
        bedrock_output_tokens=values[7],
        bedrock_model_client_elapsed_ms=values[8],
        bedrock_model_latency_ms=values[9],
        retry_count=values[10],
        throttle_count=values[11],
    )


def _consume_repository_usage(state: _ExecutionState) -> ProviderResourceUsage:
    """Consume the request-time repository transport delta for one stage."""
    current = state.repository_usage_snapshot()
    delta = _usage_delta(current, state.repository_usage_previous)
    state.repository_usage_previous = current
    return delta


def execute_representative_workload(
    *,
    run_id: str,
    raw_body: bytes,
    dependencies: RepresentativeWorkloadDependencies,
) -> RepresentativeWorkloadExecution:
    """Execute all nine measured stages with no public transport or infrastructure mutation."""
    baseline = dependencies.repository_usage_snapshot()
    state = _ExecutionState(
        raw_body=raw_body,
        repository_source=dependencies.repository_source,
        repository_usage_snapshot=dependencies.repository_usage_snapshot,
        threat_evidence_loader=dependencies.threat_evidence_loader,
        semantic_retriever=dependencies.semantic_retriever,
        synthesizer=dependencies.synthesizer,
        repository_usage_previous=baseline,
    )
    plan = RepresentativeWorkloadPlan(
        actions=(
            _RequestAdmissionAction(state),
            _RepositoryAcquisitionAction(state),
            _DependencyEvidenceAction(state),
            _VulnerabilityCorrelationAction(state),
            _RiskPrioritizationAction(state),
            _StructuredEvidenceAction(state),
            _SemanticEvidenceAction(state),
            _ModelReasoningAction(state),
            _ResultAdmissionAction(state),
        )
    )
    measurement = measure_representative_workload(
        run_id=run_id,
        plan=plan,
        serializer=_DeferredResultSerializer(state),
        clock=dependencies.clock,
        provider_coverage=dependencies.provider_coverage,
    )
    return RepresentativeWorkloadExecution(
        result=state.require_result(),
        measurement=measurement,
    )


__all__ = [
    "REPRESENTATIVE_DEFAULT_PROVIDER_COVERAGE",
    "ProviderUsageSnapshot",
    "RepresentativeThreatEvidenceLoad",
    "RepresentativeThreatEvidenceLoader",
    "RepresentativeWorkloadDependencies",
    "RepresentativeWorkloadExecution",
    "execute_representative_workload",
]
