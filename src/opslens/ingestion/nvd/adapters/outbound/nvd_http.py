"""HTTP adapter for retrieving NVD JSON 2.0 yearly-feed artifacts."""

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from opslens.shared.observability.ports import OperationalTelemetry


class NvdSourceUnavailableError(RuntimeError):
    """Raised when an NVD source artifact cannot be retrieved."""


class NvdSourceTooLargeError(RuntimeError):
    """Raised when an NVD source response exceeds its defensive size limit."""


class NvdHttpYearlyFeedSource:
    """Retrieve exact NVD JSON 2.0 yearly-feed artifacts over HTTPS."""

    USER_AGENT = "opslens-nvd-ingestion/0.1"

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        max_meta_bytes: int,
        max_feed_bytes: int,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize bounded NVD yearly-feed retrieval.

        Args:
            base_url: Base URL containing NVD JSON 2.0 CVE feed artifacts.
            timeout_seconds: Per-request HTTP timeout.
            max_meta_bytes: Defensive maximum size of one META response.
            max_feed_bytes: Defensive maximum size of one gzip response.
            telemetry: Operational telemetry implementation.
        """
        normalized_base_url = base_url.strip().rstrip("/")

        if not normalized_base_url:
            raise ValueError("NVD source base URL cannot be empty.")

        if timeout_seconds <= 0:
            raise ValueError("HTTP timeout must be greater than zero.")

        if max_meta_bytes <= 0:
            raise ValueError("NVD maximum META size must be greater than zero.")

        if max_feed_bytes <= 0:
            raise ValueError("NVD maximum feed size must be greater than zero.")

        self._base_url = normalized_base_url
        self._timeout_seconds = timeout_seconds
        self._max_meta_bytes = max_meta_bytes
        self._max_feed_bytes = max_feed_bytes
        self._telemetry = telemetry

    def fetch_meta(self, feed_year: int) -> bytes:
        """Fetch the exact bounded META artifact for one yearly feed."""
        self._validate_feed_year(feed_year)

        return self._fetch_bounded(
            url=self._build_meta_url(feed_year),
            max_bytes=self._max_meta_bytes,
            accept="text/plain",
            artifact_kind="meta",
            span_name="nvd.http.fetch_meta",
        )

    def fetch_gzip(self, feed_year: int) -> bytes:
        """Fetch the exact bounded gzip artifact for one yearly feed."""
        self._validate_feed_year(feed_year)

        return self._fetch_bounded(
            url=self._build_gzip_url(feed_year),
            max_bytes=self._max_feed_bytes,
            # NVD serves yearly GZ feeds as application/x-gzip.
            # Artifact integrity is verified independently against META.
            accept="*/*",
            artifact_kind="gzip",
            span_name="nvd.http.fetch_gzip",
        )

    def _fetch_bounded(
        self,
        *,
        url: str,
        max_bytes: int,
        accept: str,
        artifact_kind: str,
        span_name: str,
    ) -> bytes:
        """Fetch one source artifact using a bounded HTTP read."""
        request = Request(
            url,
            headers={
                "User-Agent": self.USER_AGENT,
                "Accept": accept,
            },
            method="GET",
        )

        self._telemetry.info(
            "Fetching NVD source artifact",
            fields={
                "artifact_kind": artifact_kind,
                "source_url": url,
                "timeout_seconds": self._timeout_seconds,
                "max_source_bytes": max_bytes,
            },
        )

        try:
            with self._telemetry.span(span_name):
                payload, status_code = self._execute_request(
                    request=request,
                    max_bytes=max_bytes,
                )

        except HTTPError as exc:
            self._record_failure(
                artifact_kind=artifact_kind,
                message="NVD source returned an HTTP error",
                fields={
                    "status_code": exc.code,
                    "reason": str(exc.reason),
                },
            )

            raise NvdSourceUnavailableError(
                f"NVD {artifact_kind} source returned HTTP {exc.code}."
            ) from exc

        except URLError as exc:
            self._record_failure(
                artifact_kind=artifact_kind,
                message="Unable to reach NVD source",
                fields={
                    "reason": str(exc.reason),
                },
            )

            raise NvdSourceUnavailableError(f"Unable to reach NVD {artifact_kind} source.") from exc

        except TimeoutError as exc:
            self._record_failure(
                artifact_kind=artifact_kind,
                message="NVD source request timed out",
                fields={
                    "timeout_seconds": self._timeout_seconds,
                },
            )

            raise NvdSourceUnavailableError(
                f"NVD {artifact_kind} source request timed out."
            ) from exc

        if not payload:
            self._record_failure(
                artifact_kind=artifact_kind,
                message="NVD source returned an empty response",
                fields={
                    "status_code": status_code,
                },
            )

            raise NvdSourceUnavailableError(
                f"NVD {artifact_kind} source returned an empty response."
            )

        if len(payload) > max_bytes:
            self._record_failure(
                artifact_kind=artifact_kind,
                message="NVD source exceeded configured size limit",
                fields={
                    "status_code": status_code,
                    "max_source_bytes": max_bytes,
                    "observed_bytes": len(payload),
                },
            )

            raise NvdSourceTooLargeError(
                f"NVD {artifact_kind} source exceeded configured size limit."
            )

        self._record_success(
            artifact_kind=artifact_kind,
            payload_size_bytes=len(payload),
            status_code=status_code,
        )

        return payload

    def _execute_request(
        self,
        *,
        request: Request,
        max_bytes: int,
    ) -> tuple[bytes, int]:
        """Execute one HTTP request while reading at most limit plus one."""
        with urlopen(
            request,
            timeout=self._timeout_seconds,
        ) as response:
            payload = response.read(max_bytes + 1)
            status_code = response.status

        return payload, status_code

    def _build_meta_url(self, feed_year: int) -> str:
        """Build the canonical META URL for one yearly feed."""
        return f"{self._base_url}/nvdcve-2.0-{feed_year}.meta"

    def _build_gzip_url(self, feed_year: int) -> str:
        """Build the canonical gzip URL for one yearly feed."""
        return f"{self._base_url}/nvdcve-2.0-{feed_year}.json.gz"

    @staticmethod
    def _validate_feed_year(feed_year: int) -> None:
        """Require one four-digit integer yearly-feed identifier."""
        if type(feed_year) is not int:
            raise ValueError("NVD feed year must be an integer.")

        if feed_year < 1000 or feed_year > 9999:
            raise ValueError("NVD feed year must contain exactly four digits.")

    def _record_success(
        self,
        *,
        artifact_kind: str,
        payload_size_bytes: int,
        status_code: int,
    ) -> None:
        """Record successful NVD source retrieval telemetry."""
        self._telemetry.metric(
            name="NvdSourceFetchSuccess",
            value=1.0,
            unit="Count",
        )
        self._telemetry.metric(
            name="NvdSourcePayloadBytes",
            value=float(payload_size_bytes),
            unit="Bytes",
        )
        self._telemetry.info(
            "NVD source artifact downloaded",
            fields={
                "artifact_kind": artifact_kind,
                "status_code": status_code,
                "payload_size_bytes": payload_size_bytes,
            },
        )

    def _record_failure(
        self,
        *,
        artifact_kind: str,
        message: str,
        fields: dict[str, object],
    ) -> None:
        """Record failed NVD source retrieval telemetry."""
        self._telemetry.metric(
            name="NvdSourceFetchFailure",
            value=1.0,
            unit="Count",
        )

        failure_fields = {
            "artifact_kind": artifact_kind,
            **fields,
        }

        self._telemetry.exception(
            message,
            fields=failure_fields,
        )
