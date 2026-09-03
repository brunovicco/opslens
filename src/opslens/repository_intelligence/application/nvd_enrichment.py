"""Enrich affected repository findings with exact CVE/NVD/CVSS evidence."""

from __future__ import annotations

from collections.abc import Iterable

from opslens.correlation.adapters.cve_alias import reconcile_github_cve_with_nvd
from opslens.correlation.adapters.ghsa import GhsaPyPIVulnerabilityEvidence
from opslens.repository_intelligence.domain.errors import (
    InvalidRepositoryNvdEnrichmentError,
    RepositoryNvdEnrichmentLimitError,
)
from opslens.repository_intelligence.domain.nvd_enrichment import (
    MAX_NVD_ENRICHMENT_RECORDS,
    RepositoryNvdEnrichedFinding,
    RepositoryNvdEnrichmentEvidence,
    derive_repository_nvd_cvss_evidence,
)
from opslens.repository_intelligence.domain.vulnerability_findings import (
    MAX_GHSA_VULNERABILITY_OCCURRENCES,
    RepositoryPyPIVulnerabilityFinding,
    RepositoryVulnerabilityScanEvidence,
)
from opslens.transformation.nvd.domain.models import NvdCveCoreRecord


def enrich_repository_findings_with_nvd(
    scan: RepositoryVulnerabilityScanEvidence,
    ghsa_vulnerabilities: Iterable[GhsaPyPIVulnerabilityEvidence],
    nvd_records: Iterable[NvdCveCoreRecord],
) -> RepositoryNvdEnrichmentEvidence:
    """Attach source-preserving NVD/CVSS evidence without changing affected truth."""
    ghsa_by_occurrence, ghsa_count = _index_ghsa_occurrences(ghsa_vulnerabilities)
    nvd_by_cve, nvd_count = _index_nvd_records(nvd_records)

    enriched_findings: list[RepositoryNvdEnrichedFinding] = []
    for finding in scan.findings:
        assessment = finding.assessment
        occurrence_key = (
            assessment.observed_advisory_version_id,
            assessment.vulnerability_entry_id,
        )
        source = ghsa_by_occurrence.get(occurrence_key)
        if source is None:
            raise InvalidRepositoryNvdEnrichmentError(
                "Affected repository finding is missing its exact GHSA source occurrence."
            )
        _validate_finding_source_binding(finding, source)

        nvd = (
            nvd_by_cve.get(source.github_cve_id)
            if source.github_cve_id is not None
            else None
        )
        alias = reconcile_github_cve_with_nvd(source, nvd=nvd)
        nvd_cvss = (
            derive_repository_nvd_cvss_evidence(nvd)
            if nvd is not None
            else None
        )
        enriched_findings.append(
            RepositoryNvdEnrichedFinding(
                finding=finding,
                alias=alias,
                nvd_cvss=nvd_cvss,
            )
        )

    return RepositoryNvdEnrichmentEvidence(
        scan=scan,
        supplied_ghsa_rehydration_count=ghsa_count,
        supplied_nvd_record_count=nvd_count,
        enriched_findings=tuple(enriched_findings),
    )


def _index_ghsa_occurrences(
    sources: Iterable[GhsaPyPIVulnerabilityEvidence],
) -> tuple[
    dict[tuple[str, str], GhsaPyPIVulnerabilityEvidence],
    int,
]:
    """Index bounded exact GHSA occurrences for finding-source rebinding."""
    indexed: dict[tuple[str, str], GhsaPyPIVulnerabilityEvidence] = {}
    count = 0

    for source in sources:
        count += 1
        if count > MAX_GHSA_VULNERABILITY_OCCURRENCES:
            raise RepositoryNvdEnrichmentLimitError(
                "Repository NVD enrichment exceeds the GHSA rehydration bound."
            )

        key = (
            source.observed_advisory_version_id,
            source.vulnerability_entry_id,
        )
        if key in indexed:
            raise InvalidRepositoryNvdEnrichmentError(
                "Repository NVD enrichment contains duplicate GHSA occurrence evidence."
            )
        indexed[key] = source

    return indexed, count


def _index_nvd_records(
    records: Iterable[NvdCveCoreRecord],
) -> tuple[dict[str, NvdCveCoreRecord], int]:
    """Index at most one exact NVD observation per CVE without hidden latest selection."""
    indexed: dict[str, NvdCveCoreRecord] = {}
    count = 0

    for record in records:
        count += 1
        if count > MAX_NVD_ENRICHMENT_RECORDS:
            raise RepositoryNvdEnrichmentLimitError(
                "Repository NVD enrichment exceeds the NVD observation bound."
            )

        cve_id = record.observed_version.cve_id
        if cve_id in indexed:
            raise InvalidRepositoryNvdEnrichmentError(
                "Repository NVD enrichment cannot choose between multiple NVD "
                "observations for one CVE."
            )
        indexed[cve_id] = record

    return indexed, count


def _validate_finding_source_binding(
    finding: RepositoryPyPIVulnerabilityFinding,
    source: GhsaPyPIVulnerabilityEvidence,
) -> None:
    """Require rehydrated GHSA evidence to be the exact occurrence used by Gate 4.7."""
    assessment = finding.assessment
    expected_pairs = (
        (source.ghsa_id, assessment.ghsa_id, "GHSA id"),
        (
            source.observed_advisory_version_id,
            assessment.observed_advisory_version_id,
            "GHSA observed advisory version",
        ),
        (
            source.source_advisory_sha256,
            assessment.source_advisory_sha256,
            "GHSA advisory source hash",
        ),
        (
            source.vulnerability_entry_id,
            assessment.vulnerability_entry_id,
            "GHSA vulnerability entry",
        ),
        (source.source_index, assessment.source_index, "GHSA source index"),
        (
            source.source_entry_sha256,
            assessment.source_entry_sha256,
            "GHSA entry source hash",
        ),
        (
            source.ecosystem_original,
            assessment.ghsa_ecosystem_original,
            "GHSA ecosystem",
        ),
        (
            source.package_name_original,
            assessment.ghsa_package_name_original,
            "GHSA package name",
        ),
        (
            source.vulnerable_range_original,
            assessment.vulnerable_range_original,
            "GHSA vulnerable range",
        ),
        (
            source.first_patched_version_original,
            assessment.first_patched_version_original,
            "GHSA first patched version",
        ),
    )
    for observed, expected, field_name in expected_pairs:
        if observed != expected:
            raise InvalidRepositoryNvdEnrichmentError(
                f"Repository finding cannot rebind to a different {field_name}."
            )
