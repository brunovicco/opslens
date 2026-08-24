"""Unit tests for NVD incremental COMPLETE manifest persistence."""

import hashlib
import json
from collections.abc import Mapping
from contextlib import (
    AbstractContextManager,
    nullcontext,
)
from datetime import UTC, datetime

from botocore.exceptions import ClientError

from opslens.ingestion.nvd.adapters.outbound.s3_incremental_bronze import (
    S3NvdIncrementalBronzeRepository,
)
from opslens.ingestion.nvd.application.incremental_key_factory import (
    NvdIncrementalKeyFactory,
)
from opslens.ingestion.nvd.application.incremental_manifest import (
    NvdIncrementalManifest,
    NvdIncrementalManifestFactory,
    NvdIncrementalManifestSerializer,
)
from opslens.ingestion.nvd.application.models import (
    NvdBronzeWriteResult,
    NvdBronzeWriteStatus,
)
from opslens.ingestion.nvd.domain.api_page import (
    NvdCveApiPageParser,
    NvdCveApiPagination,
)
from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)


class FakeTelemetry:
    """Capture manifest persistence telemetry."""

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Accept informational telemetry."""

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Accept exception telemetry."""

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Accept metric telemetry."""

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Return one no-op tracing context."""
        return nullcontext()


class FakeS3Client:
    """Provide deterministic S3 manifest behavior."""

    def __init__(
        self,
        *,
        put_response: Mapping[str, object] | None = None,
        put_error: ClientError | None = None,
        head_response: Mapping[str, object] | None = None,
    ) -> None:
        """Initialize deterministic responses."""
        self.put_response: Mapping[str, object] = (
            put_response if put_response is not None else dict[str, object]()
        )
        self.put_error = put_error
        self.head_response: Mapping[str, object] = (
            head_response if head_response is not None else dict[str, object]()
        )
        self.put_request: dict[str, object] | None = None

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
        """Capture one conditional manifest write."""
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
        """Return existing manifest evidence."""
        return self.head_response

def _window() -> NvdIncrementalWindow:
    """Build one deterministic update window."""
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


def _manifest() -> tuple[
    NvdIncrementalManifest,
    bytes,
    str,
]:
    """Build one complete deterministic manifest."""
    document: dict[str, object] = {
        "resultsPerPage": 1,
        "startIndex": 0,
        "totalResults": 1,
        "format": "NVD_CVE",
        "version": "2.0",
        "timestamp": "2026-08-18T20:00:01.000",
        "vulnerabilities": [
            {
                "cve": {
                    "id": "CVE-2026-1000",
                }
            }
        ],
    }

    page = NvdCveApiPageParser().parse(
        json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    )

    pagination = NvdCveApiPagination(pages=(page,))

    window = _window()
    key_factory = NvdIncrementalKeyFactory()

    manifest = NvdIncrementalManifestFactory().build(
        window=window,
        pagination=pagination,
        page_keys=(
            key_factory.build_attempt_page_key(
                window=window,
                attempt_id="a" * 64,
                start_index=page.start_index,
            ),
        ),
        page_writes=(
            NvdBronzeWriteResult(
                status=NvdBronzeWriteStatus.CREATED,
                version_id="page-version-123",
            ),
        ),
    )

    payload = NvdIncrementalManifestSerializer().serialize(manifest)

    key = key_factory.build_manifest_key(window=window)

    return manifest, payload, key


def _expected_metadata(
    manifest: NvdIncrementalManifest,
    payload: bytes,
) -> dict[str, str]:
    """Build exact expected manifest metadata."""
    return {
        "source": "nvd-cve",
        "source_interface": "cve-api-2.0",
        "artifact_kind": "manifest",
        "update_id": manifest.update_id,
        "window_start_at": (manifest.canonical_window_start_at),
        "window_end_at": (manifest.canonical_window_end_at),
        "total_results": str(manifest.total_results),
        "page_count": str(manifest.page_count),
        "manifest_version": "1",
        "completion_status": "complete",
        "object_sha256": hashlib.sha256(payload).hexdigest(),
    }


def test_create_manifest_uses_conditional_exact_write() -> None:
    """Persist canonical COMPLETE bytes conditionally."""
    manifest, payload, key = _manifest()

    client = FakeS3Client(
        put_response={
            "VersionId": "manifest-version-123",
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
        object_key=key,
    )

    assert result.status is NvdBronzeWriteStatus.CREATED
    assert result.version_id == "manifest-version-123"

    assert client.put_request is not None
    assert client.put_request["Body"] == payload
    assert client.put_request["IfNoneMatch"] == "*"
    assert client.put_request["ContentType"] == "application/json"
    assert client.put_request["Metadata"] == _expected_metadata(
        manifest,
        payload,
    )
