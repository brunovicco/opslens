"""Unit tests for immutable NVD incremental Bronze S3 pages."""

import json
from collections.abc import Mapping
from contextlib import (
    AbstractContextManager,
    nullcontext,
)
from datetime import UTC, datetime
from typing import cast

import pytest
from botocore.exceptions import ClientError

from opslens.ingestion.nvd.adapters.outbound.s3_incremental_bronze import (
    NvdIncrementalBronzeEvidenceError,
    S3NvdIncrementalBronzeRepository,
)
from opslens.ingestion.nvd.application.incremental_key_factory import (
    NvdIncrementalKeyFactory,
)
from opslens.ingestion.nvd.application.models import (
    NvdBronzeWriteStatus,
)
from opslens.ingestion.nvd.domain.api_page import (
    NvdCveApiPage,
    NvdCveApiPageParser,
)
from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)


class FakeTelemetry:
    """Capture operational telemetry from the S3 adapter."""

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


class FakeS3Client:
    """Capture deterministic S3 PutObject and HeadObject calls."""

    def __init__(
        self,
        *,
        put_response: Mapping[str, object] | None = None,
        put_error: ClientError | None = None,
        head_response: Mapping[str, object] | None = None,
    ) -> None:
        """Initialize deterministic S3 behavior."""
        self.put_response: Mapping[str, object] = (
            put_response if put_response is not None else dict[str, object]()
        )
        self.put_error = put_error
        self.head_response: Mapping[str, object] = (
            head_response if head_response is not None else dict[str, object]()
        )
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


def _window() -> NvdIncrementalWindow:
    """Build one deterministic incremental window."""
    return NvdIncrementalWindow(
        start_at=datetime(
            2026,
            8,
            18,
            18,
            0,
            tzinfo=UTC,
        ),
        end_at=datetime(
            2026,
            8,
            18,
            20,
            0,
            tzinfo=UTC,
        ),
    )


def _page() -> NvdCveApiPage:
    """Build one validated deterministic API page."""
    document: dict[str, object] = {
        "resultsPerPage": 2,
        "startIndex": 0,
        "totalResults": 2,
        "format": "NVD_CVE",
        "version": "2.0",
        "timestamp": "2026-08-18T20:00:00.000",
        "vulnerabilities": [
            {
                "cve": {
                    "id": "CVE-2026-1000",
                }
            },
            {
                "cve": {
                    "id": "CVE-2026-1001",
                }
            },
        ],
    }

    payload = json.dumps(
        document,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()

    return NvdCveApiPageParser().parse(payload)


def _expected_metadata(
    *,
    page: NvdCveApiPage,
    window: NvdIncrementalWindow,
) -> dict[str, str]:
    """Build the expected persisted provenance contract."""
    return {
        "source": "nvd-cve",
        "source_interface": "cve-api-2.0",
        "artifact_kind": "page",
        "update_id": window.update_id,
        "window_start_at": window.canonical_start_at,
        "window_end_at": window.canonical_end_at,
        "page_start": str(page.start_index),
        "results_per_page": str(page.results_per_page),
        "total_results": str(page.total_results),
        "source_format": page.source_format,
        "source_version": page.source_version,
        "source_timestamp": page.source_timestamp,
        "object_sha256": page.sha256,
    }


def test_create_page_uses_conditional_write_and_exact_bytes() -> None:
    """Persist exact API bytes using If-None-Match."""
    page = _page()
    window = _window()
    object_key = NvdIncrementalKeyFactory().build_page_key(
        window=window,
        start_index=page.start_index,
    )
    client = FakeS3Client(
        put_response={
            "VersionId": "page-version-123",
            "ETag": '"page-etag"',
        }
    )
    telemetry = FakeTelemetry()

    repository = S3NvdIncrementalBronzeRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=telemetry,
    )

    result = repository.create_page(
        page=page,
        window=window,
        object_key=object_key,
    )

    assert result.status is NvdBronzeWriteStatus.CREATED
    assert result.version_id == "page-version-123"

    assert client.put_request is not None
    assert client.put_request["Body"] == page.raw_bytes
    assert client.put_request["IfNoneMatch"] == "*"
    assert client.put_request["ContentType"] == "application/json"

    metadata = cast(
        Mapping[str, str],
        client.put_request["Metadata"],
    )

    assert metadata == _expected_metadata(
        page=page,
        window=window,
    )


def test_replay_verifies_existing_exact_evidence() -> None:
    """Treat 412 as idempotent only after full evidence verification."""
    page = _page()
    window = _window()
    object_key = NvdIncrementalKeyFactory().build_page_key(
        window=window,
        start_index=page.start_index,
    )

    client = FakeS3Client(
        put_error=_client_error(
            status_code=412,
            error_code="PreconditionFailed",
        ),
        head_response={
            "VersionId": "existing-version-123",
            "ETag": '"existing-etag"',
            "ContentLength": len(page.raw_bytes),
            "ContentType": "application/json",
            "Metadata": _expected_metadata(
                page=page,
                window=window,
            ),
        },
    )

    result = S3NvdIncrementalBronzeRepository(
        client=client,
        bucket_name="opslens-test-data",
        telemetry=FakeTelemetry(),
    ).create_page(
        page=page,
        window=window,
        object_key=object_key,
    )

    assert result.status is NvdBronzeWriteStatus.ALREADY_EXISTS
    assert result.version_id == "existing-version-123"
    assert client.head_request == {
        "Bucket": "opslens-test-data",
        "Key": object_key,
    }


