"""Tests for the scheduled GHSA run: read, plan, sync, advance.

Every case here is about the order of those four steps, because every seam between them is
a place a window can be lost with nothing recording the loss.

```text
no boundary != an obvious boundary
a window attempted != a window observed
remaining backlog != failure
```
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from opslens.ingestion.ghsa.application.incremental_sync import (
    GhsaIncrementalSyncError,
    GhsaIncrementalSyncResult,
    run_incremental_sync,
)
from opslens.ingestion.ghsa.application.sync_watermark import (
    GhsaSyncWatermarkV1,
    GhsaWatermarkSeed,
)
from opslens.ingestion.ghsa.domain.sync import GhsaSyncMode, GhsaSyncWindow

_MARK = datetime(2026, 9, 16, 18, 56, 22, tzinfo=UTC)
_MAX_SPAN = GhsaSyncWindow.MAX_SPAN


@dataclass
class _Boundary:
    """An in-memory boundary that records every advance."""

    watermark: GhsaSyncWatermarkV1
    advances: int = 0
    fail_on_advance: Exception | None = None

    def load(self) -> "_Boundary":
        """Return itself; the state and its token are the same object here."""
        return self

    def advance(
        self, *, previous: "_Boundary", watermark: GhsaSyncWatermarkV1
    ) -> "_Boundary":
        """Move the boundary, or fail the way a lost race fails.

        The caller must hand back the state it last held, which is what the real store
        needs in order to write conditionally. Mutating in place rather than returning a
        copy keeps that identity check meaningful across a catch-up loop.
        """
        assert previous is self, "each advance must build on the state the run holds"
        if self.fail_on_advance is not None:
            raise self.fail_on_advance
        self.watermark = watermark
        self.advances += 1
        return self


class _AbsentBoundary:
    """A boundary that has never been established."""

    watermark: GhsaSyncWatermarkV1

    def load(self) -> "_AbsentBoundary":
        """Refuse, the way the store refuses a missing object."""
        raise RuntimeError("no GHSA observation boundary has been established")

    def advance(
        self, *, previous: "_AbsentBoundary", watermark: GhsaSyncWatermarkV1
    ) -> "_AbsentBoundary":
        """Never reached: nothing can be advanced from a boundary that does not exist."""
        del previous, watermark
        raise AssertionError("advance must not be attempted without a boundary")


def _seeded(at: datetime = _MARK) -> _Boundary:
    """Build a boundary seeded at that instant."""
    return _Boundary(
        watermark=GhsaSyncWatermarkV1(
            observed_through_at=at, basis=GhsaWatermarkSeed(note="corpus backfill")
        )
    )


class TestTheOrdinaryRun:
    """One firing, one window, one advance."""

    def test_it_syncs_then_advances(self) -> None:
        """Order matters: an advance before the window would claim unread advisories."""
        boundary = _seeded()
        order: list[str] = []

        def synchronize(window: GhsaSyncWindow) -> None:
            order.append(f"sync:{window.canonical_end_at}")
            assert boundary.advances == 0

        result = run_incremental_sync(
            target_end_at=_MARK + timedelta(hours=6),
            boundary=boundary,
            synchronize=synchronize,
        )
        assert len(order) == 1
        assert boundary.advances == 1
        assert result.caught_up
        assert result.observed_through_at == _MARK + timedelta(hours=6)

    def test_it_filters_on_modified_by_default(self) -> None:
        """A published window never revisits an advisory revised after publication."""
        seen: list[GhsaSyncMode] = []
        run_incremental_sync(
            target_end_at=_MARK + timedelta(hours=6),
            boundary=_seeded(),
            synchronize=lambda window: seen.append(window.mode),
        )
        assert seen == [GhsaSyncMode.MODIFIED]


class TestFailureLeavesTheBoundary:
    """A window that raised was not observed."""

    def test_a_failing_sync_does_not_advance(self) -> None:
        """The next run repeats the window; repeating is cheap and losing it is not."""
        boundary = _seeded()

        def synchronize(window: GhsaSyncWindow) -> None:
            del window
            raise RuntimeError("the source refused")

        with pytest.raises(RuntimeError, match="source refused"):
            run_incremental_sync(
                target_end_at=_MARK + timedelta(hours=6),
                boundary=boundary,
                synchronize=synchronize,
            )
        assert boundary.advances == 0
        assert boundary.watermark.observed_through_at == _MARK

    def test_losing_the_advance_race_ends_the_run(self) -> None:
        """Another run moved the boundary; retrying would write one nobody's window supports."""
        boundary = _seeded()
        boundary.fail_on_advance = RuntimeError("another run advanced first")
        calls = 0

        def synchronize(window: GhsaSyncWindow) -> None:
            del window
            nonlocal calls
            calls += 1

        with pytest.raises(RuntimeError, match="another run advanced"):
            run_incremental_sync(
                target_end_at=_MARK + timedelta(days=90),
                boundary=boundary,
                synchronize=synchronize,
            )
        assert calls == 1


