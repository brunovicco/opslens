"""Execute and admit exactly one human-operated Gate 19.2 live measurement run."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from opslens.knowledge_retrieval.application.bedrock_synthesis import BEDROCK_SYNTHESIS_MODEL_ID
from opslens.public_analysis.application.representative_live_measurement_artifact import (
    RepresentativeLiveMeasurementArtifact,
    admit_serialized_representative_live_measurement_artifact,
    build_representative_live_measurement_artifact,
)
from opslens.public_analysis.application.representative_workload_execution import (
    RepresentativeWorkloadDependencies,
    RepresentativeWorkloadExecution,
    execute_representative_workload,
)

FROZEN_REPRESENTATIVE_REPOSITORY_URL = "https://github.com/openedx/mockprock"
FROZEN_REPRESENTATIVE_REPOSITORY_COMMIT = "18c954d8604df4740c829ba17fa2f3640b92b900"
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.ASCII)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.ASCII)


class RepresentativeLiveMeasurementRunError(ValueError):
    """Reject live-run metadata that drifts from the frozen representative experiment."""


class RepresentativeWorkloadExecutor(Protocol):
    """Exact execution capability injected for deterministic offline tests."""

    def __call__(
        self,
        *,
        run_id: str,
        raw_body: bytes,
        dependencies: RepresentativeWorkloadDependencies,
    ) -> RepresentativeWorkloadExecution:
        """Execute exactly one already-composed representative workload."""
        ...


def _normalized_text(value: object, *, field: str, maximum: int) -> str:
    """Require one bounded normalized non-empty identifier before provider execution."""
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > maximum
    ):
        raise RepresentativeLiveMeasurementRunError(
            f"{field} must be one normalized non-empty string of at most {maximum} characters"
        )
    return value


def _canonical_utc_timestamp(value: object) -> str:
    """Require canonical second-resolution UTC metadata before provider execution."""
    text = _normalized_text(value, field="run_timestamp_utc", maximum=32)
    if not text.endswith("Z"):
        raise RepresentativeLiveMeasurementRunError(
            "run_timestamp_utc must use explicit UTC Z notation"
        )
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise RepresentativeLiveMeasurementRunError(
            "run_timestamp_utc must be valid RFC3339 UTC"
        ) from exc
    if parsed.tzinfo != UTC or parsed.microsecond != 0:
        raise RepresentativeLiveMeasurementRunError(
            "run_timestamp_utc must use UTC with second precision"
        )
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != text:
        raise RepresentativeLiveMeasurementRunError(
            "run_timestamp_utc must use canonical YYYY-MM-DDTHH:MM:SSZ form"
        )
    return text


def _validated_source_evidence(
    value: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, str], ...]:
    """Require sorted unique named source hashes before the measured workload starts."""
    if type(value) is not tuple or not value:
        raise RepresentativeLiveMeasurementRunError(
            "source_evidence must contain at least one named hash"
        )
    admitted: list[tuple[str, str]] = []
    for item in value:
        if type(item) is not tuple or len(item) != 2:
            raise RepresentativeLiveMeasurementRunError(
                "source_evidence entries must be (name, sha256) tuples"
            )
        name = _normalized_text(item[0], field="source_evidence.name", maximum=128)
        digest = _normalized_text(
            item[1],
            field=f"source_evidence[{name}]",
            maximum=64,
        )
        if _SHA256_RE.fullmatch(digest) is None:
            raise RepresentativeLiveMeasurementRunError(
                f"source_evidence[{name}] must be one lowercase SHA-256 digest"
            )
        admitted.append((name, digest))
    names = tuple(name for name, _digest in admitted)
    if len(set(names)) != len(names):
        raise RepresentativeLiveMeasurementRunError(
            "source_evidence names must be unique"
        )
    canonical = tuple(sorted(admitted))
    if canonical != value:
        raise RepresentativeLiveMeasurementRunError(
            "source_evidence must be sorted by name"
        )
    return canonical


@dataclass(frozen=True, slots=True)
class RepresentativeLiveRunMetadata:
    """Explicit immutable coordinates required to bind one admitted live artifact."""

    run_id: str
    opslens_commit_sha: str
    run_timestamp_utc: str
    repository_url: str
    requested_ref: str
    repository_commit_sha: str
    source_evidence: tuple[tuple[str, str], ...]
    bedrock_knowledge_base_id: str
    model_id: str

    def __post_init__(self) -> None:
        """Freeze all artifact identity before any provider workload can execute."""
        object.__setattr__(
            self,
            "run_id",
            _normalized_text(self.run_id, field="run_id", maximum=256),
        )
        opslens_sha = _normalized_text(
            self.opslens_commit_sha,
            field="opslens_commit_sha",
            maximum=40,
        )
        if _GIT_SHA_RE.fullmatch(opslens_sha) is None:
            raise RepresentativeLiveMeasurementRunError(
                "opslens_commit_sha must be one lowercase full Git commit SHA"
            )
        object.__setattr__(self, "opslens_commit_sha", opslens_sha)
        object.__setattr__(
            self,
            "run_timestamp_utc",
            _canonical_utc_timestamp(self.run_timestamp_utc),
        )
        if self.repository_url != FROZEN_REPRESENTATIVE_REPOSITORY_URL:
            raise RepresentativeLiveMeasurementRunError(
                "repository_url must equal the frozen Gate 19.2 representative repository"
            )
        if self.requested_ref != FROZEN_REPRESENTATIVE_REPOSITORY_COMMIT:
            raise RepresentativeLiveMeasurementRunError(
                "requested_ref must equal the frozen exact representative commit"
            )
        if self.repository_commit_sha != FROZEN_REPRESENTATIVE_REPOSITORY_COMMIT:
            raise RepresentativeLiveMeasurementRunError(
                "repository_commit_sha must equal the frozen exact representative commit"
            )
        if self.requested_ref != self.repository_commit_sha:
            raise RepresentativeLiveMeasurementRunError(
                "requested_ref and repository_commit_sha must identify the same exact commit"
            )
        object.__setattr__(
            self,
            "source_evidence",
            _validated_source_evidence(self.source_evidence),
        )
        object.__setattr__(
            self,
            "bedrock_knowledge_base_id",
            _normalized_text(
                self.bedrock_knowledge_base_id,
                field="bedrock_knowledge_base_id",
                maximum=128,
            ),
        )
        if self.model_id != BEDROCK_SYNTHESIS_MODEL_ID:
            raise RepresentativeLiveMeasurementRunError(
                "model_id must equal the retained bounded hybrid synthesis model"
            )


@dataclass(frozen=True, slots=True)
class RepresentativeLiveMeasurementRun:
    """One exact workload execution paired with its byte-admitted immutable artifact."""

    execution: RepresentativeWorkloadExecution
    artifact: RepresentativeLiveMeasurementArtifact
    serialized_artifact: bytes

    def __post_init__(self) -> None:
        """Require exact typed execution/artifact and canonical serialized artifact bytes."""
        if type(self.execution) is not RepresentativeWorkloadExecution:
            raise TypeError("execution must be RepresentativeWorkloadExecution")
        if type(self.artifact) is not RepresentativeLiveMeasurementArtifact:
            raise TypeError("artifact must be RepresentativeLiveMeasurementArtifact")
        if type(self.serialized_artifact) is not bytes:
            raise TypeError("serialized_artifact must be bytes")
        admit_serialized_representative_live_measurement_artifact(
            self.serialized_artifact,
            expected=self.artifact,
        )


def build_frozen_representative_request_body(metadata: RepresentativeLiveRunMetadata) -> bytes:
    """Build the exact bounded public-request shape for the frozen immutable commit."""
    if type(metadata) is not RepresentativeLiveRunMetadata:
        raise TypeError("metadata must be RepresentativeLiveRunMetadata")
    return json.dumps(
        {
            "repository_url": metadata.repository_url,
            "requested_ref": metadata.requested_ref,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def execute_representative_live_measurement(
    *,
    metadata: RepresentativeLiveRunMetadata,
    dependencies: RepresentativeWorkloadDependencies,
    executor: RepresentativeWorkloadExecutor = execute_representative_workload,
) -> RepresentativeLiveMeasurementRun:
    """Execute once, build bounded evidence, and byte-admit it before persistence."""
    if type(metadata) is not RepresentativeLiveRunMetadata:
        raise TypeError("metadata must be RepresentativeLiveRunMetadata")
    if type(dependencies) is not RepresentativeWorkloadDependencies:
        raise TypeError("dependencies must be RepresentativeWorkloadDependencies")

    execution = executor(
        run_id=metadata.run_id,
        raw_body=build_frozen_representative_request_body(metadata),
        dependencies=dependencies,
    )
    if type(execution) is not RepresentativeWorkloadExecution:
        raise TypeError("executor must return RepresentativeWorkloadExecution")

    artifact = build_representative_live_measurement_artifact(
        execution=execution,
        opslens_commit_sha=metadata.opslens_commit_sha,
        run_timestamp_utc=metadata.run_timestamp_utc,
        repository_url=metadata.repository_url,
        repository_commit_sha=metadata.repository_commit_sha,
        source_evidence=metadata.source_evidence,
        bedrock_knowledge_base_id=metadata.bedrock_knowledge_base_id,
        model_id=metadata.model_id,
    )
    serialized = artifact.serialize()
    admit_serialized_representative_live_measurement_artifact(
        serialized,
        expected=artifact,
    )
    return RepresentativeLiveMeasurementRun(
        execution=execution,
        artifact=artifact,
        serialized_artifact=serialized,
    )


__all__ = [
    "FROZEN_REPRESENTATIVE_REPOSITORY_COMMIT",
    "FROZEN_REPRESENTATIVE_REPOSITORY_URL",
    "RepresentativeLiveMeasurementRun",
    "RepresentativeLiveMeasurementRunError",
    "RepresentativeLiveRunMetadata",
    "RepresentativeWorkloadExecutor",
    "build_frozen_representative_request_body",
    "execute_representative_live_measurement",
]
