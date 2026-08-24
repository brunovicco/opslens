"""Unit tests for authoritative NVD incremental runtime planning."""

from datetime import UTC, datetime, timedelta

import pytest

from opslens.ingestion.nvd.application.incremental_runtime_plan import (
    NvdIncrementalRuntimePlannerV1,
    NvdIncrementalRuntimePlanStatus,
    NvdIncrementalRuntimeRequestV1,
)


def test_plans_exact_requested_window_when_within_120_days() -> None:
    """Plan from authoritative T0 to caller target when within API limit."""
    committed_at = datetime(2026, 8, 18, 7, 0, 12, tzinfo=UTC)
    target_end_at = datetime(2026, 8, 22, 23, 0, tzinfo=UTC)

    plan = NvdIncrementalRuntimePlannerV1().plan(
        committed_through_at=committed_at,
        request=NvdIncrementalRuntimeRequestV1(
            target_end_at=target_end_at,
        ),
    )

    assert plan.status is NvdIncrementalRuntimePlanStatus.WINDOW_READY
    assert plan.window is not None
    assert plan.window.start_at == committed_at
    assert plan.window.end_at == target_end_at


def test_caps_one_runtime_window_at_120_days() -> None:
    """Process at most one API-supported window per runtime invocation."""
    committed_at = datetime(2026, 1, 1, tzinfo=UTC)
    target_end_at = committed_at + timedelta(days=200)

    plan = NvdIncrementalRuntimePlannerV1().plan(
        committed_through_at=committed_at,
        request=NvdIncrementalRuntimeRequestV1(
            target_end_at=target_end_at,
        ),
    )

    assert plan.status is NvdIncrementalRuntimePlanStatus.WINDOW_READY
    assert plan.window is not None
    assert plan.window.start_at == committed_at
    assert plan.window.end_at == committed_at + timedelta(days=120)


@pytest.mark.parametrize(
    "target_end_at",
    [
        datetime(2026, 8, 18, 7, 0, 12, tzinfo=UTC),
        datetime(2026, 8, 18, 6, 0, 12, tzinfo=UTC),
    ],
)
def test_returns_noop_when_target_is_not_after_authority(
    target_end_at: datetime,
) -> None:
    """Avoid source or persistence work when authority is already current."""
    committed_at = datetime(2026, 8, 18, 7, 0, 12, tzinfo=UTC)

    plan = NvdIncrementalRuntimePlannerV1().plan(
        committed_through_at=committed_at,
        request=NvdIncrementalRuntimeRequestV1(
            target_end_at=target_end_at,
        ),
    )

    assert (
        plan.status
        is NvdIncrementalRuntimePlanStatus.NOOP_ALREADY_CURRENT
    )
    assert plan.window is None


def test_normalizes_target_and_authority_to_utc() -> None:
    """Timezone-equivalent boundaries produce one canonical UTC plan."""
    committed_at = datetime.fromisoformat(
        "2026-08-18T03:00:12-04:00"
    )
    target_end_at = datetime.fromisoformat(
        "2026-08-19T04:00:12-03:00"
    )

    plan = NvdIncrementalRuntimePlannerV1().plan(
        committed_through_at=committed_at,
        request=NvdIncrementalRuntimeRequestV1(
            target_end_at=target_end_at,
        ),
    )

    assert plan.window is not None
    assert plan.window.start_at == datetime(
        2026,
        8,
        18,
        7,
        0,
        12,
        tzinfo=UTC,
    )
    assert plan.window.end_at == datetime(
        2026,
        8,
        19,
        7,
        0,
        12,
        tzinfo=UTC,
    )


def test_request_rejects_naive_target_end_at() -> None:
    """Require an explicit timezone at the runtime boundary."""
    with pytest.raises(
        ValueError,
        match="target_end_at must be timezone-aware",
    ):

        naive_target_end_at = datetime(
            2026,
            8,
            22,
            23,
            0,
            tzinfo=UTC,
        ).replace(tzinfo=None)

        NvdIncrementalRuntimeRequestV1(
            target_end_at=naive_target_end_at,
        )


def test_planner_rejects_naive_committed_boundary() -> None:
    """Fail closed when authoritative temporal state is malformed."""
    request = NvdIncrementalRuntimeRequestV1(
        target_end_at=datetime(2026, 8, 22, 23, 0, tzinfo=UTC),
    )

    with pytest.raises(
        ValueError,
        match="committed_through_at must be timezone-aware",
    ):

        naive_committed_at = datetime(
            2026,
            8,
            18,
            7,
            0,
            12,
            tzinfo=UTC,
        ).replace(tzinfo=None)

        NvdIncrementalRuntimePlannerV1().plan(
            committed_through_at=naive_committed_at,
            request=request,
        )
