"""Unit tests for the PyArrow CISA KEV Silver Parquet writer."""

from datetime import UTC, date, datetime
from io import BytesIO

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from opslens.transformation.kev.adapters.outbound.parquet import (
    PyArrowSilverKevRecordWriter,
)
from opslens.transformation.kev.domain.models import (
    KevRansomwareUse,
    SilverKevRecord,
)


def _record(
    cve: str,
    *,
    snapshot_date: date = date(2026, 8, 17),
    cwes: tuple[str, ...] = ("CWE-244",),
) -> SilverKevRecord:
    """Build one valid normalized KEV record for Parquet tests."""
    retrieved_at = datetime(
        snapshot_date.year,
        snapshot_date.month,
        snapshot_date.day,
        3,
        52,
        3,
        692159,
        tzinfo=UTC,
    )

    return SilverKevRecord(
        cve=cve,
        vendor_project="Cisco",
        product="Secure Firewall",
        vulnerability_name="Cisco Secure Firewall Vulnerability",
        date_added=date(2026, 8, 11),
        short_description="A vulnerability affecting the product.",
        required_action="Apply vendor mitigations.",
        due_date=date(2026, 8, 14),
        known_ransomware_campaign_use=KevRansomwareUse.UNKNOWN,
        notes="https://example.com/advisory",
        cwes=cwes,
        catalog_version="2026.08.14",
        catalog_date_released=datetime(
            2026,
            8,
            14,
            16,
            34,
            49,
            39100,
            tzinfo=UTC,
        ),
        source="cisa-kev",
        source_sha256="a" * 64,
        retrieved_at=retrieved_at,
        snapshot_date=snapshot_date,
    )


def test_writes_valid_parquet_artifact() -> None:
    """Serialize normalized KEV records into readable Parquet."""
    destination = BytesIO()

    result = PyArrowSilverKevRecordWriter().write(
        records=(
            _record("CVE-2026-10001"),
            _record("CVE-2026-10002"),
        ),
        destination=destination,
    )

    table = pq.read_table(BytesIO(destination.getvalue()))

    assert result.row_count == 2
    assert result.size_bytes == len(destination.getvalue())
    assert result.schema_version == 1
    assert table.num_rows == 2


def test_writes_expected_physical_schema() -> None:
    """Persist the exact KEV Silver v1 physical schema."""
    destination = BytesIO()

    PyArrowSilverKevRecordWriter().write(
        records=(_record("CVE-2026-10001"),),
        destination=destination,
    )

    table = pq.read_table(BytesIO(destination.getvalue()))

    assert table.column_names == [
        "cve",
        "vendor_project",
        "product",
        "vulnerability_name",
        "date_added",
        "short_description",
        "required_action",
        "due_date",
        "known_ransomware_campaign_use",
        "notes",
        "cwes",
        "catalog_version",
        "catalog_date_released",
        "source",
        "source_sha256",
        "retrieved_at",
    ]

    assert table.schema.field("cve").type == pa.string()
    assert table.schema.field("date_added").type == pa.date32()
    assert table.schema.field("due_date").type == pa.date32()
    assert table.schema.field("cwes").type == pa.list_(pa.string())
    assert table.schema.field("catalog_date_released").type == pa.timestamp(
        "us",
        tz="UTC",
    )
    assert table.schema.field("retrieved_at").type == pa.timestamp(
        "us",
        tz="UTC",
    )

    assert all(not field.nullable for field in table.schema)
    assert "snapshot_date" not in table.column_names


def test_preserves_normalized_values() -> None:
    """Preserve normalized domain values across Parquet serialization."""
    destination = BytesIO()

    PyArrowSilverKevRecordWriter().write(
        records=(_record("CVE-2026-20349"),),
        destination=destination,
    )

    row = pq.read_table(BytesIO(destination.getvalue())).to_pylist()[0]

    assert row["cve"] == "CVE-2026-20349"
    assert row["vendor_project"] == "Cisco"
    assert row["date_added"] == date(2026, 8, 11)
    assert row["due_date"] == date(2026, 8, 14)
    assert row["known_ransomware_campaign_use"] == "Unknown"
    assert row["cwes"] == ["CWE-244"]
    assert row["catalog_version"] == "2026.08.14"
    assert row["source"] == "cisa-kev"
    assert row["source_sha256"] == "a" * 64


def test_preserves_empty_cwe_array() -> None:
    """Persist an empty CWE collection as an empty list, not null."""
    destination = BytesIO()

    PyArrowSilverKevRecordWriter().write(
        records=(
            _record(
                "CVE-2026-20349",
                cwes=(),
            ),
        ),
        destination=destination,
    )

    row = pq.read_table(BytesIO(destination.getvalue())).to_pylist()[0]

    assert row["cwes"] == []


def test_writes_schema_metadata() -> None:
    """Persist dataset identity and physical schema version metadata."""
    destination = BytesIO()

    PyArrowSilverKevRecordWriter().write(
        records=(_record("CVE-2026-10001"),),
        destination=destination,
    )

    parquet_file = pq.ParquetFile(BytesIO(destination.getvalue()))

    metadata = parquet_file.schema_arrow.metadata

    assert metadata is not None
    assert metadata[b"opslens.dataset"] == b"kev-silver"
    assert metadata[b"opslens.schema_version"] == b"1"


def test_writes_multiple_batches() -> None:
    """Serialize records spanning more than one configured batch."""
    destination = BytesIO()

    result = PyArrowSilverKevRecordWriter(batch_size=2).write(
        records=(
            _record("CVE-2026-10001"),
            _record("CVE-2026-10002"),
            _record("CVE-2026-10003"),
        ),
        destination=destination,
    )

    parquet_file = pq.ParquetFile(BytesIO(destination.getvalue()))

    assert result.row_count == 3
    assert parquet_file.metadata.num_row_groups == 2


def test_rejects_empty_record_stream() -> None:
    """Reject attempts to create an empty KEV Silver artifact."""
    destination = BytesIO()

    with pytest.raises(ValueError, match="at least one record"):
        PyArrowSilverKevRecordWriter().write(
            records=(),
            destination=destination,
        )


def test_rejects_mixed_snapshot_partitions() -> None:
    """Reject records belonging to different snapshot partitions."""
    destination = BytesIO()

    with pytest.raises(
        ValueError,
        match="multiple snapshot dates",
    ):
        PyArrowSilverKevRecordWriter().write(
            records=(
                _record("CVE-2026-10001"),
                _record(
                    "CVE-2026-10002",
                    snapshot_date=date(2026, 8, 18),
                ),
            ),
            destination=destination,
        )


@pytest.mark.parametrize("batch_size", [0, -1])
def test_rejects_invalid_batch_size(batch_size: int) -> None:
    """Reject non-positive KEV Parquet batch sizes."""
    with pytest.raises(ValueError, match="batch size"):
        PyArrowSilverKevRecordWriter(batch_size=batch_size)
