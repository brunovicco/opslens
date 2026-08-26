"""Unit tests for exact NVD incremental COMPLETE S3 reads."""

import hashlib
from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime
from typing import cast

import pytest
from botocore.exceptions import ClientError

from opslens.ingestion.nvd.adapters.outbound.s3_incremental_complete import (
    NvdIncrementalCompleteManifestEvidenceError,
    NvdIncrementalCompleteManifestReadError,
    S3NvdIncrementalCompleteManifestReader,
)
from opslens.ingestion.nvd.application.incremental_complete import (
    NvdIncrementalManifestParser,
)
from opslens.ingestion.nvd.application.incremental_manifest import (
    NvdIncrementalManifest,
    NvdIncrementalManifestSerializer,
    NvdIncrementalStoredPage,
)
from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)


class FakeTelemetry:
    """Capture operational telemetry emitted by the COMPLETE reader."""

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
        self.info_events.append(message)

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture one exception event."""
        self.exception_events.append(message)

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Capture one operational metric."""
        self.metrics.append(
            (
                name,
                value,
                unit,
            )
        )

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Capture one tracing span."""
        self.spans.append(name)
        return nullcontext()


class FakeBody:
    """Return deterministic S3 object bytes."""

    def __init__(
        self,
        payload: bytes,
    ) -> None:
        """Initialize response bytes."""
        self._payload = payload

    def read(
        self,
        amt: int | None = None,
    ) -> bytes:
        """Read deterministic response bytes."""
        if amt is None:
            return self._payload

        return self._payload[:amt]


class FakeS3Client:
    """Provide one deterministic GetObject result."""

    def __init__(
        self,
        *,
        response: Mapping[str, object] | None = None,
        error: ClientError | None = None,
    ) -> None:
        """Initialize deterministic S3 behavior."""
        self.response: Mapping[str, object] = (
            response
            if response is not None
            else dict[str, object]()
        )
        self.error = error
        self.request: dict[str, str] | None = None

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> Mapping[str, object]:
        """Capture one exact-key GetObject."""
        self.request = {
            "Bucket": Bucket,
            "Key": Key,
        }

        if self.error is not None:
            raise self.error

        return self.response


def _client_error(
    *,
    status_code: int,
    error_code: str,
) -> ClientError:
    """Build one deterministic GetObject failure."""
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
        operation_name="GetObject",
    )


def _window() -> NvdIncrementalWindow:
    """Build the logical window represented by COMPLETE evidence."""
    return NvdIncrementalWindow(
        start_at=datetime(
            2026,
            8,
            18,
            7,
            0,
            12,
            tzinfo=UTC,
        ),
        end_at=datetime(
            2026,
            8,
            18,
            7,
            10,
            12,
            tzinfo=UTC,
        ),
    )


def _manifest(
    *,
    window: NvdIncrementalWindow,
) -> NvdIncrementalManifest:
    """Build one zero-result canonical COMPLETE manifest."""
    return NvdIncrementalManifest(
        update_id=window.update_id,
        window_start_at=window.start_at,
        window_end_at=window.end_at,
        total_results=0,
        pages=(
            NvdIncrementalStoredPage(
                key=(
                    "bronze/nvd/cve/updates/"
                    f"update_id={window.update_id}/"
                    "page_start=000000/"
                    "response.json"
                ),
                version_id="page-version",
                size_bytes=146,
                sha256="a" * 64,
                start_index=0,
                results_per_page=0,
                total_results=0,
                source_timestamp="2026-08-24T19:51:57.077",
            ),
        ),
    )


def _valid_response(
    *,
    window: NvdIncrementalWindow,
) -> dict[str, object]:
    """Build one valid exact S3 COMPLETE response."""
    manifest = _manifest(
        window=window,
    )

    payload = NvdIncrementalManifestSerializer().serialize(
        manifest
    )

    sha256 = hashlib.sha256(
        payload
    ).hexdigest()

    return {
        "Body": FakeBody(
            payload
        ),
        "VersionId": "manifest-version",
        "ETag": '"manifest-etag"',
        "ContentLength": len(
            payload
        ),
        "ContentType": "application/json",
        "Metadata": {
            "source": manifest.SOURCE,
            "source_interface": manifest.SOURCE_INTERFACE,
            "artifact_kind": "manifest",
            "update_id": manifest.update_id,
            "window_start_at": (
                manifest.canonical_window_start_at
            ),
            "window_end_at": (
                manifest.canonical_window_end_at
            ),
            "total_results": str(
                manifest.total_results
            ),
            "page_count": str(
                manifest.page_count
            ),
            "manifest_version": (
                manifest.MANIFEST_VERSION
            ),
            "completion_status": (
                manifest.COMPLETION_STATUS
            ),
            "object_sha256": sha256,
        },
    }


def _reader(
    *,
    client: FakeS3Client,
    telemetry: FakeTelemetry | None = None,
) -> S3NvdIncrementalCompleteManifestReader:
    """Build one COMPLETE reader under test."""
    return S3NvdIncrementalCompleteManifestReader(
        client=client,
        bucket_name="opslens-test-data",
        parser=NvdIncrementalManifestParser(),
        telemetry=(
            telemetry
            if telemetry is not None
            else FakeTelemetry()
        ),
    )


def _manifest_key(
    *,
    window: NvdIncrementalWindow,
) -> str:
    """Build the canonical COMPLETE key used by tests."""
    return (
        "bronze/nvd/cve/updates/"
        f"update_id={window.update_id}/"
        "manifest.json"
    )


def test_reads_known_existing_complete_manifest() -> None:
    """Return exact persisted evidence from one exact-key GET."""
    window = _window()

    client = FakeS3Client(
        response=_valid_response(
            window=window,
        )
    )

    telemetry = FakeTelemetry()

    persisted = _reader(
        client=client,
        telemetry=telemetry,
    ).load_existing(
        window=window,
        object_key=_manifest_key(
            window=window,
        ),
    )

    assert persisted.manifest.update_id == window.update_id
    assert persisted.version_id == "manifest-version"
    assert persisted.etag == '"manifest-etag"'
    assert persisted.size_bytes == len(
        persisted.payload
    )
    assert persisted.sha256 == hashlib.sha256(
        persisted.payload
    ).hexdigest()

    assert client.request == {
        "Bucket": "opslens-test-data",
        "Key": _manifest_key(
            window=window,
        ),
    }

    assert "NvdIncrementalCompleteManifestRead" in {
        name
        for name, _, _ in telemetry.metrics
    }


@pytest.mark.parametrize(
    ("status_code", "error_code"),
    [
        (
            403,
            "AccessDenied",
        ),
        (
            404,
            "NoSuchKey",
        ),
        (
            500,
            "InternalError",
        ),
    ],
)
def test_any_get_failure_fails_closed(
    status_code: int,
    error_code: str,
) -> None:
    """Never interpret GetObject failures as COMPLETE absence."""
    window = _window()

    telemetry = FakeTelemetry()

    reader = _reader(
        client=FakeS3Client(
            error=_client_error(
                status_code=status_code,
                error_code=error_code,
            )
        ),
        telemetry=telemetry,
    )

    with pytest.raises(
        NvdIncrementalCompleteManifestReadError,
    ):
        reader.load_existing(
            window=window,
            object_key=_manifest_key(
                window=window,
            ),
        )

    assert "NvdIncrementalCompleteManifestReadFailure" in {
        name
        for name, _, _ in telemetry.metrics
    }


def test_rejects_wrong_manifest_sha_metadata() -> None:
    """Fail closed when metadata does not bind the exact payload bytes."""
    window = _window()

    response = _valid_response(
        window=window,
    )

    metadata_value = response["Metadata"]

    assert isinstance(
        metadata_value,
        dict,
    )

    metadata = cast(
        dict[str, str],
        metadata_value,
    )

    metadata["object_sha256"] = "0" * 64

    reader = _reader(
        client=FakeS3Client(
            response=response,
        )
    )

    with pytest.raises(
        NvdIncrementalCompleteManifestEvidenceError,
        match="object_sha256",
    ):
        reader.load_existing(
            window=window,
            object_key=_manifest_key(
                window=window,
            ),
        )


def test_rejects_wrong_content_length() -> None:
    """Fail closed when ContentLength differs from exact response bytes."""
    window = _window()

    response = _valid_response(
        window=window,
    )

    content_length = response["ContentLength"]

    assert type(content_length) is int

    response["ContentLength"] = (
        content_length + 1
    )

    reader = _reader(
        client=FakeS3Client(
            response=response,
        )
    )

    with pytest.raises(
        NvdIncrementalCompleteManifestEvidenceError,
        match="ContentLength",
    ):
        reader.load_existing(
            window=window,
            object_key=_manifest_key(
                window=window,
            ),
        )


def test_rejects_wrong_content_type() -> None:
    """Fail closed when persisted COMPLETE content type is wrong."""
    window = _window()

    response = _valid_response(
        window=window,
    )

    response["ContentType"] = "text/plain"

    reader = _reader(
        client=FakeS3Client(
            response=response,
        )
    )

    with pytest.raises(
        NvdIncrementalCompleteManifestEvidenceError,
        match="ContentType",
    ):
        reader.load_existing(
            window=window,
            object_key=_manifest_key(
                window=window,
            ),
        )


def test_rejects_missing_version_id() -> None:
    """Require exact S3 VersionId for persisted COMPLETE evidence."""
    window = _window()

    response = _valid_response(
        window=window,
    )

    response.pop(
        "VersionId"
    )

    reader = _reader(
        client=FakeS3Client(
            response=response,
        )
    )

    with pytest.raises(
        NvdIncrementalCompleteManifestEvidenceError,
        match="VersionId",
    ):
        reader.load_existing(
            window=window,
            object_key=_manifest_key(
                window=window,
            ),
        )


def test_rejects_complete_for_different_logical_window() -> None:
    """Reject COMPLETE evidence belonging to another logical window."""
    requested_window = _window()

    other_window = NvdIncrementalWindow(
        start_at=requested_window.start_at,
        end_at=datetime(
            2026,
            8,
            18,
            7,
            11,
            12,
            tzinfo=UTC,
        ),
    )

    reader = _reader(
        client=FakeS3Client(
            response=_valid_response(
                window=other_window,
            )
        )
    )

    with pytest.raises(
        NvdIncrementalCompleteManifestEvidenceError,
        match="update_id",
    ):
        reader.load_existing(
            window=requested_window,
            object_key=_manifest_key(
                window=requested_window,
            ),
        )


def test_rejects_non_exact_metadata_inventory() -> None:
    """Reject extra S3 metadata outside the COMPLETE evidence contract."""
    window = _window()

    response = _valid_response(
        window=window,
    )

    metadata_value = response["Metadata"]

    assert isinstance(
        metadata_value,
        dict,
    )

    metadata = cast(
        dict[str, str],
        metadata_value,
    )

    metadata["unexpected"] = "value"

    reader = _reader(
        client=FakeS3Client(
            response=response,
        )
    )

    with pytest.raises(
        NvdIncrementalCompleteManifestEvidenceError,
        match="metadata fields are not exact",
    ):
        reader.load_existing(
            window=window,
            object_key=_manifest_key(
                window=window,
            ),
        )


def test_rejects_manifest_exceeding_size_limit() -> None:
    """Reject payloads larger than the bounded COMPLETE manifest limit."""
    window = _window()

    oversized_payload = (
        b"x"
        * (
            S3NvdIncrementalCompleteManifestReader.MAX_PAYLOAD_BYTES
            + 1
        )
    )

    response: dict[str, object] = {
        "Body": FakeBody(
            oversized_payload
        ),
        "VersionId": "manifest-version",
        "ETag": '"manifest-etag"',
        "ContentLength": len(
            oversized_payload
        ),
        "ContentType": "application/json",
        "Metadata": {},
    }

    reader = _reader(
        client=FakeS3Client(
            response=response,
        )
    )

    with pytest.raises(
        NvdIncrementalCompleteManifestEvidenceError,
        match="exceeds maximum size",
    ):
        reader.load_existing(
            window=window,
            object_key=_manifest_key(
                window=window,
            ),
        )
