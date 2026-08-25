"""Tests for bounded NVD incremental API page sizing."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime
from types import TracebackType
from urllib.parse import parse_qs, urlparse
from urllib.request import Request

import pytest

from opslens.ingestion.nvd.adapters.outbound import nvd_cve_api
from opslens.ingestion.nvd.adapters.outbound.nvd_cve_api import (
    NvdHttpCveApiSource,
)
from opslens.ingestion.nvd.domain.incremental import NvdIncrementalWindow
from opslens.ingestion.nvd.incremental_runtime_config import (
    NvdIncrementalRuntimeConfigurationError,
    NvdIncrementalRuntimeSettingsV1,
)


class FakeTelemetry:
    """Provide inert telemetry for HTTP adapter tests."""

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Accept informational telemetry."""

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Accept failure telemetry."""

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Accept metric telemetry."""

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Provide an inert tracing span."""
        return nullcontext()


class FakeHttpResponse:
    """Return one deterministic bounded HTTP response."""

    status = 200

    def __init__(self, payload: bytes) -> None:
        """Store response bytes."""
        self._payload = payload

    def read(self, size: int = -1) -> bytes:
        """Return at most the requested response bytes."""
        if size < 0:
            return self._payload
        return self._payload[:size]

    def __enter__(self) -> "FakeHttpResponse":
        """Enter the response context."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the response context."""
        return None


def _window() -> NvdIncrementalWindow:
    """Build one deterministic incremental window."""
    return NvdIncrementalWindow(
        start_at=datetime(2026, 8, 18, 8, 20, 12, tzinfo=UTC),
        end_at=datetime(2026, 8, 25, 22, 25, tzinfo=UTC),
    )


def test_explicit_results_per_page_is_sent_to_nvd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Send the measured 500-record page bound on every API request."""
    observed_query: dict[str, list[str]] = {}

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Capture the outgoing query without reaching the network."""
        nonlocal observed_query
        observed_query = parse_qs(urlparse(request.full_url).query)
        assert timeout == 30.0
        return FakeHttpResponse(b'{"ok":true}')

    monkeypatch.setattr(nvd_cve_api, "urlopen", fake_urlopen)

    source = NvdHttpCveApiSource(
        base_url="https://services.example.test/rest/json/cves/2.0",
        timeout_seconds=30.0,
        max_response_bytes=16 * 1024 * 1024,
        minimum_interval_seconds=6.0,
        max_attempts=3,
        telemetry=FakeTelemetry(),
        results_per_page=500,
    )

    payload = source.fetch_page(
        window=_window(),
        start_index=0,
    )

    assert payload == b'{"ok":true}'
    assert observed_query["resultsPerPage"] == ["500"]
    assert observed_query["startIndex"] == ["0"]


def test_runtime_settings_default_to_measured_page_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use 500 records per page unless explicitly overridden."""
    monkeypatch.setenv("NVD_DATA_BUCKET", "opslens-test-data")
    monkeypatch.delenv("NVD_CVE_API_RESULTS_PER_PAGE", raising=False)

    settings = NvdIncrementalRuntimeSettingsV1.from_environment()

    assert settings.cve_api_results_per_page == 500


def test_runtime_settings_allow_safe_page_bound_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Allow an explicit page bound within the NVD API contract."""
    monkeypatch.setenv("NVD_DATA_BUCKET", "opslens-test-data")
    monkeypatch.setenv("NVD_CVE_API_RESULTS_PER_PAGE", "250")

    settings = NvdIncrementalRuntimeSettingsV1.from_environment()

    assert settings.cve_api_results_per_page == 250


def test_runtime_settings_reject_page_bound_above_nvd_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail closed when configuration exceeds the NVD 2000-record maximum."""
    monkeypatch.setenv("NVD_DATA_BUCKET", "opslens-test-data")
    monkeypatch.setenv("NVD_CVE_API_RESULTS_PER_PAGE", "2001")

    with pytest.raises(NvdIncrementalRuntimeConfigurationError):
        NvdIncrementalRuntimeSettingsV1.from_environment()
