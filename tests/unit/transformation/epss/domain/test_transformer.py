"""Unit tests for the EPSS Bronze-to-Silver transformer."""

import gzip
import hashlib
from datetime import UTC, datetime

import pytest

from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.transformation.epss.domain.errors import InvalidEpssSilverSourceError
from opslens.transformation.epss.domain.transformer import EpssSilverTransformer


def _build_snapshot(
    *,
    rows: tuple[str, ...] = (
        "CVE-2026-12345,0.812345,0.987654",
        "CVE-2026-67890,0.123456,0.456789",
    ),
    header: str = "cve,epss,percentile",
    row_count: int | None = None,
) -> EpssSnapshot:
    """Build an in-memory validated-style EPSS snapshot for transformation tests."""
    metadata = "#model_version:v2026.06.15,score_date:2026-08-15T12:02:44Z"

    content = "\n".join(
        (
            metadata,
            header,
            *rows,
            "",
        )
    ).encode("utf-8")

    payload = gzip.compress(content)

    return EpssSnapshot(
        raw_bytes=payload,
        model_version="v2026.06.15",
        score_timestamp=datetime(2026, 8, 15, 12, 2, 44, tzinfo=UTC),
        sha256=hashlib.sha256(payload).hexdigest(),
        row_count=row_count if row_count is not None else len(rows),
    )


def test_transforms_epss_rows_into_normalized_records() -> None:
    """Transform valid Bronze rows and propagate source provenance."""
    snapshot = _build_snapshot()
    transformer = EpssSilverTransformer()

    records = list(transformer.iter_records(snapshot))

    assert len(records) == 2

    first = records[0]

    assert first.cve == "CVE-2026-12345"
    assert first.epss == 0.812345
    assert first.percentile == 0.987654
    assert first.model_version == snapshot.model_version
    assert first.score_timestamp == snapshot.score_timestamp
    assert first.snapshot_date == snapshot.score_timestamp.date()
    assert first.source == "first-epss"
    assert first.source_sha256 == snapshot.sha256


def test_preserves_source_row_order() -> None:
    """Preserve deterministic source ordering during normalization."""
    snapshot = _build_snapshot()
    transformer = EpssSilverTransformer()

    records = list(transformer.iter_records(snapshot))

    assert [record.cve for record in records] == [
        "CVE-2026-12345",
        "CVE-2026-67890",
    ]


def test_rejects_unexpected_header() -> None:
    """Reject Bronze artifacts whose CSV schema differs from the EPSS contract."""
    snapshot = _build_snapshot(header="cve,score,percentile")
    transformer = EpssSilverTransformer()

    with pytest.raises(InvalidEpssSilverSourceError, match="CSV header"):
        list(transformer.iter_records(snapshot))


def test_rejects_malformed_column_count() -> None:
    """Reject EPSS rows that do not contain exactly three columns."""
    snapshot = _build_snapshot(
        rows=("CVE-2026-12345,0.812345",),
    )
    transformer = EpssSilverTransformer()

    with pytest.raises(InvalidEpssSilverSourceError, match="expected 3 columns"):
        list(transformer.iter_records(snapshot))


def test_rejects_non_numeric_epss_score() -> None:
    """Reject EPSS rows containing non-numeric score values."""
    snapshot = _build_snapshot(
        rows=("CVE-2026-12345,not-a-number,0.987654",),
    )
    transformer = EpssSilverTransformer()

    with pytest.raises(InvalidEpssSilverSourceError, match="numeric value"):
        list(transformer.iter_records(snapshot))


def test_rejects_invalid_epss_range_with_line_context() -> None:
    """Reject EPSS scores outside the domain range and report their source line."""
    snapshot = _build_snapshot(
        rows=("CVE-2026-12345,1.5,0.987654",),
    )
    transformer = EpssSilverTransformer()

    with pytest.raises(InvalidEpssSilverSourceError, match="line 3"):
        list(transformer.iter_records(snapshot))


def test_rejects_invalid_cve_with_line_context() -> None:
    """Reject malformed CVE identifiers and retain source line evidence."""
    snapshot = _build_snapshot(
        rows=("INVALID-CVE,0.812345,0.987654",),
    )
    transformer = EpssSilverTransformer()

    with pytest.raises(InvalidEpssSilverSourceError, match="line 3"):
        list(transformer.iter_records(snapshot))


def test_rejects_row_count_mismatch() -> None:
    """Reject transformation results inconsistent with Bronze row-count evidence."""
    snapshot = _build_snapshot(
        rows=("CVE-2026-12345,0.812345,0.987654",),
        row_count=2,
    )
    transformer = EpssSilverTransformer()

    with pytest.raises(InvalidEpssSilverSourceError, match="expected 2, emitted 1"):
        list(transformer.iter_records(snapshot))


def test_rejects_invalid_gzip_payload() -> None:
    """Reject Bronze payloads that cannot be decompressed."""
    payload = b"not-a-gzip-payload"

    snapshot = EpssSnapshot(
        raw_bytes=payload,
        model_version="v2026.06.15",
        score_timestamp=datetime(2026, 8, 15, 12, 2, 44, tzinfo=UTC),
        sha256=hashlib.sha256(payload).hexdigest(),
        row_count=1,
    )

    transformer = EpssSilverTransformer()

    with pytest.raises(InvalidEpssSilverSourceError, match="gzip CSV"):
        list(transformer.iter_records(snapshot))


def test_rejects_duplicate_cve_rows() -> None:
    """Reject EPSS snapshots containing duplicate CVE identifiers."""
    snapshot = _build_snapshot(
        rows=(
            "CVE-2026-12345,0.100000,0.200000",
            "CVE-2026-12345,0.300000,0.400000",
        ),
    )
    transformer = EpssSilverTransformer()

    with pytest.raises(
        InvalidEpssSilverSourceError,
        match=r"duplicate CVE 'CVE-2026-12345'.*source line 4",
    ):
        list(transformer.iter_records(snapshot))
