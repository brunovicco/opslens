"""Unit tests for the EPSS Silver Bronze-reading S3 adapter."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext

import pytest
from botocore.exceptions import ClientError

from opslens.transformation.epss.adapters.outbound.s3_bronze import (
    S3BronzeEpssSnapshotRepository,
    S3GetObjectResponse,
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


class FakeBody:
    """Represent a deterministic S3 response body."""

    def __init__(self, payload: bytes) -> None:
        """Initialize the fake body."""
        self._payload = payload
        self.closed = False

    def read(self) -> bytes:
        """Return the configured payload."""
        return self._payload

    def close(self) -> None:
        """Record response-body closure."""
        self.closed = True


class FakeS3Client:
    """Capture S3 GetObject requests."""

    def __init__(
        self,
        *,
        body: FakeBody | None = None,
        error: ClientError | None = None,
    ) -> None:
        """Initialize the fake S3 client."""
        self.body = body or FakeBody(b"test-payload")
        self.error = error
        self.request: dict[str, str] | None = None

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> S3GetObjectResponse:
        """Capture a GetObject request and return the configured response."""
        self.request = {
            "Bucket": Bucket,
            "Key": Key,
        }

        if self.error is not None:
            raise self.error

        return {"Body": self.body}


def build_client_error() -> ClientError:
    """Build a deterministic S3 GetObject failure."""
    return ClientError(
        error_response={
            "Error": {
                "Code": "AccessDenied",
                "Message": "test error",
            },
            "ResponseMetadata": {
                "RequestId": "test-request-id",
                "HostId": "test-host-id",
                "HTTPStatusCode": 403,
                "HTTPHeaders": {},
                "RetryAttempts": 0,
            },
        },
        operation_name="GetObject",
    )


def test_reads_bronze_snapshot_bytes() -> None:
    """Read the complete Bronze payload and close the S3 response body."""
    payload = b"gzip-source-payload"
    body = FakeBody(payload)
    client = FakeS3Client(body=body)
    telemetry = FakeTelemetry()

    repository = S3BronzeEpssSnapshotRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    result = repository.get("bronze/epss/snapshot_date=2026-08-15/epss_scores.csv.gz")

    assert result == payload
    assert body.closed is True

    assert client.request == {
        "Bucket": "opslens-test-data",
        "Key": "bronze/epss/snapshot_date=2026-08-15/epss_scores.csv.gz",
    }

    assert "epss.s3.get_object" in telemetry.spans
    assert ("EpssBronzeReadBytes", float(len(payload)), "Bytes") in telemetry.metrics
    assert "EPSS Bronze snapshot read" in telemetry.info_events


def test_propagates_s3_read_failure() -> None:
    """Propagate S3 read failures after recording operational telemetry."""
    error = build_client_error()
    client = FakeS3Client(error=error)
    telemetry = FakeTelemetry()

    repository = S3BronzeEpssSnapshotRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    with pytest.raises(ClientError) as exc_info:
        repository.get("bronze/epss/test.csv.gz")

    assert exc_info.value is error
    assert ("EpssBronzeReadFailure", 1.0, "Count") in telemetry.metrics
    assert telemetry.exception_events == ["Failed to read EPSS Bronze snapshot"]


@pytest.mark.parametrize(
    ("bucket_name", "key"),
    [
        ("   ", "bronze/epss/test.csv.gz"),
        ("opslens-test-data", "   "),
    ],
)
def test_rejects_empty_storage_coordinates(
    bucket_name: str,
    key: str,
) -> None:
    """Reject empty bucket names and object keys."""
    client = FakeS3Client()
    telemetry = FakeTelemetry()

    if not bucket_name.strip():
        with pytest.raises(ValueError, match="bucket name cannot be empty"):
            S3BronzeEpssSnapshotRepository(
                client=client,
                bucket_name=bucket_name,
                telemetry=telemetry,
            )
        return

    repository = S3BronzeEpssSnapshotRepository(
        client=client,
        bucket_name=bucket_name,
        telemetry=telemetry,
    )

    with pytest.raises(ValueError, match="object key cannot be empty"):
        repository.get(key)
