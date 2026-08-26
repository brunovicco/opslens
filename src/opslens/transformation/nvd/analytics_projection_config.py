"""Environment configuration for the permanent NVD analytics projector."""

import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NvdAnalyticsProjectionRuntimeSettingsV1:
    """Represent the minimal environment-owned analytics runtime settings."""

    data_bucket: str

    def __post_init__(self) -> None:
        """Validate exact non-empty runtime coordinates."""
        if not self.data_bucket or self.data_bucket != self.data_bucket.strip():
            raise ValueError(
                "NVD analytics data bucket must be exact and non-empty."
            )

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> "NvdAnalyticsProjectionRuntimeSettingsV1":
        """Load required analytics settings from an environment mapping."""
        source = os.environ if environ is None else environ
        data_bucket = source.get(
            "NVD_DATA_BUCKET",
            "",
        ).strip()

        if not data_bucket:
            raise RuntimeError(
                "NVD_DATA_BUCKET is required for NVD analytics projection."
            )

        return cls(
            data_bucket=data_bucket,
        )
