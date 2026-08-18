"""Environment-based configuration for CISA KEV Silver transformation."""

import os
from dataclasses import dataclass


class ConfigurationError(RuntimeError):
    """Raised when required KEV Silver runtime configuration is invalid."""


@dataclass(frozen=True, slots=True)
class KevSilverTransformationSettings:
    """Represent runtime configuration for KEV Silver transformation.

    Attributes:
        data_bucket: S3 bucket containing Bronze and Silver KEV artifacts.
        silver_prefix: S3 prefix used for normalized Silver artifacts.
    """

    data_bucket: str
    silver_prefix: str

    @classmethod
    def from_environment(cls) -> "KevSilverTransformationSettings":
        """Build KEV Silver settings from environment variables.

        Returns:
            Validated KEV Silver runtime settings.

        Raises:
            ConfigurationError: If required environment variables are invalid.
        """
        data_bucket = os.getenv(
            "KEV_DATA_BUCKET",
            "",
        ).strip()

        if not data_bucket:
            raise ConfigurationError("KEV_DATA_BUCKET environment variable is required.")

        raw_silver_prefix = os.getenv(
            "KEV_SILVER_PREFIX",
            "silver/kev",
        ).strip()

        silver_prefix = raw_silver_prefix.strip("/")

        if not silver_prefix:
            raise ConfigurationError("KEV_SILVER_PREFIX cannot be empty.")

        return cls(
            data_bucket=data_bucket,
            silver_prefix=silver_prefix,
        )
