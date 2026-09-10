"""Measure physical GitHub HTTPS requests without changing repository-read authority."""

from __future__ import annotations

from dataclasses import dataclass

from opslens.public_analysis.domain import ProviderResourceUsage
from opslens.repository_intelligence.adapters.github_http import (
    GitHubHttpsConnection,
    GitHubHttpsConnectionFactory,
    GitHubHttpsResponse,
)


@dataclass(slots=True)
class GitHubHttpMeasurement:
    """Mutable counters scoped to one representative GitHub acquisition stage."""

    request_count: int = 0
    throttle_count: int = 0

    def snapshot(self) -> ProviderResourceUsage:
        """Project current transport observations into the frozen measurement contract."""
        return ProviderResourceUsage(
            github_http_request_count=self.request_count,
            throttle_count=self.throttle_count,
        )


class MeasuredGitHubHttpsConnection:
    """Decorate one existing GitHub HTTPS connection with transport-only counters."""

    def __init__(
        self,
        *,
        delegate: GitHubHttpsConnection,
        measurement: GitHubHttpMeasurement,
    ) -> None:
        """Bind one delegate without changing host, headers, response, or retry behavior."""
        self._delegate = delegate
        self._measurement = measurement

    def request(self, method: str, url: str, *, headers: dict[str, str]) -> None:
        """Count one physical request attempt, then delegate unchanged."""
        self._measurement.request_count += 1
        self._delegate.request(method, url, headers=headers)

    def getresponse(self) -> GitHubHttpsResponse:
        """Observe rate-limit response metadata without reading or rewriting its body."""
        response = self._delegate.getresponse()
        if _is_throttle_response(response):
            self._measurement.throttle_count += 1
        return response

    def close(self) -> None:
        """Close the original connection unchanged."""
        self._delegate.close()


class MeasuredGitHubHttpsConnectionFactory:
    """Wrap the retained fixed-host connection factory for one measured execution."""

    def __init__(self, delegate: GitHubHttpsConnectionFactory) -> None:
        """Create an isolated per-run measurement scope."""
        self._delegate = delegate
        self._measurement = GitHubHttpMeasurement()

    def __call__(self, host: str, timeout_seconds: float) -> GitHubHttpsConnection:
        """Create one delegated connection wrapped only with measurement behavior."""
        connection = self._delegate(host, timeout_seconds)
        return MeasuredGitHubHttpsConnection(
            delegate=connection,
            measurement=self._measurement,
        )

    def snapshot(self) -> ProviderResourceUsage:
        """Return current exact request/throttle counters for the measured run."""
        return self._measurement.snapshot()


def _is_throttle_response(response: GitHubHttpsResponse) -> bool:
    """Match the retained GitHub adapter's 429/403 rate-limit classification."""
    if response.status == 429:
        return True
    if response.status != 403:
        return False
    remaining = response.getheader("X-RateLimit-Remaining")
    retry_after = response.getheader("Retry-After")
    return remaining == "0" or retry_after is not None


__all__ = [
    "GitHubHttpMeasurement",
    "MeasuredGitHubHttpsConnection",
    "MeasuredGitHubHttpsConnectionFactory",
]
