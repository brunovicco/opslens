"""HTTP adapter for retrieving FIRST EPSS snapshots."""

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from opslens.shared.observability.ports import OperationalTelemetry


class EpssSourceUnavailableError(RuntimeError):
    """Raised when the FIRST EPSS source cannot be retrieved."""


class FirstHttpEpssSnapshotSource:
    """Retrieve the current EPSS snapshot from FIRST over HTTPS."""

    USER_AGENT = "opslens-epss-ingestion/0.1"

    def __init__(
        self,
        source_url: str,
        timeout_seconds: float,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize the FIRST HTTP adapter with explicit dependencies.

        Args:
            source_url: EPSS source URL.
            timeout_seconds: Maximum HTTP request duration.
            telemetry: Operational telemetry implementation.

        Raises:
            ValueError: If the source URL is empty or the timeout is invalid.
        """
        normalized_source_url = source_url.strip()

        if not normalized_source_url:
            raise ValueError("EPSS source URL cannot be empty.")

        if timeout_seconds <= 0:
            raise ValueError("HTTP timeout must be greater than zero.")

        self._source_url = normalized_source_url
        self._timeout_seconds = timeout_seconds
        self._telemetry = telemetry

    def fetch(self) -> bytes:
        """Download and return the current raw EPSS artifact.

        Returns:
            Original response body received from FIRST.

        Raises:
            EpssSourceUnavailableError: If the source cannot be retrieved or
                returns an empty payload.
        """
        request = self._build_request()

        self._telemetry.info(
            "Fetching EPSS source snapshot",
            fields={
                "source_url": self._source_url,
                "timeout_seconds": self._timeout_seconds,
            },
        )

        try:
            with self._telemetry.span("epss.first_http.fetch"):
                payload, status_code = self._execute_request(request)

        except HTTPError as exc:
            self._record_failure(
                message="EPSS source returned an HTTP error",
                fields={
                    "status_code": exc.code,
                    "reason": str(exc.reason),
                },
            )

            raise EpssSourceUnavailableError(f"EPSS source returned HTTP {exc.code}.") from exc

        except URLError as exc:
            self._record_failure(
                message="Unable to reach EPSS source",
                fields={
                    "reason": str(exc.reason),
                },
            )

            raise EpssSourceUnavailableError("Unable to reach EPSS source.") from exc

        except TimeoutError as exc:
            self._record_failure(
                message="EPSS source request timed out",
                fields={
                    "timeout_seconds": self._timeout_seconds,
                },
            )

            raise EpssSourceUnavailableError("EPSS source request timed out.") from exc

        if not payload:
            self._record_failure(
                message="EPSS source returned an empty response",
                fields={
                    "status_code": status_code,
                },
            )

            raise EpssSourceUnavailableError("EPSS source returned an empty response.")

        self._record_success(
            payload_size_bytes=len(payload),
            status_code=status_code,
        )

        return payload

    def _build_request(self) -> Request:
        """Build the HTTP request sent to the FIRST EPSS endpoint."""
        return Request(
            self._source_url,
            headers={
                "User-Agent": self.USER_AGENT,
                "Accept": "application/gzip",
            },
            method="GET",
        )

    def _execute_request(
        self,
        request: Request,
    ) -> tuple[bytes, int]:
        """Execute the HTTP request and return its payload and status code.

        Args:
            request: Prepared EPSS HTTP request.

        Returns:
            Tuple containing the raw response bytes and HTTP status code.

        Raises:
            HTTPError: If the remote endpoint returns an HTTP error.
            URLError: If the remote endpoint cannot be reached.
            TimeoutError: If the request exceeds the configured timeout.
        """
        with urlopen(
            request,
            timeout=self._timeout_seconds,
        ) as response:
            payload = response.read()
            status_code = response.status

        return payload, status_code

    def _record_success(
        self,
        payload_size_bytes: int,
        status_code: int,
    ) -> None:
        """Record telemetry for a successful EPSS source retrieval."""
        self._telemetry.metric(
            name="EpssSourceFetchSuccess",
            value=1.0,
            unit="Count",
        )

        self._telemetry.metric(
            name="EpssSourcePayloadBytes",
            value=float(payload_size_bytes),
            unit="Bytes",
        )

        self._telemetry.info(
            "EPSS source snapshot downloaded",
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
        """Record telemetry for a failed EPSS source retrieval."""
        self._telemetry.metric(
            name="EpssSourceFetchFailure",
            value=1.0,
            unit="Count",
        )

        self._telemetry.exception(
            message,
            fields=fields,
        )
