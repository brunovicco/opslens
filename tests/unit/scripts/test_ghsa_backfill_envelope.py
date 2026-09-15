"""Tests for the GHSA backfill plan and the envelopes the lambdas actually accept.

The GHSA domain carries two deliberate serializations of the same instant.
`GhsaSyncWindow.canonical_*_at` is the frozen source-query form used to hash
`sync_id`; it renders `+00:00`. The invocation parser requires the `Z` form.

The first version of the backfill sent the hashing form over the wire, every window was
rejected by the live lambda, and the plan output hid it by printing the same wrong
form. So the contract is asserted here against the lambda's **own** parser rather than
against a format string.

```text
hashing serialization != wire serialization
closed range != half-open range
```
"""

from datetime import UTC, datetime, timedelta
from itertools import pairwise
from typing import Final, cast

import pytest

from opslens.ingestion.ghsa.adapters.inbound.invocation import (
    GhsaBronzeInvocationParserV1,
    InvalidGhsaInvocationError,
)
from opslens.ingestion.ghsa.application.backfill_planning import (
    BackfillPlanError,
    build_bronze_invocation,
    build_silver_invocation,
    invocation_timestamp,
    plan_sync_windows,
)
from opslens.ingestion.ghsa.domain.sync import GhsaSyncMode, GhsaSyncWindow
from opslens.transformation.ghsa.adapters.inbound.invocation import (
    GhsaSilverInvocationParserV1,
)

_PUBLISHED: Final = GhsaSyncMode("published")
_HISTORY_START: Final = datetime(2017, 1, 1, tzinfo=UTC)
_TODAY: Final = datetime(2026, 9, 15, tzinfo=UTC)


def test_the_wire_form_is_not_the_hashing_form() -> None:
    """The two serializations differ, and only one is accepted on the wire."""
    moment = datetime(2026, 8, 1, tzinfo=UTC)

    assert invocation_timestamp(moment) == "2026-08-01T00:00:00Z"
    assert invocation_timestamp(moment) != moment.isoformat(timespec="seconds")


def test_a_naive_timestamp_is_refused_rather_than_silently_shifted() -> None:
    """A local time would move the window without anything reporting it."""
    with pytest.raises(BackfillPlanError, match="timezone aware"):
        invocation_timestamp(datetime(2026, 8, 1))  # noqa: DTZ001


def test_every_planned_bronze_envelope_is_accepted_by_the_lambdas_own_parser() -> None:
    """A full historical plan must not contain one window the lambda would reject."""
    parser = GhsaBronzeInvocationParserV1()
    windows = plan_sync_windows(_HISTORY_START, _TODAY, _PUBLISHED)

    assert len(windows) > 100
    for window in windows:
        parser.parse(build_bronze_invocation(window))


def test_the_round_trip_preserves_the_window_identity() -> None:
    """Ledger keys must survive the envelope, or resuming would redo finished work."""
    parser = GhsaBronzeInvocationParserV1()

    for window in plan_sync_windows(
        datetime(2025, 1, 1, tzinfo=UTC),
        datetime(2026, 1, 1, tzinfo=UTC),
        _PUBLISHED,
    ):
        assert parser.parse(build_bronze_invocation(window)).sync_id == window.sync_id


def test_the_hashing_form_would_have_been_rejected() -> None:
    """Pin the actual defect, so reintroducing it fails here instead of in production."""
    parser = GhsaBronzeInvocationParserV1()
    window = GhsaSyncWindow(
        mode=_PUBLISHED,
        start_at=datetime(2026, 8, 1, tzinfo=UTC),
        end_at=datetime(2026, 8, 31, tzinfo=UTC),
    )

    with pytest.raises(InvalidGhsaInvocationError, match="YYYY-MM-DDTHH:MM:SSZ"):
        parser.parse(
            {
                "schema_version": 1,
                "mode": window.mode.value,
                "start_at": window.canonical_start_at,
                "end_at": window.canonical_end_at,
            }
        )


def test_planned_windows_never_share_a_boundary_second() -> None:
    """The GitHub search range is closed, so an abutting cover would double-count."""
    windows = plan_sync_windows(datetime(2024, 1, 1, tzinfo=UTC), _TODAY, _PUBLISHED)

    for earlier, later in pairwise(windows):
        assert later.start_at > earlier.end_at


def test_the_cover_reaches_both_ends_of_the_requested_range() -> None:
    """A disjoint cover must not also be an incomplete one."""
    windows = plan_sync_windows(_HISTORY_START, _TODAY, _PUBLISHED)

    assert windows[0].start_at == _HISTORY_START
    assert windows[-1].end_at == _TODAY
    for earlier, later in pairwise(windows):
        assert later.start_at - earlier.end_at == timedelta(seconds=1)


def test_no_window_exceeds_the_domain_span_ceiling() -> None:
    """Every planned window must be constructible, which the domain caps at 31 days."""
    for window in plan_sync_windows(_HISTORY_START, _TODAY, _PUBLISHED):
        assert window.end_at - window.start_at <= GhsaSyncWindow.MAX_SPAN


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 1, tzinfo=UTC)),
        (datetime(2026, 5, 1, tzinfo=UTC), datetime(2026, 1, 1, tzinfo=UTC)),
    ],
)
def test_a_range_that_does_not_move_forward_is_refused(start: datetime, end: datetime) -> None:
    """An empty or inverted range must not silently produce zero work."""
    with pytest.raises(BackfillPlanError, match="end after it starts"):
        plan_sync_windows(start, end, _PUBLISHED)


def test_the_silver_envelope_is_accepted_by_its_own_parser() -> None:
    """Promotion requires the exact pair Bronze reports, in the shape Silver demands."""
    parser = GhsaSilverInvocationParserV1()
    envelope = build_silver_invocation("bronze/ghsa/advisories/manifest.json", "abc123")

    parsed = parser.parse(envelope)

    assert cast(object, parsed) is not None


@pytest.mark.parametrize(("key", "version"), [("", "v1"), ("k", ""), ("", "")])
def test_silver_promotion_refuses_an_incomplete_coordinate(key: str, version: str) -> None:
    """Silver takes an exact manifest, never a prefix, so a blank half fails closed."""
    with pytest.raises(BackfillPlanError, match="exact manifest coordinate"):
        build_silver_invocation(key, version)
