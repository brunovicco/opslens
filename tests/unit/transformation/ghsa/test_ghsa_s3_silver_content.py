"""Tests for immutable GHSA Silver content persistence."""

import base64
from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext

import pytest
from botocore.exceptions import ClientError

from opslens.transformation.ghsa.adapters.outbound.s3_silver_content import (
    GhsaSilverContentConcurrentWriteError,
    GhsaSilverContentReplayMismatchError,
    GhsaSilverContentWriteEvidenceError,
    S3GetObjectResponse,
    S3GhsaSilverContentRepository,
    S3HeadObjectResponse,
    S3PutObjectResponse,
)
from opslens.transformation.ghsa.application.record_composer import (
    GhsaSilverRecordComposerV1,
)
from opslens.transformation.ghsa.completion.key_factory import (
    GhsaSilverKeyFactoryV1,
)
from opslens.transformation.ghsa.completion.preparation import (
    GhsaSilverPreparedContentObjectV1,
)
from opslens.transformation.ghsa.domain.collections_transformer import (
    GhsaAdvisoryCollectionsTransformer,
)
from opslens.transformation.ghsa.domain.transformer import (
    GhsaAdvisoryCoreTransformer,
)
from opslens.transformation.ghsa.domain.vulnerabilities_transformer import (
    GhsaVulnerabilitiesTransformer,
)
from opslens.transformation.ghsa.runtime.provenance import (
    GhsaBronzeAdvisoryOccurrenceV1,
)
from opslens.transformation.ghsa.runtime.record_processor import (
    GhsaSilverOccurrenceRecordV1,
)
from opslens.transformation.ghsa.serialization.parquet import (
    GhsaSilverParquetSerializerV1,
)

SYNC_ID = "1" * 64
ATTEMPT_ID = "2" * 64


class FakeBody:
    """In-memory S3 object body used by replay tests."""

    def __init__(self, payload: bytes) -> None:
        """Initialize body state."""
        self._payload = payload
        self.read_count = 0
        self.closed = False

    def read(self) -> bytes:
        """Return the configured payload."""
        self.read_count += 1
        return self._payload

    def close(self) -> None:
        """Record response-body release."""
        self.closed = True


class RecordingS3Client:
    """Record conditional writes and exact replay reads."""

    def __init__(
        self,
        *,
        put_response: S3PutObjectResponse | None = None,
        put_error: ClientError | None = None,
        head_response: S3HeadObjectResponse | None = None,
        get_response: S3GetObjectResponse | None = None,
    ) -> None:
        """Initialize configured S3 outcomes."""
        self._put_response = put_response
        self._put_error = put_error
        self._head_response = head_response
        self._get_response = get_response
        self.put_calls: list[dict[str, object]] = []
        self.head_calls: list[tuple[str, str]] = []
        self.get_calls: list[tuple[str, str, str]] = []

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: Mapping[str, str],
        ChecksumSHA256: str,
        IfNoneMatch: str,
    ) -> S3PutObjectResponse:
        """Record one create-only object write."""
        self.put_calls.append(
            {
                "Bucket": Bucket,
                "Key": Key,
                "Body": Body,
                "ContentType": ContentType,
                "Metadata": dict(Metadata),
                "ChecksumSHA256": ChecksumSHA256,
                "IfNoneMatch": IfNoneMatch,
            }
        )

        if self._put_error is not None:
            raise self._put_error

        return self._put_response if self._put_response is not None else {}

    def head_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> S3HeadObjectResponse:
        """Return configured current-version discovery evidence."""
        self.head_calls.append((Bucket, Key))
        return self._head_response if self._head_response is not None else {}

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> S3GetObjectResponse:
        """Return configured exact-version replay evidence."""
        self.get_calls.append((Bucket, Key, VersionId))
        return self._get_response if self._get_response is not None else {}


class RecordingTelemetry:
    """Record operational telemetry emitted by the repository."""

    def __init__(self) -> None:
        """Initialize telemetry collections."""
        self.info_events: list[tuple[str, Mapping[str, object] | None]] = []
        self.exception_events: list[
            tuple[str, Mapping[str, object] | None]
        ] = []
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


