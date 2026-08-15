"""Unit tests for the EPSS application composition root."""

import gzip
from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from types import TracebackType
from urllib.request import Request

import pytest

from opslens.ingestion.epss.adapters.outbound import first_http
from opslens.ingestion.epss.application.models import RepositoryWriteStatus
from opslens.ingestion.epss.composition import build_ingestion_use_case
from opslens.ingestion.epss.config import EpssIngestionSettings


class FakeTelemetry:
    """Capture telemetry emitted by the composed EPSS application."""

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
        """Capture a structured informational event."""
        self.info_events.append(message)

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture a structured exception event."""
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
        """Capture a trace span using a no-op context manager."""
        self.spans.append(name)

        return nullcontext()


class FakeHttpResponse:
    """Represent a deterministic FIRST HTTP response."""

    def __init__(
        self,
        payload: bytes,
        status: int = 200,
    ) -> None:
        """Initialize the fake HTTP response."""
        self._payload = payload
        self.status = status

    def read(self) -> bytes:
        """Return the configured HTTP response payload."""
        return self._payload

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
    """Build a deterministic valid FIRST EPSS artifact."""
    content = (
        "#model_version:v2026.06.15,score_date:2026-08-14T12:00:27Z\n"
        "cve,epss,percentile\n"
        "CVE-1999-0001,0.03351,0.8762\n"
        "CVE-2026-0001,0.71000,0.9910\n"
    )

    return gzip.compress(
        content.encode("utf-8"),
        mtime=0,
    )


def test_composed_application_ingests_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Execute the composed application through HTTP and S3 boundaries."""
    source_payload = build_source_payload()

    def fake_urlopen(
        request: Request,
        timeout: float,
    ) -> FakeHttpResponse:
        """Return the deterministic FIRST test artifact."""
        assert request.full_url == "https://example.test/epss_scores-current.csv.gz"
        assert timeout == 15.0

        return FakeHttpResponse(
            payload=source_payload,
            status=200,
        )

    monkeypatch.setattr(
        first_http,
        "urlopen",
        fake_urlopen,
    )

    settings = EpssIngestionSettings(
        source_url=("https://example.test/epss_scores-current.csv.gz"),
        bronze_bucket="opslens-test-data",
        bronze_prefix="bronze/epss",
        http_timeout_seconds=15.0,
    )

    telemetry = FakeTelemetry()
    s3_client = FakeS3Client()

    use_case = build_ingestion_use_case(
        settings=settings,
        telemetry=telemetry,
        s3_client=s3_client,
    )

    result = use_case.execute()

    expected_key = "bronze/epss/snapshot_date=2026-08-14/epss_scores.csv.gz"

    assert result.status is RepositoryWriteStatus.CREATED
    assert result.s3_key == expected_key
    assert result.snapshot.snapshot_date == "2026-08-14"
    assert result.snapshot.model_version == "v2026.06.15"
    assert result.snapshot.row_count == 2
    assert result.version_id == "test-version-id"
    assert result.etag == '"test-etag"'

    assert s3_client.request is not None

    assert s3_client.request["Bucket"] == "opslens-test-data"
    assert s3_client.request["Key"] == expected_key
    assert s3_client.request["Body"] == source_payload
    assert s3_client.request["ContentType"] == "application/gzip"
    assert s3_client.request["IfNoneMatch"] == "*"

    metadata = s3_client.request["Metadata"]

    assert isinstance(metadata, Mapping)
    assert metadata["source"] == "first-epss"
    assert metadata["model_version"] == "v2026.06.15"
    assert metadata["score_date"] == "2026-08-14T12:00:27Z"
    assert metadata["sha256"] == result.snapshot.sha256

    assert "epss.first_http.fetch" in telemetry.spans
    assert "epss.s3.put_object" in telemetry.spans

    assert (
        "EpssSourceFetchSuccess",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "EpssBronzeCreated",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert telemetry.exception_events == []
