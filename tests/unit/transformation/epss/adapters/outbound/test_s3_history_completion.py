"""Tests for historical EPSS completion create-only persistence and exact replay."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from typing import Any

import pytest
from botocore.exceptions import ClientError

from opslens.transformation.epss.adapters.outbound.s3_history_completion import (
    HistoricalEpssCompletionConcurrentWriteError,
    HistoricalEpssCompletionWriteEvidenceError,
    S3HistoricalEpssCompletionRepository,
)
from opslens.transformation.epss.adapters.outbound.s3_history_completion_replay import (
    HistoricalEpssCompletionReplayMismatchError,
    S3HistoricalEpssCompletionReplayVerifier,
)
from opslens.transformation.epss.history.completion import (
    HistoricalEpssCompletionAlreadyExistsError,
    HistoricalEpssCompletionArtifactV1,
    HistoricalEpssCompletionManifestV1,
)

KEY = (
    "silver/epss-history/completions/schema_version=1/"
    f"archive_commit={'a' * 40}/snapshot_date=2021-04-14/manifest.json"
)
MANIFEST = HistoricalEpssCompletionManifestV1(
    snapshot_date=__import__("datetime").date(2021, 4, 14),
    archive_commit="a" * 40,
    bronze_manifest_key="bronze/manifest.json",
    bronze_manifest_version_id="bronze-version",
    source_object_key="bronze/source.csv.gz",
    source_object_version_id="source-version",
    source_sha256="b" * 64,
    silver_key="silver/epss/snapshot_date=2021-04-14/part-00000.parquet",
    silver_version_id="silver-version",
    silver_sha256="c" * 64,
    silver_schema_version=2,
    row_count=10,
    replay_status="created",
)
RAW_BYTES = b'{"completion":"exact"}\n'
ARTIFACT = HistoricalEpssCompletionArtifactV1(
    manifest=MANIFEST,
    key=KEY,
    raw_bytes=RAW_BYTES,
    sha256=__import__("hashlib").sha256(RAW_BYTES).hexdigest(),
)


class FakeTelemetry:
    """Capture minimal telemetry required by adapters."""

    def __init__(self) -> None:
        self.metrics: list[tuple[str, float, str]] = []

    def info(self, message: str, *, fields: Mapping[str, object] | None = None) -> None:
        """Ignore informational events."""

    def exception(self, message: str, *, fields: Mapping[str, object] | None = None) -> None:
        """Ignore exception events."""

    def metric(self, name: str, value: float, unit: str) -> None:
        """Capture one metric."""
        self.metrics.append((name, value, unit))

    def span(self, name: str) -> AbstractContextManager[object]:
        """Return a no-op trace span."""
        return nullcontext()


@dataclass
class FakeBody:
    """Readable and closable S3 response body."""

    payload: bytes
    closed: bool = False

    def read(self) -> bytes:
        """Return configured bytes."""
        return self.payload

    def close(self) -> None:
        """Record resource release."""
        self.closed = True


class FakeS3Client:
    """Provide configurable Put, Head, and exact Get behavior."""

    def __init__(self) -> None:
        self.put_error: ClientError | None = None
        self.put_response: dict[str, object] = {"VersionId": "completion-version"}
        self.version_id = "completion-version"
        self.payload = RAW_BYTES
        self.body: FakeBody | None = None

    def put_object(self, **kwargs: Any) -> dict[str, object]:
        """Return configured create evidence or raise configured error."""
        if self.put_error is not None:
            raise self.put_error
        return self.put_response

    def head_object(self, **kwargs: Any) -> dict[str, object]:
        """Return current-version replay coordinates."""
        return {"VersionId": self.version_id, "ContentLength": len(self.payload)}

    def get_object(self, **kwargs: Any) -> dict[str, object]:
        """Return exact-version replay bytes."""
        self.body = FakeBody(self.payload)
        return {
            "VersionId": self.version_id,
            "ContentLength": len(self.payload),
            "Body": self.body,
        }


def _client_error(status_code: int) -> ClientError:
    """Build one deterministic S3 conditional error."""
    return ClientError(
        error_response={
            "Error": {"Code": "test", "Message": "test"},
            "ResponseMetadata": {"HTTPStatusCode": status_code},
        },
        operation_name="PutObject",
    )


def test_completion_create_requires_exact_version_id() -> None:
    """Require immutable S3 version evidence after successful completion creation."""
    client = FakeS3Client()
    repository = S3HistoricalEpssCompletionRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=FakeTelemetry(),
    )

    stored = repository.put_if_absent(artifact=ARTIFACT)
    assert stored.version_id == "completion-version"
    assert stored.sha256 == ARTIFACT.sha256

    client.put_response = {"ETag": '"etag"'}
    with pytest.raises(HistoricalEpssCompletionWriteEvidenceError, match="VersionId"):
        repository.put_if_absent(artifact=ARTIFACT)


def test_completion_412_requires_replay_and_409_remains_distinct() -> None:
    """Never turn conditional S3 conflicts directly into completion success."""
    client = FakeS3Client()
    repository = S3HistoricalEpssCompletionRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=FakeTelemetry(),
    )

    client.put_error = _client_error(412)
    with pytest.raises(HistoricalEpssCompletionAlreadyExistsError):
        repository.put_if_absent(artifact=ARTIFACT)

    client.put_error = _client_error(409)
    with pytest.raises(HistoricalEpssCompletionConcurrentWriteError):
        repository.put_if_absent(artifact=ARTIFACT)


def test_completion_replay_requires_exact_bytes() -> None:
    """Accept replay only after exact VersionId, SHA-256, size, and bytes agree."""
    client = FakeS3Client()
    verifier = S3HistoricalEpssCompletionReplayVerifier(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=FakeTelemetry(),
    )

    stored = verifier.verify_current(artifact=ARTIFACT)
    assert stored.version_id == "completion-version"
    assert client.body is not None and client.body.closed is True

    client.payload = b'{"completion":"evil!"}\n'
    assert len(client.payload) == ARTIFACT.size_bytes
    with pytest.raises(HistoricalEpssCompletionReplayMismatchError, match="SHA-256"):
        verifier.verify_current(artifact=ARTIFACT)
