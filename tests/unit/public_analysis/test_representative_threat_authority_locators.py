"""Tests for Gate 19.2 exact threat-authority locator admission."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from opslens.public_analysis.application.representative_threat_authority_locators import (
    RepresentativeThreatAuthorityLocatorError,
    admit_representative_threat_authority_locator_manifest,
)
from opslens.public_analysis.application.representative_threat_evidence_coordinate_loaders import (
    RepresentativeGhsaOccurrenceCoordinate,
    RepresentativeThreatEvidenceCoordinates,
)

_CVE = "CVE-2026-54770"
_GHSA = "GHSA-6hx8-3wjj-gr8g@sha256:" + "5" * 64
_NVD = _CVE + "@sha256:" + "6" * 64
_DATE = "2026-09-10"


def _coordinates() -> RepresentativeThreatEvidenceCoordinates:
    """Build admitted logical coordinates for one representative threat bundle."""
    return RepresentativeThreatEvidenceCoordinates(
        cve_id=_CVE,
        ghsa_occurrences=(
            RepresentativeGhsaOccurrenceCoordinate(
                observed_advisory_version_id=_GHSA,
                source_index=0,
            ),
        ),
        nvd_observed_version_ids=(_NVD,),
        kev_snapshot_date=_DATE,
        epss_snapshot_date=_DATE,
    )


def _manifest() -> Mapping[str, object]:
    """Build one complete immutable locator manifest."""
    return {
        "schema_version": 1,
        "manifest_type": "RepresentativeThreatAuthorityLocatorManifestV1",
        "cve_id": _CVE,
        "ghsa": [
            {
                "observed_advisory_version_id": _GHSA,
                "source_index": 0,
                "s3": {
                    "object_key": "bronze/ghsa/pages/page-0001.json",
                    "version_id": "ghsa-version-1",
                },
            }
        ],
        "nvd": [
            {
                "observed_cve_version_id": _NVD,
                "s3": {
                    "object_key": "bronze/nvd/incremental/2026-09-10.json",
                    "version_id": "nvd-version-1",
                },
            }
        ],
        "kev": {
            "snapshot_date": _DATE,
            "s3": {
                "object_key": "bronze/kev/2026-09-10/catalog.json",
                "version_id": "kev-version-1",
            },
        },
        "epss": {
            "snapshot_date": _DATE,
            "s3": {
                "object_key": "bronze/epss/2026-09-10/epss_scores.csv.gz",
                "version_id": "epss-version-1",
            },
        },
    }


def test_locator_manifest_admits_exact_logical_and_physical_coordinates() -> None:
    """Admit one manifest whose locator set exactly matches logical authority."""
    admitted = admit_representative_threat_authority_locator_manifest(
        _manifest(),
        coordinates=_coordinates(),
    )

    assert admitted.cve_id == _CVE
    assert admitted.ghsa[0].s3.version_id == "ghsa-version-1"
    assert admitted.nvd[0].observed_cve_version_id == _NVD
    assert admitted.kev.snapshot_date == _DATE
    assert admitted.epss.s3.object_key.endswith("epss_scores.csv.gz")


def test_locator_manifest_rejects_missing_ghsa_locator() -> None:
    """Fail closed when an admitted logical GHSA occurrence has no physical locator."""
    manifest = dict(_manifest())
    manifest["ghsa"] = []

    with pytest.raises(
        RepresentativeThreatAuthorityLocatorError,
        match="GHSA locator set must exactly match admitted logical coordinates",
    ):
        admit_representative_threat_authority_locator_manifest(
            manifest,
            coordinates=_coordinates(),
        )


def test_locator_manifest_rejects_extra_nvd_locator() -> None:
    """Fail closed when physical NVD locators exceed admitted logical authority."""
    manifest = dict(_manifest())
    manifest["nvd"] = [
        {
            "observed_cve_version_id": _NVD,
            "s3": {"object_key": "nvd.json", "version_id": "v1"},
        },
        {
            "observed_cve_version_id": _CVE + "@sha256:" + "7" * 64,
            "s3": {"object_key": "nvd-other.json", "version_id": "v2"},
        },
    ]

    with pytest.raises(
        RepresentativeThreatAuthorityLocatorError,
        match="NVD locator set must exactly match admitted logical coordinates",
    ):
        admit_representative_threat_authority_locator_manifest(
            manifest,
            coordinates=_coordinates(),
        )


def test_locator_manifest_rejects_duplicate_ghsa_locator() -> None:
    """Reject ambiguous duplicate physical locations for one GHSA occurrence."""
    manifest = dict(_manifest())
    item = {
        "observed_advisory_version_id": _GHSA,
        "source_index": 0,
        "s3": {"object_key": "one.json", "version_id": "v1"},
    }
    manifest["ghsa"] = [item, item]

    with pytest.raises(
        RepresentativeThreatAuthorityLocatorError,
        match="duplicate GHSA locator",
    ):
        admit_representative_threat_authority_locator_manifest(
            manifest,
            coordinates=_coordinates(),
        )


def test_locator_manifest_rejects_snapshot_mismatch() -> None:
    """Reject physical snapshot authority for a date not admitted by the bundle."""
    manifest = dict(_manifest())
    manifest["kev"] = {
        "snapshot_date": "2026-09-09",
        "s3": {"object_key": "kev.json", "version_id": "v1"},
    }

    with pytest.raises(
        RepresentativeThreatAuthorityLocatorError,
        match="KEV locator snapshot mismatch",
    ):
        admit_representative_threat_authority_locator_manifest(
            manifest,
            coordinates=_coordinates(),
        )


def test_locator_manifest_rejects_empty_version_id() -> None:
    """Reject storage coordinates that omit immutable S3 version identity."""
    manifest = dict(_manifest())
    manifest["epss"] = {
        "snapshot_date": _DATE,
        "s3": {"object_key": "epss.gz", "version_id": ""},
    }

    with pytest.raises(
        RepresentativeThreatAuthorityLocatorError,
        match="version_id must be a non-empty trimmed string",
    ):
        admit_representative_threat_authority_locator_manifest(
            manifest,
            coordinates=_coordinates(),
        )
