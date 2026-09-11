"""Execute and admit exactly one human-operated Gate 19.2 live measurement run."""

from __future__ import annotations

import json
from dataclasses import dataclass
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
        """Freeze repository and model identity before any provider workload can execute."""
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
