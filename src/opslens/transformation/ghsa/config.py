"""Configuration boundary for GHSA Silver transformation runtime."""

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GhsaSilverTransformationSettings:
    """Hold bounded runtime settings required by GHSA Silver."""

    data_bucket: str

    def __post_init__(self) -> None:
        """Validate required runtime configuration."""
        if not self.data_bucket.strip():
            raise ValueError("GHSA Silver data bucket cannot be empty.")

    @classmethod
    def from_environment(cls) -> "GhsaSilverTransformationSettings":
        """Load GHSA Silver settings from Lambda environment variables."""
        data_bucket = os.getenv("GHSA_DATA_BUCKET", "").strip()

        if not data_bucket:
            raise RuntimeError("GHSA_DATA_BUCKET is required for GHSA Silver.")

        return cls(data_bucket=data_bucket)
