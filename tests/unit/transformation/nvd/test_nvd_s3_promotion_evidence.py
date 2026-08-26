"""Tests for bounded exact-version NVD promotion evidence reads."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext

import pytest
from botocore.exceptions import ClientError

from opslens.transformation.nvd.adapters.outbound.s3_promotion_evidence import (
    NvdPromotionS3EvidenceError,
    NvdPromotionS3ReadError,
    S3NvdPromotionEvidenceReaderV1,
)

BUCKET = "opslens-test-data"
KEY = "silver/nvd/cve/schema_version=1/source_kind=incremental/update_id=" + (
    "a" * 64
) + "/manifest.json"
VERSION_ID = "silver-version-1"
PAYLOAD = b'{"completion_status":"complete"}\n'


class FakeTelemetry:
    """Capture operational telemetry emitted by the exact S3 adapter."""

    def __init__(self) -> None:
        """Initialize captured telemetry."""
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
        del fields
        self.info_events.append(message)

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture one exception event."""
        del fields
        self.exception_events.append(message)

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Capture one operational metric."""
        self.metrics.append((name, value, unit))

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Capture one tracing span."""
        self.spans.append(name)
        return nullcontext()


class FakeBody:
    """Expose deterministic bounded body reads and close evidence."""

    def __init__(self, payload: bytes) -> None:
        """Initialize exact body bytes."""
        self.payload = payload
        self.read_amounts: list[int | None] = []
        self.closed = False

    def read(self, amt: int | None = None) -> bytes:
        """Return up to the requested number of bytes."""
        self.read_amounts.append(amt)
        return self.payload if amt is None else self.payload[:amt]

    def close(self) -> None:
        """Capture response stream closure."""
        self.closed = True


class FakeS3Client:
    """Return one configured exact-version GetObject response."""

    def __init__(
        self,
        *,
        response: Mapping[str, object] | None = None,
        error: ClientError | None = None,
    ) -> None:
        """Initialize deterministic S3 behavior."""
        self.response: Mapping[str, object] = (
            response if response is not None else {}
        )
        self.error = error
        self.requests: list[dict[str, str]] = []

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> Mapping[str, object]:
        """Capture one exact S3 GetObject request."""
        self.requests.append(
            {
                "Bucket": Bucket,
                "Key": Key,
                "VersionId": VersionId,
            }
        )

        if self.error is not None:
            raise self.error

        return self.response


def _response(
    body: FakeBody,
    *,
    version_id: object = VERSION_ID,
    content_length: object = len(PAYLOAD),
) -> Mapping[str, object]:
    """Build one versioned GetObject response fixture."""
    return {
        "Body": body,
        "VersionId": version_id,
        "ContentLength": content_length,
    }


def _reader(
    client: FakeS3Client,
    telemetry: FakeTelemetry | None = None,
) -> S3NvdPromotionEvidenceReaderV1:
    """Build the production reader with deterministic dependencies."""
    return S3NvdPromotionEvidenceReaderV1(
        client=client,
        bucket_name=BUCKET,
        telemetry=telemetry if telemetry is not None else FakeTelemetry(),
    )


