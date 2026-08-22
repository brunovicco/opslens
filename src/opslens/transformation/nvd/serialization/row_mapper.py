"""Deterministic domain-to-row mapping for NVD Silver schema v1."""

from opslens.transformation.nvd.serialization.models import (
    NvdSilverRecordV1,
)
from opslens.transformation.nvd.serialization.schema import (
    NVD_CVE_VERSIONS_SCHEMA_VERSION,
)


def map_nvd_silver_record_v1(
    record: NvdSilverRecordV1,
) -> dict[str, object]:
    """Map one normalized observed CVE to the explicit Silver v1 row."""
    core = record.core
    collections = record.collections
    provenance = record.provenance
    observed = core.observed_version

    descriptions = [
        {
            "lang": item.lang,
            "value": item.value,
        }
        for item in collections.descriptions
    ]

    cve_tags = [
        {
            "source_identifier": item.source_identifier,
            "tags": list(item.tags),
        }
        for item in collections.cve_tags
    ]

    weaknesses = [
        {
            "source": item.source,
            "type": item.type,
            "descriptions": [
                {
                    "lang": description.lang,
                    "value": description.value,
                }
                for description in item.descriptions
            ],
        }
        for item in collections.weaknesses
    ]

    references = [
        {
            "url": item.url,
            "source": item.source,
            "tags": list(item.tags),
        }
        for item in collections.references
    ]

    cvss_metrics = [
        {
            "family": metric.family.value,
            "version": metric.version,
            "source": metric.source,
            "type": metric.metric_type.value,
            "vector_string": metric.vector_string,
            "base_score": metric.base_score,
            "base_severity": metric.base_severity,
            "exploitability_score": metric.exploitability_score,
            "impact_score": metric.impact_score,
            "metric_json": metric.metric_json,
        }
        for metric in record.cvss.metrics
    ]

    return {
        "schema_version": NVD_CVE_VERSIONS_SCHEMA_VERSION,
        "cve_id": observed.cve_id,
        "observed_cve_version_id": observed.observed_cve_version_id,
        "source_cve_sha256": observed.source_cve_sha256,
        "observation_id": provenance.observation_id,
        "source_kind": provenance.source_kind.value,
        "source_batch_id": provenance.source_batch_id,
        "source_observed_at": provenance.source_observed_at,
        "bronze_manifest_key": provenance.bronze_manifest_key,
        "bronze_manifest_version_id": (provenance.bronze_manifest_version_id),
        "bronze_manifest_sha256": provenance.bronze_manifest_sha256,
        "bronze_object_key": provenance.bronze_object_key,
        "bronze_object_version_id": provenance.bronze_object_version_id,
        "bronze_object_sha256": provenance.bronze_object_sha256,
        "bronze_record_index": provenance.bronze_record_index,
        "bootstrap_feed_year": provenance.bootstrap_feed_year,
        "bootstrap_feed_revision": provenance.bootstrap_feed_revision,
        "incremental_update_id": provenance.incremental_update_id,
        "incremental_page_start": provenance.incremental_page_start,
        "source_identifier": core.source_identifier,
        "published_at": core.published_at,
        "last_modified_at": core.last_modified_at,
        "vuln_status": core.vuln_status.value,
        "is_rejected": core.is_rejected,
        "descriptions": descriptions,
        "cve_tags": cve_tags,
        "weaknesses": weaknesses,
        "cwe_ids": list(collections.cwe_ids),
        "references": references,
        "cvss_metrics": cvss_metrics,
        "configurations_json": (record.configurations.configurations_json),
        "configuration_count": (record.configurations.configuration_count),
    }
