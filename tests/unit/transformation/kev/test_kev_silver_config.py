"""Unit tests for CISA KEV Silver runtime configuration."""

import pytest

from opslens.transformation.kev.config import (
    ConfigurationError,
    KevSilverTransformationSettings,
)


def test_loads_required_bucket_and_default_silver_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load the data bucket while defaulting the canonical Silver prefix."""
    monkeypatch.setenv(
        "KEV_DATA_BUCKET",
        "opslens-dev-data-487757851499-us-east-1",
    )
    monkeypatch.delenv(
        "KEV_SILVER_PREFIX",
        raising=False,
    )

    settings = KevSilverTransformationSettings.from_environment()

    assert settings.data_bucket == "opslens-dev-data-487757851499-us-east-1"
    assert settings.silver_prefix == "silver/kev"


def test_normalizes_configured_silver_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Normalize environment boundary slashes around the Silver prefix."""
    monkeypatch.setenv(
        "KEV_DATA_BUCKET",
        "bucket",
    )
    monkeypatch.setenv(
        "KEV_SILVER_PREFIX",
        "/custom/kev/",
    )

    settings = KevSilverTransformationSettings.from_environment()

    assert settings.silver_prefix == "custom/kev"


def test_rejects_missing_data_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require an explicit OpsLens data bucket."""
    monkeypatch.delenv(
        "KEV_DATA_BUCKET",
        raising=False,
    )

    with pytest.raises(
        ConfigurationError,
        match="KEV_DATA_BUCKET",
    ):
        KevSilverTransformationSettings.from_environment()


def test_rejects_empty_silver_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject an empty configured KEV Silver prefix."""
    monkeypatch.setenv(
        "KEV_DATA_BUCKET",
        "bucket",
    )
    monkeypatch.setenv(
        "KEV_SILVER_PREFIX",
        "///",
    )

    with pytest.raises(
        ConfigurationError,
        match="KEV_SILVER_PREFIX",
    ):
        KevSilverTransformationSettings.from_environment()
