"""Deterministic measurement contracts for the representative public workload."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256

from opslens.public_analysis.domain.errors import PublicAnalysisValidationError

PUBLIC_ANALYSIS_WORKLOAD_ID = "public-analysis-workload:v1"
PUBLIC_ANALYSIS_WORKLOAD_MEASUREMENT_CONTRACT_VERSION = (
    "public-analysis-workload-measurement:v1"
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)


class PublicAnalysisWorkloadStage(StrEnum):
    """Ordered stages measured by the first representative public workload runner."""

    PUBLIC_HANDOFF = "public_handoff"
    STRUCTURED_EVIDENCE = "structured_evidence"
    SEMANTIC_EVIDENCE = "semantic_evidence"
    EVIDENCE_ASSEMBLY = "evidence_assembly"
    SYNTHESIS = "synthesis"
    RESULT_ADMISSION = "result_admission"


_EXPECTED_STAGE_ORDER = tuple(PublicAnalysisWorkloadStage)


def _optional_count(value: int | None, *, field: str) -> int | None:
    """Accept non-negative observed counts while preserving not-applicable as null."""
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise PublicAnalysisValidationError(f"{field} must be null or a non-negative integer")
    return value


def _required_count(value: int, *, field: str) -> int:
    """Require one non-negative integer without accepting bool."""
    if type(value) is not int or value < 0:
        raise PublicAnalysisValidationError(f"{field} must be a non-negative integer")
    return value


def _sha256_digest(value: str, *, field: str) -> str:
    """Require one lowercase SHA-256 digest."""
    if type(value) is not str or _SHA256_PATTERN.fullmatch(value) is None:
        raise PublicAnalysisValidationError(f"{field} must be a lowercase SHA-256 digest")
    return value


@dataclass(frozen=True, slots=True)
class PublicAnalysisStageMeasurement:
    """Content-free observations for one measured workload stage."""

    stage: PublicAnalysisWorkloadStage
    duration_ms: int
    github_http_request_count: int | None = None
    athena_query_count: int | None = None
    athena_bytes_scanned: int | None = None
    bedrock_retrieve_call_count: int | None = None
    bedrock_retrieve_latency_ms: int | None = None
    bedrock_model_call_count: int | None = None
    bedrock_input_tokens: int | None = None
    bedrock_output_tokens: int | None = None
    bedrock_model_latency_ms: int | None = None
    retry_count: int | None = None
    throttle_count: int | None = None

    def __post_init__(self) -> None:
        """Reject negative/malformed observations without converting null into zero."""
        if type(self.stage) is not PublicAnalysisWorkloadStage:
            raise PublicAnalysisValidationError(
                "workload stage measurement requires one recognized stage"
            )
        _required_count(self.duration_ms, field="duration_ms")
        for field_name in (
            "github_http_request_count",
            "athena_query_count",
            "athena_bytes_scanned",
            "bedrock_retrieve_call_count",
            "bedrock_retrieve_latency_ms",
            "bedrock_model_call_count",
            "bedrock_input_tokens",
            "bedrock_output_tokens",
            "bedrock_model_latency_ms",
            "retry_count",
            "throttle_count",
        ):
            _optional_count(getattr(self, field_name), field=field_name)

    def to_payload(self) -> dict[str, object]:
        """Return one canonical JSON-ready stage observation without source/model content."""
        return {
            "athena_bytes_scanned": self.athena_bytes_scanned,
            "athena_query_count": self.athena_query_count,
            "bedrock_input_tokens": self.bedrock_input_tokens,
            "bedrock_model_call_count": self.bedrock_model_call_count,
            "bedrock_model_latency_ms": self.bedrock_model_latency_ms,
            "bedrock_output_tokens": self.bedrock_output_tokens,
            "bedrock_retrieve_call_count": self.bedrock_retrieve_call_count,
            "bedrock_retrieve_latency_ms": self.bedrock_retrieve_latency_ms,
            "duration_ms": self.duration_ms,
            "github_http_request_count": self.github_http_request_count,
            "retry_count": self.retry_count,
            "stage": self.stage.value,
            "throttle_count": self.throttle_count,
        }


@dataclass(frozen=True, slots=True)
class PublicAnalysisWorkloadMeasurement:
    """Bind exact stage observations to one admitted public-product result."""

    result_id: str
    result_sha256: str
    result_size_bytes: int
    end_to_end_duration_ms: int
    stages: tuple[PublicAnalysisStageMeasurement, ...]
    workload_id: str = PUBLIC_ANALYSIS_WORKLOAD_ID

    def __post_init__(self) -> None:
        """Require exact stage coverage and preserve measured values without inference."""
        if self.workload_id != PUBLIC_ANALYSIS_WORKLOAD_ID:
            raise PublicAnalysisValidationError(
                "workload_id must match public-analysis-workload:v1"
            )
        if type(self.result_id) is not str or not self.result_id.strip():
            raise PublicAnalysisValidationError("result_id must be one non-empty string")
        _sha256_digest(self.result_sha256, field="result_sha256")
        _required_count(self.result_size_bytes, field="result_size_bytes")
        _required_count(self.end_to_end_duration_ms, field="end_to_end_duration_ms")
        if type(self.stages) is not tuple:
            raise PublicAnalysisValidationError("stages must be one tuple")
        if any(type(stage) is not PublicAnalysisStageMeasurement for stage in self.stages):
            raise PublicAnalysisValidationError(
                "stages must contain only PublicAnalysisStageMeasurement values"
            )
        if tuple(stage.stage for stage in self.stages) != _EXPECTED_STAGE_ORDER:
            raise PublicAnalysisValidationError(
                "workload measurement requires the exact representative stage order"
            )
        measured_stage_duration = sum(stage.duration_ms for stage in self.stages)
        if self.end_to_end_duration_ms < measured_stage_duration:
            raise PublicAnalysisValidationError(
                "end-to-end duration cannot be lower than summed measured stage duration"
            )

    @property
    def canonical_json(self) -> bytes:
        """Serialize the exact content-free workload observation."""
        return json.dumps(
            {
                "contract_version": PUBLIC_ANALYSIS_WORKLOAD_MEASUREMENT_CONTRACT_VERSION,
                "end_to_end_duration_ms": self.end_to_end_duration_ms,
                "result_id": self.result_id,
                "result_sha256": self.result_sha256,
                "result_size_bytes": self.result_size_bytes,
                "stages": [stage.to_payload() for stage in self.stages],
                "workload_id": self.workload_id,
            },
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

    @property
    def measurement_sha256(self) -> str:
        """Return the exact content address for the observed workload measurement."""
        return sha256(self.canonical_json).hexdigest()

    @property
    def measurement_id(self) -> str:
        """Return one versioned content-addressed measurement identifier."""
        return (
            f"{PUBLIC_ANALYSIS_WORKLOAD_MEASUREMENT_CONTRACT_VERSION}@sha256:"
            f"{self.measurement_sha256}"
        )


__all__ = [
    "PUBLIC_ANALYSIS_WORKLOAD_ID",
    "PUBLIC_ANALYSIS_WORKLOAD_MEASUREMENT_CONTRACT_VERSION",
    "PublicAnalysisStageMeasurement",
    "PublicAnalysisWorkloadMeasurement",
    "PublicAnalysisWorkloadStage",
]
