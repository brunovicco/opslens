"""Run the scheduled GHSA synchronization: read, plan, sync, advance.

Four steps, and every seam between them is a place the corpus could lose a window without
anything recording the loss. The order is the whole design.

**The boundary is never seeded implicitly.** A run that finds no boundary refuses. The
alternative — start from "now minus something" — looks like resilience and is the opposite:
it would silently declare every advisory before that instant observed, which is the
strongest false claim this system can make about its own corpus.

```text
no boundary != an obvious boundary
```

Seeding is an operator act, once, with a note saying why.

**The boundary advances only after the window returns.** If the sync raises, the boundary
stays and the next run repeats the window. Repeating is cheap; the source is idempotent
per advisory and Bronze is content-addressed, so a redundant window costs API calls and
writes nothing new.

```text
a window attempted != a window observed
```

**Catching up is bounded per invocation, and running out of budget is not a failure.** A
corpus behind by months needs several 31-day windows and a Lambda has a timeout. So the
run takes as many complete windows as its budget allows, advances after each, and reports
what remains. The next firing continues from the boundary the last one reached.

```text
remaining backlog != failure
```

**Losing the advance race ends the run, and does not retry the window.** Another run
already moved the boundary, so this run's window either duplicated work or is about to be
superseded. Retrying would be the one way to write a boundary that nobody's window
supports.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final, Protocol

from opslens.ingestion.ghsa.application.incremental_planning import (
    GhsaIncrementalPlanError,
    advance_watermark,
    plan_incremental_window,
)
from opslens.ingestion.ghsa.application.sync_watermark import (
    GhsaSyncWatermarkV1,
    GhsaWatermarkCommittedWindow,
)
from opslens.ingestion.ghsa.domain.sync import GhsaSyncMode, GhsaSyncWindow

# How many complete windows one invocation may take before handing the rest to the next
# firing. Three 31-day windows is a quarter of backlog per run, which clears any realistic
# outage in days while leaving a Lambda timeout far out of reach.
DEFAULT_MAX_WINDOWS_PER_RUN: Final = 3


class GhsaIncrementalSyncError(RuntimeError):
    """Raised when a scheduled synchronization cannot run at all."""


class PersistedBoundary(Protocol):
    """The parts of persisted boundary state this module reads."""

    @property
    def watermark(self) -> GhsaSyncWatermarkV1:
        """Return the boundary itself."""
        ...


class GhsaSyncWatermarkGateway[StateT: PersistedBoundary](Protocol):
    """The boundary operations one scheduled run needs.

    Generic over the persisted state so `advance` receives back exactly what `load`
    handed out. That is not type ceremony: the store needs the token it issued in order
    to write conditionally, and a gateway that accepted any state would type-check a run
    that advanced on a token it never read.
    """

    def load(self) -> StateT:
        """Return the current boundary and the token to write over it."""
        ...

    def advance(self, *, previous: StateT, watermark: GhsaSyncWatermarkV1) -> StateT:
        """Move the boundary forward, only if nobody else moved it first."""
        ...


@dataclass(frozen=True, slots=True)
class GhsaIncrementalSyncResult:
    """What one scheduled run did.

    Attributes:
        windows_completed: Windows synchronized and committed, in order.
        observed_through_at: Where the boundary stands afterwards.
        caught_up: Whether the boundary reached the instant the schedule fired.
        remaining: How much of the interval is left for the next firing.
        budget_exhausted: Whether the run stopped because of its own window budget
            rather than because it caught up.
    """

    windows_completed: tuple[GhsaSyncWindow, ...]
    observed_through_at: datetime
    caught_up: bool
    remaining: timedelta
    budget_exhausted: bool

    def __post_init__(self) -> None:
        """Reject a result whose parts contradict each other.

        Raises:
            GhsaIncrementalSyncError: If the completion flags disagree with the remainder.
        """
        if self.remaining < timedelta(0):
            raise GhsaIncrementalSyncError("a run cannot leave negative work behind")
        if self.caught_up != (self.remaining == timedelta(0)):
            raise GhsaIncrementalSyncError(
                "a run that reports catching up must leave nothing behind"
            )
        if self.caught_up and self.budget_exhausted:
            raise GhsaIncrementalSyncError(
                "a run cannot both have caught up and run out of budget"
            )


def run_incremental_sync[StateT: PersistedBoundary](
    *,
    target_end_at: datetime,
    boundary: GhsaSyncWatermarkGateway[StateT],
    synchronize: Callable[[GhsaSyncWindow], None],
    mode: GhsaSyncMode = GhsaSyncMode.MODIFIED,
    max_windows_per_run: int = DEFAULT_MAX_WINDOWS_PER_RUN,
) -> GhsaIncrementalSyncResult:
    """Synchronize from the current boundary toward the instant the schedule fired.

    Args:
        target_end_at: The instant the schedule fired.
        boundary: Where the corpus has been observed through.
        synchronize: Runs one window. Raising leaves the boundary where it was.
        mode: Which source timestamp to filter on.
        max_windows_per_run: Complete windows this invocation may take.

    Returns:
        What the run accomplished, including any backlog it left.

    Raises:
        GhsaIncrementalSyncError: If no boundary exists, or no window can be planned.
    """
    if type(max_windows_per_run) is not int or max_windows_per_run < 1:
        raise GhsaIncrementalSyncError(
            "a run that may take no windows cannot make progress"
        )

    current = boundary.load()
    completed: list[GhsaSyncWindow] = []

    while True:
        try:
            plan = plan_incremental_window(
                observed_through=current.watermark.observed_through_at,
                target_end_at=target_end_at,
                mode=mode,
            )
        except GhsaIncrementalPlanError as exc:
            if completed:
                # Already made progress this run; the target is simply reached.
                return GhsaIncrementalSyncResult(
                    windows_completed=tuple(completed),
                    observed_through_at=current.watermark.observed_through_at,
                    caught_up=True,
                    remaining=timedelta(0),
                    budget_exhausted=False,
                )
            raise GhsaIncrementalSyncError(
                f"no window could be planned for this firing: {exc}"
            ) from exc

        synchronize(plan.window)

        current = boundary.advance(
            previous=current,
            watermark=GhsaSyncWatermarkV1(
                observed_through_at=advance_watermark(plan),
                basis=GhsaWatermarkCommittedWindow(window=plan.window),
            ),
        )
        completed.append(plan.window)

        if plan.caught_up:
            return GhsaIncrementalSyncResult(
                windows_completed=tuple(completed),
                observed_through_at=current.watermark.observed_through_at,
                caught_up=True,
                remaining=timedelta(0),
                budget_exhausted=False,
            )

        if len(completed) >= max_windows_per_run:
            return GhsaIncrementalSyncResult(
                windows_completed=tuple(completed),
                observed_through_at=current.watermark.observed_through_at,
                caught_up=False,
                remaining=plan.remaining,
                budget_exhausted=True,
            )


__all__ = [
    "DEFAULT_MAX_WINDOWS_PER_RUN",
    "GhsaIncrementalSyncError",
    "GhsaIncrementalSyncResult",
    "GhsaSyncWatermarkGateway",
    "PersistedBoundary",
    "run_incremental_sync",
]
