"""Tests for NVD Silver runtime configuration."""

import pytest

from opslens.transformation.nvd.config import (
    NvdSilverConfigurationError,
    NvdSilverTransformationSettings,
)


def test_loads_required_data_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load one valid NVD Silver data bucket."""
    monkeypatch.setenv(
        "NVD_DATA_BUCKET",
        "opslens-dev-data",
    )

    settings = NvdSilverTransformationSettings.from_environment()

    assert settings.data_bucket == "opslens-dev-data"


def test_normalizes_surrounding_bucket_whitespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Strip surrounding whitespace from the configured bucket."""
    monkeypatch.setenv(
        "NVD_DATA_BUCKET",
        "  opslens-dev-data  ",
    )

    settings = NvdSilverTransformationSettings.from_environment()

    assert settings.data_bucket == "opslens-dev-data"


def test_rejects_missing_data_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail closed when the data bucket is not configured."""
    monkeypatch.delenv(
        "NVD_DATA_BUCKET",
        raising=False,
    )

    with pytest.raises(
        NvdSilverConfigurationError,
        match="NVD_DATA_BUCKET",
    ):
        NvdSilverTransformationSettings.from_environment()


def test_rejects_whitespace_only_data_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject a bucket value containing only whitespace."""
    monkeypatch.setenv(
        "NVD_DATA_BUCKET",
        "   ",
    )

    with pytest.raises(
        NvdSilverConfigurationError,
        match="NVD_DATA_BUCKET",
    ):
        NvdSilverTransformationSettings.from_environment()
