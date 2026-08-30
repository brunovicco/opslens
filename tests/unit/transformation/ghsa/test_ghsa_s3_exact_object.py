"""Tests for exact-version GHSA Bronze S3 reads."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext

import pytest

from opslens.transformation.ghsa.adapters.outbound.s3_exact_object import (
    GhsaS3ObjectEvidenceMismatchError,
    S3GetObjectVersionResponse,
    S3VersionedGhsaBronzeObjectReader,
)


class FakeBody:
    """In-memory S3 response body."""

    def __init__(
        self,
        payload: bytes,
    ) -> None:
        """Initialize the response body."""
        self._payload = payload
        self.closed = False
        self.read_count = 0

    def read(self) -> bytes:
        """Return the complete payload."""
        self.read_count += 1
        return self._payload

    def close(self) -> None:
        """Record resource release."""
        self.closed = True


class FakeS3Client:
    """Record exact-version GetObject requests."""

    def __init__(
        self,
        response: S3GetObjectVersionResponse,
    ) -> None:
        """Initialize the fake client."""
        self.response = response
        self.calls: list[tuple[str, str, str]] = []

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> S3GetObjectVersionResponse:
        """Return the configured exact-version response."""
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
        """Raise one deterministic infrastructure failure."""
        raise RuntimeError("S3 unavailable")


class RecordingTelemetry:
    """Minimal telemetry implementation for adapter tests."""

    def __init__(self) -> None:
        """Initialize in-memory telemetry."""
        self.info_events: list[
            tuple[str, Mapping[str, object] | None]
        ] = []
        self.exception_events: list[
            tuple[str, Mapping[str, object] | None]
        ] = []
        self.metrics: list[tuple[str, float, str]] = []
        self.spans: list[str] = []

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Record one informational event."""
        self.info_events.append((message, fields))

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Record one exception event."""
        self.exception_events.append((message, fields))

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Record one metric."""
        self.metrics.append((name, value, unit))

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Record one span and return a no-op context manager."""
        self.spans.append(name)
        return nullcontext(object())


def test_reads_exact_s3_object_version() -> None:
    """Read explicit Key and VersionId and return the exact bytes."""
    payload = b'[{"ghsa_id":"GHSA-2345-6789-cfgh"}]'
    body = FakeBody(payload)

    client = FakeS3Client(
        {
            "Body": body,
            "ContentLength": len(payload),
            "VersionId": "version-123",
        }
    )
    telemetry = RecordingTelemetry()

    reader = S3VersionedGhsaBronzeObjectReader(
        client=client,
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    result = reader.get(
        key="bronze/ghsa/advisories/page=000001/response.json",
        version_id="version-123",
    )

    assert client.calls == [
        (
            "opslens-data",
            "bronze/ghsa/advisories/page=000001/response.json",
            "version-123",
        )
    ]

    assert result.key == (
        "bronze/ghsa/advisories/page=000001/response.json"
    )
    assert result.version_id == "version-123"
    assert result.raw_bytes == payload

    assert body.read_count == 1
    assert body.closed is True

    assert telemetry.spans == [
        "ghsa.silver.s3.get_object_version"
    ]

    assert (
        "GhsaSilverBronzeReadBytes",
        float(len(payload)),
        "Bytes",
    ) in telemetry.metrics


def test_rejects_response_version_id_mismatch() -> None:
    """Fail closed if S3 returns another object version."""
    payload = b"payload"
    body = FakeBody(payload)

    client = FakeS3Client(
        {
            "Body": body,
            "ContentLength": len(payload),
            "VersionId": "different-version",
        }
    )
    telemetry = RecordingTelemetry()

    reader = S3VersionedGhsaBronzeObjectReader(
        client=client,
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    with pytest.raises(
        GhsaS3ObjectEvidenceMismatchError,
        match="VersionId",
    ):
        reader.get(
            key="bronze/ghsa/advisories/example.json",
            version_id="expected-version",
        )

    assert body.read_count == 0
    assert body.closed is True

    assert (
        "GhsaSilverBronzeEvidenceMismatch",
        1.0,
        "Count",
    ) in telemetry.metrics


def test_rejects_content_length_mismatch() -> None:
    """Require ContentLength to match bytes actually read."""
    payload = b"payload"
    body = FakeBody(payload)

    client = FakeS3Client(
        {
            "Body": body,
            "ContentLength": len(payload) + 1,
            "VersionId": "version-123",
        }
    )
    telemetry = RecordingTelemetry()

    reader = S3VersionedGhsaBronzeObjectReader(
        client=client,
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    with pytest.raises(
        GhsaS3ObjectEvidenceMismatchError,
        match="ContentLength",
    ):
        reader.get(
            key="bronze/ghsa/advisories/example.json",
            version_id="version-123",
        )

    assert body.closed is True


def test_rejects_oversized_object_before_reading_body() -> None:
    """Reject oversized S3 evidence before materializing the payload."""
    payload = b"0123456789"
    body = FakeBody(payload)

    client = FakeS3Client(
        {
            "Body": body,
            "ContentLength": len(payload),
            "VersionId": "version-123",
        }
    )
    telemetry = RecordingTelemetry()

    reader = S3VersionedGhsaBronzeObjectReader(
        client=client,
        bucket_name="opslens-data",
        telemetry=telemetry,
        max_manifest_bytes=5,
    )

    with pytest.raises(
        GhsaS3ObjectEvidenceMismatchError,
        match="size limit",
    ):
        reader.get(
            key="bronze/ghsa/advisories/manifest.json",
            version_id="version-123",
        )

    assert body.read_count == 0
    assert body.closed is True


def test_rejects_missing_response_body() -> None:
    """Reject an incomplete versioned GetObject response."""
    client = FakeS3Client(
        {
            "ContentLength": 10,
            "VersionId": "version-123",
        }
    )
    telemetry = RecordingTelemetry()

    reader = S3VersionedGhsaBronzeObjectReader(
        client=client,
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    with pytest.raises(
        GhsaS3ObjectEvidenceMismatchError,
        match="Body",
    ):
        reader.get(
            key="bronze/ghsa/advisories/example.json",
            version_id="version-123",
        )


def test_propagates_s3_failure_and_records_telemetry() -> None:
    """Keep infrastructure failures distinct from evidence mismatches."""
    telemetry = RecordingTelemetry()

    reader = S3VersionedGhsaBronzeObjectReader(
        client=FailingS3Client(),
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    with pytest.raises(
        RuntimeError,
        match="S3 unavailable",
    ):
        reader.get(
            key="bronze/ghsa/advisories/example.json",
            version_id="version-123",
        )

    assert (
        "GhsaSilverBronzeReadFailure",
        1.0,
        "Count",
    ) in telemetry.metrics
