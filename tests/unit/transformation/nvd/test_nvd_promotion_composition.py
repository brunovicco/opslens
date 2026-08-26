"""Tests for NVD watermark-promotion dependency composition."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext

from opslens.transformation.nvd.application.watermark_promotion_runtime import (
    NvdWatermarkPromotionRuntimeV1,
)
from opslens.transformation.nvd.promotion_composition import (
    compose_promotion_runtime_dependencies,
)
from opslens.transformation.nvd.promotion_config import (
    NvdPromotionRuntimeSettingsV1,
)


class _Telemetry:
    """No-op telemetry satisfying the shared operational port."""

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Ignore informational telemetry."""
        del message, fields

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Ignore exception telemetry."""
        del message, fields

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Ignore metric telemetry."""
        del name, value, unit

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Return one no-op tracing span."""
        del name
        return nullcontext()


class _EvidenceClient:
    """Satisfy the exact-version evidence-reader S3 protocol."""

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> Mapping[str, object]:
        """Reject unexpected provider calls in composition-only tests."""
        del Bucket, Key, VersionId
        raise AssertionError("Composition test must not call S3.")


class _WatermarkClient:
    """Satisfy the authoritative watermark S3 protocol."""

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> Mapping[str, object]:
        """Reject unexpected provider reads in composition-only tests."""
        del Bucket, Key
        raise AssertionError("Composition test must not call S3.")

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: Mapping[str, str],
        IfNoneMatch: str | None = None,
        IfMatch: str | None = None,
    ) -> Mapping[str, object]:
        """Reject unexpected provider writes in composition-only tests."""
        del (
            Bucket,
            Key,
            Body,
            ContentType,
            Metadata,
            IfNoneMatch,
            IfMatch,
        )
        raise AssertionError("Composition test must not call S3.")


def test_compose_builds_runtime_without_provider_calls() -> None:
    """Construct the complete runtime graph from explicit typed boundaries."""
    dependencies = compose_promotion_runtime_dependencies(
        settings=NvdPromotionRuntimeSettingsV1(
            data_bucket="opslens-test-data",
            watermark_key=(
                "control/nvd/cve/incremental/watermark.json"
            ),
        ),
        telemetry=_Telemetry(),
        evidence_s3_client=_EvidenceClient(),
        watermark_s3_client=_WatermarkClient(),
    )

    assert isinstance(
        dependencies.runtime,
        NvdWatermarkPromotionRuntimeV1,
    )
