"""Unit tests for the EPSS Silver S3 artifact writer."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from io import BytesIO
from typing import BinaryIO

import pytest
from botocore.exceptions import ClientError

from opslens.transformation.epss.adapters.outbound.s3_silver import (
    S3SilverEpssArtifactRepository,
)
from opslens.transformation.epss.application.models import (
    SilverRepositoryWriteStatus,
)


class FakeTelemetry:
    """Capture operational telemetry emitted by the adapter."""

    def __init__(self) -> None:
        """Initialize empty telemetry collections."""
        self.info_events: list[str] = []
        self.exception_events: list[str] = []
        self.metrics: list[tuple[str, float, str]] = []
        self.spans: list[str] = []

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture an informational event."""
        self.info_events.append(message)

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture an exception event."""
        self.exception_events.append(message)

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Capture an operational metric."""
        self.metrics.append((name, value, unit))

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Capture a span and return a no-op context manager."""
        self.spans.append(name)
        return nullcontext()


class FakeS3Client:
    """Capture S3 PutObject requests."""

    def __init__(
        self,
        *,
        error: ClientError | None = None,
    ) -> None:
        """Initialize the fake S3 client."""
        self.error = error
        self.request: dict[str, object] | None = None

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
        """Capture the PutObject request and return a deterministic response."""
        self.request = {
            "Bucket": Bucket,
            "Key": Key,
            "Body": Body,
            "ContentType": ContentType,
            "Metadata": Metadata,
            "IfNoneMatch": IfNoneMatch,
        }

        if self.error is not None:
            raise self.error

        return {
            "ETag": '"etag-123"',
            "VersionId": "version-123",
        }


def build_client_error(
    *,
    status_code: int,
    error_code: str,
) -> ClientError:
    """Build a deterministic typed S3 PutObject failure."""
    return ClientError(
        error_response={
            "Error": {
                "Code": error_code,
                "Message": "test error",
            },
            "ResponseMetadata": {
                "RequestId": "test-request-id",
                "HostId": "test-host-id",
                "HTTPStatusCode": status_code,
                "HTTPHeaders": {},
                "RetryAttempts": 0,
            },
        },
        operation_name="PutObject",
    )


def test_creates_silver_artifact_with_conditional_write() -> None:
    """Create a Parquet artifact using immutable S3 write semantics."""
    artifact = BytesIO(b"PAR1test-parquet")
    client = FakeS3Client()
    telemetry = FakeTelemetry()

    repository = S3SilverEpssArtifactRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    metadata = {
        "source": "first-epss",
        "source_sha256": "a" * 64,
        "schema_version": "1",
    }

    result = repository.put_if_absent(
        key="silver/epss/snapshot_date=2026-08-15/part-00000.parquet",
        artifact=artifact,
        metadata=metadata,
    )

    assert result is SilverRepositoryWriteStatus.CREATED

    assert client.request is not None
    assert client.request["Bucket"] == "opslens-test-data"
    assert client.request["Key"] == "silver/epss/snapshot_date=2026-08-15/part-00000.parquet"
    assert client.request["Body"] is artifact
    assert client.request["ContentType"] == "application/vnd.apache.parquet"
    assert client.request["Metadata"] == metadata
    assert client.request["IfNoneMatch"] == "*"

    assert "epss.silver.s3.put_object" in telemetry.spans
    assert ("EpssSilverCreated", 1.0, "Count") in telemetry.metrics
    assert "EPSS Silver artifact created" in telemetry.info_events


def test_precondition_failed_is_idempotent_result() -> None:
    """Translate S3 HTTP 412 into an already-exists result."""
    artifact = BytesIO(b"PAR1test-parquet")
    client = FakeS3Client(
        error=build_client_error(
            status_code=412,
            error_code="PreconditionFailed",
        )
    )
    telemetry = FakeTelemetry()

    repository = S3SilverEpssArtifactRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    result = repository.put_if_absent(
        key="silver/epss/snapshot_date=2026-08-15/part-00000.parquet",
        artifact=artifact,
        metadata={},
    )

    assert result is SilverRepositoryWriteStatus.ALREADY_EXISTS
    assert ("EpssSilverAlreadyExists", 1.0, "Count") in telemetry.metrics
    assert "EPSS Silver artifact already exists" in telemetry.info_events


def test_conflict_is_not_treated_as_already_exists() -> None:
    """Propagate S3 HTTP 409 so the caller can retry the write."""
    error = build_client_error(
        status_code=409,
        error_code="ConditionalRequestConflict",
    )
    client = FakeS3Client(error=error)
    telemetry = FakeTelemetry()

    repository = S3SilverEpssArtifactRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    with pytest.raises(ClientError) as exc_info:
        repository.put_if_absent(
            key="silver/epss/test.parquet",
            artifact=BytesIO(b"PAR1test-parquet"),
            metadata={},
        )

    assert exc_info.value is error
    assert ("EpssSilverWriteFailure", 1.0, "Count") in telemetry.metrics
    assert telemetry.exception_events == ["Failed to persist EPSS Silver artifact"]


def test_unexpected_s3_error_is_propagated() -> None:
    """Propagate unexpected S3 failures after recording telemetry."""
    error = build_client_error(
        status_code=403,
        error_code="AccessDenied",
    )
    client = FakeS3Client(error=error)
    telemetry = FakeTelemetry()

    repository = S3SilverEpssArtifactRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    with pytest.raises(ClientError) as exc_info:
        repository.put_if_absent(
            key="silver/epss/test.parquet",
            artifact=BytesIO(b"PAR1test-parquet"),
            metadata={},
        )

    assert exc_info.value is error
    assert ("EpssSilverWriteFailure", 1.0, "Count") in telemetry.metrics


def test_rejects_empty_bucket_name() -> None:
    """Reject repository construction without a valid bucket name."""
    with pytest.raises(ValueError, match="bucket name cannot be empty"):
        S3SilverEpssArtifactRepository(
            client=FakeS3Client(),
            bucket_name="   ",
            telemetry=FakeTelemetry(),
        )


def test_rejects_empty_object_key() -> None:
    """Reject writes without a valid Silver object key."""
    repository = S3SilverEpssArtifactRepository(
        client=FakeS3Client(),
        bucket_name="opslens-test-data",
        telemetry=FakeTelemetry(),
    )

    with pytest.raises(ValueError, match="object key cannot be empty"):
        repository.put_if_absent(
            key="   ",
            artifact=BytesIO(b"PAR1test-parquet"),
            metadata={},
        )
