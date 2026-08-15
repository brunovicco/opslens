"""Environment-based configuration for EPSS ingestion."""

import os
from dataclasses import dataclass


class ConfigurationError(RuntimeError):
    """Raised when required runtime configuration is invalid or missing."""


@dataclass(frozen=True, slots=True)
class EpssIngestionSettings:
    """Represent runtime configuration for EPSS ingestion.

    Attributes:
        source_url: URL used to download the current FIRST EPSS snapshot.
        bronze_bucket: S3 bucket that stores Bronze artifacts.
        bronze_prefix: S3 prefix used for EPSS Bronze snapshots.
        http_timeout_seconds: Timeout for the FIRST HTTP request.
    """

    source_url: str
    bronze_bucket: str
    bronze_prefix: str
    http_timeout_seconds: float

    @classmethod
    def from_environment(cls) -> "EpssIngestionSettings":
        """Build settings from environment variables.

        Returns:
            Validated EPSS ingestion settings.

        Raises:
            ConfigurationError: If required environment variables are
                missing or invalid.
        """
        source_url = os.getenv(
            "EPSS_SOURCE_URL",
            "https://epss.empiricalsecurity.com/epss_scores-current.csv.gz",
        )

        bronze_bucket = os.getenv("EPSS_BRONZE_BUCKET", "").strip()

        if not bronze_bucket:
            raise ConfigurationError("EPSS_BRONZE_BUCKET environment variable is required.")

        bronze_prefix = os.getenv(
            "EPSS_BRONZE_PREFIX",
            "bronze/epss",
        ).strip("/")

        if not bronze_prefix:
            raise ConfigurationError("EPSS_BRONZE_PREFIX cannot be empty.")

        raw_timeout = os.getenv("EPSS_HTTP_TIMEOUT_SECONDS", "15")

        try:
            timeout = float(raw_timeout)
        except ValueError as exc:
            raise ConfigurationError("EPSS_HTTP_TIMEOUT_SECONDS must be numeric.") from exc

        if timeout <= 0:
            raise ConfigurationError("EPSS_HTTP_TIMEOUT_SECONDS must be greater than zero.")

        return cls(
            source_url=source_url,
            bronze_bucket=bronze_bucket,
            bronze_prefix=bronze_prefix,
            http_timeout_seconds=timeout,
        )
