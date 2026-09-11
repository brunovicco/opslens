"""Compose exact threat-source authority outside the measured representative workload."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from opslens.public_analysis.application.representative_repository_analysis import (
    RepresentativeRepositoryThreatEvidence,
)
from opslens.public_analysis.application.representative_threat_authority_locators import (
    admit_representative_threat_authority_locator_manifest,
)
from opslens.public_analysis.application.representative_threat_authority_sources import (
    ExactEpssAuthorityReader,
    ExactGhsaAuthorityReader,
    ExactKevAuthorityReader,
    ExactNvdAuthorityReader,
    LocatorBoundRepresentativeEpssAuthoritySource,
    LocatorBoundRepresentativeGhsaAuthoritySource,
    LocatorBoundRepresentativeKevAuthoritySource,
    LocatorBoundRepresentativeNvdAuthoritySource,
)
from opslens.public_analysis.application.representative_threat_evidence_coordinate_loaders import (
    BundleBoundRepresentativeEpssAuthorityLoader,
    BundleBoundRepresentativeGhsaAuthorityLoader,
    BundleBoundRepresentativeKevAuthorityLoader,
    BundleBoundRepresentativeNvdAuthorityLoader,
    parse_representative_threat_evidence_coordinates,
)
from opslens.public_analysis.application.representative_threat_evidence_materialization import (
    RepresentativeThreatEvidenceAuthorityLoaders,
    materialize_representative_threat_evidence,
)


@dataclass(frozen=True, slots=True)
class RepresentativeThreatAuthorityReaders:
    """Group the four exact typed readers used by human-boundary preparation."""

    ghsa: ExactGhsaAuthorityReader
    nvd: ExactNvdAuthorityReader
    kev: ExactKevAuthorityReader
    epss: ExactEpssAuthorityReader


def materialize_pre_measurement_threat_evidence(
    bundle: Mapping[str, object],
    *,
    locator_manifest: Mapping[str, object],
    readers: RepresentativeThreatAuthorityReaders,
) -> RepresentativeRepositoryThreatEvidence:
    """Materialize admitted threat evidence before Gate 19.2 request-time measurement.

    Logical coordinates are parsed first, then the separately supplied physical
    locator manifest is admitted against those coordinates before any source
    loader can execute. Exact typed readers remain injected infrastructure
    capabilities; this application boundary constructs no provider client and
    owns no retry, discovery, fallback, or request-time measurement behavior.
    """
    coordinates = parse_representative_threat_evidence_coordinates(bundle)
    admitted_manifest = admit_representative_threat_authority_locator_manifest(
        locator_manifest,
        coordinates=coordinates,
    )

    loaders = RepresentativeThreatEvidenceAuthorityLoaders(
        ghsa=BundleBoundRepresentativeGhsaAuthorityLoader(
            source=LocatorBoundRepresentativeGhsaAuthoritySource(
                manifest=admitted_manifest,
                reader=readers.ghsa,
            )
        ),
        nvd=BundleBoundRepresentativeNvdAuthorityLoader(
            source=LocatorBoundRepresentativeNvdAuthoritySource(
                manifest=admitted_manifest,
                reader=readers.nvd,
            )
        ),
        kev=BundleBoundRepresentativeKevAuthorityLoader(
            source=LocatorBoundRepresentativeKevAuthoritySource(
                manifest=admitted_manifest,
                reader=readers.kev,
            )
        ),
        epss=BundleBoundRepresentativeEpssAuthorityLoader(
            source=LocatorBoundRepresentativeEpssAuthoritySource(
                manifest=admitted_manifest,
                reader=readers.epss,
            )
        ),
    )
    return materialize_representative_threat_evidence(bundle, loaders=loaders)


__all__ = [
    "RepresentativeThreatAuthorityReaders",
    "materialize_pre_measurement_threat_evidence",
]
