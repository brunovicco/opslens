"""Tests for planning the next GHSA window from the last completed one.

The cases that matter are the ones where a plausible planner loses advisories without
failing: a window that skips the interval a missed run should have covered, a window that
silently stretches past the source's maximum span, and a mode that never revisits an
advisory revised after publication.

```text
a missed run != a gap in the corpus
new advisories != a current corpus
a truncated window != a shorter window
```
"""

from datetime import UTC, datetime, timedelta

import pytest

from opslens.ingestion.ghsa.application.incremental_planning import (
    MAX_WINDOW_SPAN,
    GhsaIncrementalPlan,
    GhsaIncrementalPlanError,
    advance_watermark,
    plan_incremental_window,
)
from opslens.ingestion.ghsa.domain.sync import GhsaSyncMode, GhsaSyncWindow

_MARK = datetime(2026, 9, 16, 18, 56, 22, tzinfo=UTC)


class TestTheOrdinaryWindow:
    """One firing, one window, starting where the last one stopped."""

    def test_it_starts_at_the_watermark(self) -> None:
        """Not at "now minus a day": the gap between runs belongs to the corpus."""
        plan = plan_incremental_window(
            observed_through=_MARK, target_end_at=_MARK + timedelta(hours=6)
        )
        assert plan.window.start_at == _MARK
        assert plan.window.end_at == _MARK + timedelta(hours=6)
        assert plan.caught_up

    def test_it_filters_on_modified_by_default(self) -> None:
        """A published window never revisits an advisory revised after publication.

        That revision is precisely what produces more than one observed version of an
        advisory, which is what the projection has to select between at all.
        """
        plan = plan_incremental_window(
            observed_through=_MARK, target_end_at=_MARK + timedelta(hours=6)
        )
        assert plan.window.mode is GhsaSyncMode.MODIFIED

    def test_published_can_still_be_asked_for_explicitly(self) -> None:
        """A backfill by publication date is a legitimate different job."""
        plan = plan_incremental_window(
            observed_through=_MARK,
            target_end_at=_MARK + timedelta(hours=6),
            mode=GhsaSyncMode.PUBLISHED,
        )
        assert plan.window.mode is GhsaSyncMode.PUBLISHED

    def test_a_completed_window_is_what_advances_the_watermark(self) -> None:
        """A run that fails partway leaves the mark, so the next run repeats the window."""
        plan = plan_incremental_window(
            observed_through=_MARK, target_end_at=_MARK + timedelta(hours=6)
        )
        assert advance_watermark(plan) == plan.window.end_at


class TestCatchingUp:
    """A source with a maximum span turns a long outage into a sequence, not a gap."""

    def test_a_gap_longer_than_the_maximum_span_is_split(self) -> None:
        """Asking for 90 days at once is a request the source refuses."""
        target = _MARK + timedelta(days=90)
        plan = plan_incremental_window(observed_through=_MARK, target_end_at=target)
        assert plan.window.end_at == _MARK + MAX_WINDOW_SPAN
        assert not plan.caught_up
        assert plan.remaining == timedelta(days=90) - MAX_WINDOW_SPAN

    def test_repeated_planning_walks_the_gap_to_zero(self) -> None:
        """Each complete window moves the mark; the sequence terminates."""
        target = _MARK + timedelta(days=90)
        mark = _MARK
        windows = 0
        while True:
            plan = plan_incremental_window(observed_through=mark, target_end_at=target)
            mark = advance_watermark(plan)
            windows += 1
            if plan.caught_up:
                break
            assert windows < 10, "catching up is not converging"
        assert mark == target
        assert windows == 3

    def test_a_window_exactly_at_the_maximum_span_is_admitted(self) -> None:
        """The span is a ceiling, not a value to stay under."""
        plan = plan_incremental_window(
            observed_through=_MARK, target_end_at=_MARK + MAX_WINDOW_SPAN
        )
        assert plan.caught_up
        assert plan.window.end_at - plan.window.start_at == MAX_WINDOW_SPAN


class TestRefusals:
    """Nothing here returns a degraded window instead of raising."""

    def test_a_target_before_the_watermark_is_refused(self) -> None:
        """A clock moving backwards must not rewrite an observed corpus."""
        with pytest.raises(GhsaIncrementalPlanError, match="before the watermark"):
            plan_incremental_window(
                observed_through=_MARK, target_end_at=_MARK - timedelta(hours=1)
            )

    def test_a_target_equal_to_the_watermark_is_refused(self) -> None:
        """A zero-length window is not a small window."""
        with pytest.raises(GhsaIncrementalPlanError, match="not far enough ahead"):
            plan_incremental_window(observed_through=_MARK, target_end_at=_MARK)

    def test_a_sub_second_interval_is_refused(self) -> None:
        """The window type carries second precision; below it there is no window."""
        with pytest.raises(GhsaIncrementalPlanError, match="not far enough ahead"):
            plan_incremental_window(
                observed_through=_MARK,
                target_end_at=_MARK + timedelta(milliseconds=500),
            )

    @pytest.mark.parametrize("field", ["observed_through", "target_end_at"])
    def test_a_naive_instant_is_refused(self, field: str) -> None:
        """An instant with no zone cannot bound a window against a source in UTC."""
        naive = datetime(2026, 9, 16, 18, 56, 22)  # noqa: DTZ001
        observed = naive if field == "observed_through" else _MARK
        target = naive if field == "target_end_at" else _MARK + timedelta(hours=6)
        with pytest.raises(GhsaIncrementalPlanError, match="timezone-aware"):
            plan_incremental_window(
                observed_through=observed, target_end_at=target
            )


class TestThePlanType:
    """A plan whose parts disagree would report a gap as closed."""

    def test_caught_up_must_agree_with_what_remains(self) -> None:
        """The exact contradiction that would silently drop the tail of a catch-up."""
        window = GhsaSyncWindow(
            mode=GhsaSyncMode.MODIFIED,
            start_at=_MARK,
            end_at=_MARK + timedelta(hours=1),
        )
        with pytest.raises(GhsaIncrementalPlanError, match="caught up"):
            GhsaIncrementalPlan(
                window=window, caught_up=True, remaining=timedelta(hours=5)
            )

    def test_negative_remaining_work_is_refused(self) -> None:
        """Less than nothing left is arithmetic that went wrong somewhere."""
        window = GhsaSyncWindow(
            mode=GhsaSyncMode.MODIFIED,
            start_at=_MARK,
            end_at=_MARK + timedelta(hours=1),
        )
        with pytest.raises(GhsaIncrementalPlanError, match="negative"):
            GhsaIncrementalPlan(
                window=window, caught_up=False, remaining=timedelta(hours=-1)
            )
