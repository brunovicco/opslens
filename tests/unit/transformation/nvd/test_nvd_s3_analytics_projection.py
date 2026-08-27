"""Tests for exact-version S3 NVD analytics projection."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime
from hashlib import sha256

import pytest
from botocore.exceptions import ClientError

from opslens.transformation.nvd.adapters.outbound.s3_analytics_projection import (
    NvdAnalyticsProjectionAlreadyExistsError,
    NvdAnalyticsProjectionConcurrentWriteError,
    NvdAnalyticsProjectionEvidenceMismatchError,
    S3NvdAnalyticsProjectionRepositoryV1,
)
from opslens.transformation.nvd.application.analytics_projection_key_factory import (
    NvdAnalyticsProjectionKeyFactoryV1,
)
from opslens.transformation.nvd.application.analytics_projection_models import (
    NvdAnalyticsExactObjectRefV1,
    NvdIncrementalAnalyticsProjectionRequestV1,
)

BUCKET = "opslens-test-data"
UPDATE_ID = "a" * 64
LOGICAL_SHA = "b" * 64
MANIFEST_SHA = "c" * 64
PARQUET_BYTES = b"PAR1exact-projected-nvd-parquetPAR1"
PARQUET_SHA = sha256(PARQUET_BYTES).hexdigest()
SOURCE_VERSION = "silver-parquet-version"
DESTINATION_VERSION = "analytics-version"
BASE = (
    "silver/nvd/cve/schema_version=1/"
    "source_kind=incremental/"
    f"update_id={UPDATE_ID}"
)


class FakeTelemetry:
    """Capture operational telemetry emitted by the S3 projection adapter."""

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
        """Capture one metric."""
        self.metrics.append((name, value, unit))

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Capture one tracing span."""
        self.spans.append(name)
        return nullcontext()


class FakeBody:
    """Expose deterministic bounded response-body reads."""

    def __init__(self, payload: bytes) -> None:
        """Initialize exact response bytes."""
        self.payload = payload
        self.read_amounts: list[int | None] = []
        self.closed = False

    def read(self, amt: int | None = None) -> bytes:
        """Return up to the requested number of bytes."""
        self.read_amounts.append(amt)
        return self.payload if amt is None else self.payload[:amt]

    def close(self) -> None:
        """Capture stream closure."""
        self.closed = True


class FakeS3Client:
    """Provide deterministic CopyObject, HeadObject, and GetObject behavior."""

    def __init__(
        self,
        *,
        copy_response: Mapping[str, object] | None = None,
        head_response: Mapping[str, object] | None = None,
        get_response: Mapping[str, object] | None = None,
        copy_error: ClientError | None = None,
    ) -> None:
        """Initialize fake S3 responses."""
        self.copy_response: Mapping[str, object] = (
            copy_response if copy_response is not None else {}
        )
        self.head_response: Mapping[str, object] = (
            head_response if head_response is not None else {}
        )
        self.get_response: Mapping[str, object] = (
            get_response if get_response is not None else {}
        )
        self.copy_error = copy_error
        self.copy_requests: list[dict[str, object]] = []
        self.head_requests: list[dict[str, str]] = []
        self.get_requests: list[dict[str, str]] = []

    def copy_object(
        self,
        *,
        Bucket: str,
        Key: str,
        CopySource: Mapping[str, str],
        IfNoneMatch: str,
        MetadataDirective: str,
        ContentType: str,
        Metadata: Mapping[str, str],
    ) -> Mapping[str, object]:
        """Capture one conditional exact-version CopyObject request."""
        self.copy_requests.append(
            {
                "Bucket": Bucket,
                "Key": Key,
                "CopySource": dict(CopySource),
                "IfNoneMatch": IfNoneMatch,
                "MetadataDirective": MetadataDirective,
                "ContentType": ContentType,
                "Metadata": dict(Metadata),
            }
        )
        if self.copy_error is not None:
            raise self.copy_error
        return self.copy_response

    def head_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> Mapping[str, object]:
        """Capture one current-object HeadObject request."""
        self.head_requests.append(
            {
                "Bucket": Bucket,
                "Key": Key,
            }
        )
        return self.head_response

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> Mapping[str, object]:
        """Capture one exact destination GetObject request."""
        self.get_requests.append(
            {
                "Bucket": Bucket,
                "Key": Key,
                "VersionId": VersionId,
            }
        )
        return self.get_response


def _request(
    *,
    size_bytes: int = len(PARQUET_BYTES),
) -> NvdIncrementalAnalyticsProjectionRequestV1:
    """Build one exact incremental projection request."""
    return NvdIncrementalAnalyticsProjectionRequestV1(
        update_id=UPDATE_ID,
        committed_through_at=datetime(
            2026,
            8,
            25,
            23,
            25,
            tzinfo=UTC,
        ),
        silver_manifest=NvdAnalyticsExactObjectRefV1(
            key=f"{BASE}/manifest.json",
            version_id="silver-manifest-version",
            sha256=MANIFEST_SHA,
            size_bytes=2048,
        ),
        silver_parquet=NvdAnalyticsExactObjectRefV1(
            key=f"{BASE}/part-00000.parquet",
            version_id=SOURCE_VERSION,
            sha256=PARQUET_SHA,
            size_bytes=size_bytes,
        ),
        row_count=6749,
        logical_record_set_sha256=LOGICAL_SHA,
    )


