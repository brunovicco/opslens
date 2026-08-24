"""Unit tests for NVD incremental runtime composition."""

from collections.abc import Generator, Mapping
from contextlib import contextmanager

import pytest

from opslens.ingestion.nvd.incremental_runtime_composition import (
    build_incremental_runtime_use_case,
)
from opslens.ingestion.nvd.incremental_runtime_config import (
    NvdIncrementalRuntimeSettingsV1,
)


class FakeTelemetry:
    """Provide inert telemetry for composition tests."""

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Accept informational telemetry."""

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Accept failure telemetry."""

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Accept metric telemetry."""

    @contextmanager
    def span(
        self,
        name: str,
    ) -> Generator[object]:
        """Provide an inert tracing span."""
        yield object()


class FakeS3Client:
    """Expose S3 methods required only for structural composition."""

    def get_object(
        self,
        **kwargs: object,
    ) -> Mapping[str, object]:
        """Reject unexpected execution during composition testing."""
        raise AssertionError("S3 get_object must not run during composition.")

    def put_object(
        self,
        **kwargs: object,
    ) -> Mapping[str, object]:
        """Reject unexpected execution during composition testing."""
        raise AssertionError("S3 put_object must not run during composition.")

    def head_object(
        self,
        **kwargs: object,
    ) -> Mapping[str, object]:
        """Reject unexpected execution during composition testing."""
        raise AssertionError("S3 head_object must not run during composition.")


def _settings() -> NvdIncrementalRuntimeSettingsV1:
    """Build one valid composition configuration."""
    return NvdIncrementalRuntimeSettingsV1(
        bucket_name="opslens-test-data",
        watermark_key=(
            "control/nvd/cve/incremental/watermark.json"
        ),
        bronze_prefix="bronze/nvd/cve/updates",
        cve_api_base_url=(
            "https://services.nvd.nist.gov/rest/json/cves/2.0"
        ),
        cve_api_timeout_seconds=30.0,
        cve_api_max_response_bytes=16 * 1024 * 1024,
        cve_api_minimum_interval_seconds=6.0,
        cve_api_max_attempts=3,
    )


def test_builds_incremental_runtime_without_side_effects() -> None:
    """Compose all runtime dependencies without network or S3 access."""
    client = FakeS3Client()

    use_case = build_incremental_runtime_use_case(
        settings=_settings(),
        telemetry=FakeTelemetry(),
        watermark_s3_client=client,
        bronze_s3_client=client,
    )

    assert use_case is not None


@pytest.mark.parametrize(
    (
        "bucket_name",
        "watermark_key",
        "bronze_prefix",
        "cve_api_base_url",
    ),
    [
        (
            "",
            "control/nvd/cve/incremental/watermark.json",
            "bronze/nvd/cve/updates",
            "https://services.nvd.nist.gov/rest/json/cves/2.0",
        ),
        (
            "opslens-test-data",
            "",
            "bronze/nvd/cve/updates",
            "https://services.nvd.nist.gov/rest/json/cves/2.0",
        ),
        (
            "opslens-test-data",
            "control/nvd/cve/incremental/watermark.json",
            "",
            "https://services.nvd.nist.gov/rest/json/cves/2.0",
        ),
        (
            "opslens-test-data",
            "control/nvd/cve/incremental/watermark.json",
            "bronze/nvd/cve/updates",
            "",
        ),
    ],
)
def test_rejects_empty_required_string_settings(
    bucket_name: str,
    watermark_key: str,
    bronze_prefix: str,
    cve_api_base_url: str,
) -> None:
    """Reject empty structural runtime configuration."""
    with pytest.raises(ValueError):
        NvdIncrementalRuntimeSettingsV1(
            bucket_name=bucket_name,
            watermark_key=watermark_key,
            bronze_prefix=bronze_prefix,
            cve_api_base_url=cve_api_base_url,
            cve_api_timeout_seconds=30.0,
            cve_api_max_response_bytes=16 * 1024 * 1024,
            cve_api_minimum_interval_seconds=6.0,
            cve_api_max_attempts=3,
        )
