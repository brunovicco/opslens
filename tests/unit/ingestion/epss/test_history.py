"""Unit tests for historical EPSS source compatibility."""

import gzip
from datetime import UTC, date, datetime

import pytest

from opslens.ingestion.epss.domain.errors import InvalidEpssSnapshotError
from opslens.ingestion.epss.domain.history import (
    EpssModelEra,
    HistoricalEpssSnapshotParser,
)


def _gzip(text: str) -> bytes:
    """Encode deterministic test source text as a gzip payload."""
    return gzip.compress(text.encode("utf-8"), mtime=0)


def test_parses_v1_without_fabricating_unavailable_fields() -> None:
    """Preserve the real EPSS v1 two-column/no-metadata source shape."""
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
    assert snapshot.source_metadata_present is False
    assert snapshot.percentile_available is False
    assert snapshot.model_version is None
    assert snapshot.score_timestamp is None
    assert snapshot.row_count == 2
    assert len(snapshot.sha256) == 64


def test_rejects_v1_shape_that_claims_modern_percentile_header() -> None:
    """Fail closed when a v1 coordinate carries a modern physical header."""
    payload = _gzip(
        "cve,epss,percentile\n"
        "CVE-2020-5902,0.65117,0.999\n"
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
