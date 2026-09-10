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


class MeasurementClassification(StrEnum):
    """Evidence semantics for one whole-workload provider metric."""

    MEASURED = "MEASURED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNMEASURED = "UNMEASURED"


class ProviderResourceMetric(StrEnum):
    """Exact provider/resource dimensions retained by Gate 19.2."""

    GITHUB_HTTP_REQUEST_COUNT = "github_http_request_count"
    ATHENA_QUERY_COUNT = "athena_query_count"
    ATHENA_BYTES_SCANNED = "athena_bytes_scanned"
    BEDROCK_RETRIEVE_COUNT = "bedrock_retrieve_count"
    BEDROCK_RETRIEVE_CLIENT_ELAPSED_MS = "bedrock_retrieve_client_elapsed_ms"
    BEDROCK_MODEL_CALL_COUNT = "bedrock_model_call_count"
    BEDROCK_INPUT_TOKENS = "bedrock_input_tokens"
    BEDROCK_OUTPUT_TOKENS = "bedrock_output_tokens"
    BEDROCK_MODEL_CLIENT_ELAPSED_MS = "bedrock_model_client_elapsed_ms"
    BEDROCK_MODEL_LATENCY_MS = "bedrock_model_latency_ms"
    RETRY_COUNT = "retry_count"
    THROTTLE_COUNT = "throttle_count"


PROVIDER_RESOURCE_METRICS = tuple(ProviderResourceMetric)


@dataclass(frozen=True, slots=True)
class ProviderMeasurementCoverage:
    """Classify every provider metric so an absent measurement never means zero."""

    classifications: tuple[
        tuple[ProviderResourceMetric, MeasurementClassification], ...
    ]

    def __post_init__(self) -> None:
        """Require one classification for every provider metric in deterministic order."""
        observed = tuple(metric for metric, _classification in self.classifications)
        if observed != PROVIDER_RESOURCE_METRICS:
            raise PublicAnalysisValidationError(
                "provider measurement coverage must classify every metric exactly once"
            )
        if any(
            type(classification) is not MeasurementClassification
            for _metric, classification in self.classifications
        ):
            raise PublicAnalysisValidationError(
                "provider measurement coverage must use MeasurementClassification"
            )

    def classification_for(
        self,
        metric: ProviderResourceMetric,
    ) -> MeasurementClassification:
        """Return the explicit evidence classification for one provider metric."""
        if type(metric) is not ProviderResourceMetric:
            raise PublicAnalysisValidationError("metric must use ProviderResourceMetric")
        for candidate, classification in self.classifications:
            if candidate is metric:
                return classification
        raise AssertionError("validated provider coverage omitted a metric")


def provider_measurement_coverage(
    *,
    measured: tuple[ProviderResourceMetric, ...] = (),
    not_applicable: tuple[ProviderResourceMetric, ...] = (),
) -> ProviderMeasurementCoverage:
    """Build explicit coverage; omitted metrics remain UNMEASURED, never implicit zero."""
    if len(set(measured)) != len(measured) or len(set(not_applicable)) != len(not_applicable):
        raise PublicAnalysisValidationError("provider metric classifications cannot repeat")
    if set(measured) & set(not_applicable):
        raise PublicAnalysisValidationError(
            "provider metric cannot be both MEASURED and NOT_APPLICABLE"
        )
    if any(type(metric) is not ProviderResourceMetric for metric in (*measured, *not_applicable)):
        raise PublicAnalysisValidationError("provider coverage contains an unknown metric")

    measured_set = frozenset(measured)
    not_applicable_set = frozenset(not_applicable)
    classifications = tuple(
        (
            metric,
            MeasurementClassification.MEASURED
            if metric in measured_set
            else (
                MeasurementClassification.NOT_APPLICABLE
                if metric in not_applicable_set
                else MeasurementClassification.UNMEASURED
            ),
        )
        for metric in PROVIDER_RESOURCE_METRICS
    )
    return ProviderMeasurementCoverage(classifications=classifications)


