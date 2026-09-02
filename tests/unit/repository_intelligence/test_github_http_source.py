"""Tests for the bounded read-only GitHub REST snapshot source."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field

import pytest

from opslens.repository_intelligence.adapters.github_http import (
    GitHubHttpsConnection,
    GitHubHttpStatusError,
    GitHubInvalidResponseError,
    GitHubRateLimitError,
    GitHubResourceNotFoundError,
    GitHubResponseTooLargeError,
    GitHubRestAcquisitionError,
    GitHubRestClientConfig,
    GitHubRestSnapshotSource,
)
from opslens.repository_intelligence.application import resolve_github_repository_snapshot
from opslens.repository_intelligence.domain import InvalidRepositoryIdentityError

_REPOSITORY_ID = 1_333_092_779
_COMMIT_SHA = "4e9f1818adf637fbd4ab9200affa5e5bb535862a"
_TREE_SHA = "a" * 40


def _json_body(value: object) -> bytes:
    """Encode one deterministic JSON fixture body."""
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _repository_body() -> bytes:
    """Return the minimal real-shape public repository metadata response."""
    return _json_body(
        {
            "id": _REPOSITORY_ID,
            "name": "opslens",
            "full_name": "brunovicco/opslens",
            "private": False,
            "visibility": "public",
            "default_branch": "main",
            "owner": {"login": "brunovicco"},
        }
    )


def _git_commit_body(
    *,
    commit_sha: str = _COMMIT_SHA,
    tree_sha: str = _TREE_SHA,
) -> bytes:
    """Return one small Git database commit-object response."""
    return _json_body(
        {
            "sha": commit_sha,
            "tree": {
                "sha": tree_sha,
            },
        }
    )


@dataclass(slots=True)
class FakeHttpsResponse:
    """Provide the minimal bounded response interface used by the transport."""

    status: int = 200
    body: bytes = b"{}"
    headers: dict[str, str] = field(default_factory=lambda: dict[str, str]())
    read_calls: list[int | None] = field(default_factory=lambda: list[int | None]())

    def getheader(self, name: str, default: str | None = None) -> str | None:
        """Return one case-insensitive test header."""
        target = name.lower()
        for key, value in self.headers.items():
            if key.lower() == target:
                return value
        return default

    def read(self, amt: int | None = None) -> bytes:
        """Return no more than the caller-requested number of fixture bytes."""
        self.read_calls.append(amt)
        if amt is None:
            return self.body
        return self.body[:amt]


@dataclass(slots=True)
class FakeHttpsConnection:
    """Record one request and return one configured response."""

    response: FakeHttpsResponse
    request_calls: list[tuple[str, str, dict[str, str]]] = field(
        default_factory=lambda: list[tuple[str, str, dict[str, str]]]()
    )
    closed: bool = False
    request_error: OSError | None = None

    def request(self, method: str, url: str, *, headers: Mapping[str, str]) -> None:
        """Record one outbound request or raise the configured network error."""
        if self.request_error is not None:
            raise self.request_error
        self.request_calls.append((method, url, dict(headers)))

    def getresponse(self) -> FakeHttpsResponse:
        """Return the configured response."""
        return self.response

    def close(self) -> None:
        """Record deterministic connection cleanup."""
        self.closed = True


@dataclass(slots=True)
class FakeConnectionFactory:
    """Create one fake connection per expected serial GitHub request."""

    responses: list[FakeHttpsResponse]
    request_errors: list[OSError | None] = field(
        default_factory=lambda: list[OSError | None]()
    )
    factory_calls: list[tuple[str, float]] = field(
        default_factory=lambda: list[tuple[str, float]]()
    )
    connections: list[FakeHttpsConnection] = field(
        default_factory=lambda: list[FakeHttpsConnection]()
    )

    def __call__(self, host: str, timeout_seconds: float) -> GitHubHttpsConnection:
        """Return the next configured fake connection."""
        index = len(self.factory_calls)
        self.factory_calls.append((host, timeout_seconds))
        error = self.request_errors[index] if index < len(self.request_errors) else None
        connection = FakeHttpsConnection(
            response=self.responses[index],
            request_error=error,
        )
        self.connections.append(connection)
        return connection


def _json_response(body: bytes) -> FakeHttpsResponse:
    """Build one successful GitHub-style JSON response."""
    return FakeHttpsResponse(
        body=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )


def test_repository_read_uses_fixed_host_get_and_versioned_headers() -> None:
    """Keep destination and method outside caller control."""
    factory = FakeConnectionFactory(responses=[_json_response(_repository_body())])
    source = GitHubRestSnapshotSource(connection_factory=factory)

    payload = source.get_repository("brunovicco", "opslens")

    assert payload["id"] == _REPOSITORY_ID
    assert factory.factory_calls == [("api.github.com", 10.0)]
    connection = factory.connections[0]
    assert connection.closed is True
    assert len(connection.request_calls) == 1
    method, path, headers = connection.request_calls[0]
    assert method == "GET"
    assert path == "/repos/brunovicco/opslens"
    assert headers["Accept"] == "application/vnd.github+json"
    assert headers["X-GitHub-Api-Version"] == "2026-03-10"
    assert headers["User-Agent"] == "OpsLens/phase4"
    assert "Authorization" not in headers


def test_commit_read_uses_sha_media_type_then_exact_git_commit_object() -> None:
    """Avoid the potentially large normal commit JSON representation."""
    factory = FakeConnectionFactory(
        responses=[
            FakeHttpsResponse(body=f"{_COMMIT_SHA}\n".encode("ascii")),
            _json_response(_git_commit_body()),
        ]
    )
    source = GitHubRestSnapshotSource(connection_factory=factory)

    payload = source.get_commit("brunovicco", "opslens", "refs/tags/v1.0.0")

    assert payload == {
        "sha": _COMMIT_SHA,
        "commit": {"tree": {"sha": _TREE_SHA}},
    }
    assert len(factory.connections) == 2
    first_method, first_path, first_headers = factory.connections[0].request_calls[0]
    second_method, second_path, second_headers = factory.connections[1].request_calls[0]
    assert first_method == second_method == "GET"
    assert first_path == "/repos/brunovicco/opslens/commits/refs%2Ftags%2Fv1.0.0"
    assert first_headers["Accept"] == "application/vnd.github.sha"
    assert second_path == f"/repos/brunovicco/opslens/git/commits/{_COMMIT_SHA}"
    assert second_headers["Accept"] == "application/vnd.github+json"
    assert all(connection.closed for connection in factory.connections)


def test_optional_bearer_token_is_used_but_not_represented() -> None:
    """Allow higher-rate authenticated reads without exposing token values in repr."""
    secret = "github_pat_example_secret"
    config = GitHubRestClientConfig(token=secret)
    factory = FakeConnectionFactory(responses=[_json_response(_repository_body())])
    source = GitHubRestSnapshotSource(config=config, connection_factory=factory)

    source.get_repository("brunovicco", "opslens")

    headers = factory.connections[0].request_calls[0][2]
    assert headers["Authorization"] == f"Bearer {secret}"
    assert secret not in repr(config)


def test_invalid_repository_coordinates_fail_before_connection_creation() -> None:
    """Never let malformed owner/name values reach network path construction."""
    factory = FakeConnectionFactory(responses=[_json_response(_repository_body())])
    source = GitHubRestSnapshotSource(connection_factory=factory)

    with pytest.raises(InvalidRepositoryIdentityError):
        source.get_repository("../other", "opslens")

    assert factory.factory_calls == []


def test_content_length_over_budget_fails_before_body_read() -> None:
    """Reject a known oversized response without allocating its body."""
    response = FakeHttpsResponse(
        body=b"ignored",
        headers={
            "Content-Type": "application/json",
            "Content-Length": "100",
        },
    )
    config = GitHubRestClientConfig(max_json_response_bytes=10)
    factory = FakeConnectionFactory(responses=[response])
    source = GitHubRestSnapshotSource(config=config, connection_factory=factory)

    with pytest.raises(GitHubResponseTooLargeError):
        source.get_repository("brunovicco", "opslens")

    assert response.read_calls == []
    assert factory.connections[0].closed is True


def test_observed_body_over_budget_is_cut_off_and_rejected() -> None:
    """Bound body reads even when Content-Length is missing or untrusted."""
    response = FakeHttpsResponse(
        body=b"x" * 20,
        headers={"Content-Type": "application/json"},
    )
    config = GitHubRestClientConfig(max_json_response_bytes=10)
    factory = FakeConnectionFactory(responses=[response])
    source = GitHubRestSnapshotSource(config=config, connection_factory=factory)

    with pytest.raises(GitHubResponseTooLargeError):
        source.get_repository("brunovicco", "opslens")

    assert response.read_calls == [11]


def test_429_rate_limit_surfaces_retry_metadata_without_retry() -> None:
    """Expose server retry evidence and stop after the first limited request."""
    response = FakeHttpsResponse(
        status=429,
        headers={
            "Retry-After": "7",
            "X-RateLimit-Reset": "1788373000",
        },
    )
    factory = FakeConnectionFactory(responses=[response])
    source = GitHubRestSnapshotSource(connection_factory=factory)

    with pytest.raises(GitHubRateLimitError) as exc_info:
        source.get_repository("brunovicco", "opslens")

    error = exc_info.value
    assert error.status_code == 429
    assert error.retry_after_seconds == 7
    assert error.reset_epoch_seconds == 1_788_373_000
    assert len(factory.factory_calls) == 1


def test_403_with_zero_remaining_is_rate_limit() -> None:
    """Recognize GitHub primary-limit evidence on a 403 response."""
    response = FakeHttpsResponse(
        status=403,
        headers={
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1788373000",
        },
    )
    factory = FakeConnectionFactory(responses=[response])
    source = GitHubRestSnapshotSource(connection_factory=factory)

    with pytest.raises(GitHubRateLimitError):
        source.get_repository("brunovicco", "opslens")

    assert len(factory.factory_calls) == 1


def test_404_is_typed_not_found_without_retry() -> None:
    """Keep missing public resources distinct from transport and parsing failures."""
    factory = FakeConnectionFactory(responses=[FakeHttpsResponse(status=404)])
    source = GitHubRestSnapshotSource(connection_factory=factory)

    with pytest.raises(GitHubResourceNotFoundError):
        source.get_repository("brunovicco", "opslens")

    assert len(factory.factory_calls) == 1


def test_redirect_status_is_not_followed() -> None:
    """Treat redirects as explicit failures instead of changing destination authority."""
    response = FakeHttpsResponse(
        status=301,
        headers={"Location": "https://api.github.com/repos/new/name"},
    )
    factory = FakeConnectionFactory(responses=[response])
    source = GitHubRestSnapshotSource(connection_factory=factory)

    with pytest.raises(GitHubHttpStatusError) as exc_info:
        source.get_repository("brunovicco", "opslens")

    assert exc_info.value.status_code == 301
    assert len(factory.factory_calls) == 1


def test_unexpected_json_content_type_fails_closed() -> None:
    """Do not parse arbitrary response media as trusted GitHub JSON evidence."""
    response = FakeHttpsResponse(
        body=_repository_body(),
        headers={"Content-Type": "text/html"},
    )
    factory = FakeConnectionFactory(responses=[response])
    source = GitHubRestSnapshotSource(connection_factory=factory)

    with pytest.raises(GitHubInvalidResponseError):
        source.get_repository("brunovicco", "opslens")


def test_invalid_json_fails_closed() -> None:
    """Reject malformed GitHub response bodies after bounded reading."""
    factory = FakeConnectionFactory(responses=[_json_response(b"{not-json")])
    source = GitHubRestSnapshotSource(connection_factory=factory)

    with pytest.raises(GitHubInvalidResponseError):
        source.get_repository("brunovicco", "opslens")


def test_malformed_sha_stops_before_git_commit_object_request() -> None:
    """Never use malformed ref-resolution output as a Git object coordinate."""
    factory = FakeConnectionFactory(responses=[FakeHttpsResponse(body=b"abc123")])
    source = GitHubRestSnapshotSource(connection_factory=factory)

    with pytest.raises(GitHubInvalidResponseError):
        source.get_commit("brunovicco", "opslens", "main")

    assert len(factory.factory_calls) == 1


def test_git_commit_object_sha_must_match_resolved_sha() -> None:
    """Detect inconsistent GitHub evidence before snapshot projection."""
    factory = FakeConnectionFactory(
        responses=[
            FakeHttpsResponse(body=_COMMIT_SHA.encode("ascii")),
            _json_response(_git_commit_body(commit_sha="b" * 40)),
        ]
    )
    source = GitHubRestSnapshotSource(connection_factory=factory)

    with pytest.raises(GitHubInvalidResponseError):
        source.get_commit("brunovicco", "opslens", "main")

    assert len(factory.factory_calls) == 2


def test_network_error_is_bounded_and_connection_is_closed() -> None:
    """Map transport failures without retry loops and always close the connection."""
    factory = FakeConnectionFactory(
        responses=[_json_response(_repository_body())],
        request_errors=[OSError("network down")],
    )
    source = GitHubRestSnapshotSource(connection_factory=factory)

    with pytest.raises(GitHubRestAcquisitionError):
        source.get_repository("brunovicco", "opslens")

    assert len(factory.factory_calls) == 1
    assert factory.connections[0].closed is True


def test_snapshot_resolution_uses_exactly_three_serial_gets() -> None:
    """Integrate the concrete source with Gate 4.2 using a deterministic request budget."""
    factory = FakeConnectionFactory(
        responses=[
            _json_response(_repository_body()),
            FakeHttpsResponse(body=_COMMIT_SHA.encode("ascii")),
            _json_response(_git_commit_body()),
        ]
    )
    source = GitHubRestSnapshotSource(connection_factory=factory)

    evidence = resolve_github_repository_snapshot(
        source,
        owner="brunovicco",
        name="opslens",
    )

    assert evidence.snapshot.snapshot_id == f"github:{_REPOSITORY_ID}@{_COMMIT_SHA}"
    assert evidence.snapshot.tree_sha == _TREE_SHA
    assert len(factory.factory_calls) == 3
    assert [connection.request_calls[0][0] for connection in factory.connections] == [
        "GET",
        "GET",
        "GET",
    ]
