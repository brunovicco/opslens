"""Unit tests for deterministic NVD incremental update windows."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone

import pytest

from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)


def test_window_normalizes_boundaries_to_utc() -> None:
    """Normalize equivalent timezone representations to UTC."""
    eastern = timezone(timedelta(hours=-4))

    window = NvdIncrementalWindow(
        start_at=datetime(
            2026,
            8,
            18,
            14,
            0,
            tzinfo=eastern,
        ),
        end_at=datetime(
            2026,
            8,
            18,
            16,
            0,
            tzinfo=eastern,
        ),
    )

    assert window.start_at == datetime(
        2026,
        8,
        18,
        18,
        0,
        tzinfo=UTC,
    )
    assert window.end_at == datetime(
        2026,
        8,
        18,
        20,
        0,
        tzinfo=UTC,
    )


def test_window_serializes_expected_canonical_boundaries() -> None:
    """Expose deterministic UTC boundary representations."""
    window = NvdIncrementalWindow(
        start_at=datetime(
            2026,
            8,
            18,
            18,
            0,
            tzinfo=UTC,
        ),
        end_at=datetime(
            2026,
            8,
            18,
            20,
            0,
            tzinfo=UTC,
        ),
    )

    assert window.canonical_start_at == "2026-08-18T18:00:00Z"
    assert window.canonical_end_at == "2026-08-18T20:00:00Z"


def test_update_id_matches_frozen_contract() -> None:
    """Lock the deterministic update identity for a known real window."""
    window = NvdIncrementalWindow(
        start_at=datetime(
            2026,
            8,
            18,
            18,
            0,
            tzinfo=UTC,
        ),
        end_at=datetime(
            2026,
            8,
            18,
            20,
            0,
            tzinfo=UTC,
        ),
    )

    assert window.update_id == ("a32b0d0854956f1b8303456bdf387081983a0592d34da6b06d01056db25df891")


def test_equivalent_timezone_windows_share_update_id() -> None:
    """Make logical identity independent of timezone representation."""
    eastern = timezone(timedelta(hours=-4))

    first = NvdIncrementalWindow(
        start_at=datetime(
            2026,
            8,
            18,
            18,
            0,
            tzinfo=UTC,
        ),
        end_at=datetime(
            2026,
            8,
            18,
            20,
            0,
            tzinfo=UTC,
        ),
    )

    second = NvdIncrementalWindow(
        start_at=datetime(
            2026,
            8,
            18,
            14,
            0,
            tzinfo=eastern,
        ),
        end_at=datetime(
            2026,
            8,
            18,
            16,
            0,
            tzinfo=eastern,
        ),
    )

    assert first == second
    assert first.update_id == second.update_id


def test_update_id_changes_when_start_boundary_changes() -> None:
    """Distinguish windows with different lower boundaries."""
    first = NvdIncrementalWindow(
        start_at=datetime(
            2026,
            8,
            18,
            18,
            0,
            tzinfo=UTC,
        ),
        end_at=datetime(
            2026,
            8,
            18,
            20,
            0,
            tzinfo=UTC,
        ),
    )

    second = NvdIncrementalWindow(
        start_at=datetime(
            2026,
            8,
            18,
            18,
            1,
            tzinfo=UTC,
        ),
        end_at=datetime(
            2026,
            8,
            18,
            20,
            0,
            tzinfo=UTC,
        ),
    )

    assert first.update_id != second.update_id


def test_update_id_changes_when_end_boundary_changes() -> None:
    """Distinguish windows with different upper boundaries."""
    first = NvdIncrementalWindow(
        start_at=datetime(
            2026,
            8,
            18,
            18,
            0,
            tzinfo=UTC,
        ),
        end_at=datetime(
            2026,
            8,
            18,
            20,
            0,
            tzinfo=UTC,
        ),
    )

    second = NvdIncrementalWindow(
        start_at=datetime(
            2026,
            8,
            18,
            18,
            0,
            tzinfo=UTC,
        ),
        end_at=datetime(
            2026,
            8,
            18,
            20,
            1,
            tzinfo=UTC,
        ),
    )

    assert first.update_id != second.update_id


def test_window_preserves_fractional_seconds() -> None:
    """Retain timestamp precision when boundaries include microseconds."""
    window = NvdIncrementalWindow(
        start_at=datetime(
            2026,
            8,
            18,
            18,
            0,
            0,
            123456,
            tzinfo=UTC,
        ),
        end_at=datetime(
            2026,
            8,
            18,
            20,
            0,
            0,
            654321,
            tzinfo=UTC,
        ),
    )

    assert window.canonical_start_at == "2026-08-18T18:00:00.123456Z"
    assert window.canonical_end_at == "2026-08-18T20:00:00.654321Z"


def test_window_allows_exactly_120_days() -> None:
    """Allow the maximum supported incremental span."""
    start_at = datetime(
        2026,
        1,
        1,
        tzinfo=UTC,
    )

    window = NvdIncrementalWindow(
        start_at=start_at,
        end_at=start_at + timedelta(days=120),
    )

    assert window.end_at - window.start_at == timedelta(days=120)


def test_window_rejects_more_than_120_days() -> None:
    """Reject incremental windows beyond the maximum span."""
    start_at = datetime(
        2026,
        1,
        1,
        tzinfo=UTC,
    )

    with pytest.raises(
        ValueError,
        match="must not exceed 120 days",
    ):
        NvdIncrementalWindow(
            start_at=start_at,
            end_at=(start_at + timedelta(days=120, microseconds=1)),
        )


def test_window_rejects_equal_boundaries() -> None:
    """Reject an empty incremental window."""
    boundary = datetime(
        2026,
        8,
        18,
        18,
        0,
        tzinfo=UTC,
    )

    with pytest.raises(
        ValueError,
        match="start_at must be before end_at",
    ):
        NvdIncrementalWindow(
            start_at=boundary,
            end_at=boundary,
        )


def test_window_rejects_reversed_boundaries() -> None:
    """Reject a window whose upper boundary precedes the lower one."""
    with pytest.raises(
        ValueError,
        match="start_at must be before end_at",
    ):
        NvdIncrementalWindow(
            start_at=datetime(
                2026,
                8,
                18,
                20,
                0,
                tzinfo=UTC,
            ),
            end_at=datetime(
                2026,
                8,
                18,
                18,
                0,
                tzinfo=UTC,
            ),
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "start_at",
        "end_at",
    ],
)
def test_window_rejects_naive_datetime(
    field_name: str,
) -> None:
    """Reject boundaries without explicit timezone evidence."""
    aware = datetime(
        2026,
        8,
        18,
        20,
        0,
        tzinfo=UTC,
    )
    naive = datetime(
        2026,
        8,
        18,
        18,
        0,
        tzinfo=UTC,
    ).replace(tzinfo=None)

    values = {
        "start_at": datetime(
            2026,
            8,
            18,
            18,
            0,
            tzinfo=UTC,
        ),
        "end_at": aware,
    }
    values[field_name] = naive

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be timezone-aware",
    ):
        NvdIncrementalWindow(**values)


@pytest.mark.parametrize(
    "field_name",
    [
        "start_at",
        "end_at",
    ],
)
def test_window_rejects_non_datetime_input(
    field_name: str,
) -> None:
    """Reject values outside the datetime contract."""
    values: dict[str, object] = {
        "start_at": datetime(
            2026,
            8,
            18,
            18,
            0,
            tzinfo=UTC,
        ),
        "end_at": datetime(
            2026,
            8,
            18,
            20,
            0,
            tzinfo=UTC,
        ),
    }
    values[field_name] = "2026-08-18T18:00:00Z"

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be a datetime",
    ):
        NvdIncrementalWindow(**values)  # type: ignore[arg-type]


def test_window_is_immutable() -> None:
    """Prevent mutation after logical identity is established."""
    window = NvdIncrementalWindow(
        start_at=datetime(
            2026,
            8,
            18,
            18,
            0,
            tzinfo=UTC,
        ),
        end_at=datetime(
            2026,
            8,
            18,
            20,
            0,
            tzinfo=UTC,
        ),
    )

    attribute_name = "start_at"

    with pytest.raises(FrozenInstanceError):
        setattr(
            window,
            attribute_name,
            datetime(
                2026,
                8,
                18,
                19,
                0,
                tzinfo=UTC,
            ),
        )
