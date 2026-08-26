"""Tests for exact-version S3 reads of NVD analytics authority evidence."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext

import pytest
from botocore.exceptions import ClientError

from opslens.transformation.nvd.adapters.outbound.s3_analytics_evidence import (
    NvdAnalyticsEvidenceS3EvidenceError,
    NvdAnalyticsEvidenceS3ReadError,
    S3NvdAnalyticsEvidenceReaderV1,
)

BUCKET = "opslens-test-data"
KEY = "control/nvd/cve/incremental/watermark.json"
VERSION = "watermark-version"
PAYLOAD = b'{"authority":"exact"}\n'


class FakeTelemetry:
    """Capture analytics evidence telemetry for assertions."""

    def __init__(self) -> None:
        """Initialize captured events."""
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
        """Capture one informational event."""
        del fields
        self.info_events.append(message)

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture one exception event."""
        del fields
        self.exception_events.append(message)

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Capture one metric."""
        self.metrics.append((name, value, unit))

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Capture one trace span."""
        self.spans.append(name)
        return nullcontext()


class FakeBody:
    """Expose one deterministic bounded response body."""

    def __init__(self, payload: bytes) -> None:
        """Initialize exact body bytes."""
        self.payload = payload
        self.read_amounts: list[int | None] = []
        self.closed = False

    def read(self, amt: int | None = None) -> bytes:
        """Return at most the requested number of bytes."""
        self.read_amounts.append(amt)
        return self.payload if amt is None else self.payload[:amt]

    def close(self) -> None:
        """Capture stream closure."""
        self.closed = True


class FakeS3Client:
    """Provide one exact GetObject response or provider error."""

    def __init__(
        self,
        *,
        response: Mapping[str, object] | None = None,
        error: ClientError | None = None,
    ) -> None:
        """Initialize deterministic provider behavior."""
        self.response: Mapping[str, object] = response if response is not None else {}
        self.error = error
        self.requests: list[dict[str, str]] = []

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> Mapping[str, object]:
        """Capture one exact-version read."""
        self.requests.append(
            {
                "Bucket": Bucket,
                "Key": Key,
                "VersionId": VersionId,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response


def _client_error(status_code: int) -> ClientError:
    """Build one deterministic Botocore GetObject failure."""
    return ClientError(
        error_response={
            "Error": {
                "Code": "AccessDenied",
                "Message": "test read failure",
            },
            "ResponseMetadata": {
                "RequestId": "request-id",
                "HostId": "host-id",
                "HTTPStatusCode": status_code,
                "HTTPHeaders": {},
                "RetryAttempts": 0,
            },
        },
        operation_name="GetObject",
    )


def _reader(
    client: FakeS3Client,
    telemetry: FakeTelemetry,
) -> S3NvdAnalyticsEvidenceReaderV1:
    """Build one analytics-owned exact evidence reader."""
    return S3NvdAnalyticsEvidenceReaderV1(
        client=client,
        bucket_name=BUCKET,
        telemetry=telemetry,
    )


def test_read_exact_pins_version_bounds_bytes_and_uses_analytics_telemetry() -> None:
    """Read exact authority without emitting promotion-owned observability names."""
    body = FakeBody(PAYLOAD)
    telemetry = FakeTelemetry()
    client = FakeS3Client(
        response={
            "Body": body,
            "VersionId": VERSION,
            "ContentLength": len(PAYLOAD),
        }
    )

    result = _reader(client, telemetry).read_exact(
        key=KEY,
        version_id=VERSION,
        max_bytes=1024,
    )

    assert result.key == KEY
    assert result.version_id == VERSION
    assert result.raw_bytes == PAYLOAD
    assert client.requests == [
        {
            "Bucket": BUCKET,
            "Key": KEY,
            "VersionId": VERSION,
        }
    ]
    assert body.read_amounts == [len(PAYLOAD) + 1]
    assert body.closed is True
    assert telemetry.spans == [
        "nvd.analytics.s3.get_authority_object_version"
    ]
    assert (
        "NvdAnalyticsEvidenceBytes",
        float(len(PAYLOAD)),
        "Bytes",
    ) in telemetry.metrics
    assert all("Promotion" not in name for name, _, _ in telemetry.metrics)


def test_read_exact_rejects_returned_version_mismatch_and_closes_body() -> None:
    """Fail closed when S3 does not return the exact requested VersionId."""
    body = FakeBody(PAYLOAD)
    telemetry = FakeTelemetry()
    client = FakeS3Client(
        response={
            "Body": body,
            "VersionId": "different-version",
            "ContentLength": len(PAYLOAD),
        }
    )

    with pytest.raises(
        NvdAnalyticsEvidenceS3EvidenceError,
        match="VersionId",
    ):
        _reader(client, telemetry).read_exact(
            key=KEY,
            version_id=VERSION,
            max_bytes=1024,
        )

    assert body.closed is True
    assert (
        "NvdAnalyticsEvidenceMismatch",
        1.0,
        "Count",
    ) in telemetry.metrics


def test_read_exact_rejects_oversized_content_before_materializing_bytes() -> None:
    """Apply the authority evidence byte bound before reading response bytes."""
    body = FakeBody(PAYLOAD)
    telemetry = FakeTelemetry()
    client = FakeS3Client(
        response={
            "Body": body,
            "VersionId": VERSION,
            "ContentLength": 2048,
        }
    )

    with pytest.raises(
        NvdAnalyticsEvidenceS3EvidenceError,
        match="read bound",
    ):
        _reader(client, telemetry).read_exact(
            key=KEY,
            version_id=VERSION,
            max_bytes=1024,
        )

    assert body.read_amounts == []
    assert body.closed is True


def test_read_exact_maps_provider_failure_to_analytics_boundary_error() -> None:
    """Keep provider read failures distinct from invalid evidence."""
    telemetry = FakeTelemetry()
    client = FakeS3Client(
        error=_client_error(403)
    )

    with pytest.raises(
        NvdAnalyticsEvidenceS3ReadError,
        match="authority evidence",
    ):
        _reader(client, telemetry).read_exact(
            key=KEY,
            version_id=VERSION,
            max_bytes=1024,
        )

    assert (
        "NvdAnalyticsEvidenceReadFailure",
        1.0,
        "Count",
    ) in telemetry.metrics
    assert telemetry.exception_events == [
        "Failed to read exact NVD analytics authority evidence object"
    ]
