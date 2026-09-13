"""Tests for locator-bound exact threat-authority source adapters."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from opslens.correlation.adapters.ghsa import GhsaPyPIVulnerabilityEvidence
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.public_analysis.application.representative_threat_authority_locators import (
    RepresentativeGhsaAuthorityLocator,
    RepresentativeNvdAuthorityLocator,
    RepresentativeSnapshotAuthorityLocator,
    RepresentativeThreatAuthorityLocatorManifestV1,
    S3ImmutableObjectLocator,
)
from opslens.public_analysis.application.representative_threat_authority_sources import (
    LocatorBoundRepresentativeEpssAuthoritySource,
    LocatorBoundRepresentativeGhsaAuthoritySource,
    LocatorBoundRepresentativeKevAuthoritySource,
    LocatorBoundRepresentativeNvdAuthoritySource,
    RepresentativeThreatAuthoritySourceError,
)
from opslens.transformation.nvd.domain.models import (
    NvdCveCoreRecord,
    NvdVulnerabilityStatus,
    ObservedCveVersion,
)

_CVE = "CVE-2026-54770"
_GHSA_OBSERVED = "GHSA-6hx8-3wjj-gr8g@sha256:" + "5" * 64
_SNAPSHOT_DATE = "2026-09-10"


def _call_log() -> list[tuple[object, ...]]:
    """Create one typed fake-reader call log."""
    return []


def _nvd() -> NvdCveCoreRecord:
    """Build one valid typed NVD record."""
    observed = ObservedCveVersion.from_source({"id": _CVE})
    return NvdCveCoreRecord(
        observed_version=observed,
        source_identifier="nvd@nist.gov",
        published_at=datetime(2026, 9, 9, tzinfo=UTC),
        last_modified_at=datetime(2026, 9, 10, tzinfo=UTC),
        vuln_status=NvdVulnerabilityStatus.ANALYZED,
    )


def _ghsa() -> GhsaPyPIVulnerabilityEvidence:
    """Build one typed GHSA package occurrence."""
    return GhsaPyPIVulnerabilityEvidence(
        observed_advisory_version_id=_GHSA_OBSERVED,
        source_advisory_sha256="5" * 64,
        ghsa_id="GHSA-6hx8-3wjj-gr8g",
        github_cve_id=_CVE,
        github_identifiers=(),
        vulnerability_entry_id="entry-0",
        source_index=0,
        source_entry_sha256="6" * 64,
        ecosystem_original="pip",
        package_name_original="webob",
        vulnerable_range_original="< 1.8.11",
        first_patched_version_original="1.8.11",
    )


def _kev() -> KevCatalogSnapshot:
    """Build one complete typed KEV snapshot."""
    return KevCatalogSnapshot(
        raw_bytes=b"{}",
        catalog_version="2026.09.10",
        date_released=datetime(2026, 9, 10, tzinfo=UTC),
        retrieved_at=datetime(2026, 9, 10, 12, tzinfo=UTC),
        sha256="7" * 64,
        record_count=1,
    )


def _epss() -> EpssSnapshot:
    """Build one complete typed EPSS snapshot."""
    return EpssSnapshot(
        raw_bytes=b"x",
        model_version="v2026.06.15",
        score_timestamp=datetime(2026, 9, 10, tzinfo=UTC),
        sha256="8" * 64,
        row_count=1,
    )


def _manifest(nvd: NvdCveCoreRecord) -> RepresentativeThreatAuthorityLocatorManifestV1:
    """Build one admitted locator manifest fixture."""
    return RepresentativeThreatAuthorityLocatorManifestV1(
        cve_id=_CVE,
        ghsa=(
            RepresentativeGhsaAuthorityLocator(
                observed_advisory_version_id=_GHSA_OBSERVED,
                source_index=0,
                s3=S3ImmutableObjectLocator(
                    object_key="bronze/ghsa/page.json",
                    version_id="ghsa-version-id",
                ),
            ),
        ),
        nvd=(
            RepresentativeNvdAuthorityLocator(
                observed_cve_version_id=nvd.observed_version.observed_cve_version_id,
                s3=S3ImmutableObjectLocator(
                    object_key="bronze/nvd/feed.json",
                    version_id="nvd-version-id",
                ),
            ),
        ),
        kev=RepresentativeSnapshotAuthorityLocator(
            snapshot_date=_SNAPSHOT_DATE,
            s3=S3ImmutableObjectLocator(
                object_key="bronze/kev/catalog.json",
                version_id="kev-version-id",
            ),
        ),
        epss=RepresentativeSnapshotAuthorityLocator(
            snapshot_date=_SNAPSHOT_DATE,
            s3=S3ImmutableObjectLocator(
                object_key="bronze/epss/scores.csv.gz",
                version_id="epss-version-id",
            ),
        ),
    )


@dataclass(slots=True)
class FakeGhsaReader:
    """Record exact GHSA physical reads."""

    value: GhsaPyPIVulnerabilityEvidence
    calls: list[tuple[object, ...]] = field(default_factory=_call_log)

    def read(
        self,
        *,
        object_key: str,
        version_id: str,
        cve_id: str,
        observed_advisory_version_id: str,
        source_index: int,
    ) -> GhsaPyPIVulnerabilityEvidence:
        """Return the configured GHSA authority."""
        self.calls.append(
            (object_key, version_id, cve_id, observed_advisory_version_id, source_index)
        )
        return self.value


@dataclass(slots=True)
class FakeNvdReader:
    """Record exact NVD physical reads."""

    value: NvdCveCoreRecord
    calls: list[tuple[object, ...]] = field(default_factory=_call_log)

    def read(
        self,
        *,
        object_key: str,
        version_id: str,
        cve_id: str,
        observed_cve_version_id: str,
    ) -> NvdCveCoreRecord:
        """Return the configured NVD authority."""
        self.calls.append((object_key, version_id, cve_id, observed_cve_version_id))
        return self.value


@dataclass(slots=True)
class FakeKevReader:
    """Record exact KEV physical reads."""

    value: KevCatalogSnapshot
    calls: list[tuple[object, ...]] = field(default_factory=_call_log)

    def read(
        self,
        *,
        object_key: str,
        version_id: str,
        snapshot_date: str,
    ) -> KevCatalogSnapshot:
        """Return the configured KEV snapshot."""
        self.calls.append((object_key, version_id, snapshot_date))
        return self.value


@dataclass(slots=True)
class FakeEpssReader:
    """Record exact EPSS physical reads."""

    value: EpssSnapshot
    calls: list[tuple[object, ...]] = field(default_factory=_call_log)

    def read(
        self,
        *,
        object_key: str,
        version_id: str,
        snapshot_date: str,
    ) -> EpssSnapshot:
        """Return the configured EPSS snapshot."""
        self.calls.append((object_key, version_id, snapshot_date))
        return self.value


def test_sources_delegate_exact_admitted_physical_coordinates_once() -> None:
    """Pass exact object key and VersionId without discovery or inference."""
    nvd = _nvd()
    manifest = _manifest(nvd)
    ghsa_reader = FakeGhsaReader(_ghsa())
    nvd_reader = FakeNvdReader(nvd)
    kev_reader = FakeKevReader(_kev())
    epss_reader = FakeEpssReader(_epss())

    ghsa = LocatorBoundRepresentativeGhsaAuthoritySource(manifest, ghsa_reader)
    nvd_source = LocatorBoundRepresentativeNvdAuthoritySource(manifest, nvd_reader)
    kev = LocatorBoundRepresentativeKevAuthoritySource(manifest, kev_reader)
    epss = LocatorBoundRepresentativeEpssAuthoritySource(manifest, epss_reader)

    assert ghsa.get_occurrence(
        cve_id=_CVE,
        observed_advisory_version_id=_GHSA_OBSERVED,
        source_index=0,
    ) is ghsa_reader.value
    assert nvd_source.get_record(
        cve_id=_CVE,
        observed_cve_version_id=nvd.observed_version.observed_cve_version_id,
    ) is nvd
    assert kev.get_snapshot(snapshot_date=_SNAPSHOT_DATE) is kev_reader.value
    assert epss.get_snapshot(snapshot_date=_SNAPSHOT_DATE) is epss_reader.value

    assert ghsa_reader.calls == [
        ("bronze/ghsa/page.json", "ghsa-version-id", _CVE, _GHSA_OBSERVED, 0)
    ]
    assert nvd_reader.calls == [
        (
            "bronze/nvd/feed.json",
            "nvd-version-id",
            _CVE,
            nvd.observed_version.observed_cve_version_id,
        )
    ]
    assert kev_reader.calls == [
        ("bronze/kev/catalog.json", "kev-version-id", _SNAPSHOT_DATE)
    ]
    assert epss_reader.calls == [
        ("bronze/epss/scores.csv.gz", "epss-version-id", _SNAPSHOT_DATE)
    ]


def test_missing_ghsa_coordinate_fails_before_reader_call() -> None:
    """Reject a logical request not present in the admitted manifest."""
    nvd = _nvd()
    reader = FakeGhsaReader(_ghsa())
    source = LocatorBoundRepresentativeGhsaAuthoritySource(_manifest(nvd), reader)

    with pytest.raises(
        RepresentativeThreatAuthoritySourceError,
        match="exactly one admitted locator",
    ):
        source.get_occurrence(
            cve_id=_CVE,
            observed_advisory_version_id=_GHSA_OBSERVED,
            source_index=1,
        )

    assert reader.calls == []


def test_reader_contradiction_fails_closed() -> None:
    """Reject typed authority that contradicts the requested logical identity."""
    nvd = _nvd()
    wrong = GhsaPyPIVulnerabilityEvidence(
        observed_advisory_version_id=_GHSA_OBSERVED,
        source_advisory_sha256="5" * 64,
        ghsa_id="GHSA-6hx8-3wjj-gr8g",
        github_cve_id="CVE-2026-55558",
        github_identifiers=(),
        vulnerability_entry_id="entry-0",
        source_index=0,
        source_entry_sha256="6" * 64,
        ecosystem_original="pip",
        package_name_original="webob",
        vulnerable_range_original="< 1.8.11",
        first_patched_version_original="1.8.11",
    )
    source = LocatorBoundRepresentativeGhsaAuthoritySource(
        _manifest(nvd), FakeGhsaReader(wrong)
    )

    with pytest.raises(
        RepresentativeThreatAuthoritySourceError,
        match="contradictory logical authority",
    ):
        source.get_occurrence(
            cve_id=_CVE,
            observed_advisory_version_id=_GHSA_OBSERVED,
            source_index=0,
        )


def test_snapshot_mismatch_fails_before_reader_call() -> None:
    """Reject snapshot-date drift before touching the exact reader."""
    nvd = _nvd()
    reader = FakeKevReader(_kev())
    source = LocatorBoundRepresentativeKevAuthoritySource(_manifest(nvd), reader)

    with pytest.raises(
        RepresentativeThreatAuthoritySourceError,
        match="KEV snapshot date does not match",
    ):
        source.get_snapshot(snapshot_date="2026-09-09")

    assert reader.calls == []


class FailingKevReader:
    """Expose deterministic reader failure propagation."""

    def read(
        self,
        *,
        object_key: str,
        version_id: str,
        snapshot_date: str,
    ) -> KevCatalogSnapshot:
        """Raise the underlying exact-reader failure unchanged."""
        del object_key, version_id, snapshot_date
        raise RuntimeError("exact read failed")


def test_reader_failure_propagates_without_retry_or_fallback() -> None:
    """Propagate an exact-reader failure without hidden recovery behavior."""
    nvd = _nvd()
    source = LocatorBoundRepresentativeKevAuthoritySource(
        _manifest(nvd), FailingKevReader()
    )

    with pytest.raises(RuntimeError, match="exact read failed"):
        source.get_snapshot(snapshot_date=_SNAPSHOT_DATE)
