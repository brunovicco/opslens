"""Environment-based configuration for NVD Bootstrap ingestion."""

import os
from dataclasses import dataclass


class NvdConfigurationError(RuntimeError):
    """Raised when NVD runtime configuration is invalid or missing."""


@dataclass(frozen=True, slots=True)
class NvdIngestionSettings:
    """Represent runtime configuration for NVD Bootstrap ingestion.

    Attributes:
        source_base_url: Base URL containing NVD JSON 2.0 yearly feeds.
        bronze_bucket: S3 bucket storing immutable Bronze evidence.
        bronze_prefix: Prefix used for NVD Bootstrap Bronze objects.
        http_timeout_seconds: Per-request HTTP timeout.
        max_meta_bytes: Defensive maximum META response size.
        max_feed_bytes: Defensive maximum compressed yearly-feed size.
    """

    source_base_url: str
    bronze_bucket: str
    bronze_prefix: str
    http_timeout_seconds: float
    max_meta_bytes: int
    max_feed_bytes: int

    DEFAULT_SOURCE_BASE_URL = "https://nvd.nist.gov/feeds/json/cve/2.0"
    DEFAULT_BRONZE_PREFIX = "bronze/nvd/cve/bootstrap"

    @classmethod
    def from_environment(cls) -> "NvdIngestionSettings":
        """Build validated settings from environment variables."""
        source_base_url = (
            os.getenv(
                "NVD_SOURCE_BASE_URL",
                cls.DEFAULT_SOURCE_BASE_URL,
            )
            .strip()
            .rstrip("/")
        )

        if not source_base_url:
            raise NvdConfigurationError("NVD_SOURCE_BASE_URL cannot be empty.")

        bronze_bucket = os.getenv(
            "NVD_BRONZE_BUCKET",
            "",
        ).strip()

        if not bronze_bucket:
            raise NvdConfigurationError("NVD_BRONZE_BUCKET environment variable is required.")

        bronze_prefix = os.getenv(
            "NVD_BRONZE_PREFIX",
            cls.DEFAULT_BRONZE_PREFIX,
        ).strip("/")

        if not bronze_prefix:
            raise NvdConfigurationError("NVD_BRONZE_PREFIX cannot be empty.")

        timeout = cls._positive_float(
            environment_name="NVD_HTTP_TIMEOUT_SECONDS",
            default="30",
        )

        max_meta_bytes = cls._positive_integer(
            environment_name="NVD_MAX_META_BYTES",
            default=str(1024 * 1024),
        )

        max_feed_bytes = cls._positive_integer(
            environment_name="NVD_MAX_FEED_BYTES",
            default=str(128 * 1024 * 1024),
        )

        return cls(
            source_base_url=source_base_url,
            bronze_bucket=bronze_bucket,
            bronze_prefix=bronze_prefix,
            http_timeout_seconds=timeout,
            max_meta_bytes=max_meta_bytes,
            max_feed_bytes=max_feed_bytes,
        )

    @staticmethod
    def _positive_float(
        *,
        environment_name: str,
        default: str,
    ) -> float:
        """Read one strictly positive floating-point environment value."""
        raw_value = os.getenv(
            environment_name,
            default,
        )

        try:
            value = float(raw_value)
        except ValueError as exc:
            raise NvdConfigurationError(f"{environment_name} must be numeric.") from exc

        if value <= 0:
            raise NvdConfigurationError(f"{environment_name} must be greater than zero.")

        return value

    @staticmethod
    def _positive_integer(
        *,
        environment_name: str,
        default: str,
    ) -> int:
        """Read one strictly positive integer environment value."""
        raw_value = os.getenv(
            environment_name,
            default,
        )

        try:
            value = int(raw_value)
        except ValueError as exc:
            raise NvdConfigurationError(f"{environment_name} must be an integer.") from exc

        if value <= 0:
            raise NvdConfigurationError(f"{environment_name} must be greater than zero.")

        return value
