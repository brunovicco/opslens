"""Unit tests for CISA KEV ingestion environment configuration."""

import pytest

from opslens.ingestion.kev.config import (
    ConfigurationError,
    KevIngestionSettings,
)


def test_load_settings_with_required_bucket_and_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load required configuration while preserving safe defaults."""
    monkeypatch.setenv(
        "KEV_BRONZE_BUCKET",
        "opslens-test-data",
    )

    monkeypatch.delenv("KEV_SOURCE_URL", raising=False)
    monkeypatch.delenv("KEV_BRONZE_PREFIX", raising=False)
    monkeypatch.delenv("KEV_HTTP_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("KEV_MAX_SOURCE_BYTES", raising=False)

    settings = KevIngestionSettings.from_environment()

    assert settings.bronze_bucket == "opslens-test-data"
    assert settings.source_url == (
        "https://www.cisa.gov/sites/default/files/feeds/"
        "known_exploited_vulnerabilities.json"
    )
    assert settings.bronze_prefix == "bronze/kev"
    assert settings.http_timeout_seconds == 15.0
    assert settings.max_source_bytes == 10 * 1024 * 1024


def test_load_settings_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load deployment-specific KEV configuration."""
    monkeypatch.setenv(
        "KEV_SOURCE_URL",
        "https://example.test/kev.json",
    )
    monkeypatch.setenv(
        "KEV_BRONZE_BUCKET",
        "custom-bucket",
    )
    monkeypatch.setenv(
        "KEV_BRONZE_PREFIX",
        "/custom/kev/",
    )
    monkeypatch.setenv(
        "KEV_HTTP_TIMEOUT_SECONDS",
        "30",
    )
    monkeypatch.setenv(
        "KEV_MAX_SOURCE_BYTES",
        "2048",
    )

    settings = KevIngestionSettings.from_environment()

    assert settings.source_url == "https://example.test/kev.json"
    assert settings.bronze_bucket == "custom-bucket"
    assert settings.bronze_prefix == "custom/kev"
    assert settings.http_timeout_seconds == 30.0
    assert settings.max_source_bytes == 2048


def test_reject_missing_bronze_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject configuration without the required Bronze bucket."""
    monkeypatch.delenv("KEV_BRONZE_BUCKET", raising=False)

    with pytest.raises(
        ConfigurationError,
        match="KEV_BRONZE_BUCKET",
    ):
        KevIngestionSettings.from_environment()


def test_reject_non_numeric_http_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject a non-numeric HTTP timeout."""
    monkeypatch.setenv(
        "KEV_BRONZE_BUCKET",
        "opslens-test-data",
    )
    monkeypatch.setenv(
        "KEV_HTTP_TIMEOUT_SECONDS",
        "invalid",
    )

    with pytest.raises(
        ConfigurationError,
        match="must be numeric",
    ):
        KevIngestionSettings.from_environment()


def test_reject_non_integer_max_source_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject a non-integer source-size limit."""
    monkeypatch.setenv(
        "KEV_BRONZE_BUCKET",
        "opslens-test-data",
    )
    monkeypatch.setenv(
        "KEV_MAX_SOURCE_BYTES",
        "10mb",
    )

    with pytest.raises(
        ConfigurationError,
        match="must be an integer",
    ):
        KevIngestionSettings.from_environment()


def test_reject_non_positive_max_source_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject zero or negative source-size limits."""
    monkeypatch.setenv(
        "KEV_BRONZE_BUCKET",
        "opslens-test-data",
    )
    monkeypatch.setenv(
        "KEV_MAX_SOURCE_BYTES",
        "0",
    )

    with pytest.raises(
        ConfigurationError,
        match="greater than zero",
    ):
        KevIngestionSettings.from_environment()
