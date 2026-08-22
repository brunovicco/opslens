"""Tests for NVD Silver COMPLETE S3 persistence and replay."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime
from hashlib import sha256

import pytest
from botocore.exceptions import ClientError

from opslens.transformation.nvd.adapters.outbound.s3_silver_completion import (
    NvdSilverCompletionConcurrentWriteError,
    NvdSilverCompletionReplayMismatchError,
    NvdSilverCompletionWriteEvidenceError,
    S3GetCompletionResponse,
    S3HeadCompletionResponse,
    S3NvdSilverCompletionReplayVerifier,
    S3NvdSilverCompletionRepository,
    S3PutCompletionResponse,
)
from opslens.transformation.nvd.application.errors import (
    NvdSilverCompletionAlreadyExistsError,
)
from opslens.transformation.nvd.completion.manifest import (
    NvdSilverCompletionArtifactV1,
    NvdSilverCompletionManifestV1,
    NvdSilverStoredObjectV1,
)
from opslens.transformation.nvd.provenance.models import (
    NvdBronzeObjectReferenceV1,
    NvdBronzeObjectRole,
    VerifiedNvdBronzeEvidenceV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)


class FakeBody:
    """Provide one in-memory S3 body."""

    def __init__(self, payload: bytes) -> None:
        """Initialize body bytes."""
        self._payload = payload
        self.closed = False

    def read(self) -> bytes:
        """Return body bytes."""
        return self._payload

    def close(self) -> None:
        """Record body closure."""
        self.closed = True


class RecordingClient:
    """Provide configurable COMPLETE S3 operations."""

    def __init__(
        self,
        *,
        put_response: S3PutCompletionResponse | None = None,
        put_error: ClientError | None = None,
        head_response: S3HeadCompletionResponse | None = None,
        get_response: S3GetCompletionResponse | None = None,
    ) -> None:
        """Initialize configured responses."""
        self.put_response = put_response or {}
        self.put_error = put_error
        self.head_response = head_response or {}
        self.get_response = get_response or {}
        self.put_calls = 0
        self.head_calls = 0
        self.get_calls = 0

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: Mapping[str, str],
        IfNoneMatch: str,
    ) -> S3PutCompletionResponse:
        """Return configured PutObject outcome."""
        self.put_calls += 1

        if self.put_error is not None:
            raise self.put_error

        return self.put_response

    def head_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> S3HeadCompletionResponse:
        """Return configured HeadObject outcome."""
        self.head_calls += 1
        return self.head_response

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> S3GetCompletionResponse:
        """Return configured exact GetObject outcome."""
        self.get_calls += 1
        return self.get_response


class Telemetry:
    """Provide minimal in-memory operational telemetry."""

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Accept informational events."""

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Accept exception events."""

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Accept metric samples."""

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Return a no-op span."""
        return nullcontext(object())


def _artifact() -> NvdSilverCompletionArtifactV1:
    """Build one valid COMPLETE persistence artifact."""
    update_id = "a" * 64
    page_bytes = b"page"

    evidence = VerifiedNvdBronzeEvidenceV1(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        source_batch_id=update_id,
        manifest_key=f"bronze/nvd/cve/updates/update_id={update_id}/manifest.json",
        manifest_version_id="bronze-manifest-v1",
        manifest_sha256="b" * 64,
        manifest_size_bytes=10,
        objects=(
            NvdBronzeObjectReferenceV1(
                role=NvdBronzeObjectRole.PAGE,
                key=(
                    f"bronze/nvd/cve/updates/update_id={update_id}/page_start=000000/response.json"
                ),
                version_id="page-v1",
                size_bytes=len(page_bytes),
                sha256=sha256(page_bytes).hexdigest(),
                page_start=0,
                source_timestamp="2026-08-22T12:00:00.000",
            ),
        ),
        bootstrap_feed_year=None,
        bootstrap_feed_revision=None,
        bootstrap_source_observed_at=None,
        incremental_update_id=update_id,
        incremental_total_results=0,
        incremental_window_start_at=datetime(
            2026,
            8,
            21,
            tzinfo=UTC,
        ),
        incremental_window_end_at=datetime(
            2026,
            8,
            22,
            tzinfo=UTC,
        ),
    )

    manifest = NvdSilverCompletionManifestV1(
        bronze_evidence=evidence,
        silver_object=NvdSilverStoredObjectV1(
            key="silver/nvd/cve/part-00000.parquet",
            version_id="parquet-v1",
            sha256="c" * 64,
            size_bytes=100,
            row_count=0,
        ),
        logical_record_set_sha256="d" * 64,
        warnings=(),
    )

    raw_bytes = b'{"completion_status":"complete"}\n'

    return NvdSilverCompletionArtifactV1(
        manifest=manifest,
        manifest_key="silver/nvd/cve/manifest.json",
        manifest_bytes=raw_bytes,
        manifest_sha256=sha256(raw_bytes).hexdigest(),
    )


def _client_error(status_code: int) -> ClientError:
    """Build one fully typed Botocore ClientError."""
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


def test_creates_complete_and_requires_version_id() -> None:
    """Create COMPLETE conditionally and capture exact VersionId."""
    artifact = _artifact()
    client = RecordingClient(
        put_response={"VersionId": "complete-v1"},
    )

    stored = S3NvdSilverCompletionRepository(
        client=client,
        bucket_name="opslens-data",
        telemetry=Telemetry(),
    ).put_if_absent(
        artifact=artifact,
    )

    assert stored.version_id == "complete-v1"
    assert stored.sha256 == artifact.manifest_sha256
    assert client.put_calls == 1


def test_rejects_success_without_version_id() -> None:
    """Never accept COMPLETE without exact persisted version evidence."""
    with pytest.raises(
        NvdSilverCompletionWriteEvidenceError,
        match="VersionId",
    ):
        S3NvdSilverCompletionRepository(
            client=RecordingClient(
                put_response={},
            ),
            bucket_name="opslens-data",
            telemetry=Telemetry(),
        ).put_if_absent(
            artifact=_artifact(),
        )


def test_412_requires_exact_replay() -> None:
    """Do not treat an existing COMPLETE key as proof by itself."""
    with pytest.raises(
        NvdSilverCompletionAlreadyExistsError,
        match="replay",
    ):
        S3NvdSilverCompletionRepository(
            client=RecordingClient(
                put_error=_client_error(412),
            ),
            bucket_name="opslens-data",
            telemetry=Telemetry(),
        ).put_if_absent(
            artifact=_artifact(),
        )


def test_409_remains_concurrent_write_failure() -> None:
    """Expose concurrent COMPLETE creation separately."""
    with pytest.raises(
        NvdSilverCompletionConcurrentWriteError,
    ):
        S3NvdSilverCompletionRepository(
            client=RecordingClient(
                put_error=_client_error(409),
            ),
            bucket_name="opslens-data",
            telemetry=Telemetry(),
        ).put_if_absent(
            artifact=_artifact(),
        )


def test_replay_verifies_exact_complete_bytes() -> None:
    """Accept existing COMPLETE only through exact immutable-version equality."""
    artifact = _artifact()
    body = FakeBody(artifact.manifest_bytes)

    client = RecordingClient(
        head_response={
            "VersionId": "complete-v1",
            "ContentLength": len(artifact.manifest_bytes),
        },
        get_response={
            "Body": body,
            "VersionId": "complete-v1",
            "ContentLength": len(artifact.manifest_bytes),
        },
    )

    stored = S3NvdSilverCompletionReplayVerifier(
        client=client,
        bucket_name="opslens-data",
        telemetry=Telemetry(),
    ).verify_current(
        artifact=artifact,
    )

    assert stored.version_id == "complete-v1"
    assert stored.sha256 == artifact.manifest_sha256
    assert body.closed is True
    assert client.head_calls == 1
    assert client.get_calls == 1


def test_replay_rejects_different_same_size_bytes() -> None:
    """Fail closed when existing COMPLETE content differs."""
    artifact = _artifact()
    different = bytearray(artifact.manifest_bytes)
    different[1] ^= 1
    payload = bytes(different)

    client = RecordingClient(
        head_response={
            "VersionId": "complete-v1",
            "ContentLength": len(payload),
        },
        get_response={
            "Body": FakeBody(payload),
            "VersionId": "complete-v1",
            "ContentLength": len(payload),
        },
    )

    with pytest.raises(
        NvdSilverCompletionReplayMismatchError,
        match="SHA-256",
    ):
        S3NvdSilverCompletionReplayVerifier(
            client=client,
            bucket_name="opslens-data",
            telemetry=Telemetry(),
        ).verify_current(
            artifact=artifact,
        )
