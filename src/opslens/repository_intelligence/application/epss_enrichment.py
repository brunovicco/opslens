"""Attach exact-snapshot EPSS score evidence to repository findings."""

from __future__ import annotations

from opslens.ingestion.epss.domain.history import HistoricalEpssSnapshot
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.repository_intelligence.domain.epss_enrichment import (
    RepositoryEpssEnrichedFinding,
    RepositoryEpssEnrichmentEvidence,
    RepositoryEpssSnapshotEvidence,
    RepositoryEpssState,
)
from opslens.repository_intelligence.domain.kev_enrichment import (
    RepositoryKevEnrichedFinding,
    RepositoryKevEnrichmentEvidence,
)


def enrich_repository_findings_with_epss(
    previous: RepositoryKevEnrichmentEvidence,
    snapshot: EpssSnapshot | HistoricalEpssSnapshot,
) -> RepositoryEpssEnrichmentEvidence:
    """Evaluate EPSS score evidence from one complete exact source snapshot."""
    epss_snapshot = RepositoryEpssSnapshotEvidence(snapshot=snapshot)
    enriched_findings = tuple(
        _enrich_finding(previous_finding, epss_snapshot)
        for previous_finding in previous.enriched_findings
    )
    return RepositoryEpssEnrichmentEvidence(
        previous=previous,
        epss_snapshot=epss_snapshot,
        enriched_findings=enriched_findings,
    )


def _enrich_finding(
    previous: RepositoryKevEnrichedFinding,
    epss_snapshot: RepositoryEpssSnapshotEvidence,
) -> RepositoryEpssEnrichedFinding:
    """Derive one three-state EPSS observation without applying risk policy."""
    cve_id = previous.evaluated_cve_id
    if cve_id is None:
        return RepositoryEpssEnrichedFinding(
            previous=previous,
            epss_snapshot=epss_snapshot,
            state=RepositoryEpssState.CVE_UNAVAILABLE,
            epss_record=None,
        )

    record = epss_snapshot.record_for_cve(cve_id)
    if record is None:
        return RepositoryEpssEnrichedFinding(
            previous=previous,
            epss_snapshot=epss_snapshot,
            state=RepositoryEpssState.SCORE_ABSENT,
            epss_record=None,
        )

    return RepositoryEpssEnrichedFinding(
        previous=previous,
        epss_snapshot=epss_snapshot,
        state=RepositoryEpssState.SCORE_PRESENT,
        epss_record=record,
    )
