"""Unit tests for the EPSS Silver physical schema."""

from opslens.transformation.epss.application.schema import (
    EPSS_SILVER_DATA_COLUMNS,
    EPSS_SILVER_PARTITION_COLUMNS,
    EPSS_SILVER_SCHEMA_VERSION,
    SilverPhysicalType,
)


def test_epss_silver_schema_version_is_v2() -> None:
    """Expose the explicit legacy-compatible Silver schema version."""
    assert EPSS_SILVER_SCHEMA_VERSION == 2


def test_epss_silver_columns_have_stable_order() -> None:
    """Keep the physical Silver column order deterministic."""
    assert tuple(column.name for column in EPSS_SILVER_DATA_COLUMNS) == (
        "cve",
        "epss",
        "percentile",
        "model_version",
        "score_timestamp",
        "source",
        "source_sha256",
    )


def test_epss_silver_columns_have_expected_physical_types() -> None:
    """Define storage-neutral types for every physical Silver field."""
    assert tuple(column.physical_type for column in EPSS_SILVER_DATA_COLUMNS) == (
        SilverPhysicalType.STRING,
        SilverPhysicalType.FLOAT64,
        SilverPhysicalType.FLOAT64,
        SilverPhysicalType.STRING,
        SilverPhysicalType.TIMESTAMP_UTC_MICROS,
        SilverPhysicalType.STRING,
        SilverPhysicalType.STRING,
    )


def test_epss_silver_v2_nullability_matches_legacy_source_contract() -> None:
    """Permit null only where EPSS v1 physically lacks source evidence."""
    assert tuple(column.nullable for column in EPSS_SILVER_DATA_COLUMNS) == (
        False,
        False,
        True,
        True,
        True,
        False,
        False,
    )


def test_snapshot_date_is_partition_only() -> None:
    """Keep snapshot_date as a partition key instead of duplicating it in Parquet."""
    data_column_names = {column.name for column in EPSS_SILVER_DATA_COLUMNS}

    assert EPSS_SILVER_PARTITION_COLUMNS == ("snapshot_date",)
    assert "snapshot_date" not in data_column_names
