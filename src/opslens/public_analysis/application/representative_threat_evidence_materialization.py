"""Compose typed threat-source authority before representative admission."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from opslens.correlation.adapters.ghsa import GhsaPyPIVulnerabilityEvidence
from opslens.ingestion.epss.domain.history import HistoricalEpssSnapshot
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.public_analysis.application.representative_repository_analysis import (
    RepresentativeRepositoryThreatEvidence,
)
from opslens.public_analysis.application.representative_threat_evidence_admission import (
    RepresentativeThreatEvidenceAuthority,
    admit_representative_threat_evidence,
)
from opslens.transformation.nvd.domain.models import NvdCveCoreRecord


class RepresentativeGhsaAuthorityLoader(Protocol):
    """Load exact typed GHSA authority for one analytical proof bundle."""

    def load(
        self,
        bundle: Mapping[str, object],
    ) -> tuple[GhsaPyPIVulnerabilityEvidence, ...]:
        """Return exact typed GHSA occurrences without evaluating applicability."""
        ...


class RepresentativeNvdAuthorityLoader(Protocol):
    """Load exact typed NVD authority for one analytical proof bundle."""

    def load(self, bundle: Mapping[str, object]) -> tuple[NvdCveCoreRecord, ...]:
        """Return exact observed NVD records without synthesizing source content."""
        ...


class RepresentativeKevAuthorityLoader(Protocol):
    """Load one complete KEV source snapshot for representative admission."""

    def load(self, bundle: Mapping[str, object]) -> KevCatalogSnapshot:
        """Return the complete immutable KEV snapshot selected by the bundle."""
        ...


class RepresentativeEpssAuthorityLoader(Protocol):
    """Load one complete EPSS source snapshot for representative admission."""

    def load(
        self,
        bundle: Mapping[str, object],
    ) -> EpssSnapshot | HistoricalEpssSnapshot:
        """Return the complete immutable EPSS snapshot selected by the bundle."""
        ...


@dataclass(frozen=True, slots=True)
class RepresentativeThreatEvidenceAuthorityLoaders:
    """Group the four explicit source-authority loaders for one materialization."""

    ghsa: RepresentativeGhsaAuthorityLoader
    nvd: RepresentativeNvdAuthorityLoader
    kev: RepresentativeKevAuthorityLoader
    epss: RepresentativeEpssAuthorityLoader


def materialize_representative_threat_evidence(
    bundle: Mapping[str, object],
    *,
    loaders: RepresentativeThreatEvidenceAuthorityLoaders,
) -> RepresentativeRepositoryThreatEvidence:
    """Load exact source authority once and admit it fail-closed against the bundle.

    This coordinator intentionally owns no AWS access, retries, fallback sources,
    applicability decisions, or source reconstruction. Concrete loaders remain
    infrastructure concerns; the existing admission adapter remains the final
    authority boundary.
    """
    ghsa_vulnerabilities = loaders.ghsa.load(bundle)
    nvd_records = loaders.nvd.load(bundle)
    kev_snapshot = loaders.kev.load(bundle)
    epss_snapshot = loaders.epss.load(bundle)

    authority = RepresentativeThreatEvidenceAuthority(
        ghsa_vulnerabilities=ghsa_vulnerabilities,
        nvd_records=nvd_records,
        kev_snapshot=kev_snapshot,
        epss_snapshot=epss_snapshot,
    )
    return admit_representative_threat_evidence(bundle, authority=authority)
