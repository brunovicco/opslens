"""Summarize admitted representative threat evidence without retaining raw payloads."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from opslens.ingestion.epss.domain.history import HistoricalEpssSnapshot
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.public_analysis.application.representative_repository_analysis import (
    RepresentativeRepositoryThreatEvidence,
)
from opslens.public_analysis.application.representative_threat_evidence_coordinate_loaders import (
    RepresentativeThreatEvidenceCoordinates,
)


@dataclass(frozen=True, slots=True)
class RepresentativeThreatEvidencePreparationSummary:
    """Bounded reproducibility proof for one pre-measurement authority materialization."""

    schema_version: int
    cve_id: str
    bundle_sha256: str
    locator_manifest_sha256: str
    ghsa_occurrence_count: int
    nvd_record_count: int
    kev_snapshot_date: str
    kev_catalog_version: str
    kev_sha256: str
    kev_record_count: int
    epss_snapshot_date: str
    epss_model_version: str | None
    epss_sha256: str
    epss_row_count: int

    def to_json_dict(self) -> dict[str, object]:
        """Return deterministic JSON-safe scalar evidence only."""
        return dict(asdict(self))


def summarize_representative_threat_evidence_preparation(
    *,
    coordinates: RepresentativeThreatEvidenceCoordinates,
    evidence: RepresentativeRepositoryThreatEvidence,
    bundle_sha256: str,
    locator_manifest_sha256: str,
) -> RepresentativeThreatEvidencePreparationSummary:
    """Build a bounded summary without serializing KEV/EPSS raw source payloads."""
    if len(bundle_sha256) != 64 or len(locator_manifest_sha256) != 64:
        raise ValueError("input evidence hashes must be SHA-256 hex digests")

    epss = evidence.epss_snapshot
    if type(epss) is EpssSnapshot:
        epss_snapshot_date = epss.snapshot_date
        epss_model_version = epss.model_version
        epss_sha256 = epss.sha256
        epss_row_count = epss.row_count
    elif type(epss) is HistoricalEpssSnapshot:
        epss_snapshot_date = epss.snapshot_date.isoformat()
        epss_model_version = epss.model_version
        epss_sha256 = epss.sha256
        epss_row_count = epss.row_count
    else:  # pragma: no cover - domain constructor already rejects this state.
        raise TypeError("unsupported representative EPSS snapshot type")

    if epss_snapshot_date != coordinates.epss_snapshot_date:
        raise ValueError("prepared EPSS snapshot date contradicts admitted coordinates")
    if evidence.kev_snapshot.snapshot_date != coordinates.kev_snapshot_date:
        raise ValueError("prepared KEV snapshot date contradicts admitted coordinates")

    return RepresentativeThreatEvidencePreparationSummary(
        schema_version=1,
        cve_id=coordinates.cve_id,
        bundle_sha256=bundle_sha256,
        locator_manifest_sha256=locator_manifest_sha256,
        ghsa_occurrence_count=len(evidence.ghsa_vulnerabilities),
        nvd_record_count=len(evidence.nvd_records),
        kev_snapshot_date=evidence.kev_snapshot.snapshot_date,
        kev_catalog_version=evidence.kev_snapshot.catalog_version,
        kev_sha256=evidence.kev_snapshot.sha256,
        kev_record_count=evidence.kev_snapshot.record_count,
        epss_snapshot_date=epss_snapshot_date,
        epss_model_version=epss_model_version,
        epss_sha256=epss_sha256,
        epss_row_count=epss_row_count,
    )


__all__ = [
    "RepresentativeThreatEvidencePreparationSummary",
    "summarize_representative_threat_evidence_preparation",
]
