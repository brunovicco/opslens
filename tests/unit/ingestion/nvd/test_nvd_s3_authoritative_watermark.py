"""Unit tests for authoritative NVD watermark S3 CAS semantics."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime
from io import BytesIO

import pytest
from botocore.exceptions import ClientError

from opslens.ingestion.nvd.adapters.outbound.s3_authoritative_watermark import (
    S3NvdAuthoritativeWatermarkStore,
)
from opslens.ingestion.nvd.application.authoritative_watermark import (
    NvdAuthoritativeWatermarkSerializerV1,
    NvdAuthoritativeWatermarkV1,
    NvdWatermarkBootstrapRecoverySeedV1,
    NvdWatermarkEvidenceObjectV1,
)
from opslens.ingestion.nvd.application.authoritative_watermark_store import (
    NvdAuthoritativeWatermarkAlreadyExistsError,
    NvdAuthoritativeWatermarkConflictError,
    NvdAuthoritativeWatermarkPreconditionFailedError,
)


class FakeTelemetry:
    """Capture adapter telemetry."""

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Accept one info event."""

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Accept one exception event."""

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Accept one metric."""

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Return one no-op tracing span."""
        return nullcontext()


class FakeS3Client:
    """Capture current-object GET and conditional PUT requests."""

    def __init__(
        self,
        *,
        get_response: Mapping[str, object] | None = None,
        put_response: Mapping[str, object] | None = None,
        put_error: ClientError | None = None,
    ) -> None:
        """Initialize deterministic S3 behavior."""
        self.get_response = get_response or {}
        self.put_response = put_response or {}
        self.put_error = put_error
        self.put_request: dict[str, object] | None = None

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> Mapping[str, object]:
        """Return configured current-object response."""
        return self.get_response

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: Mapping[str, str],
        IfNoneMatch: str | None = None,
        IfMatch: str | None = None,
    ) -> Mapping[str, object]:
        """Capture one conditional write."""
        self.put_request = {
            "Bucket": Bucket,
            "Key": Key,
            "Body": Body,
            "ContentType": ContentType,
            "Metadata": Metadata,
            "IfNoneMatch": IfNoneMatch,
            "IfMatch": IfMatch,
        }

        if self.put_error is not None:
            raise self.put_error

        return self.put_response


def _client_error(status_code: int) -> ClientError:
    """Build one deterministic S3 ClientError."""
    return ClientError(
        error_response={
            "Error": {
                "Code": "TestError",
                "Message": "test",
            },
            "ResponseMetadata": {
                "RequestId": "test-request-id",
                "HostId": "test-host-id",
                "HTTPStatusCode": status_code,
                "HTTPHeaders": {},
                "RetryAttempts": 0,
            },
        },
        operation_name="PutObject",
    )


def _watermark() -> NvdAuthoritativeWatermarkV1:
    """Build the real Phase 2.3F Bootstrap recovery seed."""
    boundary = datetime(
        2026,
        8,
        18,
        7,
        0,
        12,
        tzinfo=UTC,
    )

    return NvdAuthoritativeWatermarkV1(
        committed_through_at=boundary,
        commit_basis=NvdWatermarkBootstrapRecoverySeedV1(
            source_revision_at=boundary,
            bootstrap_manifest=NvdWatermarkEvidenceObjectV1(
                key=(
                    "bronze/nvd/cve/bootstrap/"
                    "feed_year=2026/"
                    "feed_revision=20260818T070012Z-test/"
                    "manifest.json"
                ),
                version_id="bootstrap-version",
                sha256="c" * 64,
            ),
        ),
    )


def _store(
    client: FakeS3Client,
) -> S3NvdAuthoritativeWatermarkStore:
    """Build the S3 adapter."""
    return S3NvdAuthoritativeWatermarkStore(
        client=client,
        bucket_name="test-bucket",
        object_key="control/nvd/cve/incremental/watermark.json",
        telemetry=FakeTelemetry(),
    )


def test_initialize_uses_if_none_match() -> None:
    """Seed state only if no current watermark exists."""
    client = FakeS3Client(
        put_response={
            "VersionId": "watermark-version-1",
            "ETag": '"etag-1"',
        }
    )

    result = _store(client).initialize(
        watermark=_watermark(),
    )

    assert client.put_request is not None
    assert client.put_request["IfNoneMatch"] == "*"
    assert client.put_request["IfMatch"] is None
    assert result.version_id == "watermark-version-1"
    assert result.etag == '"etag-1"'


def test_initialize_412_is_already_exists() -> None:
    """Expose a lost initialization race explicitly."""
    client = FakeS3Client(
        put_error=_client_error(412),
    )

    with pytest.raises(
        NvdAuthoritativeWatermarkAlreadyExistsError,
    ):
        _store(client).initialize(
            watermark=_watermark(),
        )


def test_compare_and_swap_uses_exact_previous_etag() -> None:
    """Advance only against the exact previously-read object."""
    client = FakeS3Client(
        put_response={
            "VersionId": "watermark-version-2",
            "ETag": '"etag-2"',
        }
    )

    _store(client).compare_and_swap(
        watermark=_watermark(),
        expected_etag='"etag-1"',
    )

    assert client.put_request is not None
    assert client.put_request["IfNoneMatch"] is None
    assert client.put_request["IfMatch"] == '"etag-1"'


def test_compare_and_swap_412_is_precondition_failure() -> None:
    """Classify a stale expected ETag without overwriting state."""
    client = FakeS3Client(
        put_error=_client_error(412),
    )

    with pytest.raises(
        NvdAuthoritativeWatermarkPreconditionFailedError,
    ):
        _store(client).compare_and_swap(
            watermark=_watermark(),
            expected_etag='"stale-etag"',
        )


def test_compare_and_swap_409_is_conflict() -> None:
    """Expose a conditional-request concurrency conflict."""
    client = FakeS3Client(
        put_error=_client_error(409),
    )

    with pytest.raises(
        NvdAuthoritativeWatermarkConflictError,
    ):
        _store(client).compare_and_swap(
            watermark=_watermark(),
            expected_etag='"etag-1"',
        )


def test_load_verifies_exact_canonical_state() -> None:
    """Bind parsed business state to ETag, VersionId and exact bytes."""
    watermark = _watermark()
    serializer = NvdAuthoritativeWatermarkSerializerV1()
    payload = serializer.serialize(watermark)

    import hashlib

    payload_sha256 = hashlib.sha256(payload).hexdigest()

    client = FakeS3Client(
        get_response={
            "Body": BytesIO(payload),
            "ContentLength": len(payload),
            "ContentType": "application/json",
            "VersionId": "watermark-version-1",
            "ETag": '"etag-1"',
            "Metadata": {
                "source": "nvd-cve",
                "source_interface": "cve-api-2.0",
                "artifact_kind": "authoritative-watermark",
                "watermark_version": "1",
                "state": "committed",
                "committed_through_at": "2026-08-18T07:00:12Z",
                "commit_basis": (
                    "bootstrap_source_revision_recovery_seed"
                ),
                "object_sha256": payload_sha256,
            },
        }
    )

    result = _store(client).load()

    assert result.watermark == watermark
    assert result.version_id == "watermark-version-1"
    assert result.etag == '"etag-1"'
    assert result.sha256 == payload_sha256
