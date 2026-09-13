"""Admit bounded evidence for one successful Gate 19.2 representative live run."""

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Final, cast

from opslens.public_analysis.application.representative_workload_execution import (
    RepresentativeWorkloadExecution,
)
from opslens.public_analysis.domain import (
    PROVIDER_RESOURCE_METRICS,
    MeasurementClassification,
    RepresentativeWorkloadStage,
)

LIVE_MEASUREMENT_ARTIFACT_TYPE: Final = (
    "phase-19-gate-19-2-live-measurement:v1"
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.ASCII)
_MAX_ID_LENGTH = 512


class RepresentativeLiveMeasurementArtifactError(ValueError):
    """Reject incomplete, contradictory, or non-canonical live measurement evidence."""


def _bounded_text(value: object, *, field: str, maximum: int = _MAX_ID_LENGTH) -> str:
    """Require one normalized bounded non-empty string."""
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > maximum
    ):
        raise RepresentativeLiveMeasurementArtifactError(
            f"{field} must be one normalized non-empty string of at most {maximum} characters"
        )
    return value


def _sha256_hex(value: object, *, field: str) -> str:
    """Require one lowercase SHA-256 digest."""
    text = _bounded_text(value, field=field, maximum=64)
    if _SHA256_RE.fullmatch(text) is None:
        raise RepresentativeLiveMeasurementArtifactError(
            f"{field} must be one lowercase SHA-256 digest"
        )
    return text


def _git_sha(value: object, *, field: str) -> str:
    """Require one lowercase full Git commit SHA."""
    text = _bounded_text(value, field=field, maximum=40)
    if _GIT_SHA_RE.fullmatch(text) is None:
        raise RepresentativeLiveMeasurementArtifactError(
            f"{field} must be one lowercase 40-hex Git commit SHA"
        )
    return text


def _utc_timestamp(value: object) -> str:
    """Require canonical second-resolution RFC3339 UTC text with a trailing Z."""
    text = _bounded_text(value, field="run_timestamp_utc", maximum=32)
    if not text.endswith("Z"):
        raise RepresentativeLiveMeasurementArtifactError(
            "run_timestamp_utc must use explicit UTC Z notation"
        )
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise RepresentativeLiveMeasurementArtifactError(
            "run_timestamp_utc must be valid RFC3339 UTC"
        ) from exc
    if parsed.tzinfo != UTC or parsed.microsecond != 0:
        raise RepresentativeLiveMeasurementArtifactError(
            "run_timestamp_utc must use UTC with second precision"
        )
    canonical = parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
    if canonical != text:
        raise RepresentativeLiveMeasurementArtifactError(
            "run_timestamp_utc must use canonical YYYY-MM-DDTHH:MM:SSZ form"
        )
    return text


def _source_evidence(
    value: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, str], ...]:
    """Require sorted unique named SHA-256 evidence identifiers."""
    if type(value) is not tuple or not value:
        raise RepresentativeLiveMeasurementArtifactError(
            "source_evidence must contain at least one named hash"
        )
    admitted: list[tuple[str, str]] = []
    for item in value:
        if type(item) is not tuple or len(item) != 2:
            raise RepresentativeLiveMeasurementArtifactError(
                "source_evidence entries must be (name, sha256) tuples"
            )
        name = _bounded_text(item[0], field="source_evidence.name", maximum=128)
        digest = _sha256_hex(item[1], field=f"source_evidence[{name}]")
        admitted.append((name, digest))
    names = tuple(name for name, _digest in admitted)
    if len(set(names)) != len(names):
        raise RepresentativeLiveMeasurementArtifactError(
            "source_evidence names must be unique"
        )
    canonical = tuple(sorted(admitted))
    if canonical != value:
        raise RepresentativeLiveMeasurementArtifactError(
            "source_evidence must be sorted by name"
        )
    return canonical


