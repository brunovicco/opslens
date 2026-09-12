"""Tests for physical GitHub request accounting used by Gate 19.2."""

import json
from collections.abc import Mapping
from dataclasses import dataclass, field

import pytest

from opslens.public_analysis.adapters.github_measurement import (
    MeasuredGitHubHttpsConnectionFactory,
)
from opslens.public_analysis.domain import ProviderResourceUsage
from opslens.repository_intelligence.adapters.github_http import (
    GitHubHttpsConnection,
    GitHubRateLimitError,
    GitHubRestSnapshotSource,
)

_COMMIT_SHA = "4e9f1818adf637fbd4ab9200affa5e5bb535862a"
_TREE_SHA = "a" * 40


@dataclass(slots=True)
class FakeResponse:
    """Provide one bounded HTTPS response fixture."""

    status: int = 200
    body: bytes = b"{}"
    headers: dict[str, str] = field(default_factory=lambda: dict[str, str]())

    def getheader(self, name: str, default: str | None = None) -> str | None:
        """Return one case-insensitive fixture header."""
        target = name.lower()
        for key, value in self.headers.items():
            if key.lower() == target:
                return value
        return default

    def read(self, amt: int | None = None) -> bytes:
        """Return the bounded fixture body."""
        return self.body if amt is None else self.body[:amt]


@dataclass(slots=True)
class FakeConnection:
    """Record the delegated request without adding measurement behavior."""

    response: FakeResponse
    requests: list[tuple[str, str]] = field(default_factory=lambda: list[tuple[str, str]]())

    def request(self, method: str, url: str, *, headers: Mapping[str, str]) -> None:
        """Record method/path while leaving headers untouched."""
        assert headers
        self.requests.append((method, url))

    def getresponse(self) -> FakeResponse:
        """Return the configured response."""
        return self.response

    def close(self) -> None:
        """Satisfy the retained connection contract."""


@dataclass(slots=True)
class FakeFactory:
    """Create one connection for each expected physical request."""

    responses: list[FakeResponse]
    calls: int = 0

    def __call__(self, host: str, timeout_seconds: float) -> GitHubHttpsConnection:
        """Return the next serial response through a new fake connection."""
        assert host == "api.github.com"
        assert timeout_seconds == 10.0
        response = self.responses[self.calls]
        self.calls += 1
        return FakeConnection(response=response)


def _json_response(value: object) -> FakeResponse:
    """Build one successful GitHub JSON response."""
    return FakeResponse(
        body=json.dumps(value, separators=(",", ":")).encode(),
        headers={"Content-Type": "application/json"},
    )


def test_counts_two_physical_requests_inside_one_logical_commit_read() -> None:
    """Measure transport calls instead of assuming one call per source method."""
    delegate = FakeFactory(
        responses=[
            FakeResponse(body=f"{_COMMIT_SHA}\n".encode("ascii")),
            _json_response({"sha": _COMMIT_SHA, "tree": {"sha": _TREE_SHA}}),
        ]
    )
    measured_factory = MeasuredGitHubHttpsConnectionFactory(delegate)
    source = GitHubRestSnapshotSource(connection_factory=measured_factory)

    source.get_commit("brunovicco", "opslens", "main")

    assert measured_factory.snapshot() == ProviderResourceUsage(
        github_http_request_count=2
    )


def test_counts_rate_limit_without_changing_fail_closed_source_behavior() -> None:
    """Observe throttling metadata while preserving the retained typed source failure."""
    delegate = FakeFactory(
        responses=[
            FakeResponse(
                status=429,
                headers={"Retry-After": "60"},
            )
        ]
    )
    measured_factory = MeasuredGitHubHttpsConnectionFactory(delegate)
    source = GitHubRestSnapshotSource(connection_factory=measured_factory)

    with pytest.raises(GitHubRateLimitError):
        source.get_repository("brunovicco", "opslens")

    assert measured_factory.snapshot() == ProviderResourceUsage(
        github_http_request_count=1,
        throttle_count=1,
    )