@dataclass(frozen=True, slots=True)
class ProviderResourceUsage:
    """Numeric provider/resource counters paired with separate evidence classifications."""

    github_http_request_count: int = 0
    athena_query_count: int = 0
    athena_bytes_scanned: int = 0
    bedrock_retrieve_count: int = 0
    bedrock_retrieve_client_elapsed_ms: int = 0
    bedrock_model_call_count: int = 0
    bedrock_input_tokens: int = 0
    bedrock_output_tokens: int = 0
    bedrock_model_client_elapsed_ms: int = 0
    bedrock_model_latency_ms: int = 0
    retry_count: int = 0
    throttle_count: int = 0

    def __post_init__(self) -> None:
        """Reject negative or non-integer observed counters."""
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
            (
                "bedrock_retrieve_client_elapsed_ms",
                self.bedrock_retrieve_client_elapsed_ms,
            ),
            ("bedrock_model_call_count", self.bedrock_model_call_count),
            ("bedrock_input_tokens", self.bedrock_input_tokens),
            ("bedrock_output_tokens", self.bedrock_output_tokens),
            (
                "bedrock_model_client_elapsed_ms",
                self.bedrock_model_client_elapsed_ms,
            ),
            ("bedrock_model_latency_ms", self.bedrock_model_latency_ms),
            ("retry_count", self.retry_count),
            ("throttle_count", self.throttle_count),
        )

    def value_for(self, metric: ProviderResourceMetric) -> int:
        """Return one counter through its typed metric identity."""
        if type(metric) is not ProviderResourceMetric:
            raise PublicAnalysisValidationError("metric must use ProviderResourceMetric")
        return {
            ProviderResourceMetric.GITHUB_HTTP_REQUEST_COUNT: self.github_http_request_count,
            ProviderResourceMetric.ATHENA_QUERY_COUNT: self.athena_query_count,
            ProviderResourceMetric.ATHENA_BYTES_SCANNED: self.athena_bytes_scanned,
            ProviderResourceMetric.BEDROCK_RETRIEVE_COUNT: self.bedrock_retrieve_count,
            ProviderResourceMetric.BEDROCK_RETRIEVE_CLIENT_ELAPSED_MS: (
                self.bedrock_retrieve_client_elapsed_ms
            ),
            ProviderResourceMetric.BEDROCK_MODEL_CALL_COUNT: self.bedrock_model_call_count,
            ProviderResourceMetric.BEDROCK_INPUT_TOKENS: self.bedrock_input_tokens,
            ProviderResourceMetric.BEDROCK_OUTPUT_TOKENS: self.bedrock_output_tokens,
            ProviderResourceMetric.BEDROCK_MODEL_CLIENT_ELAPSED_MS: (
                self.bedrock_model_client_elapsed_ms
            ),
            ProviderResourceMetric.BEDROCK_MODEL_LATENCY_MS: self.bedrock_model_latency_ms,
            ProviderResourceMetric.RETRY_COUNT: self.retry_count,
            ProviderResourceMetric.THROTTLE_COUNT: self.throttle_count,
        }[metric]

    def add(self, other: ProviderResourceUsage) -> ProviderResourceUsage:
        """Add numeric counters without inventing their evidence classification."""
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
            bedrock_retrieve_client_elapsed_ms=(
                self.bedrock_retrieve_client_elapsed_ms
                + other.bedrock_retrieve_client_elapsed_ms
            ),
            bedrock_model_call_count=(
                self.bedrock_model_call_count + other.bedrock_model_call_count
            ),
            bedrock_input_tokens=self.bedrock_input_tokens + other.bedrock_input_tokens,
            bedrock_output_tokens=self.bedrock_output_tokens + other.bedrock_output_tokens,
            bedrock_model_client_elapsed_ms=(
                self.bedrock_model_client_elapsed_ms
                + other.bedrock_model_client_elapsed_ms
            ),
            bedrock_model_latency_ms=(
                self.bedrock_model_latency_ms + other.bedrock_model_latency_ms
            ),
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
    """Complete observation whose provider counters carry explicit evidence semantics."""

    run_id: str
    workload_id: str
    stage_measurements: tuple[RepresentativeStageMeasurement, ...]
    end_to_end_duration_ms: int
    serialized_result_bytes: int
    provider_totals: ProviderResourceUsage
    provider_coverage: ProviderMeasurementCoverage

    def __post_init__(self) -> None:
        """Require complete ordered stages, exact totals, and honest metric classification."""
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
        if type(self.provider_coverage) is not ProviderMeasurementCoverage:
            raise PublicAnalysisValidationError(
                "provider_coverage must use ProviderMeasurementCoverage"
            )
        for metric in PROVIDER_RESOURCE_METRICS:
            classification = self.provider_coverage.classification_for(metric)
            value = self.provider_totals.value_for(metric)
            if classification is not MeasurementClassification.MEASURED and value != 0:
                raise PublicAnalysisValidationError(
                    f"{metric.value} cannot carry a non-zero value unless it is MEASURED"
                )


def sum_provider_usage(
    stages: tuple[RepresentativeStageMeasurement, ...],
) -> ProviderResourceUsage:
    """Sum numeric stage counters; classification remains an independent authority."""
    total = ProviderResourceUsage()
    for stage in stages:
        if type(stage) is not RepresentativeStageMeasurement:
            raise PublicAnalysisValidationError(
                "stage measurements must use RepresentativeStageMeasurement"
            )
        total = total.add(stage.usage)
    return total