def _client_error(status_code: int) -> ClientError:
    """Build one deterministic Botocore GetObject error."""
    return ClientError(
        error_response={
            "Error": {
                "Code": "AccessDenied",
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
        operation_name="GetObject",
    )


def test_read_exact_uses_key_and_version_id_and_closes_body() -> None:
    """Return only bytes from the exact immutable object version requested."""
    body = FakeBody(PAYLOAD)
    telemetry = FakeTelemetry()
    client = FakeS3Client(response=_response(body))

    result = _reader(client, telemetry).read_exact(
        key=KEY,
        version_id=VERSION_ID,
        max_bytes=1024,
    )

    assert client.requests == [
        {
            "Bucket": BUCKET,
            "Key": KEY,
            "VersionId": VERSION_ID,
        }
    ]
    assert result.key == KEY
    assert result.version_id == VERSION_ID
    assert result.raw_bytes == PAYLOAD
    assert body.read_amounts == [len(PAYLOAD) + 1]
    assert body.closed is True
    assert "nvd.promotion.s3.get_object_version" in telemetry.spans
    assert (
        "NvdPromotionS3ObjectBytes",
        float(len(PAYLOAD)),
        "Bytes",
    ) in telemetry.metrics


def test_read_exact_rejects_returned_version_mismatch_and_closes_body() -> None:
    """Fail closed when S3 does not return the exact requested VersionId."""
    body = FakeBody(PAYLOAD)

    with pytest.raises(
        NvdPromotionS3EvidenceError,
        match="VersionId does not match",
    ):
        _reader(
            FakeS3Client(
                response=_response(
                    body,
                    version_id="different-version",
                )
            )
        ).read_exact(
            key=KEY,
            version_id=VERSION_ID,
            max_bytes=1024,
        )

    assert body.closed is True
    assert body.read_amounts == []


def test_read_exact_rejects_content_length_above_bound_without_reading() -> None:
    """Enforce the byte ceiling before consuming the response body."""
    body = FakeBody(PAYLOAD)

    with pytest.raises(
        NvdPromotionS3EvidenceError,
        match="exceeds the configured read bound",
    ):
        _reader(
            FakeS3Client(
                response=_response(
                    body,
                    content_length=2048,
                )
            )
        ).read_exact(
            key=KEY,
            version_id=VERSION_ID,
            max_bytes=1024,
        )

    assert body.closed is True
    assert body.read_amounts == []


def test_read_exact_rejects_short_body_against_content_length() -> None:
    """Require S3 ContentLength to equal the bytes actually observed."""
    body = FakeBody(b"short")

    with pytest.raises(
        NvdPromotionS3EvidenceError,
        match="ContentLength does not match",
    ):
        _reader(
            FakeS3Client(
                response=_response(
                    body,
                    content_length=len(PAYLOAD),
                )
            )
        ).read_exact(
            key=KEY,
            version_id=VERSION_ID,
            max_bytes=1024,
        )

    assert body.closed is True


def test_read_exact_rejects_body_longer_than_declared_content_length() -> None:
    """Detect extra bytes by reading one byte beyond the declared length."""
    body = FakeBody(PAYLOAD + b"x")

    with pytest.raises(
        NvdPromotionS3EvidenceError,
        match="ContentLength does not match",
    ):
        _reader(
            FakeS3Client(
                response=_response(
                    body,
                    content_length=len(PAYLOAD),
                )
            )
        ).read_exact(
            key=KEY,
            version_id=VERSION_ID,
            max_bytes=1024,
        )

    assert body.closed is True


def test_read_exact_rejects_missing_content_length() -> None:
    """Require positive ContentLength evidence before any body read."""
    body = FakeBody(PAYLOAD)

    with pytest.raises(
        NvdPromotionS3EvidenceError,
        match="ContentLength must be positive",
    ):
        _reader(
            FakeS3Client(
                response=_response(
                    body,
                    content_length=None,
                )
            )
        ).read_exact(
            key=KEY,
            version_id=VERSION_ID,
            max_bytes=1024,
        )

    assert body.closed is True
    assert body.read_amounts == []


def test_read_exact_maps_s3_client_error_and_emits_failure_telemetry() -> None:
    """Keep provider failures explicit at the infrastructure boundary."""
    telemetry = FakeTelemetry()

    with pytest.raises(
        NvdPromotionS3ReadError,
        match="Failed to read exact",
    ):
        _reader(
            FakeS3Client(error=_client_error(403)),
            telemetry,
        ).read_exact(
            key=KEY,
            version_id=VERSION_ID,
            max_bytes=1024,
        )

    assert "Failed to read exact NVD promotion evidence object" in (
        telemetry.exception_events
    )
    assert (
        "NvdPromotionS3ObjectReadFailure",
        1.0,
        "Count",
    ) in telemetry.metrics


def test_read_exact_rejects_invalid_local_coordinates_before_s3() -> None:
    """Never issue a provider call for malformed exact-read inputs."""
    client = FakeS3Client()
    reader = _reader(client)

    with pytest.raises(ValueError, match="VersionId"):
        reader.read_exact(
            key=KEY,
            version_id=" ",
            max_bytes=1024,
        )

    with pytest.raises(ValueError, match="max_bytes"):
        reader.read_exact(
            key=KEY,
            version_id=VERSION_ID,
            max_bytes=0,
        )

    assert client.requests == []
