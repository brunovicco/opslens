"""Environment configuration for the NVD watermark-promotion runtime."""

import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NvdPromotionRuntimeSettingsV1:
    """Represent the minimal environment-owned promotion runtime settings."""

    data_bucket: str
    watermark_key: str

    def __post_init__(self) -> None:
        """Validate exact non-empty runtime coordinates."""
        if not self.data_bucket or self.data_bucket != self.data_bucket.strip():
            raise ValueError(
                "NVD promotion data bucket must be exact and non-empty."
            )

        if not self.watermark_key or self.watermark_key != self.watermark_key.strip():
            raise ValueError(
                "NVD promotion watermark key must be exact and non-empty."
            )

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> "NvdPromotionRuntimeSettingsV1":
        """Load required promotion settings from an environment mapping."""
        source = os.environ if environ is None else environ

        data_bucket = source.get(
            "NVD_DATA_BUCKET",
            "",
        ).strip()
        watermark_key = source.get(
            "NVD_WATERMARK_KEY",
            "",
        ).strip()

        if not data_bucket:
            raise RuntimeError(
                "NVD_DATA_BUCKET is required for NVD watermark promotion."
            )

        if not watermark_key:
            raise RuntimeError(
                "NVD_WATERMARK_KEY is required for NVD watermark promotion."
            )

        return cls(
            data_bucket=data_bucket,
            watermark_key=watermark_key,
        )
