"""Tests for exact-version NVD Bronze S3 reads."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext

import pytest

from opslens.transformation.nvd.adapters.outbound.s3_exact_object import (
    NvdS3ObjectEvidenceMismatchError,
    S3GetObjectVersionResponse,
    S3VersionedNvdBronzeObjectReader,
)


class FakeBody:
    """In-memory S3 response body."""

    def __init__(self, payload: bytes) -> None:
        """Initialize the in-memory response body."""
        self._payload = payload
        self.closed = False

    def read(self) -> bytes:
        """Return the complete in-memory payload."""
        return self._payload

    def close(self) -> None:
        """Record that the response body was closed."""
        self.closed = True


class FakeS3Client:
    """Record exact-version GetObject requests."""

    def __init__(
        self,
        response: S3GetObjectVersionResponse,
    ) -> None:
        """Initialize the fake client with one fixed response."""
        self.response = response
        self.calls: list[tuple[str, str, str]] = []

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> S3GetObjectVersionResponse:
        """Return the configured response and record exact coordinates."""
        self.calls.append(
            (
                Bucket,
                Key,
                VersionId,
            )
        )

        return self.response


class FailingS3Client:
    """Simulate an infrastructure failure."""

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> S3GetObjectVersionResponse:
        """Raise a deterministic infrastructure failure."""
        raise RuntimeError("S3 unavailable")


class RecordingTelemetry:
    """Minimal telemetry implementation for adapter tests."""

    def __init__(self) -> None:
        """Initialize in-memory telemetry collections."""
        self.info_events: list[tuple[str, Mapping[str, object] | None]] = []
        self.exception_events: list[tuple[str, Mapping[str, object] | None]] = []
        self.metrics: list[tuple[str, float, str]] = []
        self.spans: list[str] = []

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Record one informational telemetry event."""
        self.info_events.append((message, fields))

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Record one exception telemetry event."""
        self.exception_events.append((message, fields))

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Record one metric sample."""
        self.metrics.append((name, value, unit))

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Record one span name and return a no-op context manager."""
        self.spans.append(name)
        return nullcontext(object())


def test_reads_exact_s3_object_version() -> None:
    """Use key and VersionId explicitly and return the exact bytes."""
    payload = b'{"example":"nvd"}'
    body = FakeBody(payload)

    client = FakeS3Client(
        {
            "Body": body,
            "ContentLength": len(payload),
            "VersionId": "version-123",
        }
    )
    telemetry = RecordingTelemetry()

    repository = S3VersionedNvdBronzeObjectReader(
        client=client,
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    result = repository.get(
        key="bronze/nvd/example.json",
        version_id="version-123",
    )

    assert client.calls == [
        (
            "opslens-data",
            "bronze/nvd/example.json",
            "version-123",
        )
    ]
    assert result.key == "bronze/nvd/example.json"
    assert result.version_id == "version-123"
    assert result.raw_bytes == payload
    assert body.closed is True

    assert telemetry.spans == ["nvd.silver.s3.get_object_version"]
    assert (
        "NvdSilverBronzeReadBytes",
        float(len(payload)),
        "Bytes",
    ) in telemetry.metrics


def test_rejects_response_version_id_mismatch() -> None:
    """Fail closed if S3 returns evidence for another version."""
    payload = b"payload"

    client = FakeS3Client(
        {
            "Body": FakeBody(payload),
            "ContentLength": len(payload),
            "VersionId": "different-version",
        }
    )
    telemetry = RecordingTelemetry()

    repository = S3VersionedNvdBronzeObjectReader(
        client=client,
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    with pytest.raises(
        NvdS3ObjectEvidenceMismatchError,
        match="VersionId",
    ):
        repository.get(
            key="bronze/nvd/example.json",
            version_id="expected-version",
        )

    assert (
        "NvdSilverBronzeEvidenceMismatch",
        1.0,
        "Count",
    ) in telemetry.metrics


def test_rejects_content_length_mismatch() -> None:
    """Require S3 transport length to match the bytes actually read."""
    payload = b"payload"

    client = FakeS3Client(
        {
            "Body": FakeBody(payload),
            "ContentLength": len(payload) + 1,
            "VersionId": "version-123",
        }
    )
    telemetry = RecordingTelemetry()

    repository = S3VersionedNvdBronzeObjectReader(
        client=client,
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    with pytest.raises(
        NvdS3ObjectEvidenceMismatchError,
        match="ContentLength",
    ):
        repository.get(
            key="bronze/nvd/example.json",
            version_id="version-123",
        )


def test_rejects_missing_response_body() -> None:
    """Do not accept an incomplete GetObject response."""
    client = FakeS3Client(
        {
            "ContentLength": 10,
            "VersionId": "version-123",
        }
    )
    telemetry = RecordingTelemetry()

    repository = S3VersionedNvdBronzeObjectReader(
        client=client,
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    with pytest.raises(
        NvdS3ObjectEvidenceMismatchError,
        match="Body",
    ):
        repository.get(
            key="bronze/nvd/example.json",
            version_id="version-123",
        )


def test_propagates_s3_failure_and_records_telemetry() -> None:
    """Keep infrastructure failures distinct from evidence mismatches."""
    telemetry = RecordingTelemetry()

    repository = S3VersionedNvdBronzeObjectReader(
        client=FailingS3Client(),
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    with pytest.raises(
        RuntimeError,
        match="S3 unavailable",
    ):
        repository.get(
            key="bronze/nvd/example.json",
            version_id="version-123",
        )

    assert (
        "NvdSilverBronzeReadFailure",
        1.0,
        "Count",
    ) in telemetry.metrics
