"""Tests for inert human-run live-provider composition at Gate 19.2."""

from collections.abc import Mapping

import pytest

from opslens.knowledge_retrieval.application.retrieval_catalog import CanonicalRetrievalCatalog
from opslens.public_analysis.adapters.representative_live_workload import (
    RepresentativeLiveRetrievalConfig,
    RepresentativeLiveWorkloadConfigError,
    SystemMeasurementClock,
    build_representative_live_workload_composition,
)
from opslens.public_analysis.adapters.representative_measured_workload import (
    RepresentativeMeasuredWorkloadComposition,
)
from opslens.public_analysis.application.representative_repository_analysis import (
    RepresentativeRepositoryThreatEvidence,
)
from opslens.public_analysis.domain import ProviderResourceUsage
from opslens.repository_intelligence.adapters.github_http import GitHubHttpsConnection


class NoIoConnectionFactory:
    """Fail if live composition accidentally opens the physical GitHub boundary."""

    def __init__(self) -> None:
        """Track accidental calls without constructing a real connection."""
        self.call_count = 0

    def __call__(self, host: str, timeout_seconds: float) -> GitHubHttpsConnection:
        """Reject any physical transport creation during composition."""
        del host, timeout_seconds
        self.call_count += 1
        raise AssertionError("live composition must not construct a GitHub HTTPS connection")


class NoIoRetrievalClient:
    """Fail if live composition accidentally invokes Bedrock Knowledge Base Retrieve."""

    def __init__(self) -> None:
        """Track accidental provider calls."""
        self.call_count = 0

    def retrieve(
        self,
        *,
        knowledgeBaseId: str,
        retrievalQuery: Mapping[str, object],
        retrievalConfiguration: Mapping[str, object],
    ) -> Mapping[str, object]:
        """Reject provider execution during inert composition."""
        del knowledgeBaseId, retrievalQuery, retrievalConfiguration
        self.call_count += 1
        raise AssertionError("live composition must not invoke Bedrock Retrieve")


class NoIoSynthesisClient:
    """Fail if live composition accidentally invokes Bedrock Converse."""

    def __init__(self) -> None:
        """Track accidental provider calls."""
        self.call_count = 0

    def converse(self, **request: object) -> Mapping[str, object]:
        """Reject model execution during inert composition."""
        del request
        self.call_count += 1
        raise AssertionError("live composition must not invoke Bedrock synthesis")


def _typed_threat_evidence() -> RepresentativeRepositoryThreatEvidence:
    """Create an exact-type inert sentinel because construction never reads evidence fields."""
    return object.__new__(RepresentativeRepositoryThreatEvidence)


def _retrieval_catalog() -> CanonicalRetrievalCatalog:
    """Create an exact-type inert sentinel because construction never resolves a chunk."""
    return object.__new__(CanonicalRetrievalCatalog)


def test_composes_live_provider_ports_without_provider_execution() -> None:
    """Bind the concrete retained adapters while keeping construction side-effect free."""
    github = NoIoConnectionFactory()
    retrieval = NoIoRetrievalClient()
    synthesis = NoIoSynthesisClient()

    composition = build_representative_live_workload_composition(
        github_connection_factory=github,
        threat_evidence=_typed_threat_evidence(),
        expected_repository_url="https://github.com/openedx/mockprock",
        expected_commit_sha="18c954d8604df4740c829ba17fa2f3640b92b900",
        retrieval_client=retrieval,
        synthesis_client=synthesis,
        retrieval_catalog=_retrieval_catalog(),
        retrieval_config=RepresentativeLiveRetrievalConfig(
            knowledge_base_id="BTVJ2PBR2A",
            data_source_id="IEL1LBE026",
            source_bucket="opslens-dev-data-487757851499-us-east-1",
        ),
    )

    assert type(composition) is RepresentativeMeasuredWorkloadComposition
    assert github.call_count == 0
    assert retrieval.call_count == 0
    assert synthesis.call_count == 0
    assert composition.github_measurement.snapshot() == ProviderResourceUsage()
    assert composition.dependencies.repository_usage_snapshot() == ProviderResourceUsage()
    assert type(composition.dependencies.clock) is SystemMeasurementClock


def test_invalid_live_retrieval_coordinates_fail_before_provider_execution() -> None:
    """Reject malformed concrete provider coordinates without constructing provider calls."""
    github = NoIoConnectionFactory()
    retrieval = NoIoRetrievalClient()
    synthesis = NoIoSynthesisClient()

    with pytest.raises(RepresentativeLiveWorkloadConfigError, match="knowledge_base_id"):
        config = RepresentativeLiveRetrievalConfig(
            knowledge_base_id=" ",
            data_source_id="IEL1LBE026",
            source_bucket="opslens-dev-data-487757851499-us-east-1",
        )
        build_representative_live_workload_composition(
            github_connection_factory=github,
            threat_evidence=_typed_threat_evidence(),
            expected_repository_url="https://github.com/openedx/mockprock",
            expected_commit_sha="18c954d8604df4740c829ba17fa2f3640b92b900",
            retrieval_client=retrieval,
            synthesis_client=synthesis,
            retrieval_catalog=_retrieval_catalog(),
            retrieval_config=config,
        )

    assert github.call_count == 0
    assert retrieval.call_count == 0
    assert synthesis.call_count == 0
