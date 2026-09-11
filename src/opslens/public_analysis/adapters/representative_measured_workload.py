"""Compose the retained measured representative workload without provider I/O."""

from __future__ import annotations

from dataclasses import dataclass

from opslens.public_analysis.adapters.github_measurement import (
    MeasuredGitHubHttpsConnectionFactory,
)
from opslens.public_analysis.application.representative_measurement import MeasurementClock
from opslens.public_analysis.application.representative_model_reasoning import (
    RepresentativeHybridSynthesizer,
)
from opslens.public_analysis.application.representative_preloaded_threat_evidence import (
    PreloadedRepresentativeThreatEvidenceLoader,
)
from opslens.public_analysis.application.representative_repository_analysis import (
    RepresentativeRepositoryThreatEvidence,
)
from opslens.public_analysis.application.representative_semantic_evidence import (
    RepresentativeSemanticRetriever,
)
from opslens.public_analysis.application.representative_workload_execution import (
    RepresentativeWorkloadDependencies,
)
from opslens.repository_intelligence.adapters.github_http import (
    GitHubHttpsConnectionFactory,
    GitHubRestClientConfig,
    GitHubRestSnapshotSource,
)


@dataclass(frozen=True, slots=True)
class RepresentativeMeasuredWorkloadComposition:
    """Bind exact request-time dependencies to one observable GitHub measurement scope."""

    dependencies: RepresentativeWorkloadDependencies
    github_measurement: MeasuredGitHubHttpsConnectionFactory

    def __post_init__(self) -> None:
        """Reject accidental replacement of the retained measured dependency container."""
        if type(self.dependencies) is not RepresentativeWorkloadDependencies:
            raise TypeError("dependencies must be RepresentativeWorkloadDependencies")
        if type(self.github_measurement) is not MeasuredGitHubHttpsConnectionFactory:
            raise TypeError("github_measurement must be MeasuredGitHubHttpsConnectionFactory")


def build_representative_measured_workload_composition(
    *,
    github_connection_factory: GitHubHttpsConnectionFactory,
    threat_evidence: RepresentativeRepositoryThreatEvidence,
    expected_repository_url: str,
    expected_commit_sha: str,
    semantic_retriever: RepresentativeSemanticRetriever,
    synthesizer: RepresentativeHybridSynthesizer,
    clock: MeasurementClock,
    github_config: GitHubRestClientConfig | None = None,
) -> RepresentativeMeasuredWorkloadComposition:
    """Compose the measured workload while performing zero network/provider calls.

    Pre-measurement threat evidence is released through the retained exact repository
    binding. GitHub request accounting remains attached to the physical HTTPS transport
    boundary. Bedrock-capable callables are injected but are not invoked here.
    """
    measured_github = MeasuredGitHubHttpsConnectionFactory(github_connection_factory)
    repository_source = GitHubRestSnapshotSource(
        config=github_config,
        connection_factory=measured_github,
    )
    threat_loader = PreloadedRepresentativeThreatEvidenceLoader(
        evidence=threat_evidence,
        expected_repository_url=expected_repository_url,
        expected_commit_sha=expected_commit_sha,
    )
    dependencies = RepresentativeWorkloadDependencies(
        repository_source=repository_source,
        repository_usage_snapshot=measured_github.snapshot,
        threat_evidence_loader=threat_loader,
        semantic_retriever=semantic_retriever,
        synthesizer=synthesizer,
        clock=clock,
    )
    return RepresentativeMeasuredWorkloadComposition(
        dependencies=dependencies,
        github_measurement=measured_github,
    )


__all__ = [
    "RepresentativeMeasuredWorkloadComposition",
    "build_representative_measured_workload_composition",
]
