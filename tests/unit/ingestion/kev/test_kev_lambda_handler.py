"""Unit tests for the CISA KEV AWS Lambda runtime boundary."""

import json
from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime

import pytest

from opslens.ingestion.kev.application.key_factory import KevBronzeKeyFactory
from opslens.ingestion.kev.application.models import (
    RepositoryWriteResult,
    RepositoryWriteStatus,
)
from opslens.ingestion.kev.application.service import IngestKevCatalog
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.ingestion.kev.domain.parser import KevCatalogParser
from opslens.ingestion.kev.lambda_handler import execute_ingestion


class FakeTelemetry:
    """Capture telemetry emitted by the Lambda runtime boundary."""

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
        """Capture an emitted metric."""
        self.metrics.append((name, value, unit))

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Capture a trace span."""
        self.spans.append(name)
        return nullcontext()


class FixedClock:
    """Return a deterministic timestamp."""

    def now(self) -> datetime:
        """Return the deterministic observation timestamp."""
        return datetime(
            2026,
            8,
            17,
            2,
            15,
            tzinfo=UTC,
        )


class FakeCatalogSource:
    """Return a deterministic KEV source artifact."""

    def __init__(self, payload: bytes) -> None:
        """Initialize the source with deterministic bytes."""
        self._payload = payload

    def fetch(self) -> bytes:
        """Return the configured source bytes."""
        return self._payload


class FailingCatalogSource:
    """Raise a deterministic source failure."""

    def fetch(self) -> bytes:
        """Raise a deterministic runtime failure."""
        raise RuntimeError("source unavailable")


class FakeBronzeRepository:
    """Return a deterministic Bronze repository result."""

    def __init__(
        self,
        status: RepositoryWriteStatus,
    ) -> None:
        """Initialize the repository with a deterministic outcome."""
        self._status = status

    def create_if_absent(
        self,
        snapshot: KevCatalogSnapshot,
        object_key: str,
    ) -> RepositoryWriteResult:
        """Return the configured repository outcome."""
        return RepositoryWriteResult(
            status=self._status,
            version_id=(
                "version-123"
                if self._status is RepositoryWriteStatus.CREATED
                else None
            ),
            etag=(
                '"etag-123"'
                if self._status is RepositoryWriteStatus.CREATED
                else None
            ),
        )


def build_source_payload() -> bytes:
    """Build a deterministic valid KEV source artifact."""
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


def build_use_case(
    status: RepositoryWriteStatus,
) -> IngestKevCatalog:
    """Build a deterministic KEV ingestion use case."""
    return IngestKevCatalog(
        source=FakeCatalogSource(build_source_payload()),
        repository=FakeBronzeRepository(status),
        parser=KevCatalogParser(),
        key_factory=KevBronzeKeyFactory(),
        clock=FixedClock(),
    )


def test_execute_ingestion_returns_created_result() -> None:
    """Return a serialized created result and emit success telemetry."""
    telemetry = FakeTelemetry()

    result = execute_ingestion(
        use_case=build_use_case(RepositoryWriteStatus.CREATED),
        telemetry=telemetry,
        request_id="request-123",
    )

    assert result["status"] == "created"
    assert result["snapshot_date"] == "2026-08-17"
    assert result["catalog_version"] == "2026.08.16"
    assert result["record_count"] == 1
    assert result["version_id"] == "version-123"

    assert (
        "KevIngestionInvocation",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "KevIngestionSuccess",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "KevIngestionCreated",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert telemetry.exception_events == []


def test_execute_ingestion_returns_already_exists_result() -> None:
    """Return an idempotent already-exists result as successful execution."""
    telemetry = FakeTelemetry()

    result = execute_ingestion(
        use_case=build_use_case(
            RepositoryWriteStatus.ALREADY_EXISTS
        ),
        telemetry=telemetry,
        request_id="request-123",
    )

    assert result["status"] == "already_exists"
    assert result["version_id"] is None
    assert result["etag"] is None

    assert (
        "KevIngestionSuccess",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "KevIngestionAlreadyExists",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "KevIngestionFailure",
        1.0,
        "Count",
    ) not in telemetry.metrics


def test_execute_ingestion_propagates_failure() -> None:
    """Record failure telemetry and propagate ingestion exceptions."""
    telemetry = FakeTelemetry()

    use_case = IngestKevCatalog(
        source=FailingCatalogSource(),
        repository=FakeBronzeRepository(
            RepositoryWriteStatus.CREATED
        ),
        parser=KevCatalogParser(),
        key_factory=KevBronzeKeyFactory(),
        clock=FixedClock(),
    )

    with pytest.raises(
        RuntimeError,
        match="source unavailable",
    ):
        execute_ingestion(
            use_case=use_case,
            telemetry=telemetry,
            request_id="request-123",
        )

    assert (
        "KevIngestionInvocation",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "KevIngestionFailure",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "KevIngestionSuccess",
        1.0,
        "Count",
    ) not in telemetry.metrics

    assert telemetry.exception_events == [
        "CISA KEV ingestion invocation failed"
    ]
