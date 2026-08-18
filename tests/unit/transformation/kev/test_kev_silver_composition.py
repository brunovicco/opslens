"""Unit tests for CISA KEV Silver runtime composition."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from typing import BinaryIO

from opslens.transformation.kev.adapters.outbound.s3_bronze import (
    S3GetObjectVersionResponse,
)
from opslens.transformation.kev.composition import (
    compose_runtime_dependencies,
)
from opslens.transformation.kev.config import (
    KevSilverTransformationSettings,
)


class FakeTelemetry:
    """Provide no-op operational telemetry for composition tests."""

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Accept informational telemetry."""
        del message, fields

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Accept exception telemetry."""
        del message, fields

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Accept metric telemetry."""
        del name, value, unit

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Return a no-op tracing span."""
        del name
        return nullcontext()


class FakeS3Client:
    """Expose both S3 capabilities required by the composition root."""

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> S3GetObjectVersionResponse:
        """Reject unexpected network use during composition."""
        del Bucket, Key, VersionId
        raise AssertionError("Composition must not read S3.")

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: BinaryIO,
        ContentType: str,
        Metadata: Mapping[str, str],
        IfNoneMatch: str,
    ) -> Mapping[str, object]:
        """Reject unexpected network use during composition."""
        del (
            Bucket,
            Key,
            Body,
            ContentType,
            Metadata,
            IfNoneMatch,
        )
        raise AssertionError("Composition must not write S3.")


def test_composes_runtime_without_performing_aws_io() -> None:
    """Construct the complete runtime without reading or writing AWS."""
    bucket = "opslens-dev-data-487757851499-us-east-1"

    runtime = compose_runtime_dependencies(
        settings=KevSilverTransformationSettings(
            data_bucket=bucket,
            silver_prefix="silver/kev",
        ),
        telemetry=FakeTelemetry(),
        s3_client=FakeS3Client(),
    )

    test_event = runtime.event_parser.parse_test_event(
        {
            "Service": "Amazon S3",
            "Event": "s3:TestEvent",
            "Bucket": bucket,
            "RequestId": "request-123",
        }
    )

    assert test_event is not None
    assert test_event.bucket == bucket
