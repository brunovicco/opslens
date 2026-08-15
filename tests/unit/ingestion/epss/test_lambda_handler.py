"""Unit tests for the EPSS AWS Lambda runtime boundary."""

import gzip
from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext

import pytest

from opslens.ingestion.epss.application.key_factory import EpssBronzeKeyFactory
from opslens.ingestion.epss.application.models import (
    RepositoryWriteResult,
    RepositoryWriteStatus,
)
from opslens.ingestion.epss.application.service import IngestEpssSnapshot
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.epss.domain.parser import EpssSnapshotParser
from opslens.ingestion.epss.lambda_handler import execute_ingestion


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
        """Capture an informational telemetry event."""
        self.info_events.append(message)

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture an exception telemetry event."""
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
        """Capture a no-op trace span."""
        self.spans.append(name)

        return nullcontext()


class FakeSnapshotSource:
    """Return a deterministic EPSS snapshot artifact."""

    def __init__(self, payload: bytes) -> None:
        """Initialize the source with deterministic bytes."""
        self._payload = payload

    def fetch(self) -> bytes:
        """Return the configured EPSS source bytes."""
        return self._payload


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
        snapshot: EpssSnapshot,
        object_key: str,
    ) -> RepositoryWriteResult:
        """Return the configured repository outcome."""
        return RepositoryWriteResult(
            status=self._status,
            version_id=("version-123" if self._status is RepositoryWriteStatus.CREATED else None),
            etag=('"etag-123"' if self._status is RepositoryWriteStatus.CREATED else None),
        )


class FailingSnapshotSource:
    """Raise a deterministic source failure."""

    def fetch(self) -> bytes:
        """Raise a deterministic runtime failure."""
        raise RuntimeError("source unavailable")


def build_source_payload() -> bytes:
    """Build a deterministic valid EPSS source artifact."""
    content = (
        "#model_version:v2026.06.15,score_date:2026-08-14T12:00:27Z\n"
        "cve,epss,percentile\n"
        "CVE-1999-0001,0.03351,0.8762\n"
    )

    return gzip.compress(
        content.encode("utf-8"),
        mtime=0,
    )


def build_use_case(
    status: RepositoryWriteStatus,
) -> IngestEpssSnapshot:
    """Build a deterministic ingestion use case for handler tests."""
    return IngestEpssSnapshot(
        source=FakeSnapshotSource(build_source_payload()),
        repository=FakeBronzeRepository(status),
        parser=EpssSnapshotParser(),
        key_factory=EpssBronzeKeyFactory(),
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
    assert result["snapshot_date"] == "2026-08-14"
    assert result["model_version"] == "v2026.06.15"
    assert result["version_id"] == "version-123"

    assert (
        "EpssIngestionInvocation",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "EpssIngestionSuccess",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "EpssIngestionCreated",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert telemetry.exception_events == []


def test_execute_ingestion_returns_already_exists_result() -> None:
    """Return an idempotent already-exists result as successful execution."""
    telemetry = FakeTelemetry()

    result = execute_ingestion(
        use_case=build_use_case(RepositoryWriteStatus.ALREADY_EXISTS),
        telemetry=telemetry,
        request_id="request-123",
    )

    assert result["status"] == "already_exists"
    assert result["version_id"] is None
    assert result["etag"] is None

    assert (
        "EpssIngestionSuccess",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "EpssIngestionAlreadyExists",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "EpssIngestionFailure",
        1.0,
        "Count",
    ) not in telemetry.metrics


def test_execute_ingestion_propagates_failure() -> None:
    """Record failure telemetry and propagate ingestion exceptions."""
    telemetry = FakeTelemetry()

    use_case = IngestEpssSnapshot(
        source=FailingSnapshotSource(),
        repository=FakeBronzeRepository(RepositoryWriteStatus.CREATED),
        parser=EpssSnapshotParser(),
        key_factory=EpssBronzeKeyFactory(),
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
        "EpssIngestionInvocation",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "EpssIngestionFailure",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "EpssIngestionSuccess",
        1.0,
        "Count",
    ) not in telemetry.metrics

    assert telemetry.exception_events == ["EPSS ingestion invocation failed"]
