"""Authenticated HTTPS adapter for GitHub global security advisories."""

import http.client
import time
from collections.abc import Callable, Mapping
from urllib.parse import urlsplit

from opslens.ingestion.ghsa.application.ports import (
    GhsaCredentialProvider,
    GhsaFetchedPage,
    GhsaHttpResponse,
    GhsaHttpTransport,
)
from opslens.ingestion.ghsa.application.rate_limit import (
    GhsaRetryDelayBudgetExceededError,
    GhsaRetryDelayPolicy,
)
from opslens.ingestion.ghsa.domain.api_page import (
    GhsaAdvisoryApiPageParser,
    GhsaRequestUrlPolicy,
)
from opslens.ingestion.ghsa.domain.sync import GhsaSyncWindow
from opslens.shared.observability.ports import OperationalTelemetry


class GhsaSourceUnavailableError(RuntimeError):
    """Raised when a bounded GitHub source request cannot be completed."""


class GhsaAuthenticationError(GhsaSourceUnavailableError):
    """Raised when GitHub rejects the configured credential."""


class GhsaRateLimitExhaustedError(GhsaSourceUnavailableError):
    """Raised after the bounded GitHub rate-limit retry budget is exhausted."""


class GhsaResponseTooLargeError(GhsaSourceUnavailableError):
    """Raised when a GitHub response exceeds the frozen page byte limit."""


