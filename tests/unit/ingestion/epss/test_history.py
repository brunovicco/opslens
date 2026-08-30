"""Unit tests for historical EPSS source compatibility."""

import gzip
from datetime import UTC, date, datetime

import pytest

from opslens.ingestion.epss.domain.errors import InvalidEpssSnapshotError
from opslens.ingestion.epss.domain.history import (
    EpssHistoricalSourceShape,
    EpssModelEra,
    HistoricalEpssSnapshotParser,
)


def _gzip(text: str) -> bytes:
    """Encode deterministic test source text as a gzip payload."""
    return gzip.compress(text.encode("utf-8"), mtime=0)


def test_parses_early_v1_without_fabricating_unavailable_fields() -> None:
    """Preserve the real early-v1 two-column/no-metadata source shape."""
    payload = _gzip(
        "cve,epss\n"
        "CVE-2020-5902,0.65117\n"
        "CVE-2021-12345,0.01234\n"
    )

    snapshot = HistoricalEpssSnapshotParser().parse(
        payload,
        snapshot_date=date(2021, 4, 14),
    )

    assert snapshot.model_era is EpssModelEra.V1
    assert snapshot.source_shape is EpssHistoricalSourceShape.LEGACY_TWO_COLUMN
    assert snapshot.source_metadata_present is False
    assert snapshot.percentile_available is False
    assert snapshot.model_version is None
    assert snapshot.score_timestamp is None
    assert snapshot.row_count == 2
    assert len(snapshot.sha256) == 64


def test_parses_late_v1_percentile_when_physically_published() -> None:
    """Preserve the real late-v1 three-column shape without inventing metadata."""
    payload = _gzip(
        "cve,epss,percentile\n"
        "CVE-2021-4034,0.04225,0.7411899992581052\n"
    )

    snapshot = HistoricalEpssSnapshotParser().parse(
        payload,
        snapshot_date=date(2022, 2, 3),
    )

    assert snapshot.model_era is EpssModelEra.V1
    assert snapshot.source_shape is EpssHistoricalSourceShape.LEGACY_THREE_COLUMN
    assert snapshot.source_metadata_present is False
    assert snapshot.percentile_available is True
    assert snapshot.model_version is None
    assert snapshot.score_timestamp is None
    assert snapshot.row_count == 1


def test_rejects_unknown_v1_physical_header() -> None:
    """Fail closed when a v1 coordinate carries an unobserved physical shape."""
    payload = _gzip(
        "cve,epss,percentile,extra\n"
        "CVE-2020-5902,0.65117,0.999,value\n"
    )

    with pytest.raises(InvalidEpssSnapshotError, match="v1 CSV header"):
        HistoricalEpssSnapshotParser().parse(
            payload,
            snapshot_date=date(2021, 4, 14),
        )


def test_parses_modern_snapshot_with_source_declared_metadata() -> None:
    """Reuse the proven modern parser and validate the archive date coordinate."""
    payload = _gzip(
        "#model_version:v2022.01.01,score_date:2022-02-04T00:00:00+00:00\n"
        "cve,epss,percentile\n"
        "CVE-2021-12345,0.01234,0.45678\n"
    )

    snapshot = HistoricalEpssSnapshotParser().parse(
        payload,
        snapshot_date=date(2022, 2, 4),
    )

    assert snapshot.model_era is EpssModelEra.V2
    assert snapshot.source_shape is EpssHistoricalSourceShape.MODERN_METADATA
    assert snapshot.source_metadata_present is True
    assert snapshot.percentile_available is True
    assert snapshot.model_version == "v2022.01.01"
    assert snapshot.score_timestamp == datetime(2022, 2, 4, tzinfo=UTC)
    assert snapshot.row_count == 1


def test_rejects_modern_source_date_archive_date_mismatch() -> None:
    """Reject a valid modern source file bound to the wrong archive date."""
    payload = _gzip(
        "#model_version:v2022.01.01,score_date:2022-02-05T00:00:00+00:00\n"
        "cve,epss,percentile\n"
        "CVE-2021-12345,0.01234,0.45678\n"
    )

    with pytest.raises(InvalidEpssSnapshotError, match="archive snapshot date"):
        HistoricalEpssSnapshotParser().parse(
            payload,
            snapshot_date=date(2022, 2, 4),
        )


def test_rejects_model_version_that_conflicts_with_documented_era() -> None:
    """Keep model-era evidence separate and fail on contradictory metadata."""
    payload = _gzip(
        "#model_version:v2023.03.01,score_date:2022-02-04T00:00:00+00:00\n"
        "cve,epss,percentile\n"
        "CVE-2021-12345,0.01234,0.45678\n"
    )

    with pytest.raises(InvalidEpssSnapshotError, match="documented model era"):
        HistoricalEpssSnapshotParser().parse(
            payload,
            snapshot_date=date(2022, 2, 4),
        )


def test_rejects_date_before_historical_ep_ss_coverage() -> None:
    """Do not invent historical source coverage before FIRST began publishing."""
    payload = _gzip("cve,epss\nCVE-2020-5902,0.65117\n")

    with pytest.raises(InvalidEpssSnapshotError, match="before 2021-04-14"):
        HistoricalEpssSnapshotParser().parse(
            payload,
            snapshot_date=date(2021, 4, 13),
        )
