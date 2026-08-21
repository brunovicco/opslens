"""HTTP adapter for NVD CVE API 2.0 incremental retrieval."""

import time
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)
from opslens.shared.observability.ports import OperationalTelemetry


class NvdCveApiSourceUnavailableError(RuntimeError):
    """Raised when an NVD CVE API page cannot be retrieved."""


class NvdCveApiResponseTooLargeError(RuntimeError):
    """Raised when an NVD CVE API response exceeds its size limit."""


class NvdHttpCveApiSource:
    """Retrieve bounded NVD CVE API 2.0 pages with polite pacing."""

    USER_AGENT = "opslens-nvd-ingestion/0.1"

    RETRYABLE_HTTP_STATUS_CODES = frozenset(
        {
            408,
            429,
            500,
            502,
            503,
            504,
        }
    )

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        max_response_bytes: int,
        minimum_interval_seconds: float,
        max_attempts: int,
        telemetry: OperationalTelemetry,
        sleep_fn: Callable[[float], None] = time.sleep,
        monotonic_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        """Initialize bounded and paced NVD CVE API retrieval.

        Args:
            base_url: NVD CVE API 2.0 endpoint.
            timeout_seconds: Per-request HTTP timeout.
            max_response_bytes: Defensive maximum API page size.
            minimum_interval_seconds: Minimum start-to-start request interval.
            max_attempts: Maximum attempts for one logical page request.
            telemetry: Operational telemetry implementation.
            sleep_fn: Injectable sleeping function for pacing.
            monotonic_fn: Injectable monotonic clock for pacing.
        """
        normalized_base_url = base_url.strip().rstrip("/?")

        if not normalized_base_url:
            raise ValueError("NVD CVE API base URL cannot be empty.")

        if timeout_seconds <= 0:
            raise ValueError("NVD CVE API timeout must be greater than zero.")

        if max_response_bytes <= 0:
            raise ValueError("NVD CVE API maximum response size must be greater than zero.")

        if minimum_interval_seconds < 0:
            raise ValueError("NVD CVE API minimum request interval must not be negative.")

        if type(max_attempts) is not int or max_attempts <= 0:
            raise ValueError("NVD CVE API max attempts must be a positive integer.")

        self._base_url = normalized_base_url
        self._timeout_seconds = timeout_seconds
        self._max_response_bytes = max_response_bytes
        self._minimum_interval_seconds = minimum_interval_seconds
        self._max_attempts = max_attempts
        self._telemetry = telemetry
        self._sleep = sleep_fn
        self._monotonic = monotonic_fn
        self._last_request_started_at: float | None = None

    def fetch_page(
        self,
        *,
        window: NvdIncrementalWindow,
        start_index: int,
    ) -> bytes:
        """Fetch one exact incremental NVD CVE API response page.

        The adapter deliberately omits ``resultsPerPage`` so that the
        NVD-optimized API default is used. The returned page envelope remains
        responsible for declaring the actual ``resultsPerPage``.

        Args:
            window: Deterministic last-modified query window.
            start_index: Zero-based result offset.

        Returns:
            Exact bounded response bytes.

        Raises:
            ValueError: If start_index violates the local request contract.
            NvdCveApiSourceUnavailableError: If all allowed source attempts
                fail or a non-retryable source error occurs.
            NvdCveApiResponseTooLargeError: If the response exceeds the
                configured defensive size limit.
        """
        self._validate_start_index(start_index)

        request = Request(
            self._build_url(
                window=window,
                start_index=start_index,
            ),
            headers={
                "User-Agent": self.USER_AGENT,
                "Accept": "application/json",
            },
            method="GET",
        )

        for attempt in range(
            1,
            self._max_attempts + 1,
        ):
            self._pace_request()

            self._telemetry.metric(
                name="NvdCveApiRequest",
                value=1.0,
                unit="Count",
            )

            self._telemetry.info(
                "Fetching NVD CVE API page",
                fields={
                    "attempt": attempt,
                    "max_attempts": self._max_attempts,
                    "start_index": start_index,
                    "window_start_at": (window.canonical_start_at),
                    "window_end_at": (window.canonical_end_at),
                },
            )

            try:
                with self._telemetry.span("nvd.cve_api.fetch_page"):
                    payload, status_code = self._execute_request(
                        request=request,
                    )

            except HTTPError as exc:
                if self._should_retry_http(
                    status_code=exc.code,
                    attempt=attempt,
                ):
                    self._record_retry(
                        attempt=attempt,
                        reason="http_error",
                        fields={
                            "status_code": exc.code,
                        },
                    )
                    continue

                self._record_failure(
                    message=("NVD CVE API returned an HTTP error"),
                    fields={
                        "attempt": attempt,
                        "status_code": exc.code,
                        "reason": str(exc.reason),
                    },
                )

                raise NvdCveApiSourceUnavailableError(
                    f"NVD CVE API returned HTTP {exc.code}."
                ) from exc

            except URLError as exc:
                if attempt < self._max_attempts:
                    self._record_retry(
                        attempt=attempt,
                        reason="url_error",
                        fields={
                            "reason": str(exc.reason),
                        },
                    )
                    continue

                self._record_failure(
                    message="Unable to reach NVD CVE API",
                    fields={
                        "attempt": attempt,
                        "reason": str(exc.reason),
                    },
                )

                raise NvdCveApiSourceUnavailableError("Unable to reach NVD CVE API.") from exc

            except TimeoutError as exc:
                if attempt < self._max_attempts:
                    self._record_retry(
                        attempt=attempt,
                        reason="timeout",
                        fields={
                            "timeout_seconds": (self._timeout_seconds),
                        },
                    )
                    continue

                self._record_failure(
                    message="NVD CVE API request timed out",
                    fields={
                        "attempt": attempt,
                        "timeout_seconds": (self._timeout_seconds),
                    },
                )

                raise NvdCveApiSourceUnavailableError("NVD CVE API request timed out.") from exc

            if not payload:
                if attempt < self._max_attempts:
                    self._record_retry(
                        attempt=attempt,
                        reason="empty_response",
                        fields={
                            "status_code": status_code,
                        },
                    )
                    continue

                self._record_failure(
                    message=("NVD CVE API returned an empty response"),
                    fields={
                        "attempt": attempt,
                        "status_code": status_code,
                    },
                )

                raise NvdCveApiSourceUnavailableError("NVD CVE API returned an empty response.")

            if len(payload) > self._max_response_bytes:
                self._record_failure(
                    message=("NVD CVE API response exceeded configured size limit"),
                    fields={
                        "attempt": attempt,
                        "status_code": status_code,
                        "max_response_bytes": (self._max_response_bytes),
                        "observed_bytes": len(payload),
                    },
                )

                raise NvdCveApiResponseTooLargeError(
                    "NVD CVE API response exceeded configured size limit."
                )

            self._record_success(
                attempt=attempt,
                payload_size_bytes=len(payload),
                status_code=status_code,
            )

            return payload

        raise AssertionError("NVD CVE API retry loop terminated unexpectedly.")

    def _pace_request(self) -> None:
        """Apply the configured minimum start-to-start request interval."""
        now = self._monotonic()

        if self._last_request_started_at is not None:
            elapsed = now - self._last_request_started_at
            remaining = self._minimum_interval_seconds - elapsed

            if remaining > 0:
                self._telemetry.metric(
                    name="NvdCveApiPacingDelaySeconds",
                    value=remaining,
                    unit="Seconds",
                )
                self._sleep(remaining)
                now = self._monotonic()

        self._last_request_started_at = now

    def _execute_request(
        self,
        *,
        request: Request,
    ) -> tuple[bytes, int]:
        """Execute one bounded HTTP request."""
        with urlopen(
            request,
            timeout=self._timeout_seconds,
        ) as response:
            payload = response.read(self._max_response_bytes + 1)
            status_code = response.status

        return payload, status_code

    def _build_url(
        self,
        *,
        window: NvdIncrementalWindow,
        start_index: int,
    ) -> str:
        """Build one deterministic last-modified API page URL."""
        query = urlencode(
            (
                (
                    "lastModStartDate",
                    window.canonical_start_at,
                ),
                (
                    "lastModEndDate",
                    window.canonical_end_at,
                ),
                (
                    "startIndex",
                    str(start_index),
                ),
            )
        )

        return f"{self._base_url}?{query}"

    def _should_retry_http(
        self,
        *,
        status_code: int,
        attempt: int,
    ) -> bool:
        """Return whether an HTTP failure is transient and retryable."""
        return status_code in self.RETRYABLE_HTTP_STATUS_CODES and attempt < self._max_attempts

    def _record_retry(
        self,
        *,
        attempt: int,
        reason: str,
        fields: dict[str, object],
    ) -> None:
        """Record one bounded retry decision."""
        self._telemetry.metric(
            name="NvdCveApiRetry",
            value=1.0,
            unit="Count",
        )

        self._telemetry.info(
            "Retrying NVD CVE API page",
            fields={
                "attempt": attempt,
                "retry_reason": reason,
                **fields,
            },
        )

    def _record_success(
        self,
        *,
        attempt: int,
        payload_size_bytes: int,
        status_code: int,
    ) -> None:
        """Record successful API page retrieval."""
        self._telemetry.metric(
            name="NvdCveApiFetchSuccess",
            value=1.0,
            unit="Count",
        )
        self._telemetry.metric(
            name="NvdCveApiPayloadBytes",
            value=float(payload_size_bytes),
            unit="Bytes",
        )
        self._telemetry.info(
            "NVD CVE API page downloaded",
            fields={
                "attempt": attempt,
                "status_code": status_code,
                "payload_size_bytes": (payload_size_bytes),
            },
        )

    def _record_failure(
        self,
        *,
        message: str,
        fields: dict[str, object],
    ) -> None:
        """Record a terminal API retrieval failure."""
        self._telemetry.metric(
            name="NvdCveApiFetchFailure",
            value=1.0,
            unit="Count",
        )
        self._telemetry.exception(
            message,
            fields=fields,
        )

    @staticmethod
    def _validate_start_index(
        start_index: int,
    ) -> None:
        """Require a non-negative integer API result offset."""
        if type(start_index) is not int:
            raise ValueError("NVD CVE API start index must be an integer.")

        if start_index < 0:
            raise ValueError("NVD CVE API start index must not be negative.")
