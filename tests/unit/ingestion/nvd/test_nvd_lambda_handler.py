"""Unit tests for the NVD Bootstrap AWS Lambda runtime boundary."""

import gzip
import hashlib
from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext

import pytest

from opslens.ingestion.nvd.application.key_factory import (
    NvdBootstrapKeyFactory,
)
from opslens.ingestion.nvd.application.manifest import (
    NvdBootstrapManifest,
    NvdBootstrapManifestFactory,
    NvdBootstrapManifestSerializer,
)
from opslens.ingestion.nvd.application.models import (
    NvdBronzeWriteResult,
    NvdBronzeWriteStatus,
)
from opslens.ingestion.nvd.application.service import (
    IngestNvdBootstrapFeed,
)
from opslens.ingestion.nvd.domain.feed_artifact import NvdFeedArtifact
from opslens.ingestion.nvd.domain.feed_integrity import (
    NvdFeedIntegrityVerifier,
)
from opslens.ingestion.nvd.domain.meta_parser import NvdFeedMetaParser
from opslens.ingestion.nvd.domain.source_identity import (
    NvdBootstrapSourceIdentity,
)
from opslens.ingestion.nvd.lambda_handler import (
    execute_ingestion,
    parse_feed_year,
)

JSON_PAYLOAD = b'{"format":"NVD_CVE","version":"2.0"}'


class FakeTelemetry:
    """Capture Lambda-boundary telemetry."""

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
        """Capture informational telemetry."""
        self.info_events.append(message)

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture exception telemetry."""
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
        """Capture one span."""
        self.spans.append(name)
        return nullcontext()


class FakeSource:
    """Return deterministic NVD source artifacts."""

    def __init__(
        self,
        *,
        fail: bool = False,
    ) -> None:
        """Initialize deterministic source behavior."""
        self._fail = fail
        self._meta_payload, self._gzip_payload = _source_payloads()

    def fetch_meta(self, feed_year: int) -> bytes:
        """Return META bytes or raise a deterministic source failure."""
        if self._fail:
            raise RuntimeError("NVD source unavailable")

        return self._meta_payload

    def fetch_gzip(self, feed_year: int) -> bytes:
        """Return deterministic gzip bytes."""
        return self._gzip_payload


class FakeRepository:
    """Return deterministic verified Bronze write evidence."""

    def create_feed(
        self,
        *,
        artifact: NvdFeedArtifact,
        identity: NvdBootstrapSourceIdentity,
        object_key: str,
    ) -> NvdBronzeWriteResult:
        """Return deterministic feed persistence evidence."""
        return NvdBronzeWriteResult(
            status=NvdBronzeWriteStatus.CREATED,
            version_id="feed-version-123",
            etag='"feed-etag"',
        )

    def create_meta(
        self,
        *,
        identity: NvdBootstrapSourceIdentity,
        object_key: str,
    ) -> NvdBronzeWriteResult:
        """Return deterministic META persistence evidence."""
        return NvdBronzeWriteResult(
            status=NvdBronzeWriteStatus.CREATED,
            version_id="meta-version-456",
            etag='"meta-etag"',
        )

    def create_manifest(
        self,
        *,
        manifest: NvdBootstrapManifest,
        payload: bytes,
        object_key: str,
    ) -> NvdBronzeWriteResult:
        """Return deterministic manifest persistence evidence."""
        return NvdBronzeWriteResult(
            status=NvdBronzeWriteStatus.CREATED,
            version_id="manifest-version-789",
            etag='"manifest-etag"',
        )


def _source_payloads() -> tuple[bytes, bytes]:
    """Build matching deterministic META and gzip artifacts."""
    gzip_payload = gzip.compress(
        JSON_PAYLOAD,
        mtime=0,
    )

    source_sha256 = hashlib.sha256(JSON_PAYLOAD).hexdigest()

    meta_payload = (
        "lastModifiedDate:2026-08-18T03:00:12-04:00\n"
        f"size:{len(JSON_PAYLOAD)}\n"
        "zipSize:1\n"
        f"gzSize:{len(gzip_payload)}\n"
        f"sha256:{source_sha256}\n"
    ).encode()

    return meta_payload, gzip_payload


def _use_case(
    *,
    source: FakeSource | None = None,
) -> IngestNvdBootstrapFeed:
    """Build the actual application service with deterministic adapters."""
    return IngestNvdBootstrapFeed(
        source=source or FakeSource(),
        repository=FakeRepository(),
        meta_parser=NvdFeedMetaParser(),
        integrity_verifier=NvdFeedIntegrityVerifier(),
        key_factory=NvdBootstrapKeyFactory(),
        manifest_factory=NvdBootstrapManifestFactory(),
        manifest_serializer=NvdBootstrapManifestSerializer(),
    )


def test_execute_ingestion_returns_complete_runtime_evidence() -> None:
    """Serialize the exact completed Bronze revision evidence."""
    telemetry = FakeTelemetry()

    result = execute_ingestion(
        use_case=_use_case(),
        telemetry=telemetry,
        request_id="request-123",
        feed_year=2026,
    )

    assert result["feed_year"] == 2026
    feed_revision = result["feed_revision"]

    assert isinstance(feed_revision, str)
    assert feed_revision.startswith("20260818T070012Z-")

    assert result["feed_status"] == "created"
    assert result["feed_version_id"] == "feed-version-123"

    assert result["meta_status"] == "created"
    assert result["meta_version_id"] == "meta-version-456"

    assert result["manifest_status"] == "created"
    assert result["manifest_version_id"] == ("manifest-version-789")

    assert (
        "NvdBootstrapIngestionInvocation",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "NvdBootstrapIngestionSuccess",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert telemetry.exception_events == []


def test_execute_ingestion_records_and_propagates_failure() -> None:
    """Fail the Lambda invocation when application ingestion fails."""
    telemetry = FakeTelemetry()

    with pytest.raises(
        RuntimeError,
        match="NVD source unavailable",
    ):
        execute_ingestion(
            use_case=_use_case(
                source=FakeSource(fail=True),
            ),
            telemetry=telemetry,
            request_id="request-123",
            feed_year=2026,
        )

    assert (
        "NvdBootstrapIngestionFailure",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "NvdBootstrapIngestionSuccess",
        1.0,
        "Count",
    ) not in telemetry.metrics

    assert telemetry.exception_events == ["NVD Bootstrap ingestion invocation failed"]


def test_parse_feed_year_accepts_explicit_integer() -> None:
    """Accept one explicit four-digit integer feed year."""
    assert (
        parse_feed_year(
            {
                "feed_year": 2026,
            }
        )
        == 2026
    )


@pytest.mark.parametrize(
    "event",
    [
        {},
        {"feed_year": "2026"},
        {"feed_year": True},
        {"feed_year": None},
    ],
)
def test_parse_feed_year_rejects_non_integer_input(
    event: Mapping[str, object],
) -> None:
    """Reject ambiguous or missing feed-year representations."""
    with pytest.raises(
        ValueError,
        match="must be an integer",
    ):
        parse_feed_year(event)


@pytest.mark.parametrize(
    "feed_year",
    [
        999,
        10000,
    ],
)
def test_parse_feed_year_rejects_non_four_digit_integer(
    feed_year: int,
) -> None:
    """Reject integer values outside the feed-year contract."""
    with pytest.raises(
        ValueError,
        match="exactly four digits",
    ):
        parse_feed_year(
            {
                "feed_year": feed_year,
            }
        )
