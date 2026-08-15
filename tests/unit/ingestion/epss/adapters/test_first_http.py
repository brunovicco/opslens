"""Unit tests for the FIRST EPSS HTTP outbound adapter."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from email.message import Message
from types import TracebackType
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from opslens.ingestion.epss.adapters.outbound import first_http
from opslens.ingestion.epss.adapters.outbound.first_http import (
    EpssSourceUnavailableError,
    FirstHttpEpssSnapshotSource,
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

    def read(self) -> bytes:
        """Return the configured HTTP response payload."""
        return self._payload

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
    """Return exact source bytes and emit success telemetry."""
    expected_payload = b"valid-gzip-bytes"

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Return a successful deterministic HTTP response."""
        assert request.full_url == "https://example.test/epss.csv.gz"
        assert timeout == 15.0
        assert request.get_header("User-agent") == (FirstHttpEpssSnapshotSource.USER_AGENT)
        assert request.get_header("Accept") == "application/gzip"

        return FakeHttpResponse(
            payload=expected_payload,
            status=200,
        )

    monkeypatch.setattr(
        first_http,
        "urlopen",
        fake_urlopen,
    )

    telemetry = FakeTelemetry()

    source = FirstHttpEpssSnapshotSource(
        source_url="https://example.test/epss.csv.gz",
        timeout_seconds=15.0,
        telemetry=telemetry,
    )

    payload = source.fetch()

    assert payload == expected_payload

    assert "epss.first_http.fetch" in telemetry.spans

    assert (
        "EpssSourceFetchSuccess",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "EpssSourcePayloadBytes",
        float(len(expected_payload)),
        "Bytes",
    ) in telemetry.metrics

    assert "Fetching EPSS source snapshot" in telemetry.info_events
    assert "EPSS source snapshot downloaded" in telemetry.info_events

    assert telemetry.exception_events == []


def test_fetch_rejects_empty_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject an empty successful response and emit failure telemetry."""

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Return an empty deterministic HTTP response."""
        return FakeHttpResponse(
            payload=b"",
            status=200,
        )

    monkeypatch.setattr(
        first_http,
        "urlopen",
        fake_urlopen,
    )

    telemetry = FakeTelemetry()

    source = FirstHttpEpssSnapshotSource(
        source_url="https://example.test/epss.csv.gz",
        timeout_seconds=15.0,
        telemetry=telemetry,
    )

    with pytest.raises(
        EpssSourceUnavailableError,
        match="empty response",
    ):
        source.fetch()

    assert "epss.first_http.fetch" in telemetry.spans

    assert (
        "EpssSourceFetchFailure",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert telemetry.exception_events == ["EPSS source returned an empty response"]


def test_fetch_maps_http_error_to_source_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Translate upstream HTTP failures and emit failure telemetry."""

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Raise a deterministic HTTP service failure."""
        headers = Message()

        raise HTTPError(
            url=request.full_url,
            code=503,
            msg="Service Unavailable",
            hdrs=headers,
            fp=None,
        )

    monkeypatch.setattr(
        first_http,
        "urlopen",
        fake_urlopen,
    )

    telemetry = FakeTelemetry()

    source = FirstHttpEpssSnapshotSource(
        source_url="https://example.test/epss.csv.gz",
        timeout_seconds=15.0,
        telemetry=telemetry,
    )

    with pytest.raises(
        EpssSourceUnavailableError,
        match="HTTP 503",
    ):
        source.fetch()

    assert "epss.first_http.fetch" in telemetry.spans

    assert (
        "EpssSourceFetchFailure",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert telemetry.exception_events == ["EPSS source returned an HTTP error"]


def test_fetch_maps_network_error_to_source_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Translate network failures and emit failure telemetry."""

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Raise a deterministic network failure."""
        raise URLError("network unavailable")

    monkeypatch.setattr(
        first_http,
        "urlopen",
        fake_urlopen,
    )

    telemetry = FakeTelemetry()

    source = FirstHttpEpssSnapshotSource(
        source_url="https://example.test/epss.csv.gz",
        timeout_seconds=15.0,
        telemetry=telemetry,
    )

    with pytest.raises(
        EpssSourceUnavailableError,
        match="Unable to reach EPSS source",
    ):
        source.fetch()

    assert "epss.first_http.fetch" in telemetry.spans

    assert (
        "EpssSourceFetchFailure",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert telemetry.exception_events == ["Unable to reach EPSS source"]


def test_fetch_maps_timeout_to_source_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Translate request timeout failures and emit failure telemetry."""

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Raise a deterministic request timeout."""
        raise TimeoutError("request timed out")

    monkeypatch.setattr(
        first_http,
        "urlopen",
        fake_urlopen,
    )

    telemetry = FakeTelemetry()

    source = FirstHttpEpssSnapshotSource(
        source_url="https://example.test/epss.csv.gz",
        timeout_seconds=15.0,
        telemetry=telemetry,
    )

    with pytest.raises(
        EpssSourceUnavailableError,
        match="request timed out",
    ):
        source.fetch()

    assert "epss.first_http.fetch" in telemetry.spans

    assert (
        "EpssSourceFetchFailure",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert telemetry.exception_events == ["EPSS source request timed out"]


def test_reject_empty_source_url() -> None:
    """Reject adapter construction with an empty source URL."""
    telemetry = FakeTelemetry()

    with pytest.raises(
        ValueError,
        match="source URL cannot be empty",
    ):
        FirstHttpEpssSnapshotSource(
            source_url="   ",
            timeout_seconds=15.0,
            telemetry=telemetry,
        )


def test_reject_non_positive_timeout() -> None:
    """Reject adapter construction with a non-positive timeout."""
    telemetry = FakeTelemetry()

    with pytest.raises(
        ValueError,
        match="timeout must be greater than zero",
    ):
        FirstHttpEpssSnapshotSource(
            source_url="https://example.test/epss.csv.gz",
            timeout_seconds=0.0,
            telemetry=telemetry,
        )
