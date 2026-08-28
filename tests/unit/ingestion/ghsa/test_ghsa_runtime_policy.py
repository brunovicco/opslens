"""Tests for GHSA rate-limit and deterministic subdivision policies."""

from datetime import UTC, datetime

import pytest

from opslens.ingestion.ghsa.application.rate_limit import (
    GhsaRetryDelayBudgetExceededError,
    GhsaRetryDelayPolicy,
)
from opslens.ingestion.ghsa.application.subdivision import (
    GhsaWindowCannotSubdivideError,
    GhsaWindowSubdivisionPlanner,
)
from opslens.ingestion.ghsa.domain.sync import GhsaSyncMode, GhsaSyncWindow


def _window(
    *,
    start_second: int = 0,
    end_second: int = 9,
) -> GhsaSyncWindow:
    """Build one small deterministic modified window."""
    return GhsaSyncWindow(
        mode=GhsaSyncMode.MODIFIED,
        start_at=datetime(2026, 8, 28, 10, 0, start_second, tzinfo=UTC),
        end_at=datetime(2026, 8, 28, 10, 0, end_second, tzinfo=UTC),
    )


def test_retry_after_has_rate_limit_precedence() -> None:
    """Honor GitHub Retry-After before reset or exponential fallback."""
    policy = GhsaRetryDelayPolicy()

    delay = policy.rate_limit_delay_seconds(
        status_code=429,
        headers={
            "Retry-After": "7",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "2000",
        },
        now_epoch_seconds=1000.0,
        consecutive_rate_limit_failures=1,
    )

    assert delay == 7.0


def test_rate_limit_reset_is_used_when_remaining_is_zero() -> None:
    """Wait until just after the documented primary-limit reset boundary."""
    policy = GhsaRetryDelayPolicy()

    delay = policy.rate_limit_delay_seconds(
        status_code=403,
        headers={
            "x-ratelimit-remaining": "0",
            "x-ratelimit-reset": "1060",
        },
        now_epoch_seconds=1000.0,
        consecutive_rate_limit_failures=1,
    )

    assert delay == 61.0


def test_retry_after_above_runtime_wait_budget_fails_closed() -> None:
    """Never shorten a GitHub-directed wait just to fit the Lambda runtime budget."""
    policy = GhsaRetryDelayPolicy(maximum_delay_seconds=120)

    with pytest.raises(
        GhsaRetryDelayBudgetExceededError,
        match="Retry-After delay 121s exceeds the 120s retry wait budget",
    ):
        policy.rate_limit_delay_seconds(
            status_code=429,
            headers={"retry-after": "121"},
            now_epoch_seconds=1000.0,
            consecutive_rate_limit_failures=1,
        )


def test_primary_reset_above_runtime_wait_budget_fails_closed() -> None:
    """Fail instead of retrying before a primary-rate-limit reset is allowed."""
    policy = GhsaRetryDelayPolicy(maximum_delay_seconds=120)

    with pytest.raises(
        GhsaRetryDelayBudgetExceededError,
        match="X-RateLimit-Reset delay 121s exceeds the 120s retry wait budget",
    ):
        policy.rate_limit_delay_seconds(
            status_code=403,
            headers={
                "x-ratelimit-remaining": "0",
                "x-ratelimit-reset": "1120",
            },
            now_epoch_seconds=1000.0,
            consecutive_rate_limit_failures=1,
        )


def test_secondary_limit_fallback_is_exponential_with_fail_closed_budget() -> None:
    """Back off exponentially but fail rather than clamp beyond the wait budget."""
    policy = GhsaRetryDelayPolicy(maximum_delay_seconds=120)

    first = policy.rate_limit_delay_seconds(
        status_code=429,
        headers={},
        now_epoch_seconds=1000.0,
        consecutive_rate_limit_failures=1,
    )
    second = policy.rate_limit_delay_seconds(
        status_code=429,
        headers={},
        now_epoch_seconds=1000.0,
        consecutive_rate_limit_failures=2,
    )

    assert (first, second) == (60.0, 120.0)

    with pytest.raises(
        GhsaRetryDelayBudgetExceededError,
        match="secondary-rate-limit backoff delay 240s exceeds the 120s retry wait budget",
    ):
        policy.rate_limit_delay_seconds(
            status_code=429,
            headers={},
            now_epoch_seconds=1000.0,
            consecutive_rate_limit_failures=3,
        )


def test_non_rate_limit_status_has_no_rate_limit_delay() -> None:
    """Keep normal server retry behavior separate from GitHub rate limits."""
    assert (
        GhsaRetryDelayPolicy().rate_limit_delay_seconds(
            status_code=503,
            headers={},
            now_epoch_seconds=1000.0,
            consecutive_rate_limit_failures=1,
        )
        is None
    )


def test_subdivision_is_deterministic_gapless_and_non_overlapping() -> None:
    """Split one inclusive range so each represented second belongs to one child."""
    parent = _window(start_second=0, end_second=9)

    left, right = GhsaWindowSubdivisionPlanner().split(parent)

    assert left.mode is parent.mode
    assert right.mode is parent.mode
    assert left.start_at == parent.start_at
    assert right.end_at == parent.end_at
    assert left.end_at.isoformat() == "2026-08-28T10:00:04+00:00"
    assert right.start_at.isoformat() == "2026-08-28T10:00:05+00:00"
    assert left.end_at < right.start_at
    assert left.sync_id != right.sync_id
    assert left.sync_id != parent.sync_id
    assert right.sync_id != parent.sync_id


def test_subdivision_rejects_parent_too_small_for_two_valid_children() -> None:
    """Fail closed before creating a degenerate closed child window."""
    parent = _window(start_second=0, end_second=2)

    with pytest.raises(
        GhsaWindowCannotSubdivideError,
        match="too small",
    ):
        GhsaWindowSubdivisionPlanner().split(parent)
