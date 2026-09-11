"""Tests for inert measured representative-workload dependency composition."""

from __future__ import annotations

import pytest

from opslens.hybrid_retrieval.adapters.bedrock_synthesis import (
    BedrockHybridSynthesisExecution,
)
from opslens.hybrid_retrieval.domain.synthesis import HybridSynthesisRequest
from opslens.knowledge_retrieval.application.bedrock_retrieval import BedrockRetrieveResult
from opslens.knowledge_retrieval.domain import RetrievalRequest
from opslens.public_analysis.adapters.representative_measured_workload import (
    RepresentativeMeasuredWorkloadComposition,
    build_representative_measured_workload_composition,
)
from opslens.public_analysis.application.representative_preloaded_threat_evidence import (
    PreloadedRepresentativeThreatEvidenceLoader,
    RepresentativePreloadedThreatEvidenceError,
)
from opslens.public_analysis.application.representative_repository_analysis import (
    RepresentativeRepositoryThreatEvidence,
)
from opslens.public_analysis.application.representative_workload_execution import (
    REPRESENTATIVE_DEFAULT_PROVIDER_COVERAGE,
    RepresentativeWorkloadDependencies,
)
from opslens.public_analysis.domain import ProviderResourceUsage
from opslens.repository_intelligence.adapters.github_http import GitHubHttpsConnection


class FakeClock:
    """Provide an inert valid measurement clock capability."""

    def monotonic_ns(self) -> int:
        """Return a deterministic non-negative reading."""
        return 0


class NoIoConnectionFactory:
    """Fail if composition accidentally performs a physical GitHub connection."""

    def __init__(self) -> None:
        """Initialize the observed physical-connection count."""
        self.call_count = 0

    def __call__(self, host: str, timeout_seconds: float) -> GitHubHttpsConnection:
        """Reject any network construction during the inert composition phase."""
        del host, timeout_seconds
        self.call_count += 1
        raise AssertionError("composition must not construct a GitHub HTTPS connection")


def _semantic_retriever(request: RetrievalRequest) -> BedrockRetrieveResult:
    """Reject provider execution if composition invokes the injected retriever."""
    del request
    raise AssertionError("composition must not invoke Bedrock Retrieve")


def _synthesizer(request: HybridSynthesisRequest) -> BedrockHybridSynthesisExecution:
    """Reject provider execution if composition invokes the injected synthesizer."""
    del request
    raise AssertionError("composition must not invoke Bedrock synthesis")


def _typed_threat_evidence() -> RepresentativeRepositoryThreatEvidence:
    """Create an inert exact-type sentinel because composition does not read its fields."""
    return object.__new__(RepresentativeRepositoryThreatEvidence)


def test_composes_measured_dependencies_without_provider_io() -> None:
    """Wire exact retained boundaries while keeping construction entirely inert."""
    connection_factory = NoIoConnectionFactory()
    clock = FakeClock()
    evidence = _typed_threat_evidence()

    composition = build_representative_measured_workload_composition(
        github_connection_factory=connection_factory,
        threat_evidence=evidence,
        expected_repository_url="https://github.com/openedx/mockprock",
        expected_commit_sha="18c954d8604df4740c829ba17fa2f3640b92b900",
        semantic_retriever=_semantic_retriever,
        synthesizer=_synthesizer,
        clock=clock,
    )

    assert type(composition) is RepresentativeMeasuredWorkloadComposition
    assert type(composition.dependencies) is RepresentativeWorkloadDependencies
    assert connection_factory.call_count == 0
    assert composition.github_measurement.snapshot() == ProviderResourceUsage()
    assert composition.dependencies.repository_usage_snapshot() == ProviderResourceUsage()
    assert composition.dependencies.semantic_retriever is _semantic_retriever
    assert composition.dependencies.synthesizer is _synthesizer
    assert composition.dependencies.clock is clock
    assert composition.dependencies.provider_coverage == REPRESENTATIVE_DEFAULT_PROVIDER_COVERAGE
    assert type(composition.dependencies.threat_evidence_loader) is (
        PreloadedRepresentativeThreatEvidenceLoader
    )


def test_invalid_repository_anchor_fails_before_provider_io() -> None:
    """Reject preload identity drift without constructing any physical connection."""
    connection_factory = NoIoConnectionFactory()

    with pytest.raises(RepresentativePreloadedThreatEvidenceError):
        build_representative_measured_workload_composition(
            github_connection_factory=connection_factory,
            threat_evidence=_typed_threat_evidence(),
            expected_repository_url="not-a-canonical-github-url",
            expected_commit_sha="18c954d8604df4740c829ba17fa2f3640b92b900",
            semantic_retriever=_semantic_retriever,
            synthesizer=_synthesizer,
            clock=FakeClock(),
        )

    assert connection_factory.call_count == 0
