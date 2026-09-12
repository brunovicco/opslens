"""Tests for exact Gate 19.2 threat-authority coordinate loaders."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from opslens.correlation.adapters.ghsa import GhsaPyPIVulnerabilityEvidence
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.public_analysis.application.representative_threat_evidence_coordinate_loaders import (
    BundleBoundRepresentativeEpssAuthorityLoader,
    BundleBoundRepresentativeGhsaAuthorityLoader,
    BundleBoundRepresentativeKevAuthorityLoader,
    BundleBoundRepresentativeNvdAuthorityLoader,
    RepresentativeThreatEvidenceCoordinateError,
    parse_representative_threat_evidence_coordinates,
)
from opslens.transformation.nvd.domain.models import (
    NvdCveCoreRecord,
    NvdVulnerabilityStatus,
    ObservedCveVersion,
)

_CVE = "CVE-2026-54770"
_GHSA_OBSERVED = (
    "GHSA-6hx8-3wjj-gr8g@sha256:"
    "5270134ee15b990dcafce267080c8279d547372c218826a5ee4362f30a972847"
)
_NVD_OBSERVED_SHA = "9f593e15a18d82f6cc9add874dedf0598e773e2430edc0bc3d4b0c03d1ec2d0b"
_NVD_OBSERVED = f"{_CVE}@sha256:{_NVD_OBSERVED_SHA}"
_SNAPSHOT_DATE = "2026-09-10"


def _call_log() -> list[tuple[object, ...]]:
    """Return one strictly typed fake-provider call log."""
    return []


def _bundle() -> Mapping[str, object]:
    """Build the minimal analytical shape required for exact coordinate extraction."""
    return {
        "schema_version": 1,
        "bundle_type": "CrossSourceCveEvidenceV1",
        "read_only": True,
        "cve_id": _CVE,
        "ghsa": {
            "advisory_versions": [
                {
                    "cve_id": _CVE,
                    "observed_advisory_version_id": _GHSA_OBSERVED,
                    "package_evidence": [
                        {
                            "source_index": 0,
                        }
                    ],
                }
            ]
        },
        "nvd": {
            "observations": [
                {
                    "cve_id": _CVE,
                    "observed_cve_version_id": _NVD_OBSERVED,
                }
            ]
        },
        "kev": {"snapshot_date": _SNAPSHOT_DATE},
        "epss": {"snapshot_date": _SNAPSHOT_DATE},
    }


def _ghsa() -> GhsaPyPIVulnerabilityEvidence:
    """Build one typed GHSA authority fixture."""
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


def _nvd() -> NvdCveCoreRecord:
    """Build one typed NVD authority fixture with canonical content identity."""
    canonical_json = b'{"id":"CVE-2026-54770"}'
    observed = ObservedCveVersion(
        cve_id=_CVE,
        canonical_json=canonical_json,
        source_cve_sha256=_NVD_OBSERVED_SHA,
    )
    return NvdCveCoreRecord(
        observed_version=observed,
        source_identifier="nvd@nist.gov",
        published_at=datetime(2026, 9, 9, tzinfo=UTC),
        last_modified_at=datetime(2026, 9, 10, tzinfo=UTC),
        vuln_status=NvdVulnerabilityStatus.ANALYZED,
    )


def _kev() -> KevCatalogSnapshot:
    """Build one complete KEV snapshot fixture for coordinate checks."""
    return KevCatalogSnapshot(
        raw_bytes=b"{}",
        catalog_version="2026.09.10",
        date_released=datetime(2026, 9, 10, tzinfo=UTC),
        retrieved_at=datetime(2026, 9, 10, 12, tzinfo=UTC),
        sha256="7" * 64,
        record_count=1,
    )


def _epss() -> EpssSnapshot:
    """Build one complete EPSS snapshot fixture for coordinate checks."""
    return EpssSnapshot(
        raw_bytes=b"x",
        model_version="v2026.06.15",
        score_timestamp=datetime(2026, 9, 10, tzinfo=UTC),
        sha256="8" * 64,
        row_count=1,
    )


@dataclass(slots=True)
class FakeGhsaSource:
    """Return one GHSA authority object while recording exact coordinates."""

    value: GhsaPyPIVulnerabilityEvidence
    calls: list[tuple[object, ...]] = field(default_factory=_call_log)

    def get_occurrence(
        self,
        *,
        cve_id: str,
        observed_advisory_version_id: str,
        source_index: int,
    ) -> GhsaPyPIVulnerabilityEvidence:
        """Record and return one exact GHSA lookup."""
        self.calls.append((cve_id, observed_advisory_version_id, source_index))
        return self.value


@dataclass(slots=True)
class FakeNvdSource:
    """Return one NVD authority object while recording exact coordinates."""

    value: NvdCveCoreRecord
    calls: list[tuple[object, ...]] = field(default_factory=_call_log)

    def get_record(
        self,
        *,
        cve_id: str,
        observed_cve_version_id: str,
    ) -> NvdCveCoreRecord:
        """Record and return one exact NVD lookup."""
        self.calls.append((cve_id, observed_cve_version_id))
        return self.value


@dataclass(slots=True)
class FakeKevSource:
    """Return one complete KEV snapshot while recording the selected date."""

    value: KevCatalogSnapshot
    calls: list[tuple[object, ...]] = field(default_factory=_call_log)

    def get_snapshot(self, *, snapshot_date: str) -> KevCatalogSnapshot:
        """Record and return one exact KEV snapshot lookup."""
        self.calls.append((snapshot_date,))
        return self.value


@dataclass(slots=True)
class FakeEpssSource:
    """Return one complete EPSS snapshot while recording the selected date."""

    value: EpssSnapshot
    calls: list[tuple[object, ...]] = field(default_factory=_call_log)

    def get_snapshot(self, *, snapshot_date: str) -> EpssSnapshot:
        """Record and return one exact EPSS snapshot lookup."""
        self.calls.append((snapshot_date,))
        return self.value


def test_parse_coordinates_preserves_exact_source_identity() -> None:
    """Preserve exact GHSA, NVD, KEV, and EPSS lookup coordinates."""
    coordinates = parse_representative_threat_evidence_coordinates(_bundle())

    assert coordinates.cve_id == _CVE
    assert len(coordinates.ghsa_occurrences) == 1
    assert coordinates.ghsa_occurrences[0].observed_advisory_version_id == _GHSA_OBSERVED
    assert coordinates.ghsa_occurrences[0].source_index == 0
    assert coordinates.nvd_observed_version_ids == (_NVD_OBSERVED,)
    assert coordinates.kev_snapshot_date == _SNAPSHOT_DATE
    assert coordinates.epss_snapshot_date == _SNAPSHOT_DATE


def test_parse_coordinates_rejects_duplicate_ghsa_occurrence() -> None:
    """Reject ambiguous duplicate GHSA package coordinates before any source read."""
    bundle = dict(_bundle())
    bundle["ghsa"] = {
        "advisory_versions": [
            {
                "cve_id": _CVE,
                "observed_advisory_version_id": _GHSA_OBSERVED,
                "package_evidence": [
                    {"source_index": 0},
                    {"source_index": 0},
                ],
            }
        ]
    }

    with pytest.raises(
        RepresentativeThreatEvidenceCoordinateError,
        match="duplicate GHSA advisory/package coordinate",
    ):
        parse_representative_threat_evidence_coordinates(bundle)


def test_bundle_bound_loaders_request_exact_coordinates_once() -> None:
    """Call every injected authority provider once with exact bundle coordinates."""
    bundle = _bundle()
    ghsa_source = FakeGhsaSource(_ghsa())
    nvd_source = FakeNvdSource(_nvd())
    kev_source = FakeKevSource(_kev())
    epss_source = FakeEpssSource(_epss())

    ghsa = BundleBoundRepresentativeGhsaAuthorityLoader(ghsa_source).load(bundle)
    nvd = BundleBoundRepresentativeNvdAuthorityLoader(nvd_source).load(bundle)
    kev = BundleBoundRepresentativeKevAuthorityLoader(kev_source).load(bundle)
    epss = BundleBoundRepresentativeEpssAuthorityLoader(epss_source).load(bundle)

    assert ghsa == (ghsa_source.value,)
    assert nvd == (nvd_source.value,)
    assert kev is kev_source.value
    assert epss is epss_source.value
    assert ghsa_source.calls == [(_CVE, _GHSA_OBSERVED, 0)]
    assert nvd_source.calls == [(_CVE, _NVD_OBSERVED)]
    assert kev_source.calls == [(_SNAPSHOT_DATE,)]
    assert epss_source.calls == [(_SNAPSHOT_DATE,)]


def test_ghsa_loader_rejects_provider_coordinate_mismatch() -> None:
    """Reject typed GHSA evidence returned for a different CVE coordinate."""
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

    with pytest.raises(
        RepresentativeThreatEvidenceCoordinateError,
        match="GHSA authority source returned contradictory coordinates",
    ):
        BundleBoundRepresentativeGhsaAuthorityLoader(FakeGhsaSource(wrong)).load(_bundle())


def test_kev_loader_rejects_provider_snapshot_mismatch() -> None:
    """Reject a complete KEV snapshot returned for a different exact date."""
    wrong = KevCatalogSnapshot(
        raw_bytes=b"{}",
        catalog_version="2026.09.09",
        date_released=datetime(2026, 9, 9, tzinfo=UTC),
        retrieved_at=datetime(2026, 9, 9, 12, tzinfo=UTC),
        sha256="9" * 64,
        record_count=1,
    )

    with pytest.raises(
        RepresentativeThreatEvidenceCoordinateError,
        match="KEV authority source returned a different snapshot date",
    ):
        BundleBoundRepresentativeKevAuthorityLoader(FakeKevSource(wrong)).load(_bundle())
