"""Unit tests for EPSS Silver domain models."""

from datetime import UTC, date, datetime

import pytest

from opslens.transformation.epss.domain.models import SilverEpssRecord


def _valid_record(
    *,
    cve: str = "CVE-2026-12345",
    epss: float = 0.812345,
    percentile: float = 0.987654,
    model_version: str = "v2026.06.15",
    score_timestamp: datetime | None = None,
    source: str = "first-epss",
    source_sha256: str = "a" * 64,
    snapshot_date: date | None = None,
) -> SilverEpssRecord:
    """Build a valid Silver EPSS record with optional field overrides."""
    resolved_score_timestamp = (
        score_timestamp
        if score_timestamp is not None
        else datetime(2026, 8, 15, 12, 2, 44, tzinfo=UTC)
    )
    resolved_snapshot_date = (
        snapshot_date if snapshot_date is not None else resolved_score_timestamp.date()
    )

    return SilverEpssRecord(
        cve=cve,
        epss=epss,
        percentile=percentile,
        model_version=model_version,
        score_timestamp=resolved_score_timestamp,
        source=source,
        source_sha256=source_sha256,
        snapshot_date=resolved_snapshot_date,
    )


def test_accepts_valid_silver_record() -> None:
    """Accept a normalized EPSS record that satisfies every invariant."""
    record = _valid_record()

    assert record.cve == "CVE-2026-12345"
    assert record.epss == 0.812345
    assert record.percentile == 0.987654
    assert record.snapshot_date == date(2026, 8, 15)


@pytest.mark.parametrize(
    "cve",
    [
        "",
        "2026-12345",
        "CVE-26-12345",
        "CVE-2026-123",
        "cve-2026-12345",
    ],
)
def test_rejects_invalid_cve(cve: str) -> None:
    """Reject values that are not canonical CVE identifiers."""
    with pytest.raises(ValueError, match="canonical CVE format"):
        _valid_record(cve=cve)


@pytest.mark.parametrize(
    "epss",
    [
        -0.000001,
        1.000001,
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_rejects_invalid_epss_score(epss: float) -> None:
    """Reject non-finite EPSS scores and scores outside the valid range."""
    with pytest.raises(ValueError, match="EPSS score"):
        _valid_record(epss=epss)


@pytest.mark.parametrize(
    "percentile",
    [
        -0.000001,
        1.000001,
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_rejects_invalid_percentile(percentile: float) -> None:
    """Reject non-finite percentiles and values outside the valid range."""
    with pytest.raises(ValueError, match="EPSS percentile"):
        _valid_record(percentile=percentile)


@pytest.mark.parametrize("model_version", ["", " ", "   "])
def test_rejects_empty_model_version(model_version: str) -> None:
    """Reject empty or whitespace-only EPSS model versions."""
    with pytest.raises(ValueError, match="model version"):
        _valid_record(model_version=model_version)


def test_rejects_naive_score_timestamp() -> None:
    """Reject timestamps without timezone information."""
    # Intentionally naive to verify the domain rejects missing timezone information.
    naive_timestamp = datetime(2026, 8, 15, 12, 2, 44)  # noqa: DTZ001

    with pytest.raises(ValueError, match="timezone-aware"):
        _valid_record(score_timestamp=naive_timestamp)


def test_rejects_unexpected_source() -> None:
    """Reject records whose provenance source is not FIRST EPSS."""
    with pytest.raises(ValueError, match="first-epss"):
        _valid_record(source="unknown")


@pytest.mark.parametrize(
    "source_sha256",
    [
        "",
        "a" * 63,
        "a" * 65,
        "g" * 64,
        "A" * 64,
    ],
)
def test_rejects_invalid_source_sha256(source_sha256: str) -> None:
    """Reject malformed SHA-256 provenance digests."""
    with pytest.raises(ValueError, match="SHA-256"):
        _valid_record(source_sha256=source_sha256)


def test_rejects_snapshot_date_different_from_score_timestamp() -> None:
    """Reject a partition date inconsistent with source provenance."""
    with pytest.raises(ValueError, match="snapshot date"):
        _valid_record(snapshot_date=date(2026, 8, 14))
