"""Unit tests for EPSS ingestion environment configuration."""

import pytest

from opslens.ingestion.epss.config import (
    ConfigurationError,
    EpssIngestionSettings,
)


def test_load_settings_with_required_bucket_and_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load required configuration while preserving safe defaults."""
    monkeypatch.setenv(
        "EPSS_BRONZE_BUCKET",
        "opslens-test-data",
    )
    monkeypatch.delenv("EPSS_SOURCE_URL", raising=False)
    monkeypatch.delenv("EPSS_BRONZE_PREFIX", raising=False)
    monkeypatch.delenv("EPSS_HTTP_TIMEOUT_SECONDS", raising=False)

    settings = EpssIngestionSettings.from_environment()

    assert settings.bronze_bucket == "opslens-test-data"
    assert settings.source_url == "https://epss.empiricalsecurity.com/epss_scores-current.csv.gz"
    assert settings.bronze_prefix == "bronze/epss"
    assert settings.http_timeout_seconds == 15.0


def test_load_settings_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load deployment-specific configuration from environment variables."""
    monkeypatch.setenv(
        "EPSS_SOURCE_URL",
        "https://example.test/epss.csv.gz",
    )
    monkeypatch.setenv(
        "EPSS_BRONZE_BUCKET",
        "custom-bucket",
    )
    monkeypatch.setenv(
        "EPSS_BRONZE_PREFIX",
        "/custom/epss/",
    )
    monkeypatch.setenv(
        "EPSS_HTTP_TIMEOUT_SECONDS",
        "30",
    )

    settings = EpssIngestionSettings.from_environment()

    assert settings.source_url == "https://example.test/epss.csv.gz"
    assert settings.bronze_bucket == "custom-bucket"
    assert settings.bronze_prefix == "custom/epss"
    assert settings.http_timeout_seconds == 30.0


def test_reject_missing_bronze_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject configuration without the required Bronze bucket."""
    monkeypatch.delenv("EPSS_BRONZE_BUCKET", raising=False)

    with pytest.raises(
        ConfigurationError,
        match="EPSS_BRONZE_BUCKET",
    ):
        EpssIngestionSettings.from_environment()


def test_reject_non_numeric_http_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject a non-numeric HTTP timeout configuration."""
    monkeypatch.setenv(
        "EPSS_BRONZE_BUCKET",
        "opslens-test-data",
    )
    monkeypatch.setenv(
        "EPSS_HTTP_TIMEOUT_SECONDS",
        "invalid",
    )

    with pytest.raises(
        ConfigurationError,
        match="must be numeric",
    ):
        EpssIngestionSettings.from_environment()


def test_reject_non_positive_http_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject HTTP timeout values that are zero or negative."""
    monkeypatch.setenv(
        "EPSS_BRONZE_BUCKET",
        "opslens-test-data",
    )
    monkeypatch.setenv(
        "EPSS_HTTP_TIMEOUT_SECONDS",
        "0",
    )

    with pytest.raises(
        ConfigurationError,
        match="greater than zero",
    ):
        EpssIngestionSettings.from_environment()
