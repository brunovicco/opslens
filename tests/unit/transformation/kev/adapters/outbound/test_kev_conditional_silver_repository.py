"""Unit tests for conditional CISA KEV Silver S3 persistence."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from io import BytesIO
from typing import BinaryIO

import pytest
from botocore.exceptions import ClientError

from opslens.transformation.kev.adapters.outbound.s3_silver import (
    S3SilverKevArtifactRepository,
)
from opslens.transformation.kev.application.runtime_models import (
    KevSilverRepositoryWriteStatus,
)

BUCKET = "opslens-dev-data-487757851499-us-east-1"

KEY = "silver/kev/snapshot_date=2026-08-17/part-00000.parquet"


class FakeTelemetry:
    """Capture operational telemetry emitted by the Silver repository."""

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
        """Accept informational telemetry."""
        del message, fields

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture exception telemetry."""
        del fields
        self.exceptions.append(message)

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Capture emitted metric names."""
        del value, unit
        self.metrics.append(name)

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Return one no-op tracing span."""
        del name
        return nullcontext()


class FakeS3Client:
    """Capture conditional PutObject calls or raise a configured error."""

    def __init__(
        self,
        *,
        error: ClientError | None = None,
    ) -> None:
        """Initialize the fake S3 client."""
        self._error = error
        self.calls = 0
        self.bucket: str | None = None
        self.key: str | None = None
        self.body: bytes | None = None
        self.content_type: str | None = None
        self.metadata: dict[str, str] | None = None
        self.if_none_match: str | None = None

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: BinaryIO,
        ContentType: str,
        Metadata: Mapping[str, str],
        IfNoneMatch: str,
    ) -> Mapping[str, object]:
        """Capture the request and return or raise the configured outcome."""
        self.calls += 1
        self.bucket = Bucket
        self.key = Key
        self.body = Body.read()
        self.content_type = ContentType
        self.metadata = dict(Metadata)
        self.if_none_match = IfNoneMatch

        if self._error is not None:
            raise self._error

        return {
            "ETag": '"silver-etag"',
            "VersionId": "silver-version-123",
        }


def _client_error(
    status_code: int,
) -> ClientError:
    """Build one representative Botocore PutObject failure."""
    return ClientError(
        {
            "Error": {
                "Code": "TestError",
                "Message": "test failure",
            },
            "ResponseMetadata": {
                "RequestId": "test-request-id",
                "HostId": "test-host-id",
                "HTTPStatusCode": status_code,
                "HTTPHeaders": {},
                "RetryAttempts": 0,
            },
        },
        "PutObject",
    )


def _metadata() -> dict[str, str]:
    """Build representative immutable KEV Silver provenance metadata."""
    return {
        "source": "cisa-kev",
        "catalog_version": "2026.08.14",
        "date_released": "2026-08-14T16:34:49.039100Z",
        "retrieved_at": "2026-08-17T03:52:03.692159Z",
        "source_sha256": "a" * 64,
        "schema_version": "1",
        "row_count": "1665",
        "bronze_version_id": "bronze-version-123",
        "bronze_etag": "bronze-etag",
    }


def test_conditionally_creates_immutable_silver_artifact() -> None:
    """Create Silver with If-None-Match and preserve provenance metadata."""
    client = FakeS3Client()
    telemetry = FakeTelemetry()

    repository = S3SilverKevArtifactRepository(
        client=client,
        bucket_name=BUCKET,
        telemetry=telemetry,
    )

    status = repository.put_if_absent(
        key=KEY,
        artifact=BytesIO(b"PARQUET"),
        metadata=_metadata(),
    )

    assert status is KevSilverRepositoryWriteStatus.CREATED
    assert client.calls == 1
    assert client.bucket == BUCKET
    assert client.key == KEY
    assert client.body == b"PARQUET"
    assert client.content_type == "application/vnd.apache.parquet"
    assert client.metadata == _metadata()
    assert client.if_none_match == "*"

    assert "KevSilverCreated" in telemetry.metrics


def test_maps_precondition_failure_to_already_exists() -> None:
    """Treat S3 HTTP 412 as successful idempotent replay."""
    client = FakeS3Client(
        error=_client_error(412),
    )
    telemetry = FakeTelemetry()

    repository = S3SilverKevArtifactRepository(
        client=client,
        bucket_name=BUCKET,
        telemetry=telemetry,
    )

    status = repository.put_if_absent(
        key=KEY,
        artifact=BytesIO(b"PARQUET"),
        metadata=_metadata(),
    )

    assert status is KevSilverRepositoryWriteStatus.ALREADY_EXISTS
    assert client.calls == 1
    assert "KevSilverAlreadyExists" in telemetry.metrics
    assert "KevSilverWriteFailure" not in telemetry.metrics


@pytest.mark.parametrize(
    "status_code",
    [
        409,
        403,
        500,
    ],
)
def test_propagates_non_idempotent_s3_failures(
    status_code: int,
) -> None:
    """Propagate unexpected S3 failures for outer runtime retry handling."""
    error = _client_error(status_code)
    telemetry = FakeTelemetry()

    repository = S3SilverKevArtifactRepository(
        client=FakeS3Client(error=error),
        bucket_name=BUCKET,
        telemetry=telemetry,
    )

    with pytest.raises(ClientError) as captured:
        repository.put_if_absent(
            key=KEY,
            artifact=BytesIO(b"PARQUET"),
            metadata=_metadata(),
        )

    assert captured.value is error
    assert "KevSilverWriteFailure" in telemetry.metrics
    assert "Failed to persist CISA KEV Silver artifact" in telemetry.exceptions


def test_rejects_empty_bucket_name() -> None:
    """Reject an invalid destination bucket configuration."""
    with pytest.raises(
        ValueError,
        match="bucket name",
    ):
        S3SilverKevArtifactRepository(
            client=FakeS3Client(),
            bucket_name="   ",
            telemetry=FakeTelemetry(),
        )


def test_rejects_empty_object_key() -> None:
    """Reject an empty deterministic Silver object key."""
    repository = S3SilverKevArtifactRepository(
        client=FakeS3Client(),
        bucket_name=BUCKET,
        telemetry=FakeTelemetry(),
    )

    with pytest.raises(
        ValueError,
        match="object key",
    ):
        repository.put_if_absent(
            key="   ",
            artifact=BytesIO(b"PARQUET"),
            metadata=_metadata(),
        )
