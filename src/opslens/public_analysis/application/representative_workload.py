"""Compose and measure one non-public representative public-analysis workload."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from opslens.hybrid_retrieval.application.assembly import assemble_hybrid_evidence
from opslens.hybrid_retrieval.application.synthesis import build_hybrid_synthesis_request
from opslens.hybrid_retrieval.domain.evidence import (
    SemanticEvidenceChunk,
    StructuredEvidenceRow,
)
from opslens.hybrid_retrieval.domain.synthesis import (
    HybridSynthesisRequest,
    HybridSynthesisResult,
)
from opslens.public_analysis.domain.product_result import (
    PUBLIC_ANALYSIS_SYNTHESIS_QUESTION,
    PublicAnalysisProductResult,
)
from opslens.public_analysis.domain.semantic_planning import PublicAnalysisAdmissionHandoff
from opslens.public_analysis.domain.workload_measurement import (
    PublicAnalysisStageMeasurement,
    PublicAnalysisWorkloadMeasurement,
    PublicAnalysisWorkloadStage,
)


class RepresentativeWorkloadClock(Protocol):
    """Injected monotonic nanosecond clock for internal and end-to-end timings."""

    def monotonic_ns(self) -> int:
        """Return one monotonic nanosecond reading."""
        ...


class PublicAnalysisWorkloadFailureCategory(StrEnum):
    """Content-free failure categories for representative workload composition."""

    CLOCK = "clock"
    PUBLIC_HANDOFF = "public_handoff"
    STRUCTURED_EVIDENCE = "structured_evidence"
    SEMANTIC_EVIDENCE = "semantic_evidence"
    EVIDENCE_ASSEMBLY = "evidence_assembly"
    SYNTHESIS = "synthesis"
    RESULT_ADMISSION = "result_admission"


class PublicAnalysisWorkloadExecutionError(RuntimeError):
    """Bound one representative-workload failure without copying downstream content."""

    def __init__(self, category: PublicAnalysisWorkloadFailureCategory) -> None:
        """Create one stable content-free execution error."""
        self.category = category
        super().__init__(f"representative public workload failed category={category.value}")


def _require_measurement_stage(
    measurement: PublicAnalysisStageMeasurement,
    *,
    expected: PublicAnalysisWorkloadStage,
) -> None:
    """Reject accounting that is mislabeled as another representative stage."""
    if type(measurement) is not PublicAnalysisStageMeasurement:
        raise TypeError("stage measurement must be PublicAnalysisStageMeasurement")
    if measurement.stage is not expected:
        raise ValueError("stage measurement does not match execution wrapper")


@dataclass(frozen=True, slots=True)
class PublicHandoffStageExecution:
    """One admitted public handoff plus measured source/planner accounting."""

    handoff: PublicAnalysisAdmissionHandoff
    measurement: PublicAnalysisStageMeasurement

    def __post_init__(self) -> None:
        """Bind the handoff to the public-handoff measurement stage."""
        if type(self.handoff) is not PublicAnalysisAdmissionHandoff:
            raise TypeError("handoff must be PublicAnalysisAdmissionHandoff")
        _require_measurement_stage(
            self.measurement,
            expected=PublicAnalysisWorkloadStage.PUBLIC_HANDOFF,
        )


@dataclass(frozen=True, slots=True)
class PublicStructuredEvidenceStageExecution:
    """Structured evidence rows plus measured acquisition/resource accounting."""

    evidence: tuple[StructuredEvidenceRow, ...]
    measurement: PublicAnalysisStageMeasurement

    def __post_init__(self) -> None:
        """Require typed rows and the exact structured-evidence measurement stage."""
        if type(self.evidence) is not tuple or any(
            type(item) is not StructuredEvidenceRow for item in self.evidence
        ):
            raise TypeError("structured evidence must contain only StructuredEvidenceRow values")
        _require_measurement_stage(
            self.measurement,
            expected=PublicAnalysisWorkloadStage.STRUCTURED_EVIDENCE,
        )


@dataclass(frozen=True, slots=True)
class PublicSemanticEvidenceStageExecution:
    """Semantic evidence chunks plus measured retrieval/resource accounting."""

    evidence: tuple[SemanticEvidenceChunk, ...]
    measurement: PublicAnalysisStageMeasurement

    def __post_init__(self) -> None:
        """Require typed chunks and the exact semantic-evidence measurement stage."""
        if type(self.evidence) is not tuple or any(
            type(item) is not SemanticEvidenceChunk for item in self.evidence
        ):
            raise TypeError("semantic evidence must contain only SemanticEvidenceChunk values")
        _require_measurement_stage(
            self.measurement,
            expected=PublicAnalysisWorkloadStage.SEMANTIC_EVIDENCE,
        )


@dataclass(frozen=True, slots=True)
class PublicSynthesisStageExecution:
    """One admitted hybrid synthesis result plus measured model accounting."""

    result: HybridSynthesisResult
    measurement: PublicAnalysisStageMeasurement

    def __post_init__(self) -> None:
        """Require one admitted result and the exact synthesis measurement stage."""
        if type(self.result) is not HybridSynthesisResult:
            raise TypeError("result must be HybridSynthesisResult")
        _require_measurement_stage(
            self.measurement,
            expected=PublicAnalysisWorkloadStage.SYNTHESIS,
        )


class PublicHandoffExecutor(Protocol):
    """Port for request-to-handoff execution with content-free measurement evidence."""

    def execute_public_handoff(self, raw_body: bytes) -> PublicHandoffStageExecution:
        """Execute the retained governed public handoff once."""
        ...


class PublicStructuredEvidenceExecutor(Protocol):
    """Port for deterministic vulnerability/risk evidence acquisition."""

    def acquire_structured_evidence(
        self,
        handoff: PublicAnalysisAdmissionHandoff,
    ) -> PublicStructuredEvidenceStageExecution:
        """Acquire exactly the structured evidence authorized by the public route."""
        ...


class PublicSemanticEvidenceExecutor(Protocol):
    """Port for bounded remediation-guidance evidence acquisition."""

    def acquire_semantic_evidence(
        self,
        handoff: PublicAnalysisAdmissionHandoff,
    ) -> PublicSemanticEvidenceStageExecution:
        """Acquire exactly the semantic evidence authorized by the public route."""
        ...


class PublicHybridSynthesisExecutor(Protocol):
    """Port for one bounded synthesis call over an already-admitted evidence envelope."""

    def synthesize_public_analysis(
        self,
        request: HybridSynthesisRequest,
    ) -> PublicSynthesisStageExecution:
        """Execute one admitted public-analysis synthesis request."""
        ...


@dataclass(frozen=True, slots=True)
class RepresentativePublicWorkloadExecutors:
    """Closed executor set for one representative non-public product execution."""

    public_handoff: PublicHandoffExecutor
    structured_evidence: PublicStructuredEvidenceExecutor
    semantic_evidence: PublicSemanticEvidenceExecutor
    synthesis: PublicHybridSynthesisExecutor


@dataclass(frozen=True, slots=True)
class RepresentativePublicWorkloadExecution:
    """Bind one admitted product result to its exact content-free measurement evidence."""

    result: PublicAnalysisProductResult
    measurement: PublicAnalysisWorkloadMeasurement

    def __post_init__(self) -> None:
        """Reject measurement/result identity or response-size drift."""
        if type(self.result) is not PublicAnalysisProductResult:
            raise TypeError("result must be PublicAnalysisProductResult")
        if type(self.measurement) is not PublicAnalysisWorkloadMeasurement:
            raise TypeError("measurement must be PublicAnalysisWorkloadMeasurement")
        if self.measurement.result_id != self.result.result_id:
            raise ValueError("workload measurement result_id drifted")
        if self.measurement.result_sha256 != self.result.result_sha256:
            raise ValueError("workload measurement result_sha256 drifted")
        if self.measurement.result_size_bytes != self.result.serialized_size_bytes:
            raise ValueError("workload measurement result_size_bytes drifted")


def _read_clock(
    clock: RepresentativeWorkloadClock,
) -> int:
    """Read one non-negative monotonic nanosecond value or fail closed."""
    try:
        value = clock.monotonic_ns()
    except Exception:
        raise PublicAnalysisWorkloadExecutionError(
            PublicAnalysisWorkloadFailureCategory.CLOCK
        ) from None
    if type(value) is not int or value < 0:
        raise PublicAnalysisWorkloadExecutionError(
            PublicAnalysisWorkloadFailureCategory.CLOCK
        )
    return value


def _elapsed_ms(
    clock: RepresentativeWorkloadClock,
    *,
    started_ns: int,
) -> int:
    """Return integer milliseconds and reject a non-monotonic injected clock."""
    ended_ns = _read_clock(clock)
    if ended_ns < started_ns:
        raise PublicAnalysisWorkloadExecutionError(
            PublicAnalysisWorkloadFailureCategory.CLOCK
        )
    return (ended_ns - started_ns) // 1_000_000


def _internal_measurement(
    *,
    stage: PublicAnalysisWorkloadStage,
    duration_ms: int,
) -> PublicAnalysisStageMeasurement:
    """Record an internal deterministic stage with provider counters left not-applicable."""
    return PublicAnalysisStageMeasurement(stage=stage, duration_ms=duration_ms)


def execute_representative_public_workload(
    raw_body: bytes,
    executors: RepresentativePublicWorkloadExecutors,
    *,
    clock: RepresentativeWorkloadClock,
) -> RepresentativePublicWorkloadExecution:
    """Compose the Gate 19.2 representative workload without introducing public transport."""
    if type(raw_body) is not bytes:
        raise TypeError("raw_body must be bytes")
    if type(executors) is not RepresentativePublicWorkloadExecutors:
        raise TypeError("executors must be RepresentativePublicWorkloadExecutors")

    end_to_end_started = _read_clock(clock)

    try:
        handoff_execution = executors.public_handoff.execute_public_handoff(raw_body)
    except Exception:
        raise PublicAnalysisWorkloadExecutionError(
            PublicAnalysisWorkloadFailureCategory.PUBLIC_HANDOFF
        ) from None
    if type(handoff_execution) is not PublicHandoffStageExecution:
        raise PublicAnalysisWorkloadExecutionError(
            PublicAnalysisWorkloadFailureCategory.PUBLIC_HANDOFF
        )
    handoff = handoff_execution.handoff

    try:
        structured_execution = executors.structured_evidence.acquire_structured_evidence(
            handoff
        )
    except Exception:
        raise PublicAnalysisWorkloadExecutionError(
            PublicAnalysisWorkloadFailureCategory.STRUCTURED_EVIDENCE
        ) from None
    if type(structured_execution) is not PublicStructuredEvidenceStageExecution:
        raise PublicAnalysisWorkloadExecutionError(
            PublicAnalysisWorkloadFailureCategory.STRUCTURED_EVIDENCE
        )

    try:
        semantic_execution = executors.semantic_evidence.acquire_semantic_evidence(handoff)
    except Exception:
        raise PublicAnalysisWorkloadExecutionError(
            PublicAnalysisWorkloadFailureCategory.SEMANTIC_EVIDENCE
        ) from None
    if type(semantic_execution) is not PublicSemanticEvidenceStageExecution:
        raise PublicAnalysisWorkloadExecutionError(
            PublicAnalysisWorkloadFailureCategory.SEMANTIC_EVIDENCE
        )

    assembly_started = _read_clock(clock)
    try:
        envelope = assemble_hybrid_evidence(
            authority_decision=handoff.route_decision,
            structured_evidence=structured_execution.evidence,
            semantic_evidence=semantic_execution.evidence,
        )
        synthesis_request = build_hybrid_synthesis_request(
            question=PUBLIC_ANALYSIS_SYNTHESIS_QUESTION,
            envelope=envelope,
        )
    except Exception:
        raise PublicAnalysisWorkloadExecutionError(
            PublicAnalysisWorkloadFailureCategory.EVIDENCE_ASSEMBLY
        ) from None
    assembly_measurement = _internal_measurement(
        stage=PublicAnalysisWorkloadStage.EVIDENCE_ASSEMBLY,
        duration_ms=_elapsed_ms(clock, started_ns=assembly_started),
    )

    try:
        synthesis_execution = executors.synthesis.synthesize_public_analysis(
            synthesis_request
        )
    except Exception:
        raise PublicAnalysisWorkloadExecutionError(
            PublicAnalysisWorkloadFailureCategory.SYNTHESIS
        ) from None
    if type(synthesis_execution) is not PublicSynthesisStageExecution:
        raise PublicAnalysisWorkloadExecutionError(
            PublicAnalysisWorkloadFailureCategory.SYNTHESIS
        )

    result_started = _read_clock(clock)
    try:
        result = PublicAnalysisProductResult(
            handoff=handoff,
            synthesis_request=synthesis_request,
            synthesis_result=synthesis_execution.result,
        )
    except Exception:
        raise PublicAnalysisWorkloadExecutionError(
            PublicAnalysisWorkloadFailureCategory.RESULT_ADMISSION
        ) from None
    result_measurement = _internal_measurement(
        stage=PublicAnalysisWorkloadStage.RESULT_ADMISSION,
        duration_ms=_elapsed_ms(clock, started_ns=result_started),
    )

    end_to_end_duration_ms = _elapsed_ms(clock, started_ns=end_to_end_started)
    measurement = PublicAnalysisWorkloadMeasurement(
        result_id=result.result_id,
        result_sha256=result.result_sha256,
        result_size_bytes=result.serialized_size_bytes,
        end_to_end_duration_ms=end_to_end_duration_ms,
        stages=(
            handoff_execution.measurement,
            structured_execution.measurement,
            semantic_execution.measurement,
            assembly_measurement,
            synthesis_execution.measurement,
            result_measurement,
        ),
    )
    return RepresentativePublicWorkloadExecution(
        result=result,
        measurement=measurement,
    )


__all__ = [
    "PublicAnalysisWorkloadExecutionError",
    "PublicAnalysisWorkloadFailureCategory",
    "PublicHandoffExecutor",
    "PublicHandoffStageExecution",
    "PublicHybridSynthesisExecutor",
    "PublicSemanticEvidenceExecutor",
    "PublicSemanticEvidenceStageExecution",
    "PublicStructuredEvidenceExecutor",
    "PublicStructuredEvidenceStageExecution",
    "PublicSynthesisStageExecution",
    "RepresentativePublicWorkloadExecution",
    "RepresentativePublicWorkloadExecutors",
    "RepresentativeWorkloadClock",
    "execute_representative_public_workload",
]
