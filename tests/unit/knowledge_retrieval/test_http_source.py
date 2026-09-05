"""Tests for bounded Gate 7.2 knowledge-source HTTPS acquisition."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import replace

import pytest

from opslens.knowledge_retrieval.adapters.http_source import (
    AcquiredKnowledgeSource,
    BoundedHttpsKnowledgeSource,
    KnowledgeSourceHttpConfig,
    KnowledgeSourceHttpStatusError,
    KnowledgeSourceInvalidResponseError,
    KnowledgeSourceResponseTooLargeError,
)
from opslens.knowledge_retrieval.domain import KnowledgeSourceDescriptor, KnowledgeSourceType
from opslens.knowledge_retrieval.domain.source_registry import RAW_GITHUB_HOST

_UV_COMMIT = "3c979abda4530fe9bf3d92e9bcf5c5575e3b3126"
_UV_PATH = "docs/concepts/projects/sync.md"


class _FakeResponse:
    """Minimal deterministic response for transport tests."""

    def __init__(
        self,
        *,
        status: int = 200,
        body: bytes = b"# Locking and syncing\n\nTrusted guidance.\n",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self.body = body
        self.headers = headers or {"Content-Type": "text/plain; charset=utf-8"}
        self.read_amounts: list[int | None] = []

    def getheader(self, name: str, default: str | None = None) -> str | None:
        """Return one fake response header."""
        return self.headers.get(name, default)

    def read(self, amt: int | None = None) -> bytes:
        """Return at most the requested fake response bytes."""
        self.read_amounts.append(amt)
        return self.body if amt is None else self.body[:amt]


class _FakeConnection:
    """Capture one fixed-host request without performing network I/O."""

    def __init__(self, response: _FakeResponse) -> None:
        self.response = response
        self.requests: list[tuple[str, str, dict[str, str]]] = []
        self.closed = False

    def request(self, method: str, url: str, *, headers: Mapping[str, str]) -> None:
        """Record one request."""
        self.requests.append((method, url, dict(headers)))

    def getresponse(self) -> _FakeResponse:
        """Return the configured fake response."""
        return self.response

    def close(self) -> None:
        """Record deterministic connection cleanup."""
        self.closed = True


class _FakeFactory:
    """Return one fake connection while recording host and timeout."""

    def __init__(self, connection: _FakeConnection) -> None:
        self.connection = connection
        self.calls: list[tuple[str, float]] = []

    def __call__(self, host: str, timeout_seconds: float) -> _FakeConnection:
        """Capture the authorized host and configured timeout."""
        self.calls.append((host, timeout_seconds))
        return self.connection


def _descriptor() -> KnowledgeSourceDescriptor:
    return KnowledgeSourceDescriptor(
        document_id="knowledge-doc:uv-locking:v1",
        source_id="astral:uv-project-sync",
        source_type=KnowledgeSourceType.MAINTAINER_DOCUMENTATION,
        canonical_uri="https://docs.astral.sh/uv/concepts/projects/sync/",
        upstream_repository="astral-sh/uv",
        upstream_commit_sha=_UV_COMMIT,
        upstream_path=_UV_PATH,
        expected_chunk_ids=("knowledge-chunk:uv-locking:refresh:v1",),
    )


def test_acquisition_uses_pinned_raw_host_target_headers_and_hash() -> None:
    """Success derives transport authority only from pinned upstream coordinates."""
    response = _FakeResponse()
    connection = _FakeConnection(response)
    factory = _FakeFactory(connection)
    source = BoundedHttpsKnowledgeSource(connection_factory=factory)

    acquired = source.acquire(_descriptor())

    assert factory.calls == [(RAW_GITHUB_HOST, 10.0)]
    assert connection.requests == [
        (
            "GET",
            f"/astral-sh/uv/{_UV_COMMIT}/{_UV_PATH}",
            {
                "Accept": "text/plain, text/markdown;q=0.9",
                "Accept-Encoding": "identity",
                "User-Agent": "OpsLens/phase7-corpus",
            },
        )
    ]
    assert connection.closed is True
    assert response.read_amounts == [2 * 1024 * 1024 + 1]
    assert acquired.body == response.body
    assert acquired.byte_count == len(response.body)
    assert acquired.content_type == "text/plain; charset=utf-8"
    assert acquired.source_bytes_sha256 == hashlib.sha256(response.body).hexdigest()


def test_canonical_uri_cannot_change_pinned_acquisition_target() -> None:
    """The human-facing page is provenance, not authority for transport routing."""
    descriptor = replace(
        _descriptor(),
        canonical_uri="https://docs.astral.sh/uv/concepts/projects/sync/?view=full#locking",
    )
    response = _FakeResponse()
    connection = _FakeConnection(response)
    factory = _FakeFactory(connection)

    BoundedHttpsKnowledgeSource(connection_factory=factory).acquire(descriptor)

    assert factory.calls == [(RAW_GITHUB_HOST, 10.0)]
    assert connection.requests[0][1] == f"/astral-sh/uv/{_UV_COMMIT}/{_UV_PATH}"


def test_redirect_fails_closed_without_following_location() -> None:
    """Redirects are not transport authority to acquire a second URL."""
    response = _FakeResponse(
        status=302,
        headers={
            "Content-Type": "text/plain",
            "Location": "https://example.com/redirected",
        },
    )
    connection = _FakeConnection(response)
    source = BoundedHttpsKnowledgeSource(connection_factory=_FakeFactory(connection))

    with pytest.raises(KnowledgeSourceHttpStatusError) as exc_info:
        source.acquire(_descriptor())

    assert exc_info.value.status_code == 302
    assert len(connection.requests) == 1
    assert response.read_amounts == []
    assert connection.closed is True


def test_acquisition_rejects_declared_or_observed_oversized_body() -> None:
    """Both Content-Length and bounded reads enforce the same local byte budget."""
    config = KnowledgeSourceHttpConfig(max_response_bytes=8)
    declared = _FakeResponse(
        body=b"123456789",
        headers={"Content-Type": "text/plain", "Content-Length": "9"},
    )
    declared_connection = _FakeConnection(declared)

    with pytest.raises(KnowledgeSourceResponseTooLargeError):
        BoundedHttpsKnowledgeSource(
            config=config,
            connection_factory=_FakeFactory(declared_connection),
        ).acquire(_descriptor())

    assert declared.read_amounts == []

    observed = _FakeResponse(body=b"123456789")
    observed_connection = _FakeConnection(observed)
    with pytest.raises(KnowledgeSourceResponseTooLargeError):
        BoundedHttpsKnowledgeSource(
            config=config,
            connection_factory=_FakeFactory(observed_connection),
        ).acquire(_descriptor())

    assert observed.read_amounts == [9]


def test_acquisition_rejects_unexpected_media_type_or_content_encoding() -> None:
    """Only identity-encoded plain/Markdown source text enters the raw corpus boundary."""
    json_response = _FakeResponse(headers={"Content-Type": "application/json"})
    with pytest.raises(KnowledgeSourceInvalidResponseError, match="Content-Type"):
        BoundedHttpsKnowledgeSource(
            connection_factory=_FakeFactory(_FakeConnection(json_response))
        ).acquire(_descriptor())

    compressed_response = _FakeResponse(
        headers={"Content-Type": "text/plain", "Content-Encoding": "gzip"}
    )
    with pytest.raises(KnowledgeSourceInvalidResponseError, match="identity-encoded"):
        BoundedHttpsKnowledgeSource(
            connection_factory=_FakeFactory(_FakeConnection(compressed_response))
        ).acquire(_descriptor())


def test_acquired_source_rejects_tampered_raw_identity() -> None:
    """Raw-body evidence fails closed when its byte count or digest is altered."""
    acquired = AcquiredKnowledgeSource.from_body(
        descriptor=_descriptor(),
        body=b"# One immutable source\n",
        content_type="text/plain",
    )

    with pytest.raises(KnowledgeSourceInvalidResponseError, match="byte_count"):
        replace(acquired, byte_count=acquired.byte_count + 1)

    with pytest.raises(KnowledgeSourceInvalidResponseError, match="source_bytes_sha256"):
        replace(acquired, source_bytes_sha256="0" * 64)