class TestNoBoundary:
    """Refusing beats guessing."""

    def test_an_absent_boundary_refuses_rather_than_seeding(self) -> None:
        """Starting from "now minus something" declares unread advisories observed."""
        with pytest.raises(RuntimeError, match="no GHSA observation boundary"):
            run_incremental_sync(
                target_end_at=_MARK + timedelta(hours=6),
                boundary=_AbsentBoundary(),
                synchronize=lambda window: None,
            )

    def test_a_target_behind_the_boundary_refuses(self) -> None:
        """A clock moving backwards must not rewrite an observed corpus."""
        with pytest.raises(GhsaIncrementalSyncError, match="no window could be planned"):
            run_incremental_sync(
                target_end_at=_MARK - timedelta(hours=1),
                boundary=_seeded(),
                synchronize=lambda window: None,
            )


class TestCatchingUp:
    """Backlog is progress reported, not an error raised."""

    def test_a_long_gap_is_worked_in_bounded_steps(self) -> None:
        """Three windows, three advances, and the rest handed to the next firing."""
        boundary = _seeded()
        windows: list[GhsaSyncWindow] = []
        result = run_incremental_sync(
            target_end_at=_MARK + timedelta(days=200),
            boundary=boundary,
            synchronize=windows.append,
            max_windows_per_run=3,
        )
        assert len(windows) == 3
        assert boundary.advances == 3
        assert result.budget_exhausted
        assert not result.caught_up
        assert result.remaining == timedelta(days=200) - 3 * _MAX_SPAN

    def test_each_window_advances_before_the_next_is_planned(self) -> None:
        """Otherwise a budget-exhausted run would leave every window uncommitted."""
        boundary = _seeded()
        observed: list[int] = []
        run_incremental_sync(
            target_end_at=_MARK + timedelta(days=200),
            boundary=boundary,
            synchronize=lambda window: observed.append(boundary.advances),
            max_windows_per_run=3,
        )
        assert observed == [0, 1, 2]

    def test_a_budget_of_one_still_makes_progress(self) -> None:
        """The smallest useful run is one window, not zero."""
        result = run_incremental_sync(
            target_end_at=_MARK + timedelta(days=200),
            boundary=_seeded(),
            synchronize=lambda window: None,
            max_windows_per_run=1,
        )
        assert len(result.windows_completed) == 1
        assert result.budget_exhausted

    def test_a_budget_of_zero_is_refused(self) -> None:
        """A run that may take no windows is a schedule that does nothing quietly."""
        with pytest.raises(GhsaIncrementalSyncError, match="no windows"):
            run_incremental_sync(
                target_end_at=_MARK + timedelta(days=1),
                boundary=_seeded(),
                synchronize=lambda window: None,
                max_windows_per_run=0,
            )

    def test_a_gap_that_fits_the_budget_reports_caught_up(self) -> None:
        """Exactly at the budget, having reached the target, is not exhaustion."""
        result = run_incremental_sync(
            target_end_at=_MARK + _MAX_SPAN,
            boundary=_seeded(),
            synchronize=lambda window: None,
            max_windows_per_run=1,
        )
        assert result.caught_up
        assert not result.budget_exhausted


class TestTheResultType:
    """A result whose parts disagree would report a backlog as cleared."""

    def test_catching_up_and_exhausting_the_budget_cannot_both_be_true(self) -> None:
        """They are opposite reasons to stop."""
        with pytest.raises(GhsaIncrementalSyncError, match="both"):
            GhsaIncrementalSyncResult(
                windows_completed=(),
                observed_through_at=_MARK,
                caught_up=True,
                remaining=timedelta(0),
                budget_exhausted=True,
            )

    def test_caught_up_must_agree_with_what_remains(self) -> None:
        """The contradiction that would hide a backlog."""
        with pytest.raises(GhsaIncrementalSyncError, match="nothing behind"):
            GhsaIncrementalSyncResult(
                windows_completed=(),
                observed_through_at=_MARK,
                caught_up=True,
                remaining=timedelta(days=1),
                budget_exhausted=False,
            )
