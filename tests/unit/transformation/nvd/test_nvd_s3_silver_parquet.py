"""Tests for immutable NVD Silver Parquet persistence."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from hashlib import sha256

import pytest
from botocore.exceptions import ClientError

from opslens.transformation.nvd.adapters.outbound.s3_silver_parquet import (
    NvdSilverParquetAlreadyExistsError,
    NvdSilverParquetConcurrentWriteError,
    NvdSilverParquetWriteEvidenceError,
    S3NvdSilverParquetRepository,
    S3PutObjectResponse,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverParquetArtifactV1,
    NvdSilverSourceKind,
)


class RecordingS3Client:
    """Record one configured PutObject interaction."""

    def __init__(
        self,
        response: S3PutObjectResponse | None = None,
        error: ClientError | None = None,
    ) -> None:
        """Initialize the fake S3 write result."""
        self._response = response
        self._error = error
        self.calls: list[dict[str, object]] = []

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: Mapping[str, str],
        IfNoneMatch: str,
    ) -> S3PutObjectResponse:
        """Record one conditional write and return its configured outcome."""
        self.calls.append(
            {
                "Bucket": Bucket,
                "Key": Key,
                "Body": Body,
                "ContentType": ContentType,
                "Metadata": dict(Metadata),
                "IfNoneMatch": IfNoneMatch,
            }
        )

        if self._error is not None:
            raise self._error

        if self._response is None:
            return {}

        return self._response


class RecordingTelemetry:
    """Record operational telemetry emitted by the adapter."""

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
    """Build one minimal valid deterministic Parquet artifact."""
    parquet_bytes = b"PAR1deterministic-nvd-silverPAR1"

    return NvdSilverParquetArtifactV1(
        parquet_bytes=parquet_bytes,
        parquet_sha256=sha256(parquet_bytes).hexdigest(),
        row_count=3,
        size_bytes=len(parquet_bytes),
        schema_version=1,
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        source_batch_id="a" * 64,
    )


def _client_error(
    status_code: int,
) -> ClientError:
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


def test_creates_parquet_conditionally_and_returns_exact_version() -> None:
    """Require create-only semantics and capture the persisted VersionId."""
    artifact = _artifact()
    client = RecordingS3Client(
        response={
            "VersionId": "silver-version-123",
            "ETag": '"etag"',
        }
    )
    telemetry = RecordingTelemetry()

    repository = S3NvdSilverParquetRepository(
        client=client,
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    stored = repository.put_if_absent(
        key="silver/nvd/cve/part-00000.parquet",
        artifact=artifact,
    )

    assert stored.key == "silver/nvd/cve/part-00000.parquet"
    assert stored.version_id == "silver-version-123"
    assert stored.sha256 == artifact.parquet_sha256
    assert stored.size_bytes == artifact.size_bytes
    assert stored.row_count == 3

    assert len(client.calls) == 1
    call = client.calls[0]

    assert call["Bucket"] == "opslens-data"
    assert call["Body"] == artifact.parquet_bytes
    assert call["IfNoneMatch"] == "*"
    assert call["ContentType"] == "application/vnd.apache.parquet"

    metadata = call["Metadata"]
    assert isinstance(metadata, dict)
    assert metadata["parquet_sha256"] == artifact.parquet_sha256
    assert metadata["row_count"] == "3"

    assert telemetry.spans == ["nvd.silver.s3.put_parquet"]
    assert (
        "NvdSilverParquetCreated",
        1.0,
        "Count",
    ) in telemetry.metrics


def test_rejects_successful_write_without_version_id() -> None:
    """Do not create completion evidence without an exact persisted VersionId."""
    telemetry = RecordingTelemetry()

    repository = S3NvdSilverParquetRepository(
        client=RecordingS3Client(
            response={
                "ETag": '"etag"',
            }
        ),
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    with pytest.raises(
        NvdSilverParquetWriteEvidenceError,
        match="VersionId",
    ):
        repository.put_if_absent(
            key="silver/nvd/cve/part-00000.parquet",
            artifact=_artifact(),
        )

    assert (
        "NvdSilverParquetWriteEvidenceMismatch",
        1.0,
        "Count",
    ) in telemetry.metrics


def test_does_not_accept_412_as_verified_replay() -> None:
    """Require later exact verification before trusting an existing object."""
    telemetry = RecordingTelemetry()

    repository = S3NvdSilverParquetRepository(
        client=RecordingS3Client(
            error=_client_error(412),
        ),
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    with pytest.raises(
        NvdSilverParquetAlreadyExistsError,
        match="requires exact replay verification",
    ):
        repository.put_if_absent(
            key="silver/nvd/cve/part-00000.parquet",
            artifact=_artifact(),
        )

    assert (
        "NvdSilverParquetAlreadyExists",
        1.0,
        "Count",
    ) in telemetry.metrics


def test_classifies_409_as_concurrent_write_conflict() -> None:
    """Expose S3's retryable conditional-write conflict separately."""
    telemetry = RecordingTelemetry()

    repository = S3NvdSilverParquetRepository(
        client=RecordingS3Client(
            error=_client_error(409),
        ),
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    with pytest.raises(
        NvdSilverParquetConcurrentWriteError,
        match="Concurrent",
    ):
        repository.put_if_absent(
            key="silver/nvd/cve/part-00000.parquet",
            artifact=_artifact(),
        )

    assert (
        "NvdSilverParquetConcurrentWrite",
        1.0,
        "Count",
    ) in telemetry.metrics


def test_propagates_unexpected_s3_failure() -> None:
    """Keep unexpected infrastructure failures distinct from idempotency."""
    telemetry = RecordingTelemetry()
    error = _client_error(500)

    repository = S3NvdSilverParquetRepository(
        client=RecordingS3Client(
            error=error,
        ),
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    with pytest.raises(ClientError):
        repository.put_if_absent(
            key="silver/nvd/cve/part-00000.parquet",
            artifact=_artifact(),
        )

    assert (
        "NvdSilverParquetWriteFailure",
        1.0,
        "Count",
    ) in telemetry.metrics
