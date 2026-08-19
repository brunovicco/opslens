"""Unit tests for NVD Bootstrap runtime configuration."""

import pytest

from opslens.ingestion.nvd.config import (
    NvdConfigurationError,
    NvdIngestionSettings,
)


def test_settings_load_defaults_and_required_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load safe defaults while requiring the Bronze bucket."""
    monkeypatch.setenv(
        "NVD_BRONZE_BUCKET",
        "opslens-test-data",
    )
    monkeypatch.delenv(
        "NVD_SOURCE_BASE_URL",
        raising=False,
    )
    monkeypatch.delenv(
        "NVD_BRONZE_PREFIX",
        raising=False,
    )
    monkeypatch.delenv(
        "NVD_HTTP_TIMEOUT_SECONDS",
        raising=False,
    )
    monkeypatch.delenv(
        "NVD_MAX_META_BYTES",
        raising=False,
    )
    monkeypatch.delenv(
        "NVD_MAX_FEED_BYTES",
        raising=False,
    )

    settings = NvdIngestionSettings.from_environment()

    assert settings.source_base_url == ("https://nvd.nist.gov/feeds/json/cve/2.0")
    assert settings.bronze_bucket == "opslens-test-data"
    assert settings.bronze_prefix == ("bronze/nvd/cve/bootstrap")
    assert settings.http_timeout_seconds == 30.0
    assert settings.max_meta_bytes == 1024 * 1024
    assert settings.max_feed_bytes == 128 * 1024 * 1024


def test_settings_normalize_base_url_and_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Normalize configurable source URL and Bronze prefix."""
    monkeypatch.setenv(
        "NVD_BRONZE_BUCKET",
        "opslens-test-data",
    )
    monkeypatch.setenv(
        "NVD_SOURCE_BASE_URL",
        "https://example.test/nvd/",
    )
    monkeypatch.setenv(
        "NVD_BRONZE_PREFIX",
        "/custom/nvd/",
    )

    settings = NvdIngestionSettings.from_environment()

    assert settings.source_base_url == ("https://example.test/nvd")
    assert settings.bronze_prefix == "custom/nvd"


def test_settings_require_bronze_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject runtime configuration without an S3 Bronze bucket."""
    monkeypatch.delenv(
        "NVD_BRONZE_BUCKET",
        raising=False,
    )

    with pytest.raises(
        NvdConfigurationError,
        match="NVD_BRONZE_BUCKET",
    ):
        NvdIngestionSettings.from_environment()


@pytest.mark.parametrize(
    ("environment_name", "value"),
    [
        ("NVD_HTTP_TIMEOUT_SECONDS", "0"),
        ("NVD_HTTP_TIMEOUT_SECONDS", "-1"),
        ("NVD_HTTP_TIMEOUT_SECONDS", "invalid"),
        ("NVD_MAX_META_BYTES", "0"),
        ("NVD_MAX_META_BYTES", "-1"),
        ("NVD_MAX_META_BYTES", "invalid"),
        ("NVD_MAX_FEED_BYTES", "0"),
        ("NVD_MAX_FEED_BYTES", "-1"),
        ("NVD_MAX_FEED_BYTES", "invalid"),
    ],
)
def test_settings_reject_invalid_numeric_limits(
    monkeypatch: pytest.MonkeyPatch,
    environment_name: str,
    value: str,
) -> None:
    """Reject malformed or non-positive defensive limits."""
    monkeypatch.setenv(
        "NVD_BRONZE_BUCKET",
        "opslens-test-data",
    )
    monkeypatch.setenv(
        environment_name,
        value,
    )

    with pytest.raises(NvdConfigurationError):
        NvdIngestionSettings.from_environment()
