"""Tests for NVD watermark-promotion runtime configuration."""

import pytest

from opslens.transformation.nvd.promotion_config import (
    NvdPromotionRuntimeSettingsV1,
)


def test_from_environment_loads_required_runtime_coordinates() -> None:
    """Load only the data bucket and authoritative watermark key."""
    settings = NvdPromotionRuntimeSettingsV1.from_environment(
        {
            "NVD_DATA_BUCKET": "opslens-test-data",
            "NVD_WATERMARK_KEY": (
                "control/nvd/cve/incremental/watermark.json"
            ),
        }
    )

    assert settings.data_bucket == "opslens-test-data"
    assert settings.watermark_key == (
        "control/nvd/cve/incremental/watermark.json"
    )


@pytest.mark.parametrize(
    ("environment", "message"),
    [
        (
            {
                "NVD_WATERMARK_KEY": (
                    "control/nvd/cve/incremental/watermark.json"
                ),
            },
            "NVD_DATA_BUCKET",
        ),
        (
            {
                "NVD_DATA_BUCKET": "opslens-test-data",
            },
            "NVD_WATERMARK_KEY",
        ),
    ],
)
def test_from_environment_requires_both_coordinates(
    environment: dict[str, str],
    message: str,
) -> None:
    """Fail before AWS client construction when configuration is incomplete."""
    with pytest.raises(
        RuntimeError,
        match=message,
    ):
        NvdPromotionRuntimeSettingsV1.from_environment(
            environment,
        )