class HttpsGhsaTransport:
    """Execute direct HTTPS GETs without automatic redirect following."""

    def get(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> GhsaHttpResponse:
        """Return one bounded HTTPS response from the exact requested host."""
        parsed = urlsplit(url)
        hostname = parsed.hostname

        if parsed.scheme != GhsaRequestUrlPolicy.SCHEME:
            raise GhsaSourceUnavailableError("GHSA transport requires HTTPS.")

        if hostname is None or hostname != GhsaRequestUrlPolicy.HOST:
            raise GhsaSourceUnavailableError("GHSA transport host is not allowlisted.")

        if parsed.port not in (None, 443):
            raise GhsaSourceUnavailableError("GHSA transport cannot use a non-HTTPS port.")

        target = parsed.path

        if parsed.query:
            target = f"{target}?{parsed.query}"

        connection = http.client.HTTPSConnection(
            host=hostname,
            port=parsed.port or 443,
            timeout=timeout_seconds,
        )

        try:
            connection.request(
                "GET",
                target,
                headers=dict(headers),
            )
            response = connection.getresponse()
            body = response.read(max_response_bytes + 1)
            response_headers = {
                key.lower(): value.strip() for key, value in response.getheaders()
            }
            return GhsaHttpResponse(
                status_code=response.status,
                body=body,
                headers=response_headers,
            )
        except (OSError, http.client.HTTPException) as exc:
            raise GhsaSourceUnavailableError(
                "GHSA HTTPS transport failed before a complete response was available."
            ) from exc
        finally:
            connection.close()


class GhsaAuthenticatedPageSource:
    """Retrieve exact GHSA pages with bounded retries and credential isolation."""

    USER_AGENT = "opslens-ghsa-ingestion/0.1"
    RETRYABLE_SERVER_STATUSES = frozenset({500, 502, 503, 504})

    def __init__(
        self,
        *,
        credential_provider: GhsaCredentialProvider,
        transport: GhsaHttpTransport,
        retry_delay_policy: GhsaRetryDelayPolicy,
        telemetry: OperationalTelemetry,
        timeout_seconds: float = 15.0,
        max_attempts: int = 3,
        sleep_fn: Callable[[float], None] = time.sleep,
        epoch_fn: Callable[[], float] = time.time,
    ) -> None:
        """Initialize authenticated bounded GitHub retrieval."""
        if timeout_seconds <= 0:
            raise ValueError("GHSA HTTP timeout must be positive.")

        if type(max_attempts) is not int or max_attempts <= 0:
            raise ValueError("GHSA HTTP max_attempts must be a positive integer.")

        self._credentials = credential_provider
        self._transport = transport
        self._retry_policy = retry_delay_policy
        self._telemetry = telemetry
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts
        self._sleep = sleep_fn
        self._epoch = epoch_fn

    def fetch(
        self,
        *,
        request_url: str,
        window: GhsaSyncWindow,
    ) -> GhsaFetchedPage:
        """Fetch one exact page without exposing the token to evidence or logs."""
        GhsaRequestUrlPolicy.validate(
            request_url,
            window=window,
            require_cursor=None,
        )
        token = self._credentials.get_token()

        if not token.strip():
            raise GhsaAuthenticationError("GHSA GitHub credential is empty.")

        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": self.USER_AGENT,
            "X-GitHub-Api-Version": window.API_VERSION,
        }
        consecutive_rate_limits = 0

        for attempt in range(1, self._max_attempts + 1):
            self._telemetry.metric(
                name="GhsaApiRequest",
                value=1.0,
                unit="Count",
            )
            self._telemetry.info(
                "Fetching GitHub security advisory page",
                fields={
                    "attempt": attempt,
                    "max_attempts": self._max_attempts,
                    "mode": window.mode.value,
                    "sync_id": window.sync_id,
                },
            )

            try:
                with self._telemetry.span("ghsa.api.fetch_page"):
                    response = self._transport.get(
                        url=request_url,
                        headers=headers,
                        timeout_seconds=self._timeout_seconds,
                        max_response_bytes=GhsaAdvisoryApiPageParser.MAX_PAGE_BYTES,
                    )
            except GhsaSourceUnavailableError:
                if attempt < self._max_attempts:
                    delay = float(2 ** (attempt - 1))
                    self._record_retry(
                        attempt=attempt,
                        reason="transport",
                        delay_seconds=delay,
                    )
                    self._sleep(delay)
                    continue
                raise

            if len(response.body) > GhsaAdvisoryApiPageParser.MAX_PAGE_BYTES:
                raise GhsaResponseTooLargeError(
                    "GHSA API response exceeded the 8 MiB page safety cap."
                )

            if response.status_code == 200:
                self._telemetry.metric(
                    name="GhsaApiFetchSuccess",
                    value=1.0,
                    unit="Count",
                )
                self._telemetry.metric(
                    name="GhsaApiPayloadBytes",
                    value=float(len(response.body)),
                    unit="Bytes",
                )
                return GhsaFetchedPage(
                    payload=response.body,
                    link_header=response.headers.get("link"),
                )

            if response.status_code == 401:
                raise GhsaAuthenticationError(
                    "GitHub rejected the configured GHSA credential."
                )

            if response.status_code in {403, 429}:
                consecutive_rate_limits += 1

                try:
                    delay = self._retry_policy.rate_limit_delay_seconds(
                        status_code=response.status_code,
                        headers=response.headers,
                        now_epoch_seconds=self._epoch(),
                        consecutive_rate_limit_failures=consecutive_rate_limits,
                    )
                except GhsaRetryDelayBudgetExceededError as exc:
                    self._telemetry.metric(
                        name="GhsaApiRateLimitWaitBudgetExceeded",
                        value=1.0,
                        unit="Count",
                    )
                    self._telemetry.info(
                        "GitHub rate-limit wait exceeds GHSA runtime budget",
                        fields={
                            "attempt": attempt,
                            "max_attempts": self._max_attempts,
                            "mode": window.mode.value,
                            "sync_id": window.sync_id,
                        },
                    )
                    raise GhsaRateLimitExhaustedError(
                        "GitHub rate-limit wait exceeds the bounded GHSA runtime retry budget."
                    ) from exc

                if delay is not None and attempt < self._max_attempts:
                    self._record_retry(
                        attempt=attempt,
                        reason="rate_limit",
                        delay_seconds=delay,
                    )
                    self._sleep(delay)
                    continue

                raise GhsaRateLimitExhaustedError(
                    "GitHub rate-limit retry budget was exhausted."
                )

            if (
                response.status_code in self.RETRYABLE_SERVER_STATUSES
                and attempt < self._max_attempts
            ):
                delay = float(2 ** (attempt - 1))
                self._record_retry(
                    attempt=attempt,
                    reason="server_error",
                    delay_seconds=delay,
                )
                self._sleep(delay)
                continue

            raise GhsaSourceUnavailableError(
                f"GitHub advisory API returned HTTP {response.status_code}."
            )

        raise AssertionError("GHSA HTTP retry loop terminated unexpectedly.")

    def _record_retry(
        self,
        *,
        attempt: int,
        reason: str,
        delay_seconds: float,
    ) -> None:
        """Record one bounded retry without logging credential material."""
        self._telemetry.metric(
            name="GhsaApiRetry",
            value=1.0,
            unit="Count",
        )
        self._telemetry.info(
            "Retrying GitHub security advisory page",
            fields={
                "attempt": attempt,
                "delay_seconds": delay_seconds,
                "retry_reason": reason,
            },
        )
