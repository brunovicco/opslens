"""Unit tests for the CISA KEV application composition root."""

import json
from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime
from types import TracebackType
from urllib.request import Request

import pytest

from opslens.ingestion.kev.adapters.outbound import cisa_http
from opslens.ingestion.kev.application.models import RepositoryWriteStatus
from opslens.ingestion.kev.composition import build_ingestion_use_case
from opslens.ingestion.kev.config import KevIngestionSettings


class FakeTelemetry:
    """Capture telemetry emitted by the composed KEV application."""

    def __init__(self) -> None:
        """Initialize telemetry collections."""
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
        """Capture an informational event."""
        self.info_events.append(message)

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture an exception event."""
        self.exception_events.append(message)

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Capture an operational metric."""
        self.metrics.append((name, value, unit))

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Capture a trace span."""
        self.spans.append(name)
        return nullcontext()


class FixedClock:
    """Return a deterministic observation timestamp."""

    def now(self) -> datetime:
        """Return the configured test timestamp."""
        return datetime(
            2026,
            8,
            17,
            2,
            15,
            tzinfo=UTC,
        )


class FakeHttpResponse:
    """Represent a deterministic CISA HTTP response."""

    def __init__(
        self,
        payload: bytes,
        status: int = 200,
    ) -> None:
        """Initialize the fake HTTP response."""
        self._payload = payload
        self.status = status

    def read(self, size: int = -1) -> bytes:
        """Return at most the requested number of bytes."""
        if size < 0:
            return self._payload

        return self._payload[:size]

    def __enter__(self) -> "FakeHttpResponse":
        """Enter the HTTP response context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the HTTP response context manager."""
        return None


class FakeS3Client:
    """Capture the S3 request produced by the composed application."""

    def __init__(self) -> None:
        """Initialize the fake S3 client."""
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
    ) -> Mapping[str, object]:
        """Capture PutObject parameters and return a successful response."""
        self.request = {
            "Bucket": Bucket,
            "Key": Key,
            "Body": Body,
            "ContentType": ContentType,
            "Metadata": Metadata,
            "IfNoneMatch": IfNoneMatch,
        }

        return {
            "VersionId": "test-version-id",
            "ETag": '"test-etag"',
        }


def build_source_payload() -> bytes:
    """Build a deterministic valid CISA KEV catalog."""
    document = {
        "catalogVersion": "2026.08.16",
        "dateReleased": "2026-08-16T20:15:00Z",
        "count": 1,
        "vulnerabilities": [
            {
                "cveID": "CVE-2026-0001",
            }
        ],
    }

    return json.dumps(
        document,
        separators=(",", ":"),
    ).encode("utf-8")


def test_composed_application_ingests_catalog(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Execute the composed KEV application through HTTP and S3 boundaries."""
    source_payload = build_source_payload()

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Return the deterministic CISA test artifact."""
        assert request.full_url == "https://example.test/kev.json"
        assert timeout == 15.0

        return FakeHttpResponse(
            payload=source_payload,
            status=200,
        )

    monkeypatch.setattr(
        cisa_http,
        "urlopen",
        fake_urlopen,
    )

    settings = KevIngestionSettings(
        source_url="https://example.test/kev.json",
        bronze_bucket="opslens-test-data",
        bronze_prefix="bronze/kev",
        http_timeout_seconds=15.0,
        max_source_bytes=1024,
    )

    telemetry = FakeTelemetry()
    s3_client = FakeS3Client()

    use_case = build_ingestion_use_case(
        settings=settings,
        telemetry=telemetry,
        s3_client=s3_client,
        clock=FixedClock(),
    )

    result = use_case.execute()

    expected_key = (
        "bronze/kev/"
        "snapshot_date=2026-08-17/"
        "known_exploited_vulnerabilities.json"
    )

    assert result.status is RepositoryWriteStatus.CREATED
    assert result.s3_key == expected_key
    assert result.snapshot.snapshot_date == "2026-08-17"
    assert result.snapshot.catalog_version == "2026.08.16"
    assert result.snapshot.record_count == 1
    assert result.version_id == "test-version-id"
    assert result.etag == '"test-etag"'

    assert s3_client.request is not None
    assert s3_client.request["Bucket"] == "opslens-test-data"
    assert s3_client.request["Key"] == expected_key
    assert s3_client.request["Body"] == source_payload
    assert s3_client.request["ContentType"] == "application/json"
    assert s3_client.request["IfNoneMatch"] == "*"

    metadata = s3_client.request["Metadata"]

    assert isinstance(metadata, Mapping)
    assert metadata["source"] == "cisa-kev"
    assert metadata["catalog_version"] == "2026.08.16"
    assert metadata["retrieved_at"] == "2026-08-17T02:15:00Z"
    assert metadata["sha256"] == result.snapshot.sha256

    assert "kev.cisa_http.fetch" in telemetry.spans
    assert "kev.s3.put_object" in telemetry.spans

    assert (
        "KevSourceFetchSuccess",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "KevBronzeCreated",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert telemetry.exception_events == []
