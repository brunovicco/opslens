"""Tests for immutable GHSA Silver COMPLETE persistence."""

import base64
from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext

import pytest
from botocore.exceptions import ClientError

from opslens.transformation.ghsa.adapters.outbound.s3_silver_completion import (
    GhsaSilverCompletionConcurrentWriteError,
    GhsaSilverCompletionReplayMismatchError,
    GhsaSilverCompletionWriteEvidenceError,
    S3GetCompletionResponse,
    S3GhsaSilverCompletionRepository,
    S3HeadCompletionResponse,
    S3PutCompletionResponse,
)
from opslens.transformation.ghsa.completion.key_factory import (
    GhsaSilverKeyFactoryV1,
)
from opslens.transformation.ghsa.completion.manifest import (
    GhsaSilverCompletionArtifactV1,
    GhsaSilverCompletionManifestSerializerV1,
    GhsaSilverCompletionManifestV1,
)
from opslens.transformation.ghsa.runtime.materializer import (
    GhsaSilverAttemptContextV1,
)

SYNC_ID = "1" * 64
ATTEMPT_ID = "2" * 64


class FakeBody:
    """In-memory S3 response body."""

    def __init__(self, payload: bytes) -> None:
        """Initialize response-body state."""
        self._payload = payload
        self.read_count = 0
        self.closed = False

    def read(self) -> bytes:
        """Return the configured payload."""
        self.read_count += 1
        return self._payload

    def close(self) -> None:
        """Record response-body release."""
        self.closed = True


class RecordingS3Client:
    """Record COMPLETE conditional writes and replay reads."""

    def __init__(
        self,
        *,
        put_response: S3PutCompletionResponse | None = None,
        put_error: ClientError | None = None,
        head_response: S3HeadCompletionResponse | None = None,
        get_response: S3GetCompletionResponse | None = None,
    ) -> None:
        """Initialize configured S3 outcomes."""
        self._put_response = put_response
        self._put_error = put_error
        self._head_response = head_response
        self._get_response = get_response
        self.put_calls: list[dict[str, object]] = []
        self.head_calls: list[tuple[str, str]] = []
        self.get_calls: list[tuple[str, str, str]] = []

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: Mapping[str, str],
        ChecksumSHA256: str,
        IfNoneMatch: str,
    ) -> S3PutCompletionResponse:
        """Record one create-only COMPLETE write."""
        self.put_calls.append(
            {
                "Bucket": Bucket,
                "Key": Key,
                "Body": Body,
                "ContentType": ContentType,
                "Metadata": dict(Metadata),
                "ChecksumSHA256": ChecksumSHA256,
                "IfNoneMatch": IfNoneMatch,
            }
        )

        if self._put_error is not None:
            raise self._put_error

        return self._put_response if self._put_response is not None else {}

    def head_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> S3HeadCompletionResponse:
        """Return configured current-version discovery evidence."""
        self.head_calls.append((Bucket, Key))
        return self._head_response if self._head_response is not None else {}

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> S3GetCompletionResponse:
        """Return configured exact-version replay evidence."""
        self.get_calls.append((Bucket, Key, VersionId))
        return self._get_response if self._get_response is not None else {}


