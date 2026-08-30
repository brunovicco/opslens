"""Unit tests for historical EPSS Silver conditional S3 persistence."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext

import pytest
from botocore.exceptions import ClientError

from opslens.transformation.epss.adapters.outbound.s3_history_silver import (
    HistoricalEpssSilverConcurrentWriteError,
    HistoricalEpssSilverWriteEvidenceError,
    S3HistoricalEpssSilverPutResponse,
    S3HistoricalEpssSilverRepository,
)
from opslens.transformation.epss.history.models import HistoricalEpssSilverArtifactV1
from opslens.transformation.epss.history.persistence import (
    HistoricalEpssSilverAlreadyExistsError,
)

KEY = "silver/epss/snapshot_date=2021-04-14/part-00000.parquet"
ARTIFACT = HistoricalEpssSilverArtifactV1(
    parquet_bytes=b"PAR1historical-epss",
    row_count=64_712,
    schema_version=2,
)


class FakeTelemetry:
    """Capture operational telemetry emitted by the S3 adapter."""

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


class FakeS3Client:
    """Capture conditional PutObject requests and return configured evidence."""

    def __init__(
        self,
        *,
        response: S3HistoricalEpssSilverPutResponse | None = None,
        error: ClientError | None = None,
    ) -> None:
        """Initialize deterministic fake S3 behavior."""
        self.response = response or {"VersionId": "silver-version-1", "ETag": '"etag"'}
        self.error = error
        self.request: dict[str, object] | None = None

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: Mapping[str, str],
        IfNoneMatch: str,
    ) -> S3HistoricalEpssSilverPutResponse:
        """Capture one PutObject call."""
        self.request = {
            "Bucket": Bucket,
            "Key": Key,
            "Body": Body,
            "ContentType": ContentType,
            "Metadata": Metadata,
            "IfNoneMatch": IfNoneMatch,
        }
        if self.error is not None:
            raise self.error
        return self.response


def _client_error(*, status_code: int, error_code: str) -> ClientError:
    """Build one deterministic S3 ClientError."""
    return ClientError(
        error_response={
            "Error": {"Code": error_code, "Message": "test error"},
            "ResponseMetadata": {
                "RequestId": "request-id",
                "HostId": "host-id",
                "HTTPStatusCode": status_code,
                "HTTPHeaders": {},
                "RetryAttempts": 0,
            },
        },
        operation_name="PutObject",
    )


def _repository(client: FakeS3Client, telemetry: FakeTelemetry | None = None) -> S3HistoricalEpssSilverRepository:
    """Build the historical Silver repository with deterministic fakes."""
    return S3HistoricalEpssSilverRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry or FakeTelemetry(),
    )


def test_creates_exact_silver_object_and_returns_version_id() -> None:
    """Require conditional creation and preserve exact S3 VersionId evidence."""
    client = FakeS3Client()
    telemetry = FakeTelemetry()
    repository = _repository(client, telemetry)

    stored = repository.put_if_absent(key=KEY, artifact=ARTIFACT)

    assert stored.key == KEY
    assert stored.version_id == "silver-version-1"
    assert stored.parquet_sha256 == ARTIFACT.parquet_sha256
    assert stored.size_bytes == ARTIFACT.size_bytes
    assert client.request is not None
    assert client.request["Body"] == ARTIFACT.parquet_bytes
    assert client.request["IfNoneMatch"] == "*"
    assert client.request["ContentType"] == "application/vnd.apache.parquet"
    assert client.request["Metadata"] == {
        "dataset": "epss_scores",
        "schema_version": "2",
        "parquet_sha256": ARTIFACT.parquet_sha256,
        "row_count": str(ARTIFACT.row_count),
    }
    assert ("EpssHistorySilverCreated", 1.0, "Count") in telemetry.metrics


def test_412_requires_replay_verification_instead_of_success() -> None:
    """Never translate S3 precondition failure directly into successful replay."""
    repository = _repository(
        FakeS3Client(
            error=_client_error(status_code=412, error_code="PreconditionFailed")
        )
    )

    with pytest.raises(HistoricalEpssSilverAlreadyExistsError, match="requires exact replay"):
        repository.put_if_absent(key=KEY, artifact=ARTIFACT)


def test_409_is_explicit_concurrent_write_failure() -> None:
    """Keep concurrent conditional-write conflict distinct from verified replay."""
    repository = _repository(
        FakeS3Client(
            error=_client_error(status_code=409, error_code="ConditionalRequestConflict")
        )
    )

    with pytest.raises(HistoricalEpssSilverConcurrentWriteError, match="Concurrent"):
        repository.put_if_absent(key=KEY, artifact=ARTIFACT)


def test_success_without_version_id_fails_closed() -> None:
    """Reject a successful PutObject response that lacks exact version evidence."""
    repository = _repository(FakeS3Client(response={"ETag": '"etag"'}))

    with pytest.raises(HistoricalEpssSilverWriteEvidenceError, match="requires VersionId"):
        repository.put_if_absent(key=KEY, artifact=ARTIFACT)


def test_unexpected_s3_error_is_propagated() -> None:
    """Propagate non-conditional S3 failures without changing their semantics."""
    error = _client_error(status_code=403, error_code="AccessDenied")
    repository = _repository(FakeS3Client(error=error))

    with pytest.raises(ClientError) as exc_info:
        repository.put_if_absent(key=KEY, artifact=ARTIFACT)

    assert exc_info.value is error
