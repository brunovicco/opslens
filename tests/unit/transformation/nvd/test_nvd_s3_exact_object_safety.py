"""Safety-bound tests for exact NVD Bronze S3 reads."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext

import pytest

from opslens.transformation.nvd.adapters.outbound.s3_exact_object import (
    NvdS3ObjectEvidenceMismatchError,
    S3GetObjectVersionResponse,
    S3VersionedNvdBronzeObjectReader,
)


class RecordingBody:
    """Record whether an S3 streaming body was materialized or closed."""

    def __init__(
        self,
        payload: bytes,
    ) -> None:
        """Initialize the body with deterministic bytes."""
        self._payload = payload
        self.read_calls = 0
        self.close_calls = 0

    def read(self) -> bytes:
        """Return the configured bytes and record materialization."""
        self.read_calls += 1
        return self._payload

    def close(self) -> None:
        """Record response-body cleanup."""
        self.close_calls += 1


class SingleResponseS3Client:
    """Return one configured exact-version S3 response."""

    def __init__(
        self,
        response: S3GetObjectVersionResponse,
    ) -> None:
        """Initialize the fake S3 client."""
        self._response = response
        self.calls: list[tuple[str, str, str]] = []

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> S3GetObjectVersionResponse:
        """Return the configured response and record its coordinate."""
        self.calls.append(
            (
                Bucket,
                Key,
                VersionId,
            )
        )

        return self._response


class NullTelemetry:
    """Implement the operational telemetry port without side effects."""

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Ignore one informational event."""
        _ = (
            message,
            fields,
        )

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Ignore one exception event."""
        _ = (
            message,
            fields,
        )

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Ignore one metric."""
        _ = (
            name,
            value,
            unit,
        )

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Return a no-op tracing span."""
        _ = name
        return nullcontext(object())


def test_oversized_manifest_is_rejected_before_body_read() -> None:
    """Reject an oversized manifest without materializing its bytes."""
    body = RecordingBody(
        b"should-not-be-read",
    )

    response: S3GetObjectVersionResponse = {
        "Body": body,
        "ContentLength": 9,
        "VersionId": "manifest-v1",
    }

    reader = S3VersionedNvdBronzeObjectReader(
        client=SingleResponseS3Client(response),
        bucket_name="data-bucket",
        telemetry=NullTelemetry(),
        max_manifest_bytes=8,
        max_source_object_bytes=128,
    )

    with pytest.raises(
        NvdS3ObjectEvidenceMismatchError,
        match="size limit",
    ):
        reader.get(
            key=("bronze/nvd/cve/updates/update_id=batch/manifest.json"),
            version_id="manifest-v1",
        )

    assert body.read_calls == 0
    assert body.close_calls == 1


def test_oversized_source_object_is_rejected_before_body_read() -> None:
    """Reject an oversized source object before allocating its payload."""
    body = RecordingBody(
        b"should-not-be-read",
    )

    response: S3GetObjectVersionResponse = {
        "Body": body,
        "ContentLength": 17,
        "VersionId": "page-v1",
    }

    reader = S3VersionedNvdBronzeObjectReader(
        client=SingleResponseS3Client(response),
        bucket_name="data-bucket",
        telemetry=NullTelemetry(),
        max_manifest_bytes=8,
        max_source_object_bytes=16,
    )

    with pytest.raises(
        NvdS3ObjectEvidenceMismatchError,
        match="size limit",
    ):
        reader.get(
            key=("bronze/nvd/cve/updates/update_id=batch/page_start=000000/response.json"),
            version_id="page-v1",
        )

    assert body.read_calls == 0
    assert body.close_calls == 1


def test_wrong_version_is_rejected_before_body_read() -> None:
    """Reject detached exact-version evidence before reading the body."""
    body = RecordingBody(
        b"payload",
    )

    response: S3GetObjectVersionResponse = {
        "Body": body,
        "ContentLength": 7,
        "VersionId": "wrong-version",
    }

    reader = S3VersionedNvdBronzeObjectReader(
        client=SingleResponseS3Client(response),
        bucket_name="data-bucket",
        telemetry=NullTelemetry(),
        max_manifest_bytes=1024,
        max_source_object_bytes=1024,
    )

    with pytest.raises(
        NvdS3ObjectEvidenceMismatchError,
        match="VersionId",
    ):
        reader.get(
            key=("bronze/nvd/cve/updates/update_id=batch/page_start=000000/response.json"),
            version_id="page-v1",
        )

    assert body.read_calls == 0
    assert body.close_calls == 1
