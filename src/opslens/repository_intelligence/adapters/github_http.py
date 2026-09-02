"""Bounded read-only GitHub REST source for immutable repository snapshot resolution."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from http.client import HTTPSConnection
from typing import Protocol, cast
from urllib.parse import quote

from opslens.repository_intelligence.domain import (
    validate_github_repository_coordinates,
    validate_github_repository_ref,
)

_GITHUB_API_HOST = "api.github.com"
_GITHUB_API_VERSION = "2026-03-10"
_GITHUB_JSON_MEDIA_TYPE = "application/vnd.github+json"
_GITHUB_SHA_MEDIA_TYPE = "application/vnd.github.sha"
_FULL_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$", re.ASCII)
_CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x1f\x7f]", re.ASCII)


class GitHubRestAcquisitionError(RuntimeError):
    """Base error for bounded GitHub REST acquisition failures."""

    reason_code = "github_acquisition_failed"


class GitHubRateLimitError(GitHubRestAcquisitionError):
    """Surface GitHub rate-limit evidence without retrying automatically."""

    reason_code = "github_rate_limited"

    def __init__(
        self,
        *,
        status_code: int,
        retry_after_seconds: int | None,
        reset_epoch_seconds: int | None,
    ) -> None:
        """Create one typed rate-limit failure from non-secret response metadata."""
        super().__init__(f"GitHub API rate limited the request with status {status_code}.")
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds
        self.reset_epoch_seconds = reset_epoch_seconds


class GitHubResponseTooLargeError(GitHubRestAcquisitionError):
    """Raised when a GitHub response exceeds an explicit byte budget."""

    reason_code = "github_response_too_large"


class GitHubResourceNotFoundError(GitHubRestAcquisitionError):
    """Raised when GitHub returns 404 for a required public resource."""

    reason_code = "github_resource_not_found"


class GitHubHttpStatusError(GitHubRestAcquisitionError):
    """Raised for a non-success GitHub HTTP status outside typed special cases."""

    reason_code = "github_http_status_error"

    def __init__(self, status_code: int) -> None:
        """Create one generic HTTP-status failure without response-body disclosure."""
        super().__init__(f"GitHub API returned HTTP status {status_code}.")
        self.status_code = status_code


class GitHubInvalidResponseError(GitHubRestAcquisitionError):
    """Raised when a bounded GitHub response cannot satisfy the source contract."""

    reason_code = "invalid_github_http_response"


@dataclass(frozen=True, slots=True)
class GitHubRestClientConfig:
    """Explicit resource and credential bounds for public GitHub REST reads."""

    timeout_seconds: float = 10.0
    max_json_response_bytes: int = 1_048_576
    max_sha_response_bytes: int = 128
    user_agent: str = "OpsLens/phase4"
    token: str | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Validate local safety bounds without exposing credential values."""
        if not math.isfinite(self.timeout_seconds) or not 0 < self.timeout_seconds <= 30:
            raise ValueError("GitHub REST timeout must be finite and between 0 and 30 seconds.")

        if (
            type(self.max_json_response_bytes) is not int
            or not 1 <= self.max_json_response_bytes <= 8 * 1024 * 1024
        ):
            raise ValueError("GitHub JSON response budget must be between 1 byte and 8 MiB.")

        if (
            type(self.max_sha_response_bytes) is not int
            or not 40 <= self.max_sha_response_bytes <= 1024
        ):
            raise ValueError("GitHub SHA response budget must be between 40 and 1024 bytes.")

        if (
            not self.user_agent
            or self.user_agent != self.user_agent.strip()
            or len(self.user_agent) > 128
            or _CONTROL_CHARACTER_PATTERN.search(self.user_agent) is not None
        ):
            raise ValueError("GitHub REST User-Agent must be a clean bounded string.")

        if self.token is not None and (
            not self.token
            or self.token != self.token.strip()
            or _CONTROL_CHARACTER_PATTERN.search(self.token) is not None
        ):
            raise ValueError("GitHub bearer token must be a non-empty clean token when supplied.")


