"""Unit tests for immutable NVD Bootstrap Bronze S3 persistence."""

import gzip
import hashlib
from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext

import pytest
from botocore.exceptions import ClientError

from opslens.ingestion.nvd.adapters.outbound.s3_bronze import (
    NvdBronzeEvidenceError,
    S3NvdBootstrapBronzeRepository,
)
from opslens.ingestion.nvd.application.key_factory import (
    NvdBootstrapKeyFactory,
)
from opslens.ingestion.nvd.application.models import NvdBronzeWriteStatus
from opslens.ingestion.nvd.domain.feed_integrity import (
    NvdFeedIntegrityVerifier,
)
from opslens.ingestion.nvd.domain.meta_parser import NvdFeedMetaParser
from opslens.ingestion.nvd.domain.source_identity import (
    NvdBootstrapSourceIdentity,
)

JSON_PAYLOAD = b'{"format":"NVD_CVE","version":"2.0"}'


class FakeTelemetry:
    """Capture S3 adapter operational telemetry."""

    def __init__(self) -> None:
        """Initialize telemetry collections."""
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
        """Capture informational telemetry."""
        self.info_events.append(message)

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture exception telemetry."""
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
        """Capture one span."""
        self.spans.append(name)
        return nullcontext()


class FakeS3Client:
    """Capture deterministic S3 PutObject and HeadObject calls."""

    def __init__(
        self,
        *,
        put_response: Mapping[str, object] | None = None,
        put_error: ClientError | None = None,
        head_response: Mapping[str, object] | None = None,
        head_error: ClientError | None = None,
    ) -> None:
        """Initialize deterministic S3 outcomes."""
        self.put_response = put_response or {}
        self.put_error = put_error
        self.head_response = head_response or {}
        self.head_error = head_error
        self.put_request: dict[str, object] | None = None
        self.head_request: dict[str, object] | None = None

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: Mapping[str, str],
        IfNoneMatch: str,
    ) -> Mapping[str, object]:
        """Capture one conditional S3 write."""
        self.put_request = {
            "Bucket": Bucket,
            "Key": Key,
            "Body": Body,
            "ContentType": ContentType,
            "Metadata": Metadata,
            "IfNoneMatch": IfNoneMatch,
        }

        if self.put_error is not None:
            raise self.put_error

        return self.put_response

    def head_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> Mapping[str, object]:
        """Capture one existing-object verification."""
        self.head_request = {
            "Bucket": Bucket,
            "Key": Key,
        }

        if self.head_error is not None:
            raise self.head_error

        return self.head_response


def _client_error(
    *,
    status_code: int,
    error_code: str,
) -> ClientError:
    """Build one deterministic Botocore ClientError."""
    return ClientError(
        error_response={
            "Error": {
                "Code": error_code,
                "Message": "test error",
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


def _source():
    """Build deterministic verified NVD source evidence."""
    gzip_payload = gzip.compress(
        JSON_PAYLOAD,
        mtime=0,
    )

    source_sha256 = hashlib.sha256(JSON_PAYLOAD).hexdigest()

    meta_payload = (
        "lastModifiedDate:2026-08-18T03:00:12-04:00\n"
        f"size:{len(JSON_PAYLOAD)}\n"
        "zipSize:1\n"
        f"gzSize:{len(gzip_payload)}\n"
        f"sha256:{source_sha256}\n"
    ).encode()

    meta = NvdFeedMetaParser().parse(meta_payload)

    artifact = NvdFeedIntegrityVerifier().verify(
        payload=gzip_payload,
        meta=meta,
    )

    identity = NvdBootstrapSourceIdentity(
        feed_year=2026,
        meta=meta,
    )

    keys = NvdBootstrapKeyFactory().build(identity)

    return artifact, identity, keys


def test_create_feed_uses_conditional_write_and_exact_bytes() -> None:
    """Persist the exact gzip bytes using If-None-Match."""
    artifact, identity, keys = _source()
    telemetry = FakeTelemetry()

    client = FakeS3Client(
        put_response={
            "VersionId": "feed-version-123",
            "ETag": '"feed-etag"',
        }
    )

    repository = S3NvdBootstrapBronzeRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    result = repository.create_feed(
        artifact=artifact,
        identity=identity,
        object_key=keys.feed_key,
    )

    assert result.status is NvdBronzeWriteStatus.CREATED
    assert result.version_id == "feed-version-123"

    assert client.put_request is not None
    assert client.put_request["Body"] == artifact.raw_gzip_bytes
    assert client.put_request["IfNoneMatch"] == "*"
    assert client.put_request["ContentType"] == "application/gzip"

    metadata = client.put_request["Metadata"]

    assert isinstance(metadata, Mapping)
    assert metadata["artifact_kind"] == "feed"
    assert metadata["source_sha256"] == identity.meta.source_sha256
    assert metadata["object_sha256"] == (artifact.bronze_object_sha256)


def test_create_meta_preserves_exact_meta_bytes() -> None:
    """Persist the original META artifact without reserialization."""
    _, identity, keys = _source()
    telemetry = FakeTelemetry()

    client = FakeS3Client(
        put_response={
            "VersionId": "meta-version-123",
        }
    )

    repository = S3NvdBootstrapBronzeRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    result = repository.create_meta(
        identity=identity,
        object_key=keys.meta_key,
    )

    assert result.version_id == "meta-version-123"
    assert client.put_request is not None
    assert client.put_request["Body"] == identity.meta.raw_bytes


def test_precondition_failure_verifies_existing_object() -> None:
    """Resolve an idempotent 412 through exact existing-object evidence."""
    artifact, identity, keys = _source()
    telemetry = FakeTelemetry()

    client = FakeS3Client(
        put_error=_client_error(
            status_code=412,
            error_code="PreconditionFailed",
        ),
        head_response={
            "VersionId": "existing-version-123",
            "ETag": '"existing-etag"',
            "ContentLength": artifact.gzip_size_bytes,
            "ContentType": "application/gzip",
            "Metadata": {
                "object_sha256": artifact.bronze_object_sha256,
            },
        },
    )

    repository = S3NvdBootstrapBronzeRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    result = repository.create_feed(
        artifact=artifact,
        identity=identity,
        object_key=keys.feed_key,
    )

    assert result.status is NvdBronzeWriteStatus.ALREADY_EXISTS
    assert result.version_id == "existing-version-123"
    assert client.head_request == {
        "Bucket": "opslens-test-data",
        "Key": keys.feed_key,
    }

    assert (
        "NvdBronzeAlreadyExists",
        1.0,
        "Count",
    ) in telemetry.metrics


def test_precondition_failure_rejects_existing_hash_mismatch() -> None:
    """Fail closed when the existing object has different provenance."""
    artifact, identity, keys = _source()
    telemetry = FakeTelemetry()

    client = FakeS3Client(
        put_error=_client_error(
            status_code=412,
            error_code="PreconditionFailed",
        ),
        head_response={
            "VersionId": "existing-version",
            "ContentLength": artifact.gzip_size_bytes,
            "ContentType": "application/gzip",
            "Metadata": {
                "object_sha256": "0" * 64,
            },
        },
    )

    repository = S3NvdBootstrapBronzeRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    with pytest.raises(
        NvdBronzeEvidenceError,
        match="SHA-256 metadata",
    ):
        repository.create_feed(
            artifact=artifact,
            identity=identity,
            object_key=keys.feed_key,
        )


def test_precondition_failure_rejects_existing_size_mismatch() -> None:
    """Fail closed when the existing object has a different byte size."""
    artifact, identity, keys = _source()
    telemetry = FakeTelemetry()

    client = FakeS3Client(
        put_error=_client_error(
            status_code=412,
            error_code="PreconditionFailed",
        ),
        head_response={
            "VersionId": "existing-version",
            "ContentLength": artifact.gzip_size_bytes + 1,
            "ContentType": "application/gzip",
            "Metadata": {
                "object_sha256": artifact.bronze_object_sha256,
            },
        },
    )

    repository = S3NvdBootstrapBronzeRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    with pytest.raises(
        NvdBronzeEvidenceError,
        match="size does not match",
    ):
        repository.create_feed(
            artifact=artifact,
            identity=identity,
            object_key=keys.feed_key,
        )


def test_created_object_requires_s3_version_id() -> None:
    """Fail closed when a successful S3 write lacks VersionId evidence."""
    artifact, identity, keys = _source()
    telemetry = FakeTelemetry()

    client = FakeS3Client(
        put_response={
            "ETag": '"etag-without-version"',
        }
    )

    repository = S3NvdBootstrapBronzeRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    with pytest.raises(
        NvdBronzeEvidenceError,
        match="does not expose an S3 VersionId",
    ):
        repository.create_feed(
            artifact=artifact,
            identity=identity,
            object_key=keys.feed_key,
        )


def test_existing_object_requires_s3_version_id() -> None:
    """Fail closed when an idempotent existing object lacks VersionId."""
    artifact, identity, keys = _source()
    telemetry = FakeTelemetry()

    client = FakeS3Client(
        put_error=_client_error(
            status_code=412,
            error_code="PreconditionFailed",
        ),
        head_response={
            "ContentLength": artifact.gzip_size_bytes,
            "ContentType": "application/gzip",
            "Metadata": {
                "object_sha256": artifact.bronze_object_sha256,
            },
        },
    )

    repository = S3NvdBootstrapBronzeRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    with pytest.raises(
        NvdBronzeEvidenceError,
        match="does not expose an S3 VersionId",
    ):
        repository.create_feed(
            artifact=artifact,
            identity=identity,
            object_key=keys.feed_key,
        )


def test_conditional_conflict_is_propagated_for_retry() -> None:
    """Propagate S3 409 instead of interpreting it as idempotency."""
    artifact, identity, keys = _source()
    telemetry = FakeTelemetry()

    error = _client_error(
        status_code=409,
        error_code="ConditionalRequestConflict",
    )

    repository = S3NvdBootstrapBronzeRepository(
        client=FakeS3Client(put_error=error),
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    with pytest.raises(ClientError) as exc_info:
        repository.create_feed(
            artifact=artifact,
            identity=identity,
            object_key=keys.feed_key,
        )

    assert exc_info.value is error


def test_rejects_empty_bucket_name() -> None:
    """Reject repository construction without an S3 bucket."""
    with pytest.raises(
        ValueError,
        match="bucket name cannot be empty",
    ):
        S3NvdBootstrapBronzeRepository(
            client=FakeS3Client(),
            bucket_name=" ",
            telemetry=FakeTelemetry(),
        )