def _metadata(
    request: NvdIncrementalAnalyticsProjectionRequestV1,
) -> dict[str, str]:
    """Build the expected permanent lineage metadata fixture."""
    source = request.silver_parquet
    return {
        "dataset": "nvd_cve_versions",
        "schema_version": "1",
        "source_kind": "incremental",
        "source_batch_id": UPDATE_ID,
        "row_count": "6749",
        "parquet_sha256": source.sha256,
        "authority_source_key": source.key,
        "authority_source_version_id": source.version_id,
        "authority_source_sha256": source.sha256,
        "authority_state": "watermark_committed",
    }


def _get_response(
    body: FakeBody,
    request: NvdIncrementalAnalyticsProjectionRequestV1,
    *,
    metadata: Mapping[str, str] | None = None,
) -> Mapping[str, object]:
    """Build one exact projected-object GetObject response."""
    return {
        "Body": body,
        "VersionId": DESTINATION_VERSION,
        "ContentLength": len(PARQUET_BYTES),
        "ContentType": "application/vnd.apache.parquet",
        "Metadata": (
            dict(metadata)
            if metadata is not None
            else _metadata(request)
        ),
    }


def _client_error(status_code: int) -> ClientError:
    """Build one deterministic Botocore CopyObject error."""
    return ClientError(
        error_response={
            "Error": {
                "Code": "PreconditionFailed",
                "Message": "test copy error",
            },
            "ResponseMetadata": {
                "RequestId": "test-request-id",
                "HostId": "test-host-id",
                "HTTPStatusCode": status_code,
                "HTTPHeaders": {},
                "RetryAttempts": 0,
            },
        },
        operation_name="CopyObject",
    )


def test_copy_if_absent_uses_structured_exact_source_and_verifies_bytes() -> None:
    """Require structured CopySource VersionId and exact destination evidence."""
    request = _request()
    destination = NvdAnalyticsProjectionKeyFactoryV1().build(
        request
    )
    body = FakeBody(PARQUET_BYTES)
    telemetry = FakeTelemetry()
    client = FakeS3Client(
        copy_response={
            "CopySourceVersionId": SOURCE_VERSION,
            "VersionId": DESTINATION_VERSION,
        },
        get_response=_get_response(body, request),
    )

    projected = S3NvdAnalyticsProjectionRepositoryV1(
        client=client,
        bucket_name=BUCKET,
        telemetry=telemetry,
    ).copy_if_absent(
        request=request,
        destination=destination,
    )

    assert projected.key == destination.object_key
    assert projected.version_id == DESTINATION_VERSION
    assert projected.sha256 == PARQUET_SHA
    assert projected.size_bytes == len(PARQUET_BYTES)
    assert client.copy_requests == [
        {
            "Bucket": BUCKET,
            "Key": destination.object_key,
            "CopySource": {
                "Bucket": BUCKET,
                "Key": request.silver_parquet.key,
                "VersionId": SOURCE_VERSION,
            },
            "IfNoneMatch": "*",
            "MetadataDirective": "REPLACE",
            "ContentType": "application/vnd.apache.parquet",
            "Metadata": _metadata(request),
        }
    ]
    assert client.get_requests == [
        {
            "Bucket": BUCKET,
            "Key": destination.object_key,
            "VersionId": DESTINATION_VERSION,
        }
    ]
    assert body.read_amounts == [len(PARQUET_BYTES) + 1]
    assert body.closed is True
    assert (
        "NvdAnalyticsProjectionBytes",
        float(len(PARQUET_BYTES)),
        "Bytes",
    ) in telemetry.metrics


def test_copy_if_absent_rejects_copy_source_version_mismatch() -> None:
    """Fail closed when CopyObject does not prove the requested source version."""
    request = _request()
    destination = NvdAnalyticsProjectionKeyFactoryV1().build(
        request
    )
    client = FakeS3Client(
        copy_response={
            "CopySourceVersionId": "different-source-version",
            "VersionId": DESTINATION_VERSION,
        }
    )

    with pytest.raises(
        NvdAnalyticsProjectionEvidenceMismatchError,
        match="CopySourceVersionId",
    ):
        S3NvdAnalyticsProjectionRepositoryV1(
            client=client,
            bucket_name=BUCKET,
            telemetry=FakeTelemetry(),
        ).copy_if_absent(
            request=request,
            destination=destination,
        )

    assert client.get_requests == []


def test_copy_if_absent_maps_412_to_replay_verification_required() -> None:
    """Never treat a 412 replay collision as success without exact verification."""
    request = _request()
    destination = NvdAnalyticsProjectionKeyFactoryV1().build(
        request
    )

    with pytest.raises(
        NvdAnalyticsProjectionAlreadyExistsError,
        match="requires exact replay verification",
    ):
        S3NvdAnalyticsProjectionRepositoryV1(
            client=FakeS3Client(
                copy_error=_client_error(412)
            ),
            bucket_name=BUCKET,
            telemetry=FakeTelemetry(),
        ).copy_if_absent(
            request=request,
            destination=destination,
        )


