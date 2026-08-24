"""Unit tests for canonical NVD incremental manifest collision semantics."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime

import pytest
from botocore.exceptions import ClientError

from opslens.ingestion.nvd.adapters.outbound.s3_incremental_bronze import (
    S3NvdIncrementalBronzeRepository,
)
from opslens.ingestion.nvd.application.incremental_complete import (
    NvdIncrementalCanonicalManifestAlreadyExistsError,
)
from opslens.ingestion.nvd.application.incremental_manifest import (
    NvdIncrementalManifest,
    NvdIncrementalManifestSerializer,
    NvdIncrementalStoredPage,
)
from opslens.ingestion.nvd.application.models import (
    NvdBronzeWriteStatus,
)
from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)


class FakeTelemetry:
    """Capture telemetry emitted during manifest persistence."""

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
        self.info_events.append(
            message
        )

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture one exception event."""
        self.exception_events.append(
            message
        )

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Capture one metric."""
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
        self.spans.append(
            name
        )
        return nullcontext()


class FakeS3Client:
    """Provide deterministic PutObject behavior."""

    def __init__(
        self,
        *,
        put_response: Mapping[str, object] | None = None,
        put_error: ClientError | None = None,
    ) -> None:
        """Initialize fake S3 behavior."""
        self.put_response: Mapping[str, object] = (
            put_response
            if put_response is not None
            else dict[str, object]()
        )
        self.put_error = put_error
        self.put_request: dict[str, object] | None = None
        self.head_calls = 0

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
        """Fail if manifest collision attempts legacy HeadObject resolution."""
        self.head_calls += 1

        raise AssertionError(
            "Canonical manifest collision must not use HeadObject."
        )


def _client_error(
    *,
    status_code: int,
    error_code: str,
) -> ClientError:
    """Build one deterministic Botocore error."""
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


def _window() -> NvdIncrementalWindow:
    """Build one deterministic logical update window."""
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


def _manifest() -> NvdIncrementalManifest:
    """Build one canonical zero-result COMPLETE manifest."""
    window = _window()

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
                    f"attempt_id={'a' * 64}/"
                    "page_start=000000/"
                    "response.json"
                ),
                version_id="page-version",
                size_bytes=146,
                sha256="b" * 64,
                start_index=0,
                results_per_page=0,
                total_results=0,
                source_timestamp="2026-08-24T19:51:57.077",
            ),
        ),
    )


def _manifest_key() -> str:
    """Build the canonical logical-window COMPLETE key."""
    window = _window()

    return (
        "bronze/nvd/cve/updates/"
        f"update_id={window.update_id}/"
        "manifest.json"
    )


def test_create_manifest_creates_canonical_complete() -> None:
    """Create canonical COMPLETE using one conditional PutObject."""
    manifest = _manifest()
    payload = NvdIncrementalManifestSerializer().serialize(
        manifest
    )

    client = FakeS3Client(
        put_response={
            "VersionId": "manifest-version",
            "ETag": '"manifest-etag"',
        }
    )

    result = S3NvdIncrementalBronzeRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=FakeTelemetry(),
    ).create_manifest(
        manifest=manifest,
        payload=payload,
        object_key=_manifest_key(),
    )

    assert result.status is NvdBronzeWriteStatus.CREATED
    assert result.version_id == "manifest-version"
    assert result.etag == '"manifest-etag"'

    assert client.put_request is not None
    assert client.put_request["IfNoneMatch"] == "*"
    assert client.put_request["Body"] == payload
    assert client.head_calls == 0


def test_manifest_412_reports_canonical_winner_without_head() -> None:
    """Delegate canonical winner resolution to the application service."""
    manifest = _manifest()
    payload = NvdIncrementalManifestSerializer().serialize(
        manifest
    )

    client = FakeS3Client(
        put_error=_client_error(
            status_code=412,
            error_code="PreconditionFailed",
        )
    )

    telemetry = FakeTelemetry()

    repository = S3NvdIncrementalBronzeRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    with pytest.raises(
        NvdIncrementalCanonicalManifestAlreadyExistsError,
        match="already exists",
    ):
        repository.create_manifest(
            manifest=manifest,
            payload=payload,
            object_key=_manifest_key(),
        )

    assert client.head_calls == 0

    assert (
        "NvdIncrementalCanonicalManifestAlreadyExists"
        in {
            name
            for name, _, _ in telemetry.metrics
        }
    )


def test_non_412_manifest_write_failure_is_propagated() -> None:
    """Preserve real S3 failures instead of treating them as races."""
    manifest = _manifest()
    payload = NvdIncrementalManifestSerializer().serialize(
        manifest
    )

    client = FakeS3Client(
        put_error=_client_error(
            status_code=500,
            error_code="InternalError",
        )
    )

    with pytest.raises(
        ClientError,
    ):
        S3NvdIncrementalBronzeRepository(
            client=client,
            bucket_name="opslens-test-data",
            telemetry=FakeTelemetry(),
        ).create_manifest(
            manifest=manifest,
            payload=payload,
            object_key=_manifest_key(),
        )

    assert client.head_calls == 0