class GitHubHttpsResponse(Protocol):
    """Minimal HTTPS response surface required by the bounded transport."""

    status: int

    def getheader(self, name: str, default: str | None = None) -> str | None:
        """Return one response header."""
        ...

    def read(self, amt: int | None = None) -> bytes:
        """Read at most the requested number of bytes."""
        ...


class GitHubHttpsConnection(Protocol):
    """Minimal HTTPS connection surface required by the bounded transport."""

    def request(self, method: str, url: str, *, headers: Mapping[str, str]) -> None:
        """Issue one request to the already fixed GitHub API host."""
        ...

    def getresponse(self) -> GitHubHttpsResponse:
        """Return the HTTP response."""
        ...

    def close(self) -> None:
        """Close the connection."""
        ...


GitHubHttpsConnectionFactory = Callable[[str, float], GitHubHttpsConnection]


@dataclass(frozen=True, slots=True)
class _BoundedResponse:
    """One successful bounded HTTP response body and media type."""

    body: bytes
    content_type: str | None


def _default_connection_factory(host: str, timeout_seconds: float) -> GitHubHttpsConnection:
    """Create one TLS-validating standard-library HTTPS connection."""
    connection = HTTPSConnection(host, timeout=timeout_seconds)
    return cast(GitHubHttpsConnection, connection)


