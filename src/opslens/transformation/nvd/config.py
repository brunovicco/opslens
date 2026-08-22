"""Environment-based configuration for NVD Silver transformation."""

import os
from dataclasses import dataclass


class NvdSilverConfigurationError(RuntimeError):
    """Raised when required NVD Silver runtime configuration is invalid."""


@dataclass(frozen=True, slots=True)
class NvdSilverTransformationSettings:
    """Represent runtime configuration for NVD Silver transformation."""

    data_bucket: str

    @classmethod
    def from_environment(cls) -> "NvdSilverTransformationSettings":
        """Build validated NVD Silver settings from environment variables."""
        data_bucket = os.getenv(
            "NVD_DATA_BUCKET",
            "",
        ).strip()

        if not data_bucket:
            raise NvdSilverConfigurationError("NVD_DATA_BUCKET environment variable is required.")

        return cls(
            data_bucket=data_bucket,
        )
