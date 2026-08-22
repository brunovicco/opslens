"""Tests for exact NVD Silver Parquet replay verification."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from hashlib import sha256

import pytest

from opslens.transformation.nvd.adapters.outbound.s3_silver_replay import (
    NvdSilverParquetReplayMismatchError,
    S3GetObjectVersionResponse,
    S3HeadObjectResponse,
    S3NvdSilverParquetReplayVerifier,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverParquetArtifactV1,
    NvdSilverSourceKind,
)


class FakeBody:
    """Provide an in-memory exact-version S3 body."""

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


class RecordingReplayClient:
    """Record HEAD and exact GET calls for replay verification."""

    def __init__(
        self,
        *,
        head_response: S3HeadObjectResponse,
        get_response: S3GetObjectVersionResponse,
    ) -> None:
        """Initialize configured S3 replay responses."""
        self.head_response = head_response
        self.get_response = get_response
        self.head_calls: list[tuple[str, str]] = []
        self.get_calls: list[tuple[str, str, str]] = []

    def head_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> S3HeadObjectResponse:
        """Return current-object metadata."""
        self.head_calls.append((Bucket, Key))
        return self.head_response

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> S3GetObjectVersionResponse:
        """Return one configured exact object version."""
        self.get_calls.append(
            (
                Bucket,
                Key,
                VersionId,
            )
        )
        return self.get_response


class RecordingTelemetry:
    """Record operational replay telemetry."""

    def __init__(self) -> None:
        """Initialize telemetry collections."""
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
        """Record one metric sample."""
        self.metrics.append((name, value, unit))

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Record one span and return a no-op context manager."""
        self.spans.append(name)
        return nullcontext(object())


def _artifact() -> NvdSilverParquetArtifactV1:
    """Build one deterministic test Parquet artifact."""
    parquet_bytes = b"PAR1deterministic-replayPAR1"

    return NvdSilverParquetArtifactV1(
        parquet_bytes=parquet_bytes,
        parquet_sha256=sha256(parquet_bytes).hexdigest(),
        row_count=7,
        size_bytes=len(parquet_bytes),
        schema_version=1,
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        source_batch_id="a" * 64,
    )


def test_verifies_current_exact_version_byte_for_byte() -> None:
    """Accept replay only after exact immutable-version verification."""
    artifact = _artifact()
    body = FakeBody(artifact.parquet_bytes)

    client = RecordingReplayClient(
        head_response={
            "ContentLength": artifact.size_bytes,
            "VersionId": "silver-version-1",
        },
        get_response={
            "Body": body,
            "ContentLength": artifact.size_bytes,
            "VersionId": "silver-version-1",
        },
    )
    telemetry = RecordingTelemetry()

    verifier = S3NvdSilverParquetReplayVerifier(
        client=client,
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    stored = verifier.verify_current(
        key="silver/nvd/cve/part-00000.parquet",
        artifact=artifact,
    )

    assert stored.version_id == "silver-version-1"
    assert stored.sha256 == artifact.parquet_sha256
    assert stored.size_bytes == artifact.size_bytes
    assert stored.row_count == artifact.row_count
    assert body.closed is True

    assert client.head_calls == [
        (
            "opslens-data",
            "silver/nvd/cve/part-00000.parquet",
        )
    ]
    assert client.get_calls == [
        (
            "opslens-data",
            "silver/nvd/cve/part-00000.parquet",
            "silver-version-1",
        )
    ]

    assert (
        "NvdSilverParquetReplayVerified",
        1.0,
        "Count",
    ) in telemetry.metrics


def test_rejects_current_object_size_mismatch_before_get() -> None:
    """Avoid downloading an already-proven physical mismatch."""
    artifact = _artifact()

    client = RecordingReplayClient(
        head_response={
            "ContentLength": artifact.size_bytes + 1,
            "VersionId": "silver-version-1",
        },
        get_response={},
    )
    telemetry = RecordingTelemetry()

    verifier = S3NvdSilverParquetReplayVerifier(
        client=client,
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    with pytest.raises(
        NvdSilverParquetReplayMismatchError,
        match="size",
    ):
        verifier.verify_current(
            key="silver/nvd/cve/part-00000.parquet",
            artifact=artifact,
        )

    assert client.get_calls == []


def test_rejects_missing_current_version_id() -> None:
    """Never trust replay without exact S3 version identity."""
    artifact = _artifact()

    client = RecordingReplayClient(
        head_response={
            "ContentLength": artifact.size_bytes,
        },
        get_response={},
    )

    with pytest.raises(
        NvdSilverParquetReplayMismatchError,
        match="VersionId",
    ):
        S3NvdSilverParquetReplayVerifier(
            client=client,
            bucket_name="opslens-data",
            telemetry=RecordingTelemetry(),
        ).verify_current(
            key="silver/nvd/cve/part-00000.parquet",
            artifact=artifact,
        )

    assert client.get_calls == []


def test_rejects_exact_get_version_mismatch() -> None:
    """Require GET evidence to bind to the version discovered by HEAD."""
    artifact = _artifact()

    client = RecordingReplayClient(
        head_response={
            "ContentLength": artifact.size_bytes,
            "VersionId": "silver-version-1",
        },
        get_response={
            "Body": FakeBody(artifact.parquet_bytes),
            "ContentLength": artifact.size_bytes,
            "VersionId": "silver-version-2",
        },
    )

    with pytest.raises(
        NvdSilverParquetReplayMismatchError,
        match="VersionId",
    ):
        S3NvdSilverParquetReplayVerifier(
            client=client,
            bucket_name="opslens-data",
            telemetry=RecordingTelemetry(),
        ).verify_current(
            key="silver/nvd/cve/part-00000.parquet",
            artifact=artifact,
        )


def test_rejects_different_exact_payload() -> None:
    """Reject same-sized Silver bytes with different content."""
    artifact = _artifact()
    different = bytearray(artifact.parquet_bytes)
    different[5] ^= 1
    persisted = bytes(different)

    assert len(persisted) == artifact.size_bytes

    client = RecordingReplayClient(
        head_response={
            "ContentLength": artifact.size_bytes,
            "VersionId": "silver-version-1",
        },
        get_response={
            "Body": FakeBody(persisted),
            "ContentLength": artifact.size_bytes,
            "VersionId": "silver-version-1",
        },
    )
    telemetry = RecordingTelemetry()

    with pytest.raises(
        NvdSilverParquetReplayMismatchError,
        match="SHA-256",
    ):
        S3NvdSilverParquetReplayVerifier(
            client=client,
            bucket_name="opslens-data",
            telemetry=telemetry,
        ).verify_current(
            key="silver/nvd/cve/part-00000.parquet",
            artifact=artifact,
        )

    assert (
        "NvdSilverParquetReplayMismatch",
        1.0,
        "Count",
    ) in telemetry.metrics
