"""Unit tests for the EPSS Silver composition root."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from typing import BinaryIO

from opslens.transformation.epss.adapters.outbound.s3_bronze import (
    S3GetObjectResponse,
)
from opslens.transformation.epss.composition import (
    build_transformation_service,
)
from opslens.transformation.epss.config import (
    EpssSilverTransformationSettings,
)


class FakeTelemetry:
    """Provide no-op operational telemetry for composition tests."""

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Ignore informational telemetry."""

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Ignore exception telemetry."""

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Ignore operational metrics."""

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Return a no-op tracing context manager."""
        return nullcontext()


class FakeBody:
    """Provide a deterministic readable S3 response body."""

    def read(self) -> bytes:
        """Return deterministic bytes."""
        return b"unused"

    def close(self) -> None:
        """Close the fake body."""


class FakeS3Client:
    """Implement the minimal S3 transformation capabilities."""

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> S3GetObjectResponse:
        """Return a deterministic fake GetObject response."""
        return {
            "Body": FakeBody(),
        }

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
        """Return a deterministic fake PutObject response."""
        return {}


def test_builds_transformation_service_from_explicit_dependencies() -> None:
    """Compose the Silver application service without AWS runtime state."""
    settings = EpssSilverTransformationSettings(
        data_bucket="opslens-test-data",
        silver_prefix="silver/epss",
    )

    service = build_transformation_service(
        settings=settings,
        telemetry=FakeTelemetry(),
        s3_client=FakeS3Client(),
    )

    assert service is not None
