"""Plan the next GHSA window from where the last one stopped.

GHSA is the only source in this system without a schedule. KEV runs nightly, EPSS daily,
NVD every two hours; the advisory corpus was loaded once by a backfill and has not moved
since. It does not break anything — the index carries a per-source watermark and every
response states it — but a freshness field that only ever goes backwards is a system
telling you honestly that it stopped.

```text
declared staleness != acceptable staleness
```

This module is the planning half of the fix, and it follows the shape NVD already uses:
the scheduler supplies only the instant it fired, the run reads where the last complete
window ended, and the watermark advances only when a window completes. A missed firing
costs nothing, because the next run starts from the watermark rather than from "now minus
a day".

```text
a missed run != a gap in the corpus
```

**The window is `modified`, not `published`.** A published-window sync keeps new
advisories arriving and never revisits an existing one — and GitHub revises advisories
after publication, which is exactly why 35,584 rows describe 35,577 advisories and why
the projection has to select a latest observed version at all. A corpus that only grows
forwards is not a current corpus.

```text
new advisories != a current corpus
```

**A long gap is split, not swallowed.** The sync window has a 31-day maximum span, and a
run that has been down longer than that cannot ask for the whole interval. The planner
returns the first admissible window and reports that more remain, so catching up is a
sequence of complete windows rather than one oversized request that the source would
refuse or silently truncate.

```text
a truncated window != a shorter window
```

This module plans. It reads nothing, writes nothing, and calls no API.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final

from opslens.ingestion.ghsa.domain.sync import (
    GhsaSyncMode,
    GhsaSyncWindow,
    InvalidGhsaSyncWindowError,
)

GHSA_INCREMENTAL_PLAN_CONTRACT_VERSION: Final = "opslens-ghsa-incremental-plan:v1"

# The window the sync contract already enforces. Restated as the planner's own ceiling so
# an oversized plan fails here, with an explanation, rather than inside the window type.
MAX_WINDOW_SPAN: Final = GhsaSyncWindow.MAX_SPAN

# Below this, a window is not worth an API round trip and its end would land inside the
# same second as its start on a fast schedule.
MIN_WINDOW_SPAN: Final = timedelta(seconds=1)


class GhsaIncrementalPlanError(ValueError):
    """Raised when no admissible window can be planned from the state given."""


@dataclass(frozen=True, slots=True)
class GhsaIncrementalPlan:
    """One window to run, and whether the corpus is caught up after it.

    Attributes:
        window: The bounded closed window to synchronize.
        caught_up: Whether this window reaches the requested target.
        remaining: How much of the interval is left after this window.
    """

    window: GhsaSyncWindow
    caught_up: bool
    remaining: timedelta

    def __post_init__(self) -> None:
        """Reject a plan whose parts contradict each other.

        Raises:
            GhsaIncrementalPlanError: If the completion flag disagrees with the remainder.
        """
        if type(self.window) is not GhsaSyncWindow:
            raise GhsaIncrementalPlanError("an incremental plan requires one typed window")
        if self.remaining < timedelta(0):
            raise GhsaIncrementalPlanError("a plan cannot have negative work remaining")
        if self.caught_up != (self.remaining == timedelta(0)):
            raise GhsaIncrementalPlanError(
                "a plan that reports being caught up must have nothing remaining"
            )


def plan_incremental_window(
    *,
    observed_through: datetime,
    target_end_at: datetime,
    mode: GhsaSyncMode = GhsaSyncMode.MODIFIED,
) -> GhsaIncrementalPlan:
    """Plan the next window from the last completed one.

    Args:
        observed_through: Where the last complete window ended. The new window starts
            exactly here: the window type is closed, so an advisory modified at precisely
            this instant was already taken.
        target_end_at: The instant the scheduler fired, as the far edge to reach.
        mode: Which timestamp the source filters on. `MODIFIED` by default, because
            `PUBLISHED` never revisits an advisory that changed after publication.

    Returns:
        The window to run, and whether it reaches the target.

    Raises:
        GhsaIncrementalPlanError: If the target does not lie usefully ahead of the
            watermark, or if either instant is unusable.
    """
    for field, value in (
        ("observed_through", observed_through),
        ("target_end_at", target_end_at),
    ):
        if type(value) is not datetime or value.tzinfo is None:
            raise GhsaIncrementalPlanError(
                f"{field} must be one timezone-aware instant"
            )

    interval = target_end_at - observed_through
    if interval < timedelta(0):
        raise GhsaIncrementalPlanError(
            "the target is before the watermark; a clock moving backwards must not "
            "rewrite a corpus that has already been observed"
        )
    if interval < MIN_WINDOW_SPAN:
        raise GhsaIncrementalPlanError(
            "the target is not far enough ahead of the watermark to be a window; "
            "nothing new can have happened in less than a second"
        )

    span = min(interval, MAX_WINDOW_SPAN)
    end_at = observed_through + span
    remaining = target_end_at - end_at

    try:
        window = GhsaSyncWindow(mode=mode, start_at=observed_through, end_at=end_at)
    except InvalidGhsaSyncWindowError as exc:
        raise GhsaIncrementalPlanError(
            f"the planned window is not admissible: {exc}"
        ) from exc

    return GhsaIncrementalPlan(
        window=window,
        caught_up=remaining == timedelta(0),
        remaining=remaining,
    )


def advance_watermark(plan: GhsaIncrementalPlan) -> datetime:
    """Return where the watermark stands after that window completes.

    Only a completed window advances it. A run that fails partway leaves the watermark
    where it was, so the next run repeats the window rather than stepping over whatever
    it did not manage to read.

    ```text
    a window attempted != a window observed
    ```

    Args:
        plan: The plan whose window completed.

    Returns:
        The new watermark instant.
    """
    return plan.window.end_at


__all__ = [
    "GHSA_INCREMENTAL_PLAN_CONTRACT_VERSION",
    "MAX_WINDOW_SPAN",
    "MIN_WINDOW_SPAN",
    "GhsaIncrementalPlan",
    "GhsaIncrementalPlanError",
    "advance_watermark",
    "plan_incremental_window",
]
