"""Unit tests for exact historical EPSS Silver replay verification."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass

import pytest

from opslens.transformation.epss.adapters.outbound.s3_history_silver_replay import (
    HistoricalEpssSilverReplayMismatchError,
    S3HistoricalEpssSilverGetResponse,
    S3HistoricalEpssSilverHeadResponse,
    S3HistoricalEpssSilverReplayVerifier,
)
from opslens.transformation.epss.history.models import HistoricalEpssSilverArtifactV1

KEY = "silver/epss/snapshot_date=2021-04-14/part-00000.parquet"
VERSION_ID = "current-version"
ARTIFACT = HistoricalEpssSilverArtifactV1(
    parquet_bytes=b"PAR1historical-epss",
    row_count=64_712,
    schema_version=2,
)


class FakeTelemetry:
    """Capture operational telemetry emitted by exact replay verification."""

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
        """Capture one informational event."""
        self.info_events.append(message)

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture one exception event."""
        self.exception_events.append(message)

    def metric(self, name: str, value: float, unit: str) -> None:
        """Capture one metric."""
        self.metrics.append((name, value, unit))

    def span(self, name: str) -> AbstractContextManager[object]:
        """Capture one span and return a no-op context manager."""
        self.spans.append(name)
        return nullcontext()


@dataclass
class FakeBody:
    """Represent readable S3 body bytes and track resource closure."""

    payload: bytes
    closed: bool = False

    def read(self) -> bytes:
        """Return deterministic body bytes."""
        return self.payload

    def close(self) -> None:
        """Record response-body closure."""
        self.closed = True


class FakeS3Client:
    """Return configured HeadObject and exact-version GetObject evidence."""

    def __init__(
        self,
        *,
        head: S3HistoricalEpssSilverHeadResponse | None = None,
        payload: bytes = ARTIFACT.parquet_bytes,
        get_version_id: str = VERSION_ID,
        get_content_length: int | None = None,
    ) -> None:
        """Initialize deterministic exact replay behavior."""
        self.head = head or {
            "VersionId": VERSION_ID,
            "ContentLength": ARTIFACT.size_bytes,
        }
        self.payload = payload
        self.get_version_id = get_version_id
        self.get_content_length = (
            len(payload) if get_content_length is None else get_content_length
        )
        self.head_calls: list[dict[str, str]] = []
        self.get_calls: list[dict[str, str]] = []
        self.bodies: list[FakeBody] = []

    def head_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> S3HistoricalEpssSilverHeadResponse:
        """Return configured current-version metadata."""
        self.head_calls.append({"Bucket": Bucket, "Key": Key})
        return self.head

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> S3HistoricalEpssSilverGetResponse:
        """Return configured bytes for the explicitly requested version."""
        self.get_calls.append(
            {"Bucket": Bucket, "Key": Key, "VersionId": VersionId}
        )
        body = FakeBody(self.payload)
        self.bodies.append(body)
        return {
            "Body": body,
            "VersionId": self.get_version_id,
            "ContentLength": self.get_content_length,
        }


def _verifier(
    client: FakeS3Client,
    telemetry: FakeTelemetry | None = None,
) -> S3HistoricalEpssSilverReplayVerifier:
    """Build one replay verifier with deterministic fakes."""
    return S3HistoricalEpssSilverReplayVerifier(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry or FakeTelemetry(),
    )


def test_verifies_current_version_by_exact_bytes_and_sha256() -> None:
    """Accept replay only after exact current-version byte verification."""
    client = FakeS3Client()
    telemetry = FakeTelemetry()
    verifier = _verifier(client, telemetry)

    stored = verifier.verify_current(key=KEY, artifact=ARTIFACT)

    assert stored.key == KEY
    assert stored.version_id == VERSION_ID
    assert stored.parquet_sha256 == ARTIFACT.parquet_sha256
    assert stored.size_bytes == ARTIFACT.size_bytes
    assert client.head_calls == [{"Bucket": "opslens-test-data", "Key": KEY}]
    assert client.get_calls == [
        {
            "Bucket": "opslens-test-data",
            "Key": KEY,
            "VersionId": VERSION_ID,
        }
    ]
    assert all(body.closed for body in client.bodies)
    assert ("EpssHistorySilverReplayVerified", 1.0, "Count") in telemetry.metrics


def test_rejects_current_size_mismatch_before_get_object() -> None:
    """Fail closed before reading bytes when HeadObject size differs."""
    client = FakeS3Client(
        head={
            "VersionId": VERSION_ID,
            "ContentLength": ARTIFACT.size_bytes + 1,
        }
    )
    verifier = _verifier(client)

    with pytest.raises(HistoricalEpssSilverReplayMismatchError, match="size"):
        verifier.verify_current(key=KEY, artifact=ARTIFACT)

    assert client.get_calls == []


def test_rejects_get_object_version_different_from_head_version() -> None:
    """Reject replay when exact GetObject evidence changes the discovered VersionId."""
    verifier = _verifier(FakeS3Client(get_version_id="other-version"))

    with pytest.raises(HistoricalEpssSilverReplayMismatchError, match="VersionId"):
        verifier.verify_current(key=KEY, artifact=ARTIFACT)


def test_rejects_same_size_but_different_bytes() -> None:
    """Require SHA-256 and byte equality, not size equality alone."""
    different = b"PAR1historical-xxxx"
    assert len(different) == ARTIFACT.size_bytes
    verifier = _verifier(FakeS3Client(payload=different))

    with pytest.raises(HistoricalEpssSilverReplayMismatchError, match="SHA-256"):
        verifier.verify_current(key=KEY, artifact=ARTIFACT)


def test_rejects_missing_head_version_id() -> None:
    """Require exact current VersionId authority from HeadObject."""
    verifier = _verifier(
        FakeS3Client(head={"ContentLength": ARTIFACT.size_bytes})
    )

    with pytest.raises(HistoricalEpssSilverReplayMismatchError, match="VersionId"):
        verifier.verify_current(key=KEY, artifact=ARTIFACT)
