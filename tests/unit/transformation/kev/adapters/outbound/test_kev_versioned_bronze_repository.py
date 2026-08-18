"""Unit tests for exact-version CISA KEV Bronze S3 reads."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from datetime import date

import pytest

from opslens.transformation.kev.adapters.inbound.s3_event import (
    KevBronzeObjectReference,
)
from opslens.transformation.kev.adapters.outbound.s3_bronze import (
    KevBronzeEvidenceMismatchError,
    S3GetObjectVersionResponse,
    S3VersionedKevBronzeRepository,
)

BUCKET = "opslens-dev-data-487757851499-us-east-1"
KEY = "bronze/kev/snapshot_date=2026-08-17/known_exploited_vulnerabilities.json"


class FakeBody:
    """Provide an in-memory S3 response body."""

    def __init__(self, payload: bytes) -> None:
        """Initialize the fake body."""
        self._payload = payload
        self.closed = False

    def read(self) -> bytes:
        """Return all configured bytes."""
        return self._payload

    def close(self) -> None:
        """Record body closure."""
        self.closed = True


class FakeS3Client:
    """Return one configured versioned GetObject response."""

    def __init__(
        self,
        response: S3GetObjectVersionResponse,
    ) -> None:
        """Initialize the fake S3 client."""
        self._response = response
        self.calls: list[tuple[str, str, str]] = []

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> S3GetObjectVersionResponse:
        """Return the configured S3 response."""
        self.calls.append((Bucket, Key, VersionId))
        return self._response


class FakeTelemetry:
    """Capture minimal operational telemetry for adapter tests."""

    def __init__(self) -> None:
        """Initialize telemetry capture."""
        self.metrics: list[str] = []
        self.exceptions: list[str] = []

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Accept informational events."""
        del message, fields

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture exception-event names."""
        del fields
        self.exceptions.append(message)

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Capture metric names."""
        del value, unit
        self.metrics.append(name)

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Return a no-op tracing span."""
        del name
        return nullcontext()


def _reference(
    *,
    bucket: str = BUCKET,
    version_id: str = "version-123",
    etag: str = "abc123",
    size_bytes: int = 7,
) -> KevBronzeObjectReference:
    """Build one validated-style KEV Bronze object reference."""
    return KevBronzeObjectReference(
        bucket=bucket,
        key=KEY,
        version_id=version_id,
        etag=etag,
        size_bytes=size_bytes,
        snapshot_date=date(2026, 8, 17),
        event_name="ObjectCreated:Put",
        sequencer="001",
    )


def _response(
    body: FakeBody,
    *,
    version_id: str = "version-123",
    etag: str = '"abc123"',
    content_length: int = 7,
) -> S3GetObjectVersionResponse:
    """Build one representative versioned GetObject response."""
    return {
        "Body": body,
        "VersionId": version_id,
        "ETag": etag,
        "ContentLength": content_length,
        "Metadata": {
            "source": "cisa-kev",
            "sha256": "a" * 64,
        },
    }


def test_reads_exact_object_version_and_verifies_transport_evidence() -> None:
    """Read the event-referenced version and preserve immutable evidence."""
    body = FakeBody(b"payload")
    client = FakeS3Client(_response(body))
    telemetry = FakeTelemetry()

    repository = S3VersionedKevBronzeRepository(
        client=client,
        bucket_name=BUCKET,
        telemetry=telemetry,
    )

    bronze = repository.get(_reference())

    assert client.calls == [
        (
            BUCKET,
            KEY,
            "version-123",
        )
    ]
    assert body.closed
    assert bronze.raw_bytes == b"payload"
    assert bronze.version_id == "version-123"
    assert bronze.etag == "abc123"
    assert bronze.content_length == 7
    assert bronze.metadata["source"] == "cisa-kev"

    assert "KevSilverBronzeReadBytes" in telemetry.metrics


def test_rejects_reference_for_unexpected_bucket() -> None:
    """Refuse evidence outside the configured OpsLens data bucket."""
    body = FakeBody(b"payload")
    client = FakeS3Client(_response(body))

    repository = S3VersionedKevBronzeRepository(
        client=client,
        bucket_name=BUCKET,
        telemetry=FakeTelemetry(),
    )

    with pytest.raises(
        KevBronzeEvidenceMismatchError,
        match="bucket",
    ):
        repository.get(
            _reference(
                bucket="unexpected-bucket",
            )
        )

    assert client.calls == []


@pytest.mark.parametrize(
    ("version_id", "etag", "content_length", "message"),
    [
        ("different-version", '"abc123"', 7, "VersionId"),
        ("version-123", '"different-etag"', 7, "ETag"),
        ("version-123", '"abc123"', 8, "ContentLength"),
    ],
)
def test_rejects_event_and_s3_response_mismatch(
    version_id: str,
    etag: str,
    content_length: int,
    message: str,
) -> None:
    """Fail closed when S3 response identity disagrees with the event."""
    body = FakeBody(b"payload")
    telemetry = FakeTelemetry()

    repository = S3VersionedKevBronzeRepository(
        client=FakeS3Client(
            _response(
                body,
                version_id=version_id,
                etag=etag,
                content_length=content_length,
            )
        ),
        bucket_name=BUCKET,
        telemetry=telemetry,
    )

    with pytest.raises(
        KevBronzeEvidenceMismatchError,
        match=message,
    ):
        repository.get(_reference())

    assert "KevSilverBronzeEvidenceMismatch" in telemetry.metrics


def test_rejects_payload_length_disagreement() -> None:
    """Fail closed when returned bytes disagree with S3 ContentLength."""
    body = FakeBody(b"short")
    telemetry = FakeTelemetry()

    repository = S3VersionedKevBronzeRepository(
        client=FakeS3Client(
            _response(
                body,
                content_length=7,
            )
        ),
        bucket_name=BUCKET,
        telemetry=telemetry,
    )

    with pytest.raises(
        KevBronzeEvidenceMismatchError,
        match="bytes actually read",
    ):
        repository.get(_reference())

    assert body.closed
    assert "KevSilverBronzeEvidenceMismatch" in telemetry.metrics