def _source_advisory() -> dict[str, object]:
    """Return one complete reviewed advisory accepted by Silver v1."""
    ghsa_id = "GHSA-2345-6789-cfgh"

    return {
        "ghsa_id": ghsa_id,
        "cve_id": "CVE-2026-12345",
        "url": f"https://api.github.com/advisories/{ghsa_id}",
        "html_url": f"https://github.com/advisories/{ghsa_id}",
        "repository_advisory_url": None,
        "summary": "Example advisory",
        "description": "Example advisory description.",
        "type": "reviewed",
        "severity": "high",
        "source_code_location": None,
        "published_at": "2026-08-20T10:00:00Z",
        "updated_at": "2026-08-21T11:00:00Z",
        "github_reviewed_at": "2026-08-21T12:00:00Z",
        "nvd_published_at": None,
        "withdrawn_at": None,
        "identifiers": [
            {"type": "GHSA", "value": ghsa_id},
            {"type": "CVE", "value": "CVE-2026-12345"},
        ],
        "references": [f"https://github.com/advisories/{ghsa_id}"],
        "cwes": [
            {
                "cwe_id": "CWE-79",
                "name": "Cross-site Scripting",
            },
        ],
        "cvss_severities": {
            "cvss_v3": {
                "vector_string": (
                    "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/"
                    "S:U/C:H/I:H/A:H"
                ),
                "score": 9.8,
            },
        },
        "vulnerabilities": [
            {
                "package": {
                    "ecosystem": "pip",
                    "name": "example-package",
                },
                "vulnerable_version_range": ">= 1.0.0, < 1.2.0",
                "first_patched_version": "1.2.0",
                "vulnerable_functions": ["unsafe_load"],
            },
        ],
    }


def _prepared() -> GhsaSilverPreparedContentObjectV1:
    """Build one deterministic authoritative content artifact."""
    source = _source_advisory()
    occurrence = GhsaBronzeAdvisoryOccurrenceV1.from_source(
        sync_id=SYNC_ID,
        attempt_id=ATTEMPT_ID,
        manifest_key="bronze/ghsa/advisories/manifest.json",
        manifest_version_id="manifest-version",
        page_ordinal=1,
        page_key="bronze/ghsa/advisories/page=000001/response.json",
        page_version_id="page-version",
        source_index=0,
        source_advisory=source,
    )
    composer = GhsaSilverRecordComposerV1(
        core_transformer=GhsaAdvisoryCoreTransformer(),
        collections_transformer=GhsaAdvisoryCollectionsTransformer(),
        vulnerabilities_transformer=GhsaVulnerabilitiesTransformer(),
    )
    record = composer.compose(source)
    binding = GhsaSilverOccurrenceRecordV1(
        occurrence=occurrence,
        record=record,
    )
    artifact = GhsaSilverParquetSerializerV1().serialize((record,))

    return GhsaSilverPreparedContentObjectV1(
        key=GhsaSilverKeyFactoryV1().build_content_object_key(
            occurrence.observed_version
        ),
        binding=binding,
        parquet_artifact=artifact,
    )


def _metadata(
    prepared: GhsaSilverPreparedContentObjectV1,
) -> dict[str, str]:
    """Build the exact informational S3 metadata contract."""
    return {
        "dataset": "ghsa_advisory_versions",
        "schema_version": "1",
        "ghsa_id": prepared.ghsa_id,
        "observed_advisory_version_id": (
            prepared.observed_advisory_version_id
        ),
        "source_advisory_sha256": prepared.source_advisory_sha256,
        "parquet_sha256": prepared.parquet_artifact.parquet_sha256,
        "row_count": "1",
    }


def _checksum(prepared: GhsaSilverPreparedContentObjectV1) -> str:
    """Return the S3 base64 SHA-256 representation for the artifact."""
    return base64.b64encode(
        bytes.fromhex(prepared.parquet_artifact.parquet_sha256)
    ).decode("ascii")


def _client_error(status_code: int) -> ClientError:
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


