"""Domain contracts for non-public representative workload measurement."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from opslens.public_analysis.domain.errors import PublicAnalysisValidationError

REPRESENTATIVE_PUBLIC_ANALYSIS_WORKLOAD_ID = "public-analysis-workload:v1"


class RepresentativeWorkloadStage(StrEnum):
    """Ordered stages required by the Gate 19.2 representative workload."""

    REQUEST_ADMISSION = "public_request_admission"
    REPOSITORY_ACQUISITION = "repository_acquisition"
    DEPENDENCY_EVIDENCE = "dependency_evidence"
    VULNERABILITY_CORRELATION = "vulnerability_correlation"
    RISK_PRIORITIZATION = "risk_prioritization"
    STRUCTURED_EVIDENCE = "structured_evidence"
    SEMANTIC_EVIDENCE = "semantic_evidence"
    MODEL_REASONING = "model_reasoning"
    RESULT_ADMISSION = "result_admission"


REPRESENTATIVE_WORKLOAD_STAGE_ORDER = tuple(RepresentativeWorkloadStage)


@dataclass(frozen=True, slots=True)
class ProviderResourceUsage:
    """Measured provider/resource counters for one executed representative stage."""

    github_http_request_count: int = 0
    athena_query_count: int = 0
    athena_bytes_scanned: int = 0
    bedrock_retrieve_count: int = 0
    bedrock_model_call_count: int = 0
    bedrock_input_tokens: int = 0
    bedrock_output_tokens: int = 0
    retry_count: int = 0
    throttle_count: int = 0

    def __post_init__(self) -> None:
        """Reject negative or non-integer measured counters."""
        for field_name, value in self.as_items():
            if type(value) is not int or value < 0:
                raise PublicAnalysisValidationError(
                    f"{field_name} must be a non-negative integer"
                )

    def as_items(self) -> tuple[tuple[str, int], ...]:
        """Return counters in a deterministic field order."""
        return (
            ("github_http_request_count", self.github_http_request_count),
            ("athena_query_count", self.athena_query_count),
            ("athena_bytes_scanned", self.athena_bytes_scanned),
            ("bedrock_retrieve_count", self.bedrock_retrieve_count),
            ("bedrock_model_call_count", self.bedrock_model_call_count),
            ("bedrock_input_tokens", self.bedrock_input_tokens),
            ("bedrock_output_tokens", self.bedrock_output_tokens),
            ("retry_count", self.retry_count),
            ("throttle_count", self.throttle_count),
        )

    def add(self, other: ProviderResourceUsage) -> ProviderResourceUsage:
        """Add measured counters without introducing inferred utilization."""
        if type(other) is not ProviderResourceUsage:
            raise PublicAnalysisValidationError("provider usage must use the frozen contract")
        return ProviderResourceUsage(
            github_http_request_count=(
                self.github_http_request_count + other.github_http_request_count
            ),
            athena_query_count=self.athena_query_count + other.athena_query_count,
            athena_bytes_scanned=self.athena_bytes_scanned + other.athena_bytes_scanned,
            bedrock_retrieve_count=(
                self.bedrock_retrieve_count + other.bedrock_retrieve_count
            ),
            bedrock_model_call_count=(
                self.bedrock_model_call_count + other.bedrock_model_call_count
            ),
            bedrock_input_tokens=self.bedrock_input_tokens + other.bedrock_input_tokens,
            bedrock_output_tokens=self.bedrock_output_tokens + other.bedrock_output_tokens,
            retry_count=self.retry_count + other.retry_count,
            throttle_count=self.throttle_count + other.throttle_count,
        )


@dataclass(frozen=True, slots=True)
class RepresentativeStageMeasurement:
    """One stage observation from a concrete non-public representative run."""

    stage: RepresentativeWorkloadStage
    duration_ms: int
    usage: ProviderResourceUsage

    def __post_init__(self) -> None:
        """Validate stage identity, duration, and exact usage contract."""
        if type(self.stage) is not RepresentativeWorkloadStage:
            raise PublicAnalysisValidationError("stage must use RepresentativeWorkloadStage")
        if type(self.duration_ms) is not int or self.duration_ms < 0:
            raise PublicAnalysisValidationError("duration_ms must be a non-negative integer")
        if type(self.usage) is not ProviderResourceUsage:
            raise PublicAnalysisValidationError("stage usage must use ProviderResourceUsage")


@dataclass(frozen=True, slots=True)
class RepresentativeWorkloadMeasurement:
    """Complete measured observation for one representative workload execution."""

    run_id: str
    workload_id: str
    stage_measurements: tuple[RepresentativeStageMeasurement, ...]
    end_to_end_duration_ms: int
    serialized_result_bytes: int
    provider_totals: ProviderResourceUsage

    def __post_init__(self) -> None:
        """Require complete ordered stages and exact measured aggregate counters."""
        if type(self.run_id) is not str or not self.run_id.strip():
            raise PublicAnalysisValidationError("run_id must be a non-empty string")
        if self.workload_id != REPRESENTATIVE_PUBLIC_ANALYSIS_WORKLOAD_ID:
            raise PublicAnalysisValidationError("workload_id must use public-analysis-workload:v1")
        if tuple(item.stage for item in self.stage_measurements) != (
            REPRESENTATIVE_WORKLOAD_STAGE_ORDER
        ):
            raise PublicAnalysisValidationError(
                "representative measurement requires the exact ordered stage set"
            )
        if type(self.end_to_end_duration_ms) is not int or self.end_to_end_duration_ms < 0:
            raise PublicAnalysisValidationError(
                "end_to_end_duration_ms must be a non-negative integer"
            )
        stage_total = sum(item.duration_ms for item in self.stage_measurements)
        if stage_total > self.end_to_end_duration_ms:
            raise PublicAnalysisValidationError(
                "stage durations cannot exceed the measured end-to-end duration"
            )
        if type(self.serialized_result_bytes) is not int or self.serialized_result_bytes < 1:
            raise PublicAnalysisValidationError(
                "serialized_result_bytes must be a positive integer"
            )
        if type(self.provider_totals) is not ProviderResourceUsage:
            raise PublicAnalysisValidationError(
                "provider_totals must use ProviderResourceUsage"
            )
        if self.provider_totals != sum_provider_usage(self.stage_measurements):
            raise PublicAnalysisValidationError(
                "provider_totals must equal the exact sum of stage measurements"
            )


def sum_provider_usage(
    stages: tuple[RepresentativeStageMeasurement, ...],
) -> ProviderResourceUsage:
    """Sum only observed stage counters into one whole-run measurement."""
    total = ProviderResourceUsage()
    for stage in stages:
        if type(stage) is not RepresentativeStageMeasurement:
            raise PublicAnalysisValidationError(
                "stage measurements must use RepresentativeStageMeasurement"
            )
        total = total.add(stage.usage)
    return total
