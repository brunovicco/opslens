"""Unit tests for NVD incremental runtime environment configuration."""

import pytest

from opslens.ingestion.nvd.incremental_runtime_config import (
    NvdIncrementalRuntimeConfigurationError,
    NvdIncrementalRuntimeSettingsV1,
)


def test_loads_required_bucket_with_safe_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build runtime configuration using only the required environment."""
    monkeypatch.setenv(
        "NVD_DATA_BUCKET",
        "opslens-dev-data",
    )

    settings = NvdIncrementalRuntimeSettingsV1.from_environment()

    assert settings.bucket_name == "opslens-dev-data"
    assert (
        settings.watermark_key
        == "control/nvd/cve/incremental/watermark.json"
    )
    assert settings.bronze_prefix == "bronze/nvd/cve/updates"
    assert (
        settings.cve_api_base_url
        == "https://services.nvd.nist.gov/rest/json/cves/2.0"
    )
    assert settings.cve_api_timeout_seconds == 30.0
    assert settings.cve_api_max_response_bytes == 16 * 1024 * 1024
    assert settings.cve_api_minimum_interval_seconds == 6.0
    assert settings.cve_api_max_attempts == 3


def test_loads_explicit_environment_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Honor explicit runtime configuration overrides."""
    monkeypatch.setenv(
        "NVD_DATA_BUCKET",
        "custom-data-bucket",
    )
    monkeypatch.setenv(
        "NVD_WATERMARK_KEY",
        "control/custom/watermark.json",
    )
    monkeypatch.setenv(
        "NVD_INCREMENTAL_BRONZE_PREFIX",
        "bronze/custom/updates",
    )
    monkeypatch.setenv(
        "NVD_CVE_API_BASE_URL",
        "https://example.test/cves/2.0",
    )
    monkeypatch.setenv(
        "NVD_CVE_API_TIMEOUT_SECONDS",
        "45",
    )
    monkeypatch.setenv(
        "NVD_CVE_API_MAX_RESPONSE_BYTES",
        "1048576",
    )
    monkeypatch.setenv(
        "NVD_CVE_API_MINIMUM_INTERVAL_SECONDS",
        "7.5",
    )
    monkeypatch.setenv(
        "NVD_CVE_API_MAX_ATTEMPTS",
        "4",
    )

    settings = NvdIncrementalRuntimeSettingsV1.from_environment()

    assert settings.bucket_name == "custom-data-bucket"
    assert settings.watermark_key == "control/custom/watermark.json"
    assert settings.bronze_prefix == "bronze/custom/updates"
    assert settings.cve_api_base_url == "https://example.test/cves/2.0"
    assert settings.cve_api_timeout_seconds == 45.0
    assert settings.cve_api_max_response_bytes == 1_048_576
    assert settings.cve_api_minimum_interval_seconds == 7.5
    assert settings.cve_api_max_attempts == 4


def test_rejects_missing_data_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require the exact S3 data bucket at runtime."""
    monkeypatch.delenv(
        "NVD_DATA_BUCKET",
        raising=False,
    )

    with pytest.raises(
        NvdIncrementalRuntimeConfigurationError,
        match="NVD_DATA_BUCKET",
    ):
        NvdIncrementalRuntimeSettingsV1.from_environment()


@pytest.mark.parametrize(
    ("environment_name", "value"),
    [
        ("NVD_CVE_API_TIMEOUT_SECONDS", "0"),
        ("NVD_CVE_API_TIMEOUT_SECONDS", "invalid"),
        ("NVD_CVE_API_MAX_RESPONSE_BYTES", "0"),
        ("NVD_CVE_API_MINIMUM_INTERVAL_SECONDS", "-1"),
        ("NVD_CVE_API_MAX_ATTEMPTS", "0"),
        ("NVD_CVE_API_MAX_ATTEMPTS", "invalid"),
    ],
)
def test_rejects_invalid_numeric_environment(
    monkeypatch: pytest.MonkeyPatch,
    environment_name: str,
    value: str,
) -> None:
    """Fail closed on malformed or unsafe numeric runtime settings."""
    monkeypatch.setenv(
        "NVD_DATA_BUCKET",
        "opslens-dev-data",
    )
    monkeypatch.setenv(
        environment_name,
        value,
    )

    with pytest.raises(
        NvdIncrementalRuntimeConfigurationError,
    ):
        NvdIncrementalRuntimeSettingsV1.from_environment()
