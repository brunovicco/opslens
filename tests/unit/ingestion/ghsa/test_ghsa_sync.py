"""Tests for deterministic GHSA synchronization-window identity."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from opslens.ingestion.ghsa.domain.errors import (
    InvalidGhsaSyncWindowError,
)
from opslens.ingestion.ghsa.domain.sync import (
    GhsaSyncMode,
    GhsaSyncWindow,
)


def test_equivalent_offsets_share_the_same_sync_identity() -> None:
    """Normalize timezone offsets before deriving logical source-query identity."""
    utc_window = GhsaSyncWindow(
        mode=GhsaSyncMode.MODIFIED,
        start_at=datetime(2026, 8, 26, 0, 0, 0, tzinfo=UTC),
        end_at=datetime(2026, 8, 26, 23, 59, 59, tzinfo=UTC),
    )
    offset = timezone(timedelta(hours=-3))
    offset_window = GhsaSyncWindow(
        mode=GhsaSyncMode.MODIFIED,
        start_at=datetime(2026, 8, 25, 21, 0, 0, tzinfo=offset),
        end_at=datetime(2026, 8, 26, 20, 59, 59, tzinfo=offset),
    )

    assert offset_window.start_at == utc_window.start_at
    assert offset_window.end_at == utc_window.end_at
    assert offset_window.sync_id == utc_window.sync_id
    assert offset_window.filter_expression == (
        "2026-08-26T00:00:00+00:00..2026-08-26T23:59:59+00:00"
    )


def test_sync_identity_binds_mode_and_source_contract() -> None:
    """Keep bootstrap published windows distinct from modified synchronization."""
    start_at = datetime(2026, 7, 1, 0, 0, 0, tzinfo=UTC)
    end_at = datetime(2026, 7, 31, 23, 59, 59, tzinfo=UTC)
    published = GhsaSyncWindow(
        mode=GhsaSyncMode.PUBLISHED,
        start_at=start_at,
        end_at=end_at,
    )
    modified = GhsaSyncWindow(
        mode=GhsaSyncMode.MODIFIED,
        start_at=start_at,
        end_at=end_at,
    )

    assert published.sync_id != modified.sync_id
    assert len(published.sync_id) == 64
    assert len(modified.sync_id) == 64


def test_rejects_naive_timestamps() -> None:
    """Require explicit timezone evidence for every synchronization boundary."""
    naive_start = datetime(2026, 8, 26, 0, 0, 0)  # noqa: DTZ001 - intentional invalid input

    with pytest.raises(
        InvalidGhsaSyncWindowError,
        match="timezone-aware",
    ):
        GhsaSyncWindow(
            mode=GhsaSyncMode.MODIFIED,
            start_at=naive_start,
            end_at=datetime(2026, 8, 27, 0, 0, 0, tzinfo=UTC),
        )


def test_rejects_fractional_second_boundaries() -> None:
    """Freeze source-query timestamps to documented whole-second precision."""
    with pytest.raises(
        InvalidGhsaSyncWindowError,
        match="whole-second precision",
    ):
        GhsaSyncWindow(
            mode=GhsaSyncMode.MODIFIED,
            start_at=datetime(2026, 8, 26, 0, 0, 0, 1, tzinfo=UTC),
            end_at=datetime(2026, 8, 27, 0, 0, 0, tzinfo=UTC),
        )


def test_rejects_non_increasing_window() -> None:
    """Require one proper closed range rather than a zero or negative span."""
    boundary = datetime(2026, 8, 26, 0, 0, 0, tzinfo=UTC)

    with pytest.raises(
        InvalidGhsaSyncWindowError,
        match="before end_at",
    ):
        GhsaSyncWindow(
            mode=GhsaSyncMode.MODIFIED,
            start_at=boundary,
            end_at=boundary,
        )


def test_rejects_window_above_bronze_safety_span() -> None:
    """Keep one logical GHSA Bronze unit bounded to at most 31 days."""
    with pytest.raises(
        InvalidGhsaSyncWindowError,
        match="must not exceed 31 days",
    ):
        GhsaSyncWindow(
            mode=GhsaSyncMode.PUBLISHED,
            start_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            end_at=datetime(2026, 2, 2, 0, 0, 0, tzinfo=UTC),
        )
