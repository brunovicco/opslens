# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""Tests for the explicit GHSA Silver PyArrow schema v1."""

import pyarrow as pa

from opslens.transformation.ghsa.serialization.schema import (
    GHSA_ADVISORY_VERSIONS_SCHEMA_NAME,
    GHSA_ADVISORY_VERSIONS_SCHEMA_V1,
    GHSA_ADVISORY_VERSIONS_SCHEMA_VERSION,
)


def test_schema_identity_and_metadata_are_frozen() -> None:
    """Expose one stable dataset and schema-version identity."""
    assert GHSA_ADVISORY_VERSIONS_SCHEMA_NAME == "ghsa_advisory_versions"
    assert GHSA_ADVISORY_VERSIONS_SCHEMA_VERSION == 1
    assert GHSA_ADVISORY_VERSIONS_SCHEMA_V1.metadata == {
        b"opslens.dataset": b"ghsa_advisory_versions",
        b"opslens.schema_version": b"1",
        b"opslens.canonical_json_version": b"1",
    }


def test_schema_field_order_is_explicit() -> None:
    """Freeze physical column ordering for deterministic serialization."""
    assert GHSA_ADVISORY_VERSIONS_SCHEMA_V1.names == [
        "schema_version",
        "ghsa_id",
        "observed_advisory_version_id",
        "source_advisory_sha256",
        "cve_id",
        "advisory_type",
        "severity",
        "url",
        "html_url",
        "repository_advisory_url",
        "source_code_location",
        "summary",
        "description",
        "published_at",
        "updated_at",
        "github_reviewed_at",
        "nvd_published_at",
        "withdrawn_at",
        "is_withdrawn",
        "identifiers",
        "references",
        "cwes",
        "cvss_metrics",
        "cvss_severities_json",
        "vulnerability_entry_count",
        "vulnerabilities",
    ]


def test_schema_uses_nested_lists_for_one_to_many_evidence() -> None:
    """Keep package evidence nested instead of duplicating advisory-level rows."""
    identifiers = GHSA_ADVISORY_VERSIONS_SCHEMA_V1.field("identifiers").type
    vulnerabilities = GHSA_ADVISORY_VERSIONS_SCHEMA_V1.field("vulnerabilities").type

    assert pa.types.is_list(identifiers)
    assert pa.types.is_struct(identifiers.value_type)
    assert pa.types.is_list(vulnerabilities)
    assert pa.types.is_struct(vulnerabilities.value_type)


def test_schema_uses_utc_microsecond_timestamps() -> None:
    """Prevent implicit timestamp-unit or timezone drift."""
    expected = pa.timestamp("us", tz="UTC")

    for field_name in (
        "published_at",
        "updated_at",
        "github_reviewed_at",
        "nvd_published_at",
        "withdrawn_at",
    ):
        assert GHSA_ADVISORY_VERSIONS_SCHEMA_V1.field(field_name).type == expected


def test_nullable_source_fields_remain_nullable() -> None:
    """Preserve source nullability instead of inventing placeholder values."""
    for field_name in (
        "cve_id",
        "repository_advisory_url",
        "source_code_location",
        "github_reviewed_at",
        "nvd_published_at",
        "withdrawn_at",
    ):
        assert GHSA_ADVISORY_VERSIONS_SCHEMA_V1.field(field_name).nullable
