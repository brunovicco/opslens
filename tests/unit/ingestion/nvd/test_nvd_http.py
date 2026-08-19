"""Unit tests for the NVD yearly-feed HTTP outbound adapter."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from email.message import Message
from types import TracebackType
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from opslens.ingestion.nvd.adapters.outbound import nvd_http
from opslens.ingestion.nvd.adapters.outbound.nvd_http import (
    NvdHttpYearlyFeedSource,
    NvdSourceTooLargeError,
    NvdSourceUnavailableError,
)


class FakeTelemetry:
    """Capture telemetry emitted by the NVD HTTP adapter."""

    def __init__(self) -> None:
        """Initialize captured telemetry collections."""
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
        """Capture an informational event."""
        self.info_events.append(message)

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture an exception event."""
        self.exception_events.append(message)

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Capture one operational metric."""
        self.metrics.append((name, value, unit))

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Capture one span and return a no-op context manager."""
        self.spans.append(name)
        return nullcontext()


class FakeHttpResponse:
    """Represent a deterministic HTTP response."""

    def __init__(
        self,
        payload: bytes,
        status: int = 200,
    ) -> None:
        """Initialize the fake response."""
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
        """Enter the fake response context."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the fake response context."""
        return None


def _source(
    telemetry: FakeTelemetry,
    *,
    max_meta_bytes: int = 1024,
    max_feed_bytes: int = 4096,
) -> NvdHttpYearlyFeedSource:
    """Build an NVD HTTP source for unit tests."""
    return NvdHttpYearlyFeedSource(
        base_url="https://example.test/nvd",
        timeout_seconds=15.0,
        max_meta_bytes=max_meta_bytes,
        max_feed_bytes=max_feed_bytes,
        telemetry=telemetry,
    )


def test_fetch_meta_returns_exact_bounded_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return exact META bytes through a bounded source read."""
    expected_payload = b"sha256:abc\n"
    response = FakeHttpResponse(expected_payload)

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Return a deterministic META response."""
        assert request.full_url == ("https://example.test/nvd/nvdcve-2.0-2026.meta")
        assert timeout == 15.0
        assert request.get_header("User-agent") == (NvdHttpYearlyFeedSource.USER_AGENT)
        assert request.get_header("Accept") == "text/plain"

        return response

    monkeypatch.setattr(
        nvd_http,
        "urlopen",
        fake_urlopen,
    )

    telemetry = FakeTelemetry()

    payload = _source(telemetry).fetch_meta(2026)

    assert payload == expected_payload
    assert response.requested_read_size == 1025
    assert "nvd.http.fetch_meta" in telemetry.spans


def test_fetch_gzip_returns_exact_bounded_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return exact gzip bytes through a bounded source read."""
    expected_payload = b"\x1f\x8btest"
    response = FakeHttpResponse(expected_payload)

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Return a deterministic gzip response."""
        assert request.full_url == ("https://example.test/nvd/nvdcve-2.0-2026.json.gz")
        assert timeout == 15.0
        assert request.get_header("Accept") == "*/*"

        return response

    monkeypatch.setattr(
        nvd_http,
        "urlopen",
        fake_urlopen,
    )

    telemetry = FakeTelemetry()

    payload = _source(telemetry).fetch_gzip(2026)

    assert payload == expected_payload
    assert response.requested_read_size == 4097
    assert "nvd.http.fetch_gzip" in telemetry.spans


@pytest.mark.parametrize(
    ("method_name", "max_meta_bytes", "max_feed_bytes"),
    [
        ("fetch_meta", 10, 4096),
        ("fetch_gzip", 1024, 10),
    ],
)
def test_fetch_rejects_response_above_size_limit(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    max_meta_bytes: int,
    max_feed_bytes: int,
) -> None:
    """Reject source responses larger than configured defensive limits."""
    response = FakeHttpResponse(b"x" * 11)

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Return a deterministic oversized response."""
        return response

    monkeypatch.setattr(
        nvd_http,
        "urlopen",
        fake_urlopen,
    )

    telemetry = FakeTelemetry()

    source = _source(
        telemetry,
        max_meta_bytes=max_meta_bytes,
        max_feed_bytes=max_feed_bytes,
    )

    fetch = getattr(source, method_name)

    with pytest.raises(
        NvdSourceTooLargeError,
        match="size limit",
    ):
        fetch(2026)


def test_fetch_maps_http_error_to_source_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Translate upstream HTTP errors into an NVD source failure."""

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Raise a deterministic HTTP source failure."""
        headers = Message()

        raise HTTPError(
            url=request.full_url,
            code=503,
            msg="Service Unavailable",
            hdrs=headers,
            fp=None,
        )

    monkeypatch.setattr(
        nvd_http,
        "urlopen",
        fake_urlopen,
    )

    telemetry = FakeTelemetry()

    with pytest.raises(
        NvdSourceUnavailableError,
        match="HTTP 503",
    ):
        _source(telemetry).fetch_meta(2026)

    assert (
        "NvdSourceFetchFailure",
        1.0,
        "Count",
    ) in telemetry.metrics


def test_fetch_rejects_empty_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject empty source artifacts."""
    response = FakeHttpResponse(b"")

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Return an empty deterministic response."""
        return response

    monkeypatch.setattr(
        nvd_http,
        "urlopen",
        fake_urlopen,
    )

    telemetry = FakeTelemetry()

    with pytest.raises(
        NvdSourceUnavailableError,
        match="empty response",
    ):
        _source(telemetry).fetch_meta(2026)


@pytest.mark.parametrize(
    "feed_year",
    [
        999,
        10000,
    ],
)
def test_fetch_rejects_invalid_feed_year(
    feed_year: int,
) -> None:
    """Reject yearly-feed identifiers outside the four-digit contract."""
    telemetry = FakeTelemetry()

    with pytest.raises(
        ValueError,
        match="exactly four digits",
    ):
        _source(telemetry).fetch_meta(feed_year)


def test_fetch_rejects_boolean_feed_year() -> None:
    """Reject booleans as yearly-feed identifiers."""
    telemetry = FakeTelemetry()

    with pytest.raises(
        ValueError,
        match="must be an integer",
    ):
        _source(telemetry).fetch_meta(True)
