# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""Explicit PyArrow schema for versioned GHSA Silver records."""

import pyarrow as pa

GHSA_ADVISORY_VERSIONS_SCHEMA_NAME = "ghsa_advisory_versions"
GHSA_ADVISORY_VERSIONS_SCHEMA_VERSION = 1

_IDENTIFIER_TYPE = pa.struct(
    [
        pa.field("type", pa.string(), nullable=False),
        pa.field("value", pa.string(), nullable=False),
    ]
)

_CWE_TYPE = pa.struct(
    [
        pa.field("cwe_id", pa.string(), nullable=False),
        pa.field("name", pa.string(), nullable=False),
    ]
)

_CVSS_METRIC_TYPE = pa.struct(
    [
        pa.field("family", pa.string(), nullable=False),
        pa.field("vector_string", pa.string(), nullable=False),
        pa.field("score", pa.float64(), nullable=False),
    ]
)

_VULNERABILITY_TYPE = pa.struct(
    [
        pa.field("source_index", pa.int32(), nullable=False),
        pa.field("vulnerability_entry_id", pa.string(), nullable=False),
        pa.field("source_entry_sha256", pa.string(), nullable=False),
        pa.field("ecosystem", pa.string(), nullable=False),
        pa.field("package_name", pa.string(), nullable=False),
        pa.field("vulnerable_version_range", pa.string(), nullable=False),
        pa.field("first_patched_version", pa.string(), nullable=True),
        pa.field("vulnerable_functions", pa.list_(pa.string()), nullable=False),
        pa.field("source_entry_json", pa.string(), nullable=False),
    ]
)

_UTC_TIMESTAMP = pa.timestamp("us", tz="UTC")

GHSA_ADVISORY_VERSIONS_SCHEMA_V1 = pa.schema(
    [
        pa.field("schema_version", pa.int16(), nullable=False),
        pa.field("ghsa_id", pa.string(), nullable=False),
        pa.field("observed_advisory_version_id", pa.string(), nullable=False),
        pa.field("source_advisory_sha256", pa.string(), nullable=False),
        pa.field("cve_id", pa.string(), nullable=True),
        pa.field("advisory_type", pa.string(), nullable=False),
        pa.field("severity", pa.string(), nullable=False),
        pa.field("url", pa.string(), nullable=False),
        pa.field("html_url", pa.string(), nullable=False),
        pa.field("repository_advisory_url", pa.string(), nullable=True),
        pa.field("source_code_location", pa.string(), nullable=True),
        pa.field("summary", pa.string(), nullable=False),
        pa.field("description", pa.string(), nullable=False),
        pa.field("published_at", _UTC_TIMESTAMP, nullable=False),
        pa.field("updated_at", _UTC_TIMESTAMP, nullable=False),
        pa.field("github_reviewed_at", _UTC_TIMESTAMP, nullable=True),
        pa.field("nvd_published_at", _UTC_TIMESTAMP, nullable=True),
        pa.field("withdrawn_at", _UTC_TIMESTAMP, nullable=True),
        pa.field("is_withdrawn", pa.bool_(), nullable=False),
        pa.field("identifiers", pa.list_(_IDENTIFIER_TYPE), nullable=False),
        pa.field("references", pa.list_(pa.string()), nullable=False),
        pa.field("cwes", pa.list_(_CWE_TYPE), nullable=False),
        pa.field("cvss_metrics", pa.list_(_CVSS_METRIC_TYPE), nullable=False),
        pa.field("cvss_severities_json", pa.string(), nullable=False),
        pa.field("vulnerability_entry_count", pa.int32(), nullable=False),
        pa.field("vulnerabilities", pa.list_(_VULNERABILITY_TYPE), nullable=False),
    ],
    metadata={
        b"opslens.dataset": b"ghsa_advisory_versions",
        b"opslens.schema_version": b"1",
        b"opslens.canonical_json_version": b"1",
    },
)