def test_replay_rejects_different_object_sha() -> None:
    """Fail closed when the existing object hash differs."""
    page = _page()
    window = _window()
    metadata = _expected_metadata(
        page=page,
        window=window,
    )
    metadata["object_sha256"] = "0" * 64

    client = FakeS3Client(
        put_error=_client_error(
            status_code=412,
            error_code="PreconditionFailed",
        ),
        head_response={
            "VersionId": "existing-version-123",
            "ContentLength": len(page.raw_bytes),
            "ContentType": "application/json",
            "Metadata": metadata,
        },
    )

    with pytest.raises(
        NvdIncrementalBronzeEvidenceError,
        match="object_sha256",
    ):
        S3NvdIncrementalBronzeRepository(
            client=client,
            bucket_name="opslens-test-data",
            telemetry=FakeTelemetry(),
        ).create_page(
            page=page,
            window=window,
            object_key=(
                NvdIncrementalKeyFactory().build_page_key(
                    window=window,
                    start_index=0,
                )
            ),
        )


def test_replay_rejects_different_window_metadata() -> None:
    """Fail closed when existing evidence belongs to another window."""
    page = _page()
    window = _window()
    metadata = _expected_metadata(
        page=page,
        window=window,
    )
    metadata["window_end_at"] = "2026-08-18T21:00:00Z"

    client = FakeS3Client(
        put_error=_client_error(
            status_code=412,
            error_code="PreconditionFailed",
        ),
        head_response={
            "VersionId": "existing-version-123",
            "ContentLength": len(page.raw_bytes),
            "ContentType": "application/json",
            "Metadata": metadata,
        },
    )

    with pytest.raises(
        NvdIncrementalBronzeEvidenceError,
        match="window_end_at",
    ):
        S3NvdIncrementalBronzeRepository(
            client=client,
            bucket_name="opslens-test-data",
            telemetry=FakeTelemetry(),
        ).create_page(
            page=page,
            window=window,
            object_key=(
                NvdIncrementalKeyFactory().build_page_key(
                    window=window,
                    start_index=0,
                )
            ),
        )


def test_replay_rejects_different_content_length() -> None:
    """Fail closed when existing byte size differs."""
    page = _page()
    window = _window()

    client = FakeS3Client(
        put_error=_client_error(
            status_code=412,
            error_code="PreconditionFailed",
        ),
        head_response={
            "VersionId": "existing-version-123",
            "ContentLength": (len(page.raw_bytes) + 1),
            "ContentType": "application/json",
            "Metadata": _expected_metadata(
                page=page,
                window=window,
            ),
        },
    )

    with pytest.raises(
        NvdIncrementalBronzeEvidenceError,
        match="size",
    ):
        S3NvdIncrementalBronzeRepository(
            client=client,
            bucket_name="opslens-test-data",
            telemetry=FakeTelemetry(),
        ).create_page(
            page=page,
            window=window,
            object_key=(
                NvdIncrementalKeyFactory().build_page_key(
                    window=window,
                    start_index=0,
                )
            ),
        )


def test_create_requires_s3_version_id() -> None:
    """Require exact S3 object-version evidence after creation."""
    page = _page()
    window = _window()

    with pytest.raises(
        NvdIncrementalBronzeEvidenceError,
        match="VersionId",
    ):
        S3NvdIncrementalBronzeRepository(
            client=FakeS3Client(put_response={}),
            bucket_name="opslens-test-data",
            telemetry=FakeTelemetry(),
        ).create_page(
            page=page,
            window=window,
            object_key=(
                NvdIncrementalKeyFactory().build_page_key(
                    window=window,
                    start_index=0,
                )
            ),
        )


def test_non_precondition_s3_error_propagates() -> None:
    """Propagate non-idempotency S3 failures."""
    page = _page()
    window = _window()

    with pytest.raises(ClientError):
        S3NvdIncrementalBronzeRepository(
            client=FakeS3Client(
                put_error=_client_error(
                    status_code=503,
                    error_code="SlowDown",
                )
            ),
            bucket_name="opslens-test-data",
            telemetry=FakeTelemetry(),
        ).create_page(
            page=page,
            window=window,
            object_key=(
                NvdIncrementalKeyFactory().build_page_key(
                    window=window,
                    start_index=0,
                )
            ),
        )


def test_create_page_rejects_empty_object_key() -> None:
    """Reject persistence without a deterministic object key."""
    with pytest.raises(
        ValueError,
        match="object key cannot be empty",
    ):
        S3NvdIncrementalBronzeRepository(
            client=FakeS3Client(),
            bucket_name="opslens-test-data",
            telemetry=FakeTelemetry(),
        ).create_page(
            page=_page(),
            window=_window(),
            object_key="",
        )
