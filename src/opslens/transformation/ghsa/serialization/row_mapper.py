"""Deterministic domain-to-row mapping for GHSA Silver schema v1."""

from opslens.transformation.ghsa.serialization.models import (
    GhsaSilverRecordV1,
)
from opslens.transformation.ghsa.serialization.schema import (
    GHSA_ADVISORY_VERSIONS_SCHEMA_VERSION,
)


def map_ghsa_silver_record_v1(record: GhsaSilverRecordV1) -> dict[str, object]:
    """Map one normalized observed advisory version to the explicit Silver v1 row."""
    core = record.core
    observed = core.observed_version
    collections = record.collections

    identifiers = [
        {
            "type": item.identifier_type,
            "value": item.value,
        }
        for item in collections.identifiers
    ]

    cwes = [
        {
            "cwe_id": item.cwe_id,
            "name": item.name,
        }
        for item in collections.cwes
    ]

    cvss_metrics = [
        {
            "family": metric.family.value,
            "vector_string": metric.vector_string,
            "score": metric.score,
        }
        for metric in collections.cvss_severities.metrics
    ]

    vulnerabilities = [
        {
            "source_index": entry.source_index,
            "vulnerability_entry_id": entry.vulnerability_entry_id,
            "source_entry_sha256": entry.source_entry_sha256,
            "ecosystem": entry.package.ecosystem.value,
            "package_name": entry.package.name,
            "vulnerable_version_range": entry.vulnerable_version_range,
            "first_patched_version": entry.first_patched_version,
            "vulnerable_functions": list(entry.vulnerable_functions),
            "source_entry_json": entry.source_entry_json,
        }
        for entry in record.vulnerabilities.entries
    ]

    return {
        "schema_version": GHSA_ADVISORY_VERSIONS_SCHEMA_VERSION,
        "ghsa_id": observed.ghsa_id,
        "observed_advisory_version_id": observed.observed_advisory_version_id,
        "source_advisory_sha256": observed.source_advisory_sha256,
        "cve_id": core.cve_id,
        "advisory_type": core.advisory_type.value,
        "severity": core.severity.value,
        "url": core.url,
        "html_url": core.html_url,
        "repository_advisory_url": core.repository_advisory_url,
        "source_code_location": core.source_code_location,
        "summary": core.summary,
        "description": core.description,
        "published_at": core.published_at,
        "updated_at": core.updated_at,
        "github_reviewed_at": core.github_reviewed_at,
        "nvd_published_at": core.nvd_published_at,
        "withdrawn_at": core.withdrawn_at,
        "is_withdrawn": core.is_withdrawn,
        "identifiers": identifiers,
        "references": list(collections.references),
        "cwes": cwes,
        "cvss_metrics": cvss_metrics,
        "cvss_severities_json": collections.cvss_severities.canonical_json,
        "vulnerability_entry_count": len(record.vulnerabilities.entries),
        "vulnerabilities": vulnerabilities,
    }