class GitHubRestSnapshotSource:
    """Implement the snapshot source Protocol with fixed-host serial GitHub GETs."""

    def __init__(
        self,
        *,
        config: GitHubRestClientConfig | None = None,
        connection_factory: GitHubHttpsConnectionFactory = _default_connection_factory,
    ) -> None:
        """Create a source with explicit local bounds and an injectable HTTPS factory."""
        self._config = config or GitHubRestClientConfig()
        self._connection_factory = connection_factory

    def get_repository(self, owner: str, name: str) -> dict[str, object]:
        """Read public repository metadata from the fixed GitHub API host."""
        owner, name = validate_github_repository_coordinates(owner, name)
        path = f"/repos/{_segment(owner)}/{_segment(name)}"
        return self._get_json(path)

    def get_commit(self, owner: str, name: str, ref: str) -> dict[str, object]:
        """Resolve a ref to SHA, then read the exact small Git commit object."""
        owner, name = validate_github_repository_coordinates(owner, name)
        ref = validate_github_repository_ref(ref)

        prefix = f"/repos/{_segment(owner)}/{_segment(name)}"
        sha = self._get_sha(f"{prefix}/commits/{_segment(ref)}")
        commit_object = self._get_json(f"{prefix}/git/commits/{sha}")

        source_sha = commit_object.get("sha")
        if source_sha != sha:
            raise GitHubInvalidResponseError(
                "GitHub Git commit object SHA does not match the resolved commit SHA."
            )

        tree = commit_object.get("tree")
        if not isinstance(tree, dict):
            raise GitHubInvalidResponseError(
                "GitHub Git commit object must contain a tree object."
            )

        return {
            "sha": sha,
            "commit": {
                "tree": cast(dict[str, object], tree),
            },
        }

    def _get_json(self, path: str) -> dict[str, object]:
        """Fetch one bounded GitHub JSON object."""
        response = self._get(
            path=path,
            accept=_GITHUB_JSON_MEDIA_TYPE,
            max_response_bytes=self._config.max_json_response_bytes,
        )
        media_type = _base_media_type(response.content_type)
        if media_type != "application/json":
            raise GitHubInvalidResponseError(
                f"GitHub JSON response used unexpected Content-Type {response.content_type!r}."
            )

        try:
            text = response.body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise GitHubInvalidResponseError(
                "GitHub JSON response must be valid UTF-8."
            ) from exc

        try:
            parsed = cast(object, json.loads(text))
        except json.JSONDecodeError as exc:
            raise GitHubInvalidResponseError(
                "GitHub response must contain valid JSON."
            ) from exc

        if not isinstance(parsed, dict):
            raise GitHubInvalidResponseError(
                "GitHub JSON response must contain an object."
            )

        return cast(dict[str, object], parsed)

    def _get_sha(self, path: str) -> str:
        """Resolve one commit ref through GitHub's SHA-only media type."""
        response = self._get(
            path=path,
            accept=_GITHUB_SHA_MEDIA_TYPE,
            max_response_bytes=self._config.max_sha_response_bytes,
        )
        try:
            sha = response.body.decode("ascii").strip()
        except UnicodeDecodeError as exc:
            raise GitHubInvalidResponseError(
                "GitHub SHA response must contain ASCII text."
            ) from exc

        if _FULL_GIT_SHA_PATTERN.fullmatch(sha) is None:
            raise GitHubInvalidResponseError(
                "GitHub SHA response must contain one full lowercase 40-hex commit SHA."
            )

        return sha

    def _get(
        self,
        *,
        path: str,
        accept: str,
        max_response_bytes: int,
    ) -> _BoundedResponse:
        """Perform one fixed-host GET with no redirect or retry behavior."""
        connection = self._connection_factory(
            _GITHUB_API_HOST,
            self._config.timeout_seconds,
        )
        try:
            connection.request(
                "GET",
                path,
                headers=self._headers(accept),
            )
            response = connection.getresponse()
            self._raise_for_status(response)
            body = _read_bounded(response, max_response_bytes)
            return _BoundedResponse(
                body=body,
                content_type=response.getheader("Content-Type"),
            )
        except GitHubRestAcquisitionError:
            raise
        except OSError as exc:
            raise GitHubRestAcquisitionError(
                "GitHub HTTPS acquisition failed before a valid response was obtained."
            ) from exc
        finally:
            connection.close()

    def _headers(self, accept: str) -> dict[str, str]:
        """Build deterministic GitHub REST request headers without logging credentials."""
        headers = {
            "Accept": accept,
            "X-GitHub-Api-Version": _GITHUB_API_VERSION,
            "User-Agent": self._config.user_agent,
        }
        if self._config.token is not None:
            headers["Authorization"] = f"Bearer {self._config.token}"
        return headers

    @staticmethod
    def _raise_for_status(response: GitHubHttpsResponse) -> None:
        """Map HTTP status and rate-limit headers to bounded typed failures."""
        status = response.status
        if status == 200:
            return

        retry_after = _optional_non_negative_int(response.getheader("Retry-After"))
        remaining = _optional_non_negative_int(response.getheader("X-RateLimit-Remaining"))
        reset_epoch = _optional_non_negative_int(response.getheader("X-RateLimit-Reset"))

        if status == 429 or (status == 403 and (remaining == 0 or retry_after is not None)):
            raise GitHubRateLimitError(
                status_code=status,
                retry_after_seconds=retry_after,
                reset_epoch_seconds=reset_epoch,
            )

        if status == 404:
            raise GitHubResourceNotFoundError(
                "Required public GitHub resource was not found."
            )

        raise GitHubHttpStatusError(status)


def _segment(value: str) -> str:
    """Encode one already validated value as exactly one URL path segment."""
    return quote(value, safe="")


def _base_media_type(content_type: str | None) -> str | None:
    """Return a lowercase media type without parameters."""
    if content_type is None:
        return None
    return content_type.split(";", maxsplit=1)[0].strip().lower()


def _read_bounded(response: GitHubHttpsResponse, max_bytes: int) -> bytes:
    """Reject known or observed response bodies larger than the explicit budget."""
    content_length = _optional_non_negative_int(response.getheader("Content-Length"))
    if content_length is not None and content_length > max_bytes:
        raise GitHubResponseTooLargeError(
            "GitHub response Content-Length exceeds the configured byte budget."
        )

    body = response.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise GitHubResponseTooLargeError(
            "GitHub response body exceeds the configured byte budget."
        )
    return body


def _optional_non_negative_int(value: str | None) -> int | None:
    """Parse optional non-negative integer response metadata conservatively."""
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None
