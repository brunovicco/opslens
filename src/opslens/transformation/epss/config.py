"""Environment-based configuration for EPSS Silver transformation."""

import os
from dataclasses import dataclass


class ConfigurationError(RuntimeError):
    """Raised when required Silver runtime configuration is invalid."""


@dataclass(frozen=True, slots=True)
class EpssSilverTransformationSettings:
    """Represent runtime configuration for EPSS Silver transformation.

    Attributes:
        data_bucket: S3 bucket containing Bronze and Silver EPSS artifacts.
        silver_prefix: S3 prefix used for normalized Silver artifacts.
    """

    data_bucket: str
    silver_prefix: str

    @classmethod
    def from_environment(cls) -> "EpssSilverTransformationSettings":
        """Build transformation settings from environment variables.

        Returns:
            Validated Silver transformation settings.

        Raises:
            ConfigurationError: If required environment variables are
                missing or invalid.
        """
        data_bucket = os.getenv(
            "EPSS_DATA_BUCKET",
            "",
        ).strip()

        if not data_bucket:
            raise ConfigurationError("EPSS_DATA_BUCKET environment variable is required.")

        silver_prefix = os.getenv(
            "EPSS_SILVER_PREFIX",
            "silver/epss",
        ).strip("/")

        if not silver_prefix:
            raise ConfigurationError("EPSS_SILVER_PREFIX cannot be empty.")

        return cls(
            data_bucket=data_bucket,
            silver_prefix=silver_prefix,
        )