def test_creates_content_conditionally_with_exact_checksum_and_version() -> None:
    """Require create-only semantics plus S3 checksum and VersionId evidence."""
    prepared = _prepared()
    checksum = _checksum(prepared)
    client = RecordingS3Client(
        put_response={
            "VersionId": "silver-version-123",
            "ETag": '"etag"',
            "ChecksumSHA256": checksum,
        }
    )
    telemetry = RecordingTelemetry()
    repository = S3GhsaSilverContentRepository(
        client=client,
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    stored = repository.put_if_absent(prepared)

    assert stored.key == prepared.key
    assert stored.version_id == "silver-version-123"
    assert stored.row_count == 1
    assert stored.parquet_sha256 == prepared.parquet_artifact.parquet_sha256
    assert len(client.put_calls) == 1

    call = client.put_calls[0]
    assert call["Bucket"] == "opslens-data"
    assert call["Key"] == prepared.key
    assert call["Body"] == prepared.parquet_artifact.parquet_bytes
    assert call["IfNoneMatch"] == "*"
    assert call["ChecksumSHA256"] == checksum
    assert call["ContentType"] == "application/vnd.apache.parquet"
    assert call["Metadata"] == _metadata(prepared)
    assert client.head_calls == []
    assert client.get_calls == []
    assert (
        "GhsaSilverContentCreated",
        1.0,
        "Count",
    ) in telemetry.metrics


def test_rejects_successful_write_without_exact_version_id() -> None:
    """Do not accept a created object without exact persisted version evidence."""
    prepared = _prepared()
    repository = S3GhsaSilverContentRepository(
        client=RecordingS3Client(
            put_response={
                "ChecksumSHA256": _checksum(prepared),
            }
        ),
        bucket_name="opslens-data",
        telemetry=RecordingTelemetry(),
    )

    with pytest.raises(
        GhsaSilverContentWriteEvidenceError,
        match="VersionId",
    ):
        repository.put_if_absent(prepared)


def test_rejects_successful_write_without_exact_checksum_acknowledgement() -> None:
    """Require S3 to acknowledge the same SHA-256 supplied with PutObject."""
    prepared = _prepared()
    repository = S3GhsaSilverContentRepository(
        client=RecordingS3Client(
            put_response={
                "VersionId": "silver-version-123",
                "ChecksumSHA256": "wrong-checksum",
            }
        ),
        bucket_name="opslens-data",
        telemetry=RecordingTelemetry(),
    )

    with pytest.raises(
        GhsaSilverContentWriteEvidenceError,
        match="ChecksumSHA256",
    ):
        repository.put_if_absent(prepared)


def test_accepts_412_only_after_exact_versioned_replay_verification() -> None:
    """Treat an existing key as success only when exact bytes and metadata match."""
    prepared = _prepared()
    metadata = _metadata(prepared)
    body = FakeBody(prepared.parquet_artifact.parquet_bytes)
    client = RecordingS3Client(
        put_error=_client_error(412),
        head_response={
            "VersionId": "existing-version",
            "ContentLength": prepared.parquet_artifact.size_bytes,
            "Metadata": metadata,
        },
        get_response={
            "Body": body,
            "VersionId": "existing-version",
            "ContentLength": prepared.parquet_artifact.size_bytes,
            "Metadata": metadata,
        },
    )
    telemetry = RecordingTelemetry()
    repository = S3GhsaSilverContentRepository(
        client=client,
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    stored = repository.put_if_absent(prepared)

    assert stored.version_id == "existing-version"
    assert client.head_calls == [("opslens-data", prepared.key)]
    assert client.get_calls == [
        (
            "opslens-data",
            prepared.key,
            "existing-version",
        )
    ]
    assert body.read_count == 1
    assert body.closed is True
    assert (
        "GhsaSilverContentReplayVerified",
        1.0,
        "Count",
    ) in telemetry.metrics


def test_rejects_412_when_existing_version_bytes_do_not_match() -> None:
    """Fail closed when a content-addressed key contains different bytes."""
    prepared = _prepared()
    metadata = _metadata(prepared)
    body = FakeBody(b"PAR1different-contentPAR1")
    client = RecordingS3Client(
        put_error=_client_error(412),
        head_response={
            "VersionId": "existing-version",
            "ContentLength": prepared.parquet_artifact.size_bytes,
            "Metadata": metadata,
        },
        get_response={
            "Body": body,
            "VersionId": "existing-version",
            "ContentLength": prepared.parquet_artifact.size_bytes,
            "Metadata": metadata,
        },
    )
    telemetry = RecordingTelemetry()
    repository = S3GhsaSilverContentRepository(
        client=client,
        bucket_name="opslens-data",
        telemetry=telemetry,
    )

    with pytest.raises(
        GhsaSilverContentReplayMismatchError,
        match="bytes do not match",
    ):
        repository.put_if_absent(prepared)

    assert body.closed is True
    assert (
        "GhsaSilverContentReplayMismatch",
        1.0,
        "Count",
    ) in telemetry.metrics


def test_rejects_412_when_head_metadata_does_not_match() -> None:
    """Reject replay discovery that does not bind to the expected identity."""
    prepared = _prepared()
    metadata = _metadata(prepared)
    metadata["parquet_sha256"] = "9" * 64
    client = RecordingS3Client(
        put_error=_client_error(412),
        head_response={
            "VersionId": "existing-version",
            "ContentLength": prepared.parquet_artifact.size_bytes,
            "Metadata": metadata,
        },
    )
    repository = S3GhsaSilverContentRepository(
        client=client,
        bucket_name="opslens-data",
        telemetry=RecordingTelemetry(),
    )

    with pytest.raises(
        GhsaSilverContentReplayMismatchError,
        match="metadata does not match",
    ):
        repository.put_if_absent(prepared)

    assert client.get_calls == []


def test_classifies_409_as_concurrent_write_conflict() -> None:
    """Expose S3's retryable conditional-write conflict separately."""
    repository = S3GhsaSilverContentRepository(
        client=RecordingS3Client(
            put_error=_client_error(409),
        ),
        bucket_name="opslens-data",
        telemetry=RecordingTelemetry(),
    )

    with pytest.raises(
        GhsaSilverContentConcurrentWriteError,
        match="Concurrent",
    ):
        repository.put_if_absent(_prepared())


def test_propagates_unexpected_s3_failure() -> None:
    """Keep unexpected infrastructure failure distinct from idempotent replay."""
    repository = S3GhsaSilverContentRepository(
        client=RecordingS3Client(
            put_error=_client_error(500),
        ),
        bucket_name="opslens-data",
        telemetry=RecordingTelemetry(),
    )

    with pytest.raises(ClientError):
        repository.put_if_absent(_prepared())
