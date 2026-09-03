"""Attach complete-snapshot CISA KEV membership evidence to repository findings."""

from __future__ import annotations

from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.repository_intelligence.domain.kev_enrichment import (
    RepositoryKevEnrichedFinding,
    RepositoryKevEnrichmentEvidence,
    RepositoryKevSnapshotEvidence,
    RepositoryKevState,
)
from opslens.repository_intelligence.domain.nvd_enrichment import (
    RepositoryNvdEnrichedFinding,
    RepositoryNvdEnrichmentEvidence,
)


def enrich_repository_findings_with_kev(
    previous: RepositoryNvdEnrichmentEvidence,
    snapshot: KevCatalogSnapshot,
) -> RepositoryKevEnrichmentEvidence:
    """Evaluate KEV membership from one complete immutable CISA catalog snapshot."""
    kev_snapshot = RepositoryKevSnapshotEvidence(snapshot=snapshot)
    enriched_findings = tuple(
        _enrich_finding(previous_finding, kev_snapshot)
        for previous_finding in previous.enriched_findings
    )
    return RepositoryKevEnrichmentEvidence(
        previous=previous,
        kev_snapshot=kev_snapshot,
        enriched_findings=enriched_findings,
    )


def _enrich_finding(
    previous: RepositoryNvdEnrichedFinding,
    kev_snapshot: RepositoryKevSnapshotEvidence,
) -> RepositoryKevEnrichedFinding:
    """Derive one three-state KEV decision without changing repository applicability."""
    cve_id = previous.alias.github_cve_id
    if cve_id is None:
        return RepositoryKevEnrichedFinding(
            previous=previous,
            kev_snapshot=kev_snapshot,
            state=RepositoryKevState.CVE_UNAVAILABLE,
            kev_record=None,
        )

    record = kev_snapshot.record_for_cve(cve_id)
    if record is None:
        return RepositoryKevEnrichedFinding(
            previous=previous,
            kev_snapshot=kev_snapshot,
            state=RepositoryKevState.ABSENT,
            kev_record=None,
        )

    return RepositoryKevEnrichedFinding(
        previous=previous,
        kev_snapshot=kev_snapshot,
        state=RepositoryKevState.PRESENT,
        kev_record=record,
    )
