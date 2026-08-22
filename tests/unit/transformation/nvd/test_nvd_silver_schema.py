# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""Tests for the explicit NVD Silver PyArrow schema v1."""

import pyarrow as pa

from opslens.transformation.nvd.serialization.schema import (
    NVD_CVE_VERSIONS_SCHEMA_NAME,
    NVD_CVE_VERSIONS_SCHEMA_V1,
    NVD_CVE_VERSIONS_SCHEMA_VERSION,
)


def test_schema_identity_is_frozen() -> None:
    """Expose a stable dataset and schema-version identity."""
    assert NVD_CVE_VERSIONS_SCHEMA_NAME == "nvd_cve_versions"
    assert NVD_CVE_VERSIONS_SCHEMA_VERSION == 1

    assert NVD_CVE_VERSIONS_SCHEMA_V1.metadata == {
        b"opslens.dataset": b"nvd_cve_versions",
        b"opslens.schema_version": b"1",
        b"opslens.canonical_json_version": b"1",
    }


def test_schema_field_order_is_explicit() -> None:
    """Freeze physical column ordering for deterministic serialization."""
    assert NVD_CVE_VERSIONS_SCHEMA_V1.names == [
        "schema_version",
        "cve_id",
        "observed_cve_version_id",
        "source_cve_sha256",
        "observation_id",
        "source_kind",
        "source_batch_id",
        "source_observed_at",
        "bronze_manifest_key",
        "bronze_manifest_version_id",
        "bronze_manifest_sha256",
        "bronze_object_key",
        "bronze_object_version_id",
        "bronze_object_sha256",
        "bronze_record_index",
        "bootstrap_feed_year",
        "bootstrap_feed_revision",
        "incremental_update_id",
        "incremental_page_start",
        "source_identifier",
        "published_at",
        "last_modified_at",
        "vuln_status",
        "is_rejected",
        "descriptions",
        "cve_tags",
        "weaknesses",
        "cwe_ids",
        "references",
        "cvss_metrics",
        "configurations_json",
        "configuration_count",
    ]


def test_schema_uses_utc_microsecond_timestamps() -> None:
    """Prevent implicit timestamp-unit or timezone drift."""
    expected = pa.timestamp(
        "us",
        tz="UTC",
    )

    for field_name in (
        "source_observed_at",
        "published_at",
        "last_modified_at",
    ):
        assert NVD_CVE_VERSIONS_SCHEMA_V1.field(field_name).type == expected


def test_optional_source_specific_fields_are_nullable() -> None:
    """Permit bootstrap and incremental coordinates in one stable schema."""
    for field_name in (
        "bootstrap_feed_year",
        "bootstrap_feed_revision",
        "incremental_update_id",
        "incremental_page_start",
    ):
        assert NVD_CVE_VERSIONS_SCHEMA_V1.field(field_name).nullable


def test_identity_and_evidence_fields_are_non_nullable() -> None:
    """Keep Silver identity and exact Bronze evidence mandatory."""
    for field_name in (
        "cve_id",
        "observed_cve_version_id",
        "source_cve_sha256",
        "observation_id",
        "bronze_manifest_key",
        "bronze_manifest_version_id",
        "bronze_manifest_sha256",
        "bronze_object_key",
        "bronze_object_version_id",
        "bronze_object_sha256",
        "bronze_record_index",
    ):
        assert not NVD_CVE_VERSIONS_SCHEMA_V1.field(field_name).nullable
