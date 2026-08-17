"""Unit tests for the CISA KEV S3 Bronze outbound adapter."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime

import pytest
from botocore.exceptions import ClientError

from opslens.ingestion.kev.adapters.outbound.s3_bronze import (
    S3BronzeCatalogRepository,
)
from opslens.ingestion.kev.application.models import RepositoryWriteStatus
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot


class FakeTelemetry:
    """Capture operational telemetry emitted by the S3 adapter."""

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


def build_snapshot() -> KevCatalogSnapshot:
    """Build a deterministic validated KEV snapshot for repository tests."""
    return KevCatalogSnapshot(
        raw_bytes=b'{"catalogVersion":"2026.08.16"}',
        catalog_version="2026.08.16",
        date_released=datetime(
            2026,
            8,
            16,
            20,
            15,
            tzinfo=UTC,
        ),
        retrieved_at=datetime(
            2026,
            8,
            17,
            2,
            15,
            tzinfo=UTC,
        ),
        sha256="a" * 64,
        record_count=1482,
    )


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


def test_create_catalog_with_conditional_write() -> None:
    """Create a KEV catalog using provenance metadata and If-None-Match."""
    snapshot = build_snapshot()
    telemetry = FakeTelemetry()

    client = FakeS3Client(
        response={
            "VersionId": "version-123",
            "ETag": '"etag-123"',
        }
    )

    repository = S3BronzeCatalogRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    result = repository.create_if_absent(
        snapshot=snapshot,
        object_key=(
            "bronze/kev/"
            "snapshot_date=2026-08-17/"
            "known_exploited_vulnerabilities.json"
        ),
    )

    assert result.status is RepositoryWriteStatus.CREATED
    assert result.version_id == "version-123"
    assert result.etag == '"etag-123"'

    assert client.request is not None
    assert client.request["IfNoneMatch"] == "*"
    assert client.request["ContentType"] == "application/json"
    assert client.request["Body"] == snapshot.raw_bytes

    metadata = client.request["Metadata"]

    assert isinstance(metadata, Mapping)
    assert metadata["source"] == "cisa-kev"
    assert metadata["catalog_version"] == "2026.08.16"
    assert metadata["date_released"] == "2026-08-16T20:15:00Z"
    assert metadata["retrieved_at"] == "2026-08-17T02:15:00Z"
    assert metadata["sha256"] == snapshot.sha256
    assert metadata["record_count"] == "1482"

    assert "kev.s3.put_object" in telemetry.spans

    assert (
        "KevBronzeCreated",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "KevBronzePayloadBytes",
        float(snapshot.payload_size_bytes),
        "Bytes",
    ) in telemetry.metrics

    assert "CISA KEV Bronze catalog created" in telemetry.info_events


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

    repository = S3BronzeCatalogRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    result = repository.create_if_absent(
        snapshot=snapshot,
        object_key="bronze/kev/test.json",
    )

    assert result.status is RepositoryWriteStatus.ALREADY_EXISTS
    assert result.version_id is None
    assert result.etag is None

    assert (
        "KevBronzeAlreadyExists",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "CISA KEV Bronze catalog already exists"
        in telemetry.info_events
    )


def test_conflict_is_propagated_for_retry() -> None:
    """Propagate S3 HTTP 409 so the invocation can be retried."""
    snapshot = build_snapshot()
    telemetry = FakeTelemetry()

    error = build_client_error(
        status_code=409,
        error_code="ConditionalRequestConflict",
    )

    client = FakeS3Client(error=error)

    repository = S3BronzeCatalogRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    with pytest.raises(ClientError) as exc_info:
        repository.create_if_absent(
            snapshot=snapshot,
            object_key="bronze/kev/test.json",
        )

    assert exc_info.value is error

    assert (
        "KevBronzeWriteFailure",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert telemetry.exception_events == [
        "Failed to persist CISA KEV Bronze catalog"
    ]


def test_access_denied_is_propagated() -> None:
    """Propagate S3 authorization failures after recording telemetry."""
    snapshot = build_snapshot()
    telemetry = FakeTelemetry()

    error = build_client_error(
        status_code=403,
        error_code="AccessDenied",
    )

    client = FakeS3Client(error=error)

    repository = S3BronzeCatalogRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    with pytest.raises(ClientError) as exc_info:
        repository.create_if_absent(
            snapshot=snapshot,
            object_key="bronze/kev/test.json",
        )

    assert exc_info.value is error

    assert (
        "KevBronzeWriteFailure",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert telemetry.exception_events == [
        "Failed to persist CISA KEV Bronze catalog"
    ]


def test_reject_empty_bucket_name() -> None:
    """Reject repository construction without a valid S3 bucket name."""
    telemetry = FakeTelemetry()
    client = FakeS3Client()

    with pytest.raises(
        ValueError,
        match="bucket name cannot be empty",
    ):
        S3BronzeCatalogRepository(
            client=client,
            bucket_name="   ",
            telemetry=telemetry,
        )
