"""Environment configuration for NVD incremental runtime."""

import os
from dataclasses import dataclass
from typing import ClassVar

from opslens.ingestion.nvd.domain.api_page import MAX_RESULTS_PER_PAGE


class NvdIncrementalRuntimeConfigurationError(RuntimeError):
    """Raised when NVD incremental runtime configuration is invalid."""


@dataclass(frozen=True, slots=True)
class NvdIncrementalRuntimeSettingsV1:
    """Represent validated configuration for incremental NVD runtime."""

    DEFAULT_WATERMARK_KEY: ClassVar[str] = (
        "control/nvd/cve/incremental/watermark.json"
    )
    DEFAULT_BRONZE_PREFIX: ClassVar[str] = "bronze/nvd/cve/updates"
    DEFAULT_CVE_API_BASE_URL: ClassVar[str] = (
        "https://services.nvd.nist.gov/rest/json/cves/2.0"
    )
    DEFAULT_CVE_API_TIMEOUT_SECONDS: ClassVar[float] = 30.0
    DEFAULT_CVE_API_MAX_RESPONSE_BYTES: ClassVar[int] = 16 * 1024 * 1024
    DEFAULT_CVE_API_MINIMUM_INTERVAL_SECONDS: ClassVar[float] = 6.0
    DEFAULT_CVE_API_MAX_ATTEMPTS: ClassVar[int] = 3
    DEFAULT_CVE_API_RESULTS_PER_PAGE: ClassVar[int] = 500

    bucket_name: str
    watermark_key: str
    bronze_prefix: str
    cve_api_base_url: str
    cve_api_timeout_seconds: float
    cve_api_max_response_bytes: int
    cve_api_minimum_interval_seconds: float
    cve_api_max_attempts: int
    cve_api_results_per_page: int = DEFAULT_CVE_API_RESULTS_PER_PAGE

    def __post_init__(self) -> None:
        """Validate incremental runtime configuration."""
        bucket_name = self.bucket_name.strip()
        watermark_key = self.watermark_key.strip("/")
        bronze_prefix = self.bronze_prefix.strip("/")
        cve_api_base_url = self.cve_api_base_url.strip().rstrip("/?")

        if not bucket_name:
            raise ValueError(
                "NVD incremental runtime bucket name cannot be empty."
            )

        if not watermark_key:
            raise ValueError(
                "NVD incremental runtime watermark key cannot be empty."
            )

        if not bronze_prefix:
            raise ValueError(
                "NVD incremental runtime Bronze prefix cannot be empty."
            )

        if not cve_api_base_url:
            raise ValueError(
                "NVD incremental runtime CVE API base URL cannot be empty."
            )

        if self.cve_api_timeout_seconds <= 0:
            raise ValueError(
                "NVD incremental runtime CVE API timeout must be positive."
            )

        if self.cve_api_max_response_bytes <= 0:
            raise ValueError(
                "NVD incremental runtime CVE API maximum response size "
                "must be positive."
            )

        if self.cve_api_minimum_interval_seconds < 0:
            raise ValueError(
                "NVD incremental runtime CVE API minimum interval "
                "must not be negative."
            )

        if (
            type(self.cve_api_max_attempts) is not int
            or self.cve_api_max_attempts <= 0
        ):
            raise ValueError(
                "NVD incremental runtime CVE API max attempts "
                "must be a positive integer."
            )

        if (
            type(self.cve_api_results_per_page) is not int
            or self.cve_api_results_per_page <= 0
            or self.cve_api_results_per_page > MAX_RESULTS_PER_PAGE
        ):
            raise ValueError(
                "NVD incremental runtime CVE API results per page must be "
                f"between 1 and {MAX_RESULTS_PER_PAGE}."
            )

        object.__setattr__(self, "bucket_name", bucket_name)
        object.__setattr__(self, "watermark_key", watermark_key)
        object.__setattr__(self, "bronze_prefix", bronze_prefix)
        object.__setattr__(self, "cve_api_base_url", cve_api_base_url)

    @classmethod
    def from_environment(cls) -> "NvdIncrementalRuntimeSettingsV1":
        """Build validated incremental NVD runtime settings from environment."""
        bucket_name = os.getenv(
            "NVD_DATA_BUCKET",
            "",
        ).strip()

        if not bucket_name:
            raise NvdIncrementalRuntimeConfigurationError(
                "NVD_DATA_BUCKET environment variable is required."
            )

        try:
            return cls(
                bucket_name=bucket_name,
                watermark_key=os.getenv(
                    "NVD_WATERMARK_KEY",
                    cls.DEFAULT_WATERMARK_KEY,
                ),
                bronze_prefix=os.getenv(
                    "NVD_INCREMENTAL_BRONZE_PREFIX",
                    cls.DEFAULT_BRONZE_PREFIX,
                ),
                cve_api_base_url=os.getenv(
                    "NVD_CVE_API_BASE_URL",
                    cls.DEFAULT_CVE_API_BASE_URL,
                ),
                cve_api_timeout_seconds=cls._positive_float(
                    environment_name="NVD_CVE_API_TIMEOUT_SECONDS",
                    default=cls.DEFAULT_CVE_API_TIMEOUT_SECONDS,
                ),
                cve_api_max_response_bytes=cls._positive_integer(
                    environment_name="NVD_CVE_API_MAX_RESPONSE_BYTES",
                    default=cls.DEFAULT_CVE_API_MAX_RESPONSE_BYTES,
                ),
                cve_api_minimum_interval_seconds=cls._non_negative_float(
                    environment_name=(
                        "NVD_CVE_API_MINIMUM_INTERVAL_SECONDS"
                    ),
                    default=cls.DEFAULT_CVE_API_MINIMUM_INTERVAL_SECONDS,
                ),
                cve_api_max_attempts=cls._positive_integer(
                    environment_name="NVD_CVE_API_MAX_ATTEMPTS",
                    default=cls.DEFAULT_CVE_API_MAX_ATTEMPTS,
                ),
                cve_api_results_per_page=cls._positive_integer(
                    environment_name="NVD_CVE_API_RESULTS_PER_PAGE",
                    default=cls.DEFAULT_CVE_API_RESULTS_PER_PAGE,
                ),
            )
        except ValueError as exc:
            raise NvdIncrementalRuntimeConfigurationError(
                "NVD incremental runtime environment configuration "
                "is invalid."
            ) from exc

    @staticmethod
    def _positive_float(
        *,
        environment_name: str,
        default: float,
    ) -> float:
        """Read one strictly positive floating-point environment value."""
        raw_value = os.getenv(
            environment_name,
            str(default),
        )

        try:
            value = float(raw_value)
        except ValueError as exc:
            raise ValueError(
                f"{environment_name} must be numeric."
            ) from exc

        if value <= 0:
            raise ValueError(
                f"{environment_name} must be greater than zero."
            )

        return value

    @staticmethod
    def _non_negative_float(
        *,
        environment_name: str,
        default: float,
    ) -> float:
        """Read one non-negative floating-point environment value."""
        raw_value = os.getenv(
            environment_name,
            str(default),
        )

        try:
            value = float(raw_value)
        except ValueError as exc:
            raise ValueError(
                f"{environment_name} must be numeric."
            ) from exc

        if value < 0:
            raise ValueError(
                f"{environment_name} must not be negative."
            )

        return value

    @staticmethod
    def _positive_integer(
        *,
        environment_name: str,
        default: int,
    ) -> int:
        """Read one strictly positive integer environment value."""
        raw_value = os.getenv(
            environment_name,
            str(default),
        )

        try:
            value = int(raw_value)
        except ValueError as exc:
            raise ValueError(
                f"{environment_name} must be an integer."
            ) from exc

        if value <= 0:
            raise ValueError(
                f"{environment_name} must be greater than zero."
            )

        return value
