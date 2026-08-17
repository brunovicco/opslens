"""Unit tests for the CISA KEV HTTP outbound adapter."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from email.message import Message
from types import TracebackType
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from opslens.ingestion.kev.adapters.outbound import cisa_http
from opslens.ingestion.kev.adapters.outbound.cisa_http import (
    CisaHttpKevCatalogSource,
    KevSourceTooLargeError,
    KevSourceUnavailableError,
)


class FakeTelemetry:
    """Capture operational telemetry emitted by the HTTP adapter."""

    def __init__(self) -> None:
        """Initialize empty telemetry collections."""
        self.info_events: list[str] = []
        self.exception_events: list[str] = []
        self.metrics: list[tuple[str, float, str]] = []
        self.spans: list[str] = []

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture an informational telemetry event."""
        self.info_events.append(message)

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture an exception telemetry event."""
        self.exception_events.append(message)

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Capture an emitted operational metric."""
        self.metrics.append((name, value, unit))

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Capture a trace span and return a no-op context manager."""
        self.spans.append(name)
        return nullcontext()


class FakeHttpResponse:
    """Represent a deterministic HTTP response for adapter tests."""

    def __init__(
        self,
        payload: bytes,
        status: int = 200,
    ) -> None:
        """Initialize the fake HTTP response."""
        self._payload = payload
        self.status = status
        self.requested_read_size: int | None = None

    def read(self, size: int = -1) -> bytes:
        """Return at most the requested number of bytes."""
        self.requested_read_size = size

        if size < 0:
            return self._payload

        return self._payload[:size]

    def __enter__(self) -> "FakeHttpResponse":
        """Enter the fake response context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the fake response context manager."""
        return None


def test_fetch_returns_original_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return exact source bytes while enforcing the bounded read."""
    expected_payload = b'{"valid":true}'
    response = FakeHttpResponse(expected_payload)

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Return a successful deterministic HTTP response."""
        assert request.full_url == "https://example.test/kev.json"
        assert timeout == 15.0
        assert request.get_header("User-agent") == CisaHttpKevCatalogSource.USER_AGENT
        assert request.get_header("Accept") == "application/json"

        return response

    monkeypatch.setattr(
        cisa_http,
        "urlopen",
        fake_urlopen,
    )

    telemetry = FakeTelemetry()

    source = CisaHttpKevCatalogSource(
        source_url="https://example.test/kev.json",
        timeout_seconds=15.0,
        max_source_bytes=1024,
        telemetry=telemetry,
    )

    payload = source.fetch()

    assert payload == expected_payload
    assert response.requested_read_size == 1025
    assert "kev.cisa_http.fetch" in telemetry.spans

    assert (
        "KevSourceFetchSuccess",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert telemetry.exception_events == []


def test_fetch_rejects_response_above_size_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject a source response exceeding the configured defensive limit."""
    response = FakeHttpResponse(b"x" * 11)

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Return a deterministic oversized response."""
        return response

    monkeypatch.setattr(
        cisa_http,
        "urlopen",
        fake_urlopen,
    )

    telemetry = FakeTelemetry()

    source = CisaHttpKevCatalogSource(
        source_url="https://example.test/kev.json",
        timeout_seconds=15.0,
        max_source_bytes=10,
        telemetry=telemetry,
    )

    with pytest.raises(
        KevSourceTooLargeError,
        match="size limit",
    ):
        source.fetch()

    assert response.requested_read_size == 11

    assert (
        "KevSourceFetchFailure",
        1.0,
        "Count",
    ) in telemetry.metrics


def test_fetch_maps_http_error_to_source_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Translate upstream HTTP errors into a source failure."""
    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Raise a deterministic CISA HTTP failure."""
        headers = Message()

        raise HTTPError(
            url=request.full_url,
            code=503,
            msg="Service Unavailable",
            hdrs=headers,
            fp=None,
        )

    monkeypatch.setattr(
        cisa_http,
        "urlopen",
        fake_urlopen,
    )

    telemetry = FakeTelemetry()

    source = CisaHttpKevCatalogSource(
        source_url="https://example.test/kev.json",
        timeout_seconds=15.0,
        max_source_bytes=1024,
        telemetry=telemetry,
    )

    with pytest.raises(
        KevSourceUnavailableError,
        match="HTTP 503",
    ):
        source.fetch()

    assert (
        "KevSourceFetchFailure",
        1.0,
        "Count",
    ) in telemetry.metrics
