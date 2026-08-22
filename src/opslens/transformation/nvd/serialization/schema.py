# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""Explicit PyArrow schema for versioned NVD Silver records."""

import pyarrow as pa

NVD_CVE_VERSIONS_SCHEMA_NAME = "nvd_cve_versions"
NVD_CVE_VERSIONS_SCHEMA_VERSION = 1

_LOCALIZED_TEXT_TYPE = pa.struct(
    [
        pa.field("lang", pa.string(), nullable=False),
        pa.field("value", pa.string(), nullable=False),
    ]
)

_CVE_TAG_TYPE = pa.struct(
    [
        pa.field(
            "source_identifier",
            pa.string(),
            nullable=True,
        ),
        pa.field(
            "tags",
            pa.list_(pa.string()),
            nullable=False,
        ),
    ]
)

_WEAKNESS_TYPE = pa.struct(
    [
        pa.field("source", pa.string(), nullable=False),
        pa.field("type", pa.string(), nullable=False),
        pa.field(
            "descriptions",
            pa.list_(_LOCALIZED_TEXT_TYPE),
            nullable=False,
        ),
    ]
)

_REFERENCE_TYPE = pa.struct(
    [
        pa.field("url", pa.string(), nullable=False),
        pa.field("source", pa.string(), nullable=True),
        pa.field(
            "tags",
            pa.list_(pa.string()),
            nullable=False,
        ),
    ]
)

_CVSS_METRIC_TYPE = pa.struct(
    [
        pa.field("family", pa.string(), nullable=False),
        pa.field("version", pa.string(), nullable=False),
        pa.field("source", pa.string(), nullable=False),
        pa.field("type", pa.string(), nullable=False),
        pa.field(
            "vector_string",
            pa.string(),
            nullable=False,
        ),
        pa.field(
            "base_score",
            pa.float64(),
            nullable=False,
        ),
        pa.field(
            "base_severity",
            pa.string(),
            nullable=True,
        ),
        pa.field(
            "exploitability_score",
            pa.float64(),
            nullable=True,
        ),
        pa.field(
            "impact_score",
            pa.float64(),
            nullable=True,
        ),
        pa.field(
            "metric_json",
            pa.string(),
            nullable=False,
        ),
    ]
)

_UTC_TIMESTAMP = pa.timestamp(
    "us",
    tz="UTC",
)

NVD_CVE_VERSIONS_SCHEMA_V1 = pa.schema(
    [
        pa.field(
            "schema_version",
            pa.int16(),
            nullable=False,
        ),
        pa.field(
            "cve_id",
            pa.string(),
            nullable=False,
        ),
        pa.field(
            "observed_cve_version_id",
            pa.string(),
            nullable=False,
        ),
        pa.field(
            "source_cve_sha256",
            pa.string(),
            nullable=False,
        ),
        pa.field(
            "observation_id",
            pa.string(),
            nullable=False,
        ),
        pa.field(
            "source_kind",
            pa.string(),
            nullable=False,
        ),
        pa.field(
            "source_batch_id",
            pa.string(),
            nullable=False,
        ),
        pa.field(
            "source_observed_at",
            _UTC_TIMESTAMP,
            nullable=False,
        ),
        pa.field(
            "bronze_manifest_key",
            pa.string(),
            nullable=False,
        ),
        pa.field(
            "bronze_manifest_version_id",
            pa.string(),
            nullable=False,
        ),
        pa.field(
            "bronze_manifest_sha256",
            pa.string(),
            nullable=False,
        ),
        pa.field(
            "bronze_object_key",
            pa.string(),
            nullable=False,
        ),
        pa.field(
            "bronze_object_version_id",
            pa.string(),
            nullable=False,
        ),
        pa.field(
            "bronze_object_sha256",
            pa.string(),
            nullable=False,
        ),
        pa.field(
            "bronze_record_index",
            pa.int64(),
            nullable=False,
        ),
        pa.field(
            "bootstrap_feed_year",
            pa.int16(),
            nullable=True,
        ),
        pa.field(
            "bootstrap_feed_revision",
            pa.string(),
            nullable=True,
        ),
        pa.field(
            "incremental_update_id",
            pa.string(),
            nullable=True,
        ),
        pa.field(
            "incremental_page_start",
            pa.int64(),
            nullable=True,
        ),
        pa.field(
            "source_identifier",
            pa.string(),
            nullable=False,
        ),
        pa.field(
            "published_at",
            _UTC_TIMESTAMP,
            nullable=False,
        ),
        pa.field(
            "last_modified_at",
            _UTC_TIMESTAMP,
            nullable=False,
        ),
        pa.field(
            "vuln_status",
            pa.string(),
            nullable=False,
        ),
        pa.field(
            "is_rejected",
            pa.bool_(),
            nullable=False,
        ),
        pa.field(
            "descriptions",
            pa.list_(_LOCALIZED_TEXT_TYPE),
            nullable=False,
        ),
        pa.field(
            "cve_tags",
            pa.list_(_CVE_TAG_TYPE),
            nullable=False,
        ),
        pa.field(
            "weaknesses",
            pa.list_(_WEAKNESS_TYPE),
            nullable=False,
        ),
        pa.field(
            "cwe_ids",
            pa.list_(pa.string()),
            nullable=False,
        ),
        pa.field(
            "references",
            pa.list_(_REFERENCE_TYPE),
            nullable=False,
        ),
        pa.field(
            "cvss_metrics",
            pa.list_(_CVSS_METRIC_TYPE),
            nullable=False,
        ),
        pa.field(
            "configurations_json",
            pa.string(),
            nullable=False,
        ),
        pa.field(
            "configuration_count",
            pa.int32(),
            nullable=False,
        ),
    ],
    metadata={
        b"opslens.dataset": b"nvd_cve_versions",
        b"opslens.schema_version": b"1",
        b"opslens.canonical_json_version": b"1",
    },
)