class RecordingTelemetry:
    """Record operational telemetry emitted by COMPLETE persistence."""

    def __init__(self) -> None:
        """Initialize telemetry collections."""
        self.info_events: list[tuple[str, Mapping[str, object] | None]] = []
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
        """Record one metric sample."""
        self.metrics.append((name, value, unit))

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Record one span and return a no-op context manager."""
        self.spans.append(name)
        return nullcontext(object())


def _artifact() -> GhsaSilverCompletionArtifactV1:
    """Build one canonical zero-result COMPLETE artifact."""
    context = GhsaSilverAttemptContextV1(
        sync_id=SYNC_ID,
        attempt_id=ATTEMPT_ID,
        manifest_key="bronze/ghsa/advisories/manifest.json",
        manifest_version_id="bronze-manifest-version",
    )
    manifest = GhsaSilverCompletionManifestV1(
        context=context,
        logical_record_set_sha256="3" * 64,
        occurrences=(),
    )

    return GhsaSilverCompletionManifestSerializerV1(
        key_factory=GhsaSilverKeyFactoryV1(),
    ).serialize(manifest)


def _metadata(artifact: GhsaSilverCompletionArtifactV1) -> dict[str, str]:
    """Build the expected bounded S3 COMPLETE metadata."""
    manifest = artifact.manifest

    return {
        "dataset": "ghsa_advisory_versions",
        "schema_version": "1",
        "completion_status": "complete",
        "sync_id": manifest.context.sync_id,
        "attempt_id": manifest.context.attempt_id,
        "record_count": str(manifest.record_count),
        "manifest_sha256": artifact.manifest_sha256,
    }


def _checksum(artifact: GhsaSilverCompletionArtifactV1) -> str:
    """Return the S3 base64 SHA-256 representation for COMPLETE."""
    return base64.b64encode(
        bytes.fromhex(artifact.manifest_sha256)
    ).decode("ascii")


def _client_error(status_code: int) -> ClientError:
    """Build one Botocore ClientError with a deterministic HTTP status."""
    return ClientError(
        {
            "Error": {
                "Code": "TestError",
                "Message": "test",
            },
            "ResponseMetadata": {
                "RequestId": "request-id",
                "HostId": "host-id",
                "HTTPStatusCode": status_code,
                "HTTPHeaders": {},
                "RetryAttempts": 0,
            },
        },
        "PutObject",
    )


def test_creates_complete_conditionally_with_checksum_and_version() -> None:
    """Require create-only COMPLETE plus checksum and VersionId evidence."""
    artifact = _artifact()
    checksum = _checksum(artifact)
    client = RecordingS3Client(
        put_response={
            "VersionId": "complete-version",
            "ChecksumSHA256": checksum,
        }
    )
    telemetry = RecordingTelemetry()
    repository = S3GhsaSilverCompletionRepository(
        client=client,
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    stored = repository.put_if_absent(artifact)

    assert stored.key == artifact.key
    assert stored.version_id == "complete-version"
    assert stored.sha256 == artifact.manifest_sha256
    assert stored.size_bytes == len(artifact.manifest_bytes)

    call = client.put_calls[0]
    assert call["IfNoneMatch"] == "*"
    assert call["ChecksumSHA256"] == checksum
    assert call["ContentType"] == "application/json"
    assert call["Metadata"] == _metadata(artifact)
    assert client.head_calls == []
    assert client.get_calls == []
    assert (
        "GhsaSilverCompleteCreated",
        1.0,
        "Count",
    ) in telemetry.metrics


def test_rejects_successful_complete_without_version_id() -> None:
    """Do not accept COMPLETE without exact persisted version evidence."""
    artifact = _artifact()
    repository = S3GhsaSilverCompletionRepository(
        client=RecordingS3Client(
            put_response={
                "ChecksumSHA256": _checksum(artifact),
            }
        ),
        bucket_name="opslens-data",
        telemetry=RecordingTelemetry(),
    )

    with pytest.raises(
        GhsaSilverCompletionWriteEvidenceError,
        match="VersionId",
    ):
        repository.put_if_absent(artifact)


def test_accepts_existing_complete_only_after_exact_replay() -> None:
    """Accept 412 only after exact immutable-version COMPLETE verification."""
    artifact = _artifact()
    metadata = _metadata(artifact)
    body = FakeBody(artifact.manifest_bytes)
    client = RecordingS3Client(
        put_error=_client_error(412),
        head_response={
            "VersionId": "existing-complete-version",
            "ContentLength": len(artifact.manifest_bytes),
            "Metadata": metadata,
        },
        get_response={
            "Body": body,
            "VersionId": "existing-complete-version",
            "ContentLength": len(artifact.manifest_bytes),
            "Metadata": metadata,
        },
    )
    telemetry = RecordingTelemetry()
    repository = S3GhsaSilverCompletionRepository(
        client=client,
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    stored = repository.put_if_absent(artifact)

    assert stored.version_id == "existing-complete-version"
    assert client.head_calls == [("opslens-data", artifact.key)]
    assert client.get_calls == [
        (
            "opslens-data",
            artifact.key,
            "existing-complete-version",
        )
    ]
    assert body.read_count == 1
    assert body.closed is True
    assert (
        "GhsaSilverCompleteReplayVerified",
        1.0,
        "Count",
    ) in telemetry.metrics


def test_rejects_existing_complete_when_bytes_differ() -> None:
    """Fail closed when an existing COMPLETE version has different bytes."""
    artifact = _artifact()
    metadata = _metadata(artifact)
    body = FakeBody(b'{"different":true}\n')
    repository = S3GhsaSilverCompletionRepository(
        client=RecordingS3Client(
            put_error=_client_error(412),
            head_response={
                "VersionId": "existing-complete-version",
                "ContentLength": len(artifact.manifest_bytes),
                "Metadata": metadata,
            },
            get_response={
                "Body": body,
                "VersionId": "existing-complete-version",
                "ContentLength": len(artifact.manifest_bytes),
                "Metadata": metadata,
            },
        ),
        bucket_name="opslens-data",
        telemetry=RecordingTelemetry(),
    )

    with pytest.raises(
        GhsaSilverCompletionReplayMismatchError,
        match="bytes do not match",
    ):
        repository.put_if_absent(artifact)

    assert body.closed is True


def test_classifies_complete_409_as_concurrent_write() -> None:
    """Expose S3's retryable COMPLETE conditional-write conflict separately."""
    repository = S3GhsaSilverCompletionRepository(
        client=RecordingS3Client(
            put_error=_client_error(409),
        ),
        bucket_name="opslens-data",
        telemetry=RecordingTelemetry(),
    )

    with pytest.raises(
        GhsaSilverCompletionConcurrentWriteError,
        match="Concurrent",
    ):
        repository.put_if_absent(_artifact())


def test_propagates_unexpected_complete_s3_failure() -> None:
    """Keep infrastructure failure distinct from idempotent replay."""
    repository = S3GhsaSilverCompletionRepository(
        client=RecordingS3Client(
            put_error=_client_error(500),
        ),
        bucket_name="opslens-data",
        telemetry=RecordingTelemetry(),
    )

    with pytest.raises(ClientError):
        repository.put_if_absent(_artifact())