@dataclass(frozen=True, slots=True)
class RepresentativeLiveMeasurementArtifact:
    """Content-free immutable evidence for one successful representative live execution."""

    opslens_commit_sha: str
    run_timestamp_utc: str
    repository_url: str
    repository_commit_sha: str
    source_evidence: tuple[tuple[str, str], ...]
    bedrock_knowledge_base_id: str
    model_id: str
    run_id: str
    workload_id: str
    end_to_end_duration_ms: int
    stage_durations_ms: tuple[tuple[str, int], ...]
    provider_totals: tuple[tuple[str, int], ...]
    provider_classifications: tuple[tuple[str, str], ...]
    serialized_result_bytes: int
    final_result_sha256: str
    public_endpoint_count: int = 0
    new_aws_resource_count: int = 0
    new_iam_role_policy_count: int = 0
    third_party_repository_code_execution_count: int = 0
    schema_version: int = 1
    artifact_type: str = LIVE_MEASUREMENT_ARTIFACT_TYPE
    outcome: str = "SUCCESS"

    def __post_init__(self) -> None:
        """Require complete bounded evidence and explicit zero-mutation invariants."""
        if self.schema_version != 1 or self.artifact_type != LIVE_MEASUREMENT_ARTIFACT_TYPE:
            raise RepresentativeLiveMeasurementArtifactError(
                "live measurement artifact identity must use the frozen v1 contract"
            )
        if self.outcome != "SUCCESS":
            raise RepresentativeLiveMeasurementArtifactError(
                "this artifact contract admits successful live measurements only"
            )
        object.__setattr__(
            self,
            "opslens_commit_sha",
            _git_sha(self.opslens_commit_sha, field="opslens_commit_sha"),
        )
        object.__setattr__(self, "run_timestamp_utc", _utc_timestamp(self.run_timestamp_utc))
        repository_url = _bounded_text(
            self.repository_url, field="repository_url", maximum=512
        )
        if not repository_url.startswith("https://github.com/"):
            raise RepresentativeLiveMeasurementArtifactError(
                "repository_url must be one canonical GitHub HTTPS URL"
            )
        object.__setattr__(self, "repository_url", repository_url)
        object.__setattr__(
            self,
            "repository_commit_sha",
            _git_sha(self.repository_commit_sha, field="repository_commit_sha"),
        )
        object.__setattr__(self, "source_evidence", _source_evidence(self.source_evidence))
        object.__setattr__(
            self,
            "bedrock_knowledge_base_id",
            _bounded_text(
                self.bedrock_knowledge_base_id,
                field="bedrock_knowledge_base_id",
                maximum=128,
            ),
        )
        object.__setattr__(
            self,
            "model_id",
            _bounded_text(self.model_id, field="model_id", maximum=512),
        )
        object.__setattr__(
            self,
            "run_id",
            _bounded_text(self.run_id, field="run_id", maximum=256),
        )
        object.__setattr__(
            self,
            "workload_id",
            _bounded_text(self.workload_id, field="workload_id", maximum=128),
        )
        for field_name, value in (
            ("end_to_end_duration_ms", self.end_to_end_duration_ms),
            ("serialized_result_bytes", self.serialized_result_bytes),
        ):
            if type(value) is not int or value < 1:
                raise RepresentativeLiveMeasurementArtifactError(
                    f"{field_name} must be a positive integer"
                )
        object.__setattr__(
            self,
            "final_result_sha256",
            _sha256_hex(self.final_result_sha256, field="final_result_sha256"),
        )
        expected_stage_names = tuple(stage.value for stage in RepresentativeWorkloadStage)
        if tuple(name for name, _value in self.stage_durations_ms) != expected_stage_names:
            raise RepresentativeLiveMeasurementArtifactError(
                "stage_durations_ms must preserve the exact representative stage order"
            )
        if any(type(value) is not int or value < 0 for _name, value in self.stage_durations_ms):
            raise RepresentativeLiveMeasurementArtifactError(
                "stage durations must be non-negative integers"
            )
        expected_metrics = tuple(metric.value for metric in PROVIDER_RESOURCE_METRICS)
        if tuple(name for name, _value in self.provider_totals) != expected_metrics:
            raise RepresentativeLiveMeasurementArtifactError(
                "provider_totals must preserve the frozen provider metric order"
            )
        if any(type(value) is not int or value < 0 for _name, value in self.provider_totals):
            raise RepresentativeLiveMeasurementArtifactError(
                "provider totals must be non-negative integers"
            )
        if tuple(name for name, _value in self.provider_classifications) != expected_metrics:
            raise RepresentativeLiveMeasurementArtifactError(
                "provider_classifications must preserve the frozen provider metric order"
            )
        valid_classifications = frozenset(item.value for item in MeasurementClassification)
        if any(
            classification not in valid_classifications
            for _name, classification in self.provider_classifications
        ):
            raise RepresentativeLiveMeasurementArtifactError(
                "provider_classifications contain an unsupported value"
            )
        for field_name, value in (
            ("public_endpoint_count", self.public_endpoint_count),
            ("new_aws_resource_count", self.new_aws_resource_count),
            ("new_iam_role_policy_count", self.new_iam_role_policy_count),
            (
                "third_party_repository_code_execution_count",
                self.third_party_repository_code_execution_count,
            ),
        ):
            if type(value) is not int or value != 0:
                raise RepresentativeLiveMeasurementArtifactError(
                    f"{field_name} must remain exactly zero"
                )

    def to_json_dict(self) -> dict[str, object]:
        """Project deterministic JSON-safe evidence without raw provider content."""
        return {
            "artifact_type": self.artifact_type,
            "bedrock_knowledge_base_id": self.bedrock_knowledge_base_id,
            "end_to_end_duration_ms": self.end_to_end_duration_ms,
            "final_result_sha256": self.final_result_sha256,
            "model_id": self.model_id,
            "new_aws_resource_count": self.new_aws_resource_count,
            "new_iam_role_policy_count": self.new_iam_role_policy_count,
            "opslens_commit_sha": self.opslens_commit_sha,
            "outcome": self.outcome,
            "provider_classifications": [
                {"classification": classification, "metric": metric}
                for metric, classification in self.provider_classifications
            ],
            "provider_totals": [
                {"metric": metric, "value": value}
                for metric, value in self.provider_totals
            ],
            "public_endpoint_count": self.public_endpoint_count,
            "repository_commit_sha": self.repository_commit_sha,
            "repository_url": self.repository_url,
            "run_id": self.run_id,
            "run_timestamp_utc": self.run_timestamp_utc,
            "schema_version": self.schema_version,
            "serialized_result_bytes": self.serialized_result_bytes,
            "source_evidence": [
                {"name": name, "sha256": digest}
                for name, digest in self.source_evidence
            ],
            "stage_durations_ms": [
                {"duration_ms": duration_ms, "stage": stage}
                for stage, duration_ms in self.stage_durations_ms
            ],
            "third_party_repository_code_execution_count": (
                self.third_party_repository_code_execution_count
            ),
            "workload_id": self.workload_id,
        }

    def serialize(self) -> bytes:
        """Serialize canonical UTF-8 JSON with a final newline."""
        return (
            json.dumps(
                self.to_json_dict(),
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")


def build_representative_live_measurement_artifact(
    *,
    execution: RepresentativeWorkloadExecution,
    opslens_commit_sha: str,
    run_timestamp_utc: str,
    repository_url: str,
    repository_commit_sha: str,
    source_evidence: tuple[tuple[str, str], ...],
    bedrock_knowledge_base_id: str,
    model_id: str,
) -> RepresentativeLiveMeasurementArtifact:
    """Bind one admitted execution to bounded immutable live-run metadata."""
    if type(execution) is not RepresentativeWorkloadExecution:
        raise TypeError("execution must be RepresentativeWorkloadExecution")
    measurement = execution.measurement
    result_bytes = execution.result.serialize()
    if not result_bytes or len(result_bytes) != measurement.serialized_result_bytes:
        raise RepresentativeLiveMeasurementArtifactError(
            "serialized admitted result contradicts the representative measurement"
        )
    return RepresentativeLiveMeasurementArtifact(
        opslens_commit_sha=opslens_commit_sha,
        run_timestamp_utc=run_timestamp_utc,
        repository_url=repository_url,
        repository_commit_sha=repository_commit_sha,
        source_evidence=source_evidence,
        bedrock_knowledge_base_id=bedrock_knowledge_base_id,
        model_id=model_id,
        run_id=measurement.run_id,
        workload_id=measurement.workload_id,
        end_to_end_duration_ms=measurement.end_to_end_duration_ms,
        stage_durations_ms=tuple(
            (item.stage.value, item.duration_ms)
            for item in measurement.stage_measurements
        ),
        provider_totals=measurement.provider_totals.as_items(),
        provider_classifications=tuple(
            (metric.value, measurement.provider_coverage.classification_for(metric).value)
            for metric in PROVIDER_RESOURCE_METRICS
        ),
        serialized_result_bytes=measurement.serialized_result_bytes,
        final_result_sha256=sha256(result_bytes).hexdigest(),
    )


def admit_serialized_representative_live_measurement_artifact(
    serialized: bytes,
    *,
    expected: RepresentativeLiveMeasurementArtifact,
) -> RepresentativeLiveMeasurementArtifact:
    """Verify one serialized artifact is canonical and exactly matches admitted evidence."""
    if type(serialized) is not bytes or not serialized:
        raise RepresentativeLiveMeasurementArtifactError(
            "serialized live measurement artifact must be non-empty bytes"
        )
    if type(expected) is not RepresentativeLiveMeasurementArtifact:
        raise TypeError("expected must be RepresentativeLiveMeasurementArtifact")
    if serialized != expected.serialize():
        raise RepresentativeLiveMeasurementArtifactError(
            "serialized live measurement artifact does not match admitted evidence"
        )
    try:
        parsed = cast(object, json.loads(serialized.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RepresentativeLiveMeasurementArtifactError(
            "serialized live measurement artifact must be valid UTF-8 JSON"
        ) from exc
    if parsed != expected.to_json_dict():
        raise RepresentativeLiveMeasurementArtifactError(
            "serialized live measurement JSON changed semantic evidence"
        )
    return expected


__all__ = [
    "LIVE_MEASUREMENT_ARTIFACT_TYPE",
    "RepresentativeLiveMeasurementArtifact",
    "RepresentativeLiveMeasurementArtifactError",
    "admit_serialized_representative_live_measurement_artifact",
    "build_representative_live_measurement_artifact",
]
