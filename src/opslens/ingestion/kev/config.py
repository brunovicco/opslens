"""Environment-based configuration for CISA KEV ingestion."""

import os
from dataclasses import dataclass


class ConfigurationError(RuntimeError):
    """Raised when required runtime configuration is invalid or missing."""


@dataclass(frozen=True, slots=True)
class KevIngestionSettings:
    """Represent runtime configuration for CISA KEV ingestion.

    Attributes:
        source_url: Canonical CISA KEV catalog URL.
        bronze_bucket: S3 bucket that stores Bronze artifacts.
        bronze_prefix: S3 prefix used for KEV Bronze observations.
        http_timeout_seconds: Timeout for the CISA HTTP request.
        max_source_bytes: Maximum source payload accepted by the HTTP adapter.
    """

    source_url: str
    bronze_bucket: str
    bronze_prefix: str
    http_timeout_seconds: float
    max_source_bytes: int

    @classmethod
    def from_environment(cls) -> "KevIngestionSettings":
        """Build validated settings from environment variables."""
        source_url = os.getenv(
            "KEV_SOURCE_URL",
            (
                "https://www.cisa.gov/sites/default/files/feeds/"
                "known_exploited_vulnerabilities.json"
            ),
        ).strip()

        if not source_url:
            raise ConfigurationError("KEV_SOURCE_URL cannot be empty.")

        bronze_bucket = os.getenv("KEV_BRONZE_BUCKET", "").strip()

        if not bronze_bucket:
            raise ConfigurationError(
                "KEV_BRONZE_BUCKET environment variable is required."
            )

        bronze_prefix = os.getenv(
            "KEV_BRONZE_PREFIX",
            "bronze/kev",
        ).strip("/")

        if not bronze_prefix:
            raise ConfigurationError("KEV_BRONZE_PREFIX cannot be empty.")

        raw_timeout = os.getenv(
            "KEV_HTTP_TIMEOUT_SECONDS",
            "15",
        )

        try:
            timeout = float(raw_timeout)
        except ValueError as exc:
            raise ConfigurationError(
                "KEV_HTTP_TIMEOUT_SECONDS must be numeric."
            ) from exc

        if timeout <= 0:
            raise ConfigurationError(
                "KEV_HTTP_TIMEOUT_SECONDS must be greater than zero."
            )

        raw_max_source_bytes = os.getenv(
            "KEV_MAX_SOURCE_BYTES",
            str(10 * 1024 * 1024),
        )

        try:
            max_source_bytes = int(raw_max_source_bytes)
        except ValueError as exc:
            raise ConfigurationError(
                "KEV_MAX_SOURCE_BYTES must be an integer."
            ) from exc

        if max_source_bytes <= 0:
            raise ConfigurationError(
                "KEV_MAX_SOURCE_BYTES must be greater than zero."
            )

        return cls(
            source_url=source_url,
            bronze_bucket=bronze_bucket,
            bronze_prefix=bronze_prefix,
            http_timeout_seconds=timeout,
            max_source_bytes=max_source_bytes,
        )
