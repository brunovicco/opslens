"""Unit tests for the NVD Bootstrap composition root."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext

from opslens.ingestion.nvd.application.service import (
    IngestNvdBootstrapFeed,
)
from opslens.ingestion.nvd.composition import (
    build_ingestion_use_case,
)
from opslens.ingestion.nvd.config import NvdIngestionSettings


class FakeTelemetry:
    """Provide no-op operational telemetry for composition tests."""

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Ignore informational telemetry."""
        return None

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Ignore exception telemetry."""
        return None

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Ignore metrics."""
        return None

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Return a no-op span context."""
        return nullcontext()


class FakeS3Client:
    """Provide the minimum S3 shape needed by composition."""

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: Mapping[str, str],
        IfNoneMatch: str,
    ) -> Mapping[str, object]:
        """Return a deterministic S3 create response."""
        return {
            "VersionId": "test-version",
        }

    def head_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> Mapping[str, object]:
        """Return deterministic existing-object metadata."""
        return {
            "VersionId": "test-version",
        }


def test_build_ingestion_use_case_returns_application_service() -> None:
    """Compose the NVD service without leaking infrastructure concerns."""
    settings = NvdIngestionSettings(
        source_base_url="https://example.test/nvd",
        bronze_bucket="opslens-test-data",
        bronze_prefix="bronze/test/nvd",
        http_timeout_seconds=10.0,
        max_meta_bytes=1024,
        max_feed_bytes=4096,
    )

    use_case = build_ingestion_use_case(
        settings=settings,
        telemetry=FakeTelemetry(),
        s3_client=FakeS3Client(),
    )

    assert isinstance(
        use_case,
        IngestNvdBootstrapFeed,
    )
