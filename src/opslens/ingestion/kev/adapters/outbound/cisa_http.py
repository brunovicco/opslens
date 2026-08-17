"""HTTP adapter for retrieving the canonical CISA KEV catalog."""

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from opslens.shared.observability.ports import OperationalTelemetry


class KevSourceUnavailableError(RuntimeError):
    """Raised when the CISA KEV source cannot be retrieved."""


class KevSourceTooLargeError(RuntimeError):
    """Raised when the CISA KEV response exceeds the configured safety limit."""


class CisaHttpKevCatalogSource:
    """Retrieve the canonical CISA KEV catalog over HTTPS."""

    USER_AGENT = "opslens-kev-ingestion/0.1"

    def __init__(
        self,
        source_url: str,
        timeout_seconds: float,
        max_source_bytes: int,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize the CISA HTTP adapter with bounded source retrieval."""
        normalized_source_url = source_url.strip()

        if not normalized_source_url:
            raise ValueError("KEV source URL cannot be empty.")

        if timeout_seconds <= 0:
            raise ValueError("HTTP timeout must be greater than zero.")

        if max_source_bytes <= 0:
            raise ValueError("KEV maximum source size must be greater than zero.")

        self._source_url = normalized_source_url
        self._timeout_seconds = timeout_seconds
        self._max_source_bytes = max_source_bytes
        self._telemetry = telemetry

    def fetch(self) -> bytes:
        """Download and return the original bounded CISA KEV artifact."""
        request = self._build_request()

        self._telemetry.info(
            "Fetching CISA KEV catalog",
            fields={
                "source_url": self._source_url,
                "timeout_seconds": self._timeout_seconds,
                "max_source_bytes": self._max_source_bytes,
            },
        )

        try:
            with self._telemetry.span("kev.cisa_http.fetch"):
                payload, status_code = self._execute_request(request)

        except HTTPError as exc:
            self._record_failure(
                message="CISA KEV source returned an HTTP error",
                fields={
                    "status_code": exc.code,
                    "reason": str(exc.reason),
                },
            )

            raise KevSourceUnavailableError(
                f"CISA KEV source returned HTTP {exc.code}."
            ) from exc

        except URLError as exc:
            self._record_failure(
                message="Unable to reach CISA KEV source",
                fields={
                    "reason": str(exc.reason),
                },
            )

            raise KevSourceUnavailableError(
                "Unable to reach CISA KEV source."
            ) from exc

        except TimeoutError as exc:
            self._record_failure(
                message="CISA KEV source request timed out",
                fields={
                    "timeout_seconds": self._timeout_seconds,
                },
            )

            raise KevSourceUnavailableError(
                "CISA KEV source request timed out."
            ) from exc

        if not payload:
            self._record_failure(
                message="CISA KEV source returned an empty response",
                fields={
                    "status_code": status_code,
                },
            )

            raise KevSourceUnavailableError(
                "CISA KEV source returned an empty response."
            )

        if len(payload) > self._max_source_bytes:
            self._record_failure(
                message="CISA KEV source exceeded the configured size limit",
                fields={
                    "status_code": status_code,
                    "max_source_bytes": self._max_source_bytes,
                    "observed_bytes": len(payload),
                },
            )

            raise KevSourceTooLargeError(
                "CISA KEV source exceeded the configured size limit."
            )

        self._record_success(
            payload_size_bytes=len(payload),
            status_code=status_code,
        )

        return payload

    def _build_request(self) -> Request:
        """Build the HTTP request sent to the canonical CISA endpoint."""
        return Request(
            self._source_url,
            headers={
                "User-Agent": self.USER_AGENT,
                "Accept": "application/json",
            },
            method="GET",
        )

    def _execute_request(
        self,
        request: Request,
    ) -> tuple[bytes, int]:
        """Execute one bounded HTTP request."""
        with urlopen(
            request,
            timeout=self._timeout_seconds,
        ) as response:
            payload = response.read(self._max_source_bytes + 1)
            status_code = response.status

        return payload, status_code

    def _record_success(
        self,
        payload_size_bytes: int,
        status_code: int,
    ) -> None:
        """Record telemetry for successful KEV retrieval."""
        self._telemetry.metric(
            name="KevSourceFetchSuccess",
            value=1.0,
            unit="Count",
        )
        self._telemetry.metric(
            name="KevSourcePayloadBytes",
            value=float(payload_size_bytes),
            unit="Bytes",
        )
        self._telemetry.info(
            "CISA KEV catalog downloaded",
            fields={
                "status_code": status_code,
                "payload_size_bytes": payload_size_bytes,
            },
        )

    def _record_failure(
        self,
        message: str,
        fields: dict[str, object],
    ) -> None:
        """Record telemetry for failed KEV retrieval."""
        self._telemetry.metric(
            name="KevSourceFetchFailure",
            value=1.0,
            unit="Count",
        )
        self._telemetry.exception(
            message,
            fields=fields,
        )
