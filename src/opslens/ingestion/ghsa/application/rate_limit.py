"""Deterministic GitHub rate-limit retry decisions."""

from collections.abc import Mapping
from dataclasses import dataclass


class GhsaRetryDelayBudgetExceededError(RuntimeError):
    """Raised when GitHub requires a wait beyond the bounded runtime budget."""


@dataclass(frozen=True, slots=True)
class GhsaRetryDelayPolicy:
    """Derive bounded retry delays from GitHub rate-limit response headers."""

    minimum_secondary_delay_seconds: int = 60
    maximum_delay_seconds: int = 120

    def __post_init__(self) -> None:
        """Validate retry-delay bounds."""
        if self.minimum_secondary_delay_seconds <= 0:
            raise ValueError("GHSA minimum secondary-rate-limit delay must be positive.")

        if self.maximum_delay_seconds < self.minimum_secondary_delay_seconds:
            raise ValueError("GHSA maximum retry delay must cover the minimum delay.")

    def rate_limit_delay_seconds(
        self,
        *,
        status_code: int,
        headers: Mapping[str, str],
        now_epoch_seconds: float,
        consecutive_rate_limit_failures: int,
    ) -> float | None:
        """Return a GitHub-compliant delay for 403/429 responses."""
        if status_code not in {403, 429}:
            return None

        if consecutive_rate_limit_failures <= 0:
            raise ValueError("GHSA consecutive rate-limit failures must be positive.")

        normalized = {key.lower(): value.strip() for key, value in headers.items()}
        retry_after = self._parse_non_negative_int(normalized.get("retry-after"))

        if retry_after is not None:
            return self._require_within_budget(
                float(retry_after),
                source="Retry-After",
            )

        remaining = normalized.get("x-ratelimit-remaining")
        reset_epoch = self._parse_non_negative_int(normalized.get("x-ratelimit-reset"))

        if remaining == "0" and reset_epoch is not None:
            delay = max(float(reset_epoch) - now_epoch_seconds + 1.0, 0.0)
            return self._require_within_budget(
                delay,
                source="X-RateLimit-Reset",
            )

        exponential = float(
            self.minimum_secondary_delay_seconds
            * (2 ** (consecutive_rate_limit_failures - 1))
        )
        return self._require_within_budget(
            exponential,
            source="secondary-rate-limit backoff",
        )

    def _require_within_budget(
        self,
        delay_seconds: float,
        *,
        source: str,
    ) -> float:
        """Reject waits that would violate the frozen runtime retry budget."""
        if delay_seconds > float(self.maximum_delay_seconds):
            raise GhsaRetryDelayBudgetExceededError(
                f"GHSA {source} delay {delay_seconds:g}s exceeds the "
                f"{self.maximum_delay_seconds}s retry wait budget."
            )

        return delay_seconds

    @staticmethod
    def _parse_non_negative_int(value: str | None) -> int | None:
        """Parse one non-negative decimal header value."""
        if value is None or not value.isdecimal():
            return None

        parsed = int(value)
        return parsed if parsed >= 0 else None
