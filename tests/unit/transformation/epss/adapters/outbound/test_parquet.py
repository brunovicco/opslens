"""Unit tests for the PyArrow EPSS Silver Parquet writer."""

from datetime import UTC, date, datetime
from io import BytesIO

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from opslens.transformation.epss.adapters.outbound.parquet import (
    PyArrowSilverEpssRecordWriter,
)
from opslens.transformation.epss.domain.models import SilverEpssRecord


def _record(
    cve: str,
    *,
    epss: float = 0.812345,
    percentile: float = 0.987654,
    snapshot_date: date = date(2026, 8, 15),
) -> SilverEpssRecord:
    """Build a valid normalized modern EPSS record for Parquet tests."""
    score_timestamp = datetime(
        snapshot_date.year,
        snapshot_date.month,
        snapshot_date.day,
        12,
        2,
        44,
        tzinfo=UTC,
    )

    return SilverEpssRecord(
        cve=cve,
        epss=epss,
        percentile=percentile,
        model_version="v2026.06.15",
        score_timestamp=score_timestamp,
        source="first-epss",
        source_sha256="a" * 64,
        snapshot_date=snapshot_date,
    )


def _legacy_record(cve: str) -> SilverEpssRecord:
    """Build a truthful EPSS v1 record with unavailable fields left null."""
    return SilverEpssRecord(
        cve=cve,
        epss=0.65117,
        percentile=None,
        model_version=None,
        score_timestamp=None,
        source="first-epss",
        source_sha256="b" * 64,
        snapshot_date=date(2021, 4, 14),
    )


def test_writes_valid_parquet_artifact() -> None:
    """Serialize normalized records into a readable Parquet artifact."""
    destination = BytesIO()

    writer = PyArrowSilverEpssRecordWriter()

    result = writer.write(
        records=(
            _record("CVE-2026-12345"),
            _record("CVE-2026-67890"),
        ),
        destination=destination,
    )

    table = pq.read_table(BytesIO(destination.getvalue()))

    assert result.row_count == 2
    assert result.size_bytes == len(destination.getvalue())
    assert result.schema_version == 2
    assert table.num_rows == 2


def test_writes_expected_physical_schema() -> None:
    """Persist the exact EPSS Silver v2 physical column contract."""
    destination = BytesIO()

    PyArrowSilverEpssRecordWriter().write(
        records=(_record("CVE-2026-12345"),),
        destination=destination,
    )

    table = pq.read_table(BytesIO(destination.getvalue()))

    assert table.column_names == [
        "cve",
        "epss",
        "percentile",
        "model_version",
        "score_timestamp",
        "source",
        "source_sha256",
    ]

    assert table.schema.field("cve").type == pa.string()
    assert table.schema.field("epss").type == pa.float64()
    assert table.schema.field("percentile").type == pa.float64()
    assert table.schema.field("score_timestamp").type == pa.timestamp("us", tz="UTC")
    assert table.schema.field("cve").nullable is False
    assert table.schema.field("epss").nullable is False
    assert table.schema.field("percentile").nullable is True
    assert table.schema.field("model_version").nullable is True
    assert table.schema.field("score_timestamp").nullable is True
    assert table.schema.field("source").nullable is False
    assert table.schema.field("source_sha256").nullable is False
    assert "snapshot_date" not in table.column_names


def test_preserves_normalized_values() -> None:
    """Preserve domain values through the Parquet serialization boundary."""
    destination = BytesIO()

    PyArrowSilverEpssRecordWriter().write(
        records=(
            _record(
                "CVE-2026-12345",
                epss=0.812345,
                percentile=0.987654,
            ),
        ),
        destination=destination,
    )

    table = pq.read_table(BytesIO(destination.getvalue()))
    row = table.to_pylist()[0]

    assert row["cve"] == "CVE-2026-12345"
    assert row["epss"] == pytest.approx(0.812345)
    assert row["percentile"] == pytest.approx(0.987654)
    assert row["model_version"] == "v2026.06.15"
    assert row["source"] == "first-epss"
    assert row["source_sha256"] == "a" * 64


def test_preserves_legacy_unavailable_fields_as_null() -> None:
    """Serialize EPSS v1 unavailable evidence as null instead of fabrication."""
    destination = BytesIO()

    PyArrowSilverEpssRecordWriter().write(
        records=(_legacy_record("CVE-2020-5902"),),
        destination=destination,
    )

    table = pq.read_table(BytesIO(destination.getvalue()))
    row = table.to_pylist()[0]

    assert row["cve"] == "CVE-2020-5902"
    assert row["epss"] == pytest.approx(0.65117)
    assert row["percentile"] is None
    assert row["model_version"] is None
    assert row["score_timestamp"] is None
    assert row["source"] == "first-epss"
    assert row["source_sha256"] == "b" * 64


def test_writes_schema_metadata() -> None:
    """Persist dataset identity and schema version as Parquet metadata."""
    destination = BytesIO()

    PyArrowSilverEpssRecordWriter().write(
        records=(_record("CVE-2026-12345"),),
        destination=destination,
    )

    parquet_file = pq.ParquetFile(BytesIO(destination.getvalue()))
    metadata = parquet_file.schema_arrow.metadata

    assert metadata is not None
    assert metadata[b"opslens.dataset"] == b"epss-silver"
    assert metadata[b"opslens.schema_version"] == b"2"


def test_writes_multiple_batches() -> None:
    """Serialize more records than one configured in-memory batch."""
    destination = BytesIO()

    writer = PyArrowSilverEpssRecordWriter(batch_size=2)

    result = writer.write(
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
    """Reject attempts to create a Silver artifact without records."""
    destination = BytesIO()

    with pytest.raises(ValueError, match="at least one record"):
        PyArrowSilverEpssRecordWriter().write(
            records=(),
            destination=destination,
        )


def test_rejects_mixed_snapshot_partitions() -> None:
    """Reject one Parquet artifact containing multiple snapshot partitions."""
    destination = BytesIO()

    with pytest.raises(ValueError, match="multiple snapshot dates"):
        PyArrowSilverEpssRecordWriter().write(
            records=(
                _record("CVE-2026-12345"),
                _record(
                    "CVE-2026-67890",
                    snapshot_date=date(2026, 8, 16),
                ),
            ),
            destination=destination,
        )


@pytest.mark.parametrize("batch_size", [0, -1])
def test_rejects_invalid_batch_size(batch_size: int) -> None:
    """Reject non-positive Parquet batch sizes."""
    with pytest.raises(ValueError, match="batch size"):
        PyArrowSilverEpssRecordWriter(batch_size=batch_size)
