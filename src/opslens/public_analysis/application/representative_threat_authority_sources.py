"""Resolve admitted threat-authority locators through exact typed readers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from opslens.correlation.adapters.ghsa import GhsaPyPIVulnerabilityEvidence
from opslens.ingestion.epss.domain.history import HistoricalEpssSnapshot
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.public_analysis.application.representative_threat_authority_locators import (
    RepresentativeGhsaAuthorityLocator,
    RepresentativeNvdAuthorityLocator,
    RepresentativeSnapshotAuthorityLocator,
    RepresentativeThreatAuthorityLocatorManifestV1,
)
from opslens.transformation.nvd.domain.models import NvdCveCoreRecord


class RepresentativeThreatAuthoritySourceError(ValueError):
    """Reject missing, ambiguous, or contradictory exact source materialization."""


class ExactGhsaAuthorityReader(Protocol):
    """Materialize typed GHSA authority from one exact immutable object."""

    def read(
        self,
        *,
        object_key: str,
        version_id: str,
        cve_id: str,
        observed_advisory_version_id: str,
        source_index: int,
    ) -> GhsaPyPIVulnerabilityEvidence:
        """Return one typed GHSA package occurrence from exact physical authority."""
        ...


class ExactNvdAuthorityReader(Protocol):
    """Materialize typed NVD authority from one exact immutable object."""

    def read(
        self,
        *,
        object_key: str,
        version_id: str,
        cve_id: str,
        observed_cve_version_id: str,
    ) -> NvdCveCoreRecord:
        """Return one typed NVD record from exact physical authority."""
        ...


class ExactKevAuthorityReader(Protocol):
    """Materialize one complete KEV snapshot from one exact immutable object."""

    def read(
        self,
        *,
        object_key: str,
        version_id: str,
        snapshot_date: str,
    ) -> KevCatalogSnapshot:
        """Return the complete typed KEV snapshot from exact physical authority."""
        ...


class ExactEpssAuthorityReader(Protocol):
    """Materialize one complete EPSS snapshot from one exact immutable object."""

    def read(
        self,
        *,
        object_key: str,
        version_id: str,
        snapshot_date: str,
    ) -> EpssSnapshot | HistoricalEpssSnapshot:
        """Return the complete typed EPSS snapshot from exact physical authority."""
        ...


def _exact_ghsa_locator(
    manifest: RepresentativeThreatAuthorityLocatorManifestV1,
    *,
    observed_advisory_version_id: str,
    source_index: int,
) -> RepresentativeGhsaAuthorityLocator:
    matches = tuple(
        item
        for item in manifest.ghsa
        if item.observed_advisory_version_id == observed_advisory_version_id
        and item.source_index == source_index
    )
    if len(matches) != 1:
        raise RepresentativeThreatAuthoritySourceError(
            "GHSA logical identity must resolve to exactly one admitted locator"
        )
    return matches[0]


def _exact_nvd_locator(
    manifest: RepresentativeThreatAuthorityLocatorManifestV1,
    *,
    observed_cve_version_id: str,
) -> RepresentativeNvdAuthorityLocator:
    matches = tuple(
        item
        for item in manifest.nvd
        if item.observed_cve_version_id == observed_cve_version_id
    )
    if len(matches) != 1:
        raise RepresentativeThreatAuthoritySourceError(
            "NVD logical identity must resolve to exactly one admitted locator"
        )
    return matches[0]


def _exact_snapshot_locator(
    locator: RepresentativeSnapshotAuthorityLocator,
    *,
    snapshot_date: str,
    source: str,
) -> RepresentativeSnapshotAuthorityLocator:
    if locator.snapshot_date != snapshot_date:
        raise RepresentativeThreatAuthoritySourceError(
            f"{source} snapshot date does not match the admitted locator"
        )
    return locator


@dataclass(frozen=True, slots=True)
class LocatorBoundRepresentativeGhsaAuthoritySource:
    """Resolve GHSA logical requests only through the admitted locator manifest."""

    manifest: RepresentativeThreatAuthorityLocatorManifestV1
    reader: ExactGhsaAuthorityReader

    def get_occurrence(
        self,
        *,
        cve_id: str,
        observed_advisory_version_id: str,
        source_index: int,
    ) -> GhsaPyPIVulnerabilityEvidence:
        """Delegate one exact GHSA read and verify its returned logical identity."""
        if cve_id != self.manifest.cve_id:
            raise RepresentativeThreatAuthoritySourceError("GHSA CVE identity mismatch")
        locator = _exact_ghsa_locator(
            self.manifest,
            observed_advisory_version_id=observed_advisory_version_id,
            source_index=source_index,
        )
        result = self.reader.read(
            object_key=locator.s3.object_key,
            version_id=locator.s3.version_id,
            cve_id=cve_id,
            observed_advisory_version_id=observed_advisory_version_id,
            source_index=source_index,
        )
        if (
            result.github_cve_id != cve_id
            or result.observed_advisory_version_id != observed_advisory_version_id
            or result.source_index != source_index
        ):
            raise RepresentativeThreatAuthoritySourceError(
                "GHSA exact reader returned contradictory logical authority"
            )
        return result


@dataclass(frozen=True, slots=True)
class LocatorBoundRepresentativeNvdAuthoritySource:
    """Resolve NVD logical requests only through the admitted locator manifest."""

    manifest: RepresentativeThreatAuthorityLocatorManifestV1
    reader: ExactNvdAuthorityReader

    def get_record(
        self,
        *,
        cve_id: str,
        observed_cve_version_id: str,
    ) -> NvdCveCoreRecord:
        """Delegate one exact NVD read and verify its returned logical identity."""
        if cve_id != self.manifest.cve_id:
            raise RepresentativeThreatAuthoritySourceError("NVD CVE identity mismatch")
        locator = _exact_nvd_locator(
            self.manifest,
            observed_cve_version_id=observed_cve_version_id,
        )
        result = self.reader.read(
            object_key=locator.s3.object_key,
            version_id=locator.s3.version_id,
            cve_id=cve_id,
            observed_cve_version_id=observed_cve_version_id,
        )
        if (
            result.observed_version.cve_id != cve_id
            or result.observed_version.observed_cve_version_id != observed_cve_version_id
        ):
            raise RepresentativeThreatAuthoritySourceError(
                "NVD exact reader returned contradictory logical authority"
            )
        return result


@dataclass(frozen=True, slots=True)
class LocatorBoundRepresentativeKevAuthoritySource:
    """Resolve KEV snapshot requests only through the admitted locator manifest."""

    manifest: RepresentativeThreatAuthorityLocatorManifestV1
    reader: ExactKevAuthorityReader

    def get_snapshot(self, *, snapshot_date: str) -> KevCatalogSnapshot:
        """Delegate one exact KEV read and verify the complete snapshot date."""
        locator = _exact_snapshot_locator(
            self.manifest.kev,
            snapshot_date=snapshot_date,
            source="KEV",
        )
        result = self.reader.read(
            object_key=locator.s3.object_key,
            version_id=locator.s3.version_id,
            snapshot_date=snapshot_date,
        )
        if result.snapshot_date != snapshot_date:
            raise RepresentativeThreatAuthoritySourceError(
                "KEV exact reader returned a contradictory snapshot date"
            )
        return result


@dataclass(frozen=True, slots=True)
class LocatorBoundRepresentativeEpssAuthoritySource:
    """Resolve EPSS snapshot requests only through the admitted locator manifest."""

    manifest: RepresentativeThreatAuthorityLocatorManifestV1
    reader: ExactEpssAuthorityReader

    def get_snapshot(
        self,
        *,
        snapshot_date: str,
    ) -> EpssSnapshot | HistoricalEpssSnapshot:
        """Delegate one exact EPSS read and verify the complete snapshot date."""
        locator = _exact_snapshot_locator(
            self.manifest.epss,
            snapshot_date=snapshot_date,
            source="EPSS",
        )
        result = self.reader.read(
            object_key=locator.s3.object_key,
            version_id=locator.s3.version_id,
            snapshot_date=snapshot_date,
        )
        if isinstance(result, EpssSnapshot):
            actual_date = result.snapshot_date
        else:
            actual_date = result.snapshot_date.isoformat()
        if actual_date != snapshot_date:
            raise RepresentativeThreatAuthoritySourceError(
                "EPSS exact reader returned a contradictory snapshot date"
            )
        return result
