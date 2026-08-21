"""Unit tests for the NVD CVE API 2.0 HTTP adapter."""

from collections.abc import Mapping
from contextlib import (
    AbstractContextManager,
    nullcontext,
)
from datetime import UTC, datetime
from email.message import Message
from types import TracebackType
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request

import pytest

from opslens.ingestion.nvd.adapters.outbound import (
    nvd_cve_api,
)
from opslens.ingestion.nvd.adapters.outbound.nvd_cve_api import (
    NvdCveApiResponseTooLargeError,
    NvdCveApiSourceUnavailableError,
    NvdHttpCveApiSource,
)
from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)


class FakeTelemetry:
    """Capture telemetry emitted by the CVE API adapter."""

    def __init__(self) -> None:
        """Initialize captured telemetry."""
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
        """Capture one informational event."""
        self.info_events.append(message)

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture one exception event."""
        self.exception_events.append(message)

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Capture one metric."""
        self.metrics.append(
            (
                name,
                value,
                unit,
            )
        )

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Capture one tracing span."""
        self.spans.append(name)
        return nullcontext()


class FakeClock:
    """Provide deterministic monotonic time and sleeping."""

    def __init__(self) -> None:
        """Initialize at monotonic time zero."""
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        """Return current fake monotonic time."""
        return self.now

    def sleep(self, seconds: float) -> None:
        """Advance fake time by one requested sleep."""
        self.sleeps.append(seconds)
        self.now += seconds

    def advance(self, seconds: float) -> None:
        """Advance time without recording a sleep."""
        self.now += seconds


class FakeHttpResponse:
    """Represent one deterministic HTTP response."""

    def __init__(
        self,
        payload: bytes,
        status: int = 200,
    ) -> None:
        """Initialize response bytes and status."""
        self._payload = payload
        self.status = status
        self.requested_read_size: int | None = None

    def read(
        self,
        size: int = -1,
    ) -> bytes:
        """Return at most the requested bytes."""
        self.requested_read_size = size

        if size < 0:
            return self._payload

        return self._payload[:size]

    def __enter__(
        self,
    ) -> "FakeHttpResponse":
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


def _window() -> NvdIncrementalWindow:
    """Build the real Phase 2.3A two-hour test window."""
    return NvdIncrementalWindow(
        start_at=datetime(
            2026,
            8,
            18,
            18,
            0,
            tzinfo=UTC,
        ),
        end_at=datetime(
            2026,
            8,
            18,
            20,
            0,
            tzinfo=UTC,
        ),
    )


def _source(
    telemetry: FakeTelemetry,
    clock: FakeClock,
    *,
    max_response_bytes: int = 4096,
    minimum_interval_seconds: float = 6.0,
    max_attempts: int = 3,
) -> NvdHttpCveApiSource:
    """Build an API source with deterministic pacing dependencies."""
    return NvdHttpCveApiSource(
        base_url=("https://services.example.test/rest/json/cves/2.0"),
        timeout_seconds=15.0,
        max_response_bytes=max_response_bytes,
        minimum_interval_seconds=(minimum_interval_seconds),
        max_attempts=max_attempts,
        telemetry=telemetry,
        sleep_fn=clock.sleep,
        monotonic_fn=clock.monotonic,
    )


def test_fetch_page_builds_expected_api_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Send the normalized window and page offset to the CVE API."""
    expected_payload = b'{"ok":true}'
    response = FakeHttpResponse(expected_payload)

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Inspect and satisfy one API request."""
        parsed = urlparse(request.full_url)
        query = parse_qs(parsed.query)

        assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == (
            "https://services.example.test/rest/json/cves/2.0"
        )
        assert query == {
            "lastModStartDate": ["2026-08-18T18:00:00Z"],
            "lastModEndDate": ["2026-08-18T20:00:00Z"],
            "startIndex": ["0"],
        }
        assert "resultsPerPage" not in query
        assert request.get_header("Accept") == "application/json"
        assert request.get_header("User-agent") == NvdHttpCveApiSource.USER_AGENT
        assert timeout == 15.0

        return response

    monkeypatch.setattr(
        nvd_cve_api,
        "urlopen",
        fake_urlopen,
    )

    telemetry = FakeTelemetry()
    clock = FakeClock()

    payload = _source(
        telemetry,
        clock,
    ).fetch_page(
        window=_window(),
        start_index=0,
    )

    assert payload == expected_payload
    assert response.requested_read_size == 4097
    assert clock.sleeps == []
    assert "nvd.cve_api.fetch_page" in telemetry.spans


def test_second_request_observes_six_second_pacing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wait before a consecutive request from the same adapter."""
    responses = [
        FakeHttpResponse(b'{"page":1}'),
        FakeHttpResponse(b'{"page":2}'),
    ]

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Return consecutive successful responses."""
        return responses.pop(0)

    monkeypatch.setattr(
        nvd_cve_api,
        "urlopen",
        fake_urlopen,
    )

    telemetry = FakeTelemetry()
    clock = FakeClock()
    source = _source(
        telemetry,
        clock,
    )

    source.fetch_page(
        window=_window(),
        start_index=0,
    )
    source.fetch_page(
        window=_window(),
        start_index=2000,
    )

    assert clock.sleeps == [6.0]
    assert (
        "NvdCveApiPacingDelaySeconds",
        6.0,
        "Seconds",
    ) in telemetry.metrics


def test_no_sleep_when_previous_request_started_over_six_seconds_ago(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Avoid unnecessary delay when the source call itself consumed pacing."""
    response = FakeHttpResponse(b'{"ok":true}')
    clock = FakeClock()

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Model one source request lasting seven seconds."""
        clock.advance(7.0)
        return response

    monkeypatch.setattr(
        nvd_cve_api,
        "urlopen",
        fake_urlopen,
    )

    source = _source(
        FakeTelemetry(),
        clock,
    )

    source.fetch_page(
        window=_window(),
        start_index=0,
    )
    source.fetch_page(
        window=_window(),
        start_index=1,
    )

    assert clock.sleeps == []


def test_retryable_http_error_is_paced_and_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retry a transient source HTTP failure without hammering NVD."""
    calls = 0

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Fail once with 503, then succeed."""
        nonlocal calls
        calls += 1

        if calls == 1:
            raise HTTPError(
                url=request.full_url,
                code=503,
                msg="Service Unavailable",
                hdrs=Message(),
                fp=None,
            )

        return FakeHttpResponse(b'{"ok":true}')

    monkeypatch.setattr(
        nvd_cve_api,
        "urlopen",
        fake_urlopen,
    )

    telemetry = FakeTelemetry()
    clock = FakeClock()

    payload = _source(
        telemetry,
        clock,
    ).fetch_page(
        window=_window(),
        start_index=0,
    )

    assert payload == b'{"ok":true}'
    assert calls == 2
    assert clock.sleeps == [6.0]
    assert (
        "NvdCveApiRetry",
        1.0,
        "Count",
    ) in telemetry.metrics


def test_rate_limit_response_is_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Treat HTTP 429 as a transient bounded retry condition."""
    calls = 0

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Fail once with 429, then succeed."""
        nonlocal calls
        calls += 1

        if calls == 1:
            raise HTTPError(
                url=request.full_url,
                code=429,
                msg="Too Many Requests",
                hdrs=Message(),
                fp=None,
            )

        return FakeHttpResponse(b'{"ok":true}')

    monkeypatch.setattr(
        nvd_cve_api,
        "urlopen",
        fake_urlopen,
    )

    clock = FakeClock()

    _source(
        FakeTelemetry(),
        clock,
    ).fetch_page(
        window=_window(),
        start_index=0,
    )

    assert calls == 2
    assert clock.sleeps == [6.0]


def test_non_retryable_http_error_fails_immediately(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not retry deterministic client-side HTTP failures."""
    calls = 0

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Return a deterministic HTTP 400 failure."""
        nonlocal calls
        calls += 1

        raise HTTPError(
            url=request.full_url,
            code=400,
            msg="Bad Request",
            hdrs=Message(),
            fp=None,
        )

    monkeypatch.setattr(
        nvd_cve_api,
        "urlopen",
        fake_urlopen,
    )

    telemetry = FakeTelemetry()
    clock = FakeClock()

    with pytest.raises(
        NvdCveApiSourceUnavailableError,
        match="HTTP 400",
    ):
        _source(
            telemetry,
            clock,
        ).fetch_page(
            window=_window(),
            start_index=0,
        )

    assert calls == 1
    assert clock.sleeps == []


def test_url_error_is_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retry transient network reachability failures."""
    calls = 0

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Fail once at the network layer."""
        nonlocal calls
        calls += 1

        if calls == 1:
            raise URLError("temporary network failure")

        return FakeHttpResponse(b'{"ok":true}')

    monkeypatch.setattr(
        nvd_cve_api,
        "urlopen",
        fake_urlopen,
    )

    clock = FakeClock()

    payload = _source(
        FakeTelemetry(),
        clock,
    ).fetch_page(
        window=_window(),
        start_index=0,
    )

    assert payload == b'{"ok":true}'
    assert calls == 2
    assert clock.sleeps == [6.0]


def test_timeout_is_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retry transient request timeouts."""
    calls = 0

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Fail once with a timeout."""
        nonlocal calls
        calls += 1

        if calls == 1:
            raise TimeoutError

        return FakeHttpResponse(b'{"ok":true}')

    monkeypatch.setattr(
        nvd_cve_api,
        "urlopen",
        fake_urlopen,
    )

    clock = FakeClock()

    payload = _source(
        FakeTelemetry(),
        clock,
    ).fetch_page(
        window=_window(),
        start_index=0,
    )

    assert payload == b'{"ok":true}'
    assert calls == 2
    assert clock.sleeps == [6.0]


def test_retry_exhaustion_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stop after the configured bounded retry budget."""
    calls = 0

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Always fail with a retryable source error."""
        nonlocal calls
        calls += 1

        raise HTTPError(
            url=request.full_url,
            code=503,
            msg="Service Unavailable",
            hdrs=Message(),
            fp=None,
        )

    monkeypatch.setattr(
        nvd_cve_api,
        "urlopen",
        fake_urlopen,
    )

    telemetry = FakeTelemetry()
    clock = FakeClock()

    with pytest.raises(
        NvdCveApiSourceUnavailableError,
        match="HTTP 503",
    ):
        _source(
            telemetry,
            clock,
            max_attempts=3,
        ).fetch_page(
            window=_window(),
            start_index=0,
        )

    assert calls == 3
    assert clock.sleeps == [
        6.0,
        6.0,
    ]


def test_empty_response_is_bounded_retry_condition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retry an anomalous empty HTTP 200 response."""
    responses = [
        FakeHttpResponse(b""),
        FakeHttpResponse(b'{"ok":true}'),
    ]

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Return empty bytes once, then valid bytes."""
        return responses.pop(0)

    monkeypatch.setattr(
        nvd_cve_api,
        "urlopen",
        fake_urlopen,
    )

    clock = FakeClock()

    payload = _source(
        FakeTelemetry(),
        clock,
    ).fetch_page(
        window=_window(),
        start_index=0,
    )

    assert payload == b'{"ok":true}'
    assert clock.sleeps == [6.0]


def test_oversized_response_fails_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Treat defensive response-size overflow as terminal."""
    calls = 0
    response = FakeHttpResponse(b"x" * 11)

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Return an oversized response."""
        nonlocal calls
        calls += 1
        return response

    monkeypatch.setattr(
        nvd_cve_api,
        "urlopen",
        fake_urlopen,
    )

    with pytest.raises(
        NvdCveApiResponseTooLargeError,
        match="size limit",
    ):
        _source(
            FakeTelemetry(),
            FakeClock(),
            max_response_bytes=10,
        ).fetch_page(
            window=_window(),
            start_index=0,
        )

    assert calls == 1
    assert response.requested_read_size == 11


@pytest.mark.parametrize(
    "start_index",
    [
        -1,
        True,
    ],
)
def test_fetch_rejects_invalid_start_index(
    start_index: int,
) -> None:
    """Reject invalid zero-based result offsets."""
    source = _source(
        FakeTelemetry(),
        FakeClock(),
    )

    with pytest.raises(ValueError):
        source.fetch_page(
            window=_window(),
            start_index=start_index,
        )


@pytest.mark.parametrize(
    (
        "minimum_interval_seconds",
        "max_attempts",
    ),
    [
        (-0.1, 3),
        (6.0, 0),
    ],
)
def test_constructor_rejects_invalid_retry_or_pacing_configuration(
    minimum_interval_seconds: float,
    max_attempts: int,
) -> None:
    """Reject invalid request-control configuration."""
    with pytest.raises(ValueError):
        _source(
            FakeTelemetry(),
            FakeClock(),
            minimum_interval_seconds=(minimum_interval_seconds),
            max_attempts=max_attempts,
        )