def test_copy_if_absent_maps_409_to_concurrent_conflict() -> None:
    """Keep concurrent conditional-copy conflict distinct from replay."""
    request = _request()
    destination = NvdAnalyticsProjectionKeyFactoryV1().build(
        request
    )

    with pytest.raises(
        NvdAnalyticsProjectionConcurrentWriteError,
        match="Concurrent",
    ):
        S3NvdAnalyticsProjectionRepositoryV1(
            client=FakeS3Client(
                copy_error=_client_error(409)
            ),
            bucket_name=BUCKET,
            telemetry=FakeTelemetry(),
        ).copy_if_absent(
            request=request,
            destination=destination,
        )


def test_verify_current_resolves_current_version_then_reads_exact_version() -> None:
    """Verify replay by pinning current destination to its exact VersionId."""
    request = _request()
    destination = NvdAnalyticsProjectionKeyFactoryV1().build(
        request
    )
    body = FakeBody(PARQUET_BYTES)
    client = FakeS3Client(
        head_response={
            "VersionId": DESTINATION_VERSION,
        },
        get_response=_get_response(body, request),
    )

    projected = S3NvdAnalyticsProjectionRepositoryV1(
        client=client,
        bucket_name=BUCKET,
        telemetry=FakeTelemetry(),
    ).verify_current(
        request=request,
        destination=destination,
    )

    assert projected.version_id == DESTINATION_VERSION
    assert client.head_requests == [
        {
            "Bucket": BUCKET,
            "Key": destination.object_key,
        }
    ]
    assert client.get_requests[0]["VersionId"] == DESTINATION_VERSION


def test_destination_hash_mismatch_fails_closed() -> None:
    """Reject a projected object whose exact bytes differ from Silver authority."""
    request = _request()
    destination = NvdAnalyticsProjectionKeyFactoryV1().build(
        request
    )
    wrong = b"PAR1different-projected-bytesPAR1"
    body = FakeBody(wrong)
    response: dict[str, object] = {
        "Body": body,
        "VersionId": DESTINATION_VERSION,
        "ContentLength": len(wrong),
        "ContentType": "application/vnd.apache.parquet",
        "Metadata": _metadata(request),
    }
    changed_request = NvdIncrementalAnalyticsProjectionRequestV1(
        update_id=request.update_id,
        committed_through_at=request.committed_through_at,
        silver_manifest=request.silver_manifest,
        silver_parquet=NvdAnalyticsExactObjectRefV1(
            key=request.silver_parquet.key,
            version_id=request.silver_parquet.version_id,
            sha256=request.silver_parquet.sha256,
            size_bytes=len(wrong),
        ),
        row_count=request.row_count,
        logical_record_set_sha256=request.logical_record_set_sha256,
    )
    changed_destination = NvdAnalyticsProjectionKeyFactoryV1().build(
        changed_request
    )

    with pytest.raises(
        NvdAnalyticsProjectionEvidenceMismatchError,
        match="SHA-256",
    ):
        S3NvdAnalyticsProjectionRepositoryV1(
            client=FakeS3Client(
                head_response={
                    "VersionId": DESTINATION_VERSION,
                },
                get_response=response,
            ),
            bucket_name=BUCKET,
            telemetry=FakeTelemetry(),
        ).verify_current(
            request=changed_request,
            destination=changed_destination,
        )

    assert destination.object_key == changed_destination.object_key
    assert body.closed is True


def test_destination_metadata_mismatch_fails_closed() -> None:
    """Reject replay when current lineage metadata differs from expected authority."""
    request = _request()
    destination = NvdAnalyticsProjectionKeyFactoryV1().build(
        request
    )
    body = FakeBody(PARQUET_BYTES)
    metadata = _metadata(request)
    metadata["authority_state"] = "wrong-state"

    with pytest.raises(
        NvdAnalyticsProjectionEvidenceMismatchError,
        match="lineage metadata",
    ):
        S3NvdAnalyticsProjectionRepositoryV1(
            client=FakeS3Client(
                head_response={
                    "VersionId": DESTINATION_VERSION,
                },
                get_response=_get_response(
                    body,
                    request,
                    metadata=metadata,
                ),
            ),
            bucket_name=BUCKET,
            telemetry=FakeTelemetry(),
        ).verify_current(
            request=request,
            destination=destination,
        )

    assert body.closed is True


def test_source_above_bound_is_rejected_before_s3() -> None:
    """Do not copy a source that cannot later be verified within the hard bound."""
    request = _request(size_bytes=1024)
    destination = NvdAnalyticsProjectionKeyFactoryV1().build(
        request
    )
    client = FakeS3Client()

    with pytest.raises(ValueError, match="exceeds verification byte bound"):
        S3NvdAnalyticsProjectionRepositoryV1(
            client=client,
            bucket_name=BUCKET,
            telemetry=FakeTelemetry(),
            max_parquet_bytes=512,
        ).copy_if_absent(
            request=request,
            destination=destination,
        )

    assert client.copy_requests == []
