"""Unit tests for the EPSS S3 Bronze outbound adapter."""

import gzip
from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext

import pytest
from botocore.exceptions import ClientError

from opslens.ingestion.epss.adapters.outbound.s3_bronze import (
    S3BronzeSnapshotRepository,
)
from opslens.ingestion.epss.application.models import RepositoryWriteStatus
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.epss.domain.parser import EpssSnapshotParser


class FakeTelemetry:
    """Capture operational telemetry emitted by an adapter."""

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
        """Capture an informational telemetry event."""
        self.info_events.append(message)

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture an exception telemetry event."""
        self.exception_events.append(message)

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Capture an emitted metric."""
        self.metrics.append((name, value, unit))

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Capture a trace span and return a no-op context manager."""
        self.spans.append(name)
        return nullcontext()


class FakeS3Client:
    """Capture S3 PutObject requests for unit tests."""

    def __init__(
        self,
        response: Mapping[str, object] | None = None,
        error: ClientError | None = None,
    ) -> None:
        """Initialize the fake S3 client."""
        self._response = response or {}
        self._error = error
        self.request: dict[str, object] | None = None

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
        """Capture the request and return the configured result."""
        self.request = {
            "Bucket": Bucket,
            "Key": Key,
            "Body": Body,
            "ContentType": ContentType,
            "Metadata": Metadata,
            "IfNoneMatch": IfNoneMatch,
        }

        if self._error is not None:
            raise self._error

        return self._response


def build_snapshot() -> EpssSnapshot:
    """Build a deterministic validated EPSS snapshot for repository tests."""
    content = (
        "#model_version:v2026.06.15,score_date:2026-08-14T12:00:27Z\n"
        "cve,epss,percentile\n"
        "CVE-1999-0001,0.03351,0.8762\n"
    )

    payload = gzip.compress(
        content.encode("utf-8"),
        mtime=0,
    )

    return EpssSnapshotParser().parse(payload)


def build_client_error(
    status_code: int,
    error_code: str,
) -> ClientError:
    """Build a deterministic typed Botocore ClientError."""
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


def test_create_snapshot_with_conditional_write() -> None:
    """Create a snapshot using deterministic metadata and If-None-Match."""
    snapshot = build_snapshot()
    telemetry = FakeTelemetry()
    client = FakeS3Client(
        response={
            "VersionId": "version-123",
            "ETag": '"etag-123"',
        }
    )

    repository = S3BronzeSnapshotRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    result = repository.create_if_absent(
        snapshot=snapshot,
        object_key=("bronze/epss/snapshot_date=2026-08-14/epss_scores.csv.gz"),
    )

    assert result.status is RepositoryWriteStatus.CREATED
    assert result.version_id == "version-123"
    assert result.etag == '"etag-123"'

    assert client.request is not None
    assert client.request["IfNoneMatch"] == "*"
    assert client.request["ContentType"] == "application/gzip"
    assert client.request["Body"] == snapshot.raw_bytes

    metadata = client.request["Metadata"]

    assert isinstance(metadata, Mapping)
    assert metadata["source"] == "first-epss"
    assert metadata["model_version"] == "v2026.06.15"
    assert metadata["score_date"] == "2026-08-14T12:00:27Z"
    assert metadata["sha256"] == snapshot.sha256

    assert "epss.s3.put_object" in telemetry.spans

    assert (
        "EpssBronzeCreated",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "EpssBronzePayloadBytes",
        float(snapshot.payload_size_bytes),
        "Bytes",
    ) in telemetry.metrics

    assert "EPSS Bronze snapshot created" in telemetry.info_events


def test_precondition_failed_is_idempotent_result() -> None:
    """Translate S3 HTTP 412 into an already-exists result."""
    snapshot = build_snapshot()
    telemetry = FakeTelemetry()

    client = FakeS3Client(
        error=build_client_error(
            status_code=412,
            error_code="PreconditionFailed",
        )
    )

    repository = S3BronzeSnapshotRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    result = repository.create_if_absent(
        snapshot=snapshot,
        object_key="bronze/epss/test.csv.gz",
    )

    assert result.status is RepositoryWriteStatus.ALREADY_EXISTS
    assert result.version_id is None
    assert result.etag is None

    assert (
        "EpssBronzeAlreadyExists",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert "EPSS Bronze snapshot already exists" in telemetry.info_events


def test_conflict_is_not_treated_as_already_exists() -> None:
    """Propagate S3 HTTP 409 so callers can retry the operation."""
    snapshot = build_snapshot()
    telemetry = FakeTelemetry()

    error = build_client_error(
        status_code=409,
        error_code="ConditionalRequestConflict",
    )

    client = FakeS3Client(error=error)

    repository = S3BronzeSnapshotRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    with pytest.raises(ClientError) as exc_info:
        repository.create_if_absent(
            snapshot=snapshot,
            object_key="bronze/epss/test.csv.gz",
        )

    assert exc_info.value is error

    assert (
        "EpssBronzeWriteFailure",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert telemetry.exception_events == ["Failed to persist EPSS Bronze snapshot"]


def test_unexpected_s3_error_is_propagated() -> None:
    """Propagate unexpected S3 failures after recording telemetry."""
    snapshot = build_snapshot()
    telemetry = FakeTelemetry()

    error = build_client_error(
        status_code=403,
        error_code="AccessDenied",
    )

    client = FakeS3Client(error=error)

    repository = S3BronzeSnapshotRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    with pytest.raises(ClientError) as exc_info:
        repository.create_if_absent(
            snapshot=snapshot,
            object_key="bronze/epss/test.csv.gz",
        )

    assert exc_info.value is error

    assert (
        "EpssBronzeWriteFailure",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert telemetry.exception_events == ["Failed to persist EPSS Bronze snapshot"]


def test_reject_empty_bucket_name() -> None:
    """Reject repository construction without a valid S3 bucket name."""
    telemetry = FakeTelemetry()
    client = FakeS3Client()

    with pytest.raises(
        ValueError,
        match="bucket name cannot be empty",
    ):
        S3BronzeSnapshotRepository(
            client=client,
            bucket_name="   ",
            telemetry=telemetry,
        )
