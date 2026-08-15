"""Unit tests for EPSS Silver runtime configuration."""

import pytest

from opslens.transformation.epss.config import (
    ConfigurationError,
    EpssSilverTransformationSettings,
)


def test_loads_required_bucket_and_default_silver_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load the required data bucket and default Silver prefix."""
    monkeypatch.setenv(
        "EPSS_DATA_BUCKET",
        "opslens-test-data",
    )
    monkeypatch.delenv(
        "EPSS_SILVER_PREFIX",
        raising=False,
    )

    settings = EpssSilverTransformationSettings.from_environment()

    assert settings.data_bucket == "opslens-test-data"
    assert settings.silver_prefix == "silver/epss"


def test_loads_explicit_silver_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load an explicitly configured canonical Silver prefix."""
    monkeypatch.setenv(
        "EPSS_DATA_BUCKET",
        "opslens-test-data",
    )
    monkeypatch.setenv(
        "EPSS_SILVER_PREFIX",
        "/analytics/epss/",
    )

    settings = EpssSilverTransformationSettings.from_environment()

    assert settings.silver_prefix == "analytics/epss"


def test_rejects_missing_data_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject runtime configuration without a data bucket."""
    monkeypatch.delenv(
        "EPSS_DATA_BUCKET",
        raising=False,
    )

    with pytest.raises(
        ConfigurationError,
        match="EPSS_DATA_BUCKET environment variable is required",
    ):
        EpssSilverTransformationSettings.from_environment()


def test_rejects_empty_silver_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject runtime configuration with an empty Silver prefix."""
    monkeypatch.setenv(
        "EPSS_DATA_BUCKET",
        "opslens-test-data",
    )
    monkeypatch.setenv(
        "EPSS_SILVER_PREFIX",
        "/",
    )

    with pytest.raises(
        ConfigurationError,
        match="EPSS_SILVER_PREFIX cannot be empty",
    ):
        EpssSilverTransformationSettings.from_environment()
