"""Tests for bounded Gate 19.2 threat-evidence preparation summaries."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.public_analysis.application.representative_repository_analysis import (
    RepresentativeRepositoryThreatEvidence,
)
from opslens.public_analysis.application.representative_threat_evidence_coordinate_loaders import (
    RepresentativeThreatEvidenceCoordinates,
)
from opslens.public_analysis.application.representative_threat_evidence_preparation import (
    summarize_representative_threat_evidence_preparation,
)

_SHA_A = "a" * 64
_SHA_B = "b" * 64
_SHA_C = "c" * 64
_SHA_D = "d" * 64


def _coordinates() -> RepresentativeThreatEvidenceCoordinates:
    """Return exact source coordinates for the frozen representative date."""
    return RepresentativeThreatEvidenceCoordinates(
        cve_id="CVE-2026-54770",
        ghsa_occurrences=(),
        nvd_observed_version_ids=(),
        kev_snapshot_date="2026-09-10",
        epss_snapshot_date="2026-09-10",
    )


def _evidence(*, epss_date: str = "2026-09-10") -> RepresentativeRepositoryThreatEvidence:
    """Build complete typed snapshots without external provider access."""
    return RepresentativeRepositoryThreatEvidence(
        ghsa_vulnerabilities=(),
        nvd_records=(),
        kev_snapshot=KevCatalogSnapshot(
            raw_bytes=b"{}",
            catalog_version="2026.09.10",
            date_released=datetime(2026, 9, 10, tzinfo=UTC),
            retrieved_at=datetime(2026, 9, 10, 12, tzinfo=UTC),
            sha256=_SHA_C,
            record_count=1,
        ),
        epss_snapshot=EpssSnapshot(
            raw_bytes=b"gzip",
            model_version="v2026.06.15",
            score_timestamp=datetime.fromisoformat(f"{epss_date}T00:00:00+00:00"),
            sha256=_SHA_D,
            row_count=1,
        ),
    )


def test_summary_contains_only_bounded_scalar_reproducibility_fields() -> None:
    """Exclude raw snapshot payloads while preserving source identity and counts."""
    summary = summarize_representative_threat_evidence_preparation(
        coordinates=_coordinates(),
        evidence=_evidence(),
        bundle_sha256=_SHA_A,
        locator_manifest_sha256=_SHA_B,
    )

    assert summary.cve_id == "CVE-2026-54770"
    assert summary.kev_snapshot_date == "2026-09-10"
    assert summary.epss_snapshot_date == "2026-09-10"
    assert summary.kev_sha256 == _SHA_C
    assert summary.epss_sha256 == _SHA_D
    assert summary.ghsa_occurrence_count == 0
    assert summary.nvd_record_count == 0
    serialized = summary.to_json_dict()
    assert "raw_bytes" not in serialized
    assert serialized["bundle_sha256"] == _SHA_A


def test_summary_rejects_snapshot_date_drift() -> None:
    """Fail closed if materialized EPSS authority contradicts admitted coordinates."""
    with pytest.raises(ValueError, match="EPSS snapshot date"):
        summarize_representative_threat_evidence_preparation(
            coordinates=_coordinates(),
            evidence=_evidence(epss_date="2026-09-09"),
            bundle_sha256=_SHA_A,
            locator_manifest_sha256=_SHA_B,
        )


def test_summary_rejects_non_sha256_input_identity() -> None:
    """Require strong deterministic identities for both operator-supplied JSON inputs."""
    with pytest.raises(ValueError, match="SHA-256"):
        summarize_representative_threat_evidence_preparation(
            coordinates=_coordinates(),
            evidence=_evidence(),
            bundle_sha256="short",
            locator_manifest_sha256=_SHA_B,
        )
