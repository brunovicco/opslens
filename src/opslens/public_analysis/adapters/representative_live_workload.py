"""Compose concrete live-provider ports for the human-run Gate 19.2 workload."""

from __future__ import annotations

import time
from dataclasses import dataclass

from opslens.hybrid_retrieval.adapters.bedrock_synthesis import (
    BedrockHybridConverseClient,
    BedrockHybridSynthesizer,
)
from opslens.knowledge_retrieval.adapters.bedrock_retrieval import (
    BedrockAgentRuntimeClient,
    BedrockKnowledgeBaseRetrieveAdapter,
)
from opslens.knowledge_retrieval.application.bedrock_retrieval import (
    BedrockRetrieveResult,
    run_bounded_retrieve,
)
from opslens.knowledge_retrieval.application.retrieval_catalog import CanonicalRetrievalCatalog
from opslens.knowledge_retrieval.domain import RetrievalRequest
from opslens.public_analysis.adapters.representative_measured_workload import (
    RepresentativeMeasuredWorkloadComposition,
    build_representative_measured_workload_composition,
)
from opslens.public_analysis.application.representative_repository_analysis import (
    RepresentativeRepositoryThreatEvidence,
)
from opslens.repository_intelligence.adapters.github_http import (
    GitHubHttpsConnectionFactory,
    GitHubRestClientConfig,
)


class RepresentativeLiveWorkloadConfigError(ValueError):
    """Reject incomplete concrete live-provider coordinates before execution."""


def _bounded_text(value: object, *, field: str, maximum: int) -> str:
    """Require one normalized bounded non-empty provider coordinate."""
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > maximum
    ):
        raise RepresentativeLiveWorkloadConfigError(
            f"{field} must be one normalized non-empty string of at most {maximum} characters"
        )
    return value


@dataclass(frozen=True, slots=True)
class RepresentativeLiveRetrievalConfig:
    """Exact retained Knowledge Base coordinates used by the representative workload."""

    knowledge_base_id: str
    data_source_id: str
    source_bucket: str

    def __post_init__(self) -> None:
        """Validate only the explicit coordinates consumed by bounded Retrieve admission."""
        object.__setattr__(
            self,
            "knowledge_base_id",
            _bounded_text(
                self.knowledge_base_id,
                field="knowledge_base_id",
                maximum=128,
            ),
        )
        object.__setattr__(
            self,
            "data_source_id",
            _bounded_text(self.data_source_id, field="data_source_id", maximum=128),
        )
        object.__setattr__(
            self,
            "source_bucket",
            _bounded_text(self.source_bucket, field="source_bucket", maximum=255),
        )


class SystemMeasurementClock:
    """Expose the local monotonic nanosecond clock through the measurement port."""

    def monotonic_ns(self) -> int:
        """Return a monotonic reading without coupling measurement to wall-clock time."""
        return time.monotonic_ns()


def build_representative_live_workload_composition(
    *,
    github_connection_factory: GitHubHttpsConnectionFactory,
    threat_evidence: RepresentativeRepositoryThreatEvidence,
    expected_repository_url: str,
    expected_commit_sha: str,
    retrieval_client: BedrockAgentRuntimeClient,
    synthesis_client: BedrockHybridConverseClient,
    retrieval_catalog: CanonicalRetrievalCatalog,
    retrieval_config: RepresentativeLiveRetrievalConfig,
    github_config: GitHubRestClientConfig | None = None,
) -> RepresentativeMeasuredWorkloadComposition:
    """Wire retained live adapters without performing any provider operation.

    The returned callables execute providers only when the human operator later calls
    ``execute_representative_workload``. Threat-source S3 reads are intentionally absent
    from this composition because their materialization occurs before measurement.
    """
    if type(threat_evidence) is not RepresentativeRepositoryThreatEvidence:
        raise TypeError("threat_evidence must be RepresentativeRepositoryThreatEvidence")
    if type(retrieval_catalog) is not CanonicalRetrievalCatalog:
        raise TypeError("retrieval_catalog must be CanonicalRetrievalCatalog")
    if type(retrieval_config) is not RepresentativeLiveRetrievalConfig:
        raise TypeError("retrieval_config must be RepresentativeLiveRetrievalConfig")

    retrieval_adapter = BedrockKnowledgeBaseRetrieveAdapter(retrieval_client)
    hybrid_synthesizer = BedrockHybridSynthesizer(synthesis_client)

    def semantic_retriever(request: RetrievalRequest) -> BedrockRetrieveResult:
        """Execute one retained bounded direct Retrieve request when the workload reaches it."""
        return run_bounded_retrieve(
            retrieval_adapter,
            request=request,
            catalog=retrieval_catalog,
            knowledge_base_id=retrieval_config.knowledge_base_id,
            expected_source_bucket=retrieval_config.source_bucket,
            expected_data_source_id=retrieval_config.data_source_id,
        )

    return build_representative_measured_workload_composition(
        github_connection_factory=github_connection_factory,
        threat_evidence=threat_evidence,
        expected_repository_url=expected_repository_url,
        expected_commit_sha=expected_commit_sha,
        semantic_retriever=semantic_retriever,
        synthesizer=hybrid_synthesizer.synthesize,
        clock=SystemMeasurementClock(),
        github_config=github_config,
    )


__all__ = [
    "RepresentativeLiveRetrievalConfig",
    "RepresentativeLiveWorkloadConfigError",
    "SystemMeasurementClock",
    "build_representative_live_workload_composition",
]
