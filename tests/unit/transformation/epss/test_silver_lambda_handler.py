"""Unit tests for the EPSS Silver AWS Lambda runtime boundary."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from datetime import date

import pytest

from opslens.transformation.epss.adapters.inbound.s3_event import (
    S3ObjectCreatedEventParser,
)
from opslens.transformation.epss.application.models import (
    EpssSilverTransformationResult,
    SilverRepositoryWriteStatus,
)
from opslens.transformation.epss.lambda_handler import (
    execute_transformation_event,
)

BUCKET = "opslens-test-data"


class FakeTelemetry:
    """Capture telemetry emitted by the Silver Lambda boundary."""

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
        """Capture an operational metric."""
        self.metrics.append((name, value, unit))

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Capture a no-op trace span."""
        self.spans.append(name)
        return nullcontext()


class FakeTransformationService:
    """Return deterministic Silver transformation outcomes."""

    def __init__(
        self,
        *,
        statuses: Mapping[str, SilverRepositoryWriteStatus],
        failing_key: str | None = None,
    ) -> None:
        """Initialize deterministic service behavior."""
        self._statuses = statuses
        self._failing_key = failing_key
        self.calls: list[str] = []

    def transform(
        self,
        bronze_key: str,
    ) -> EpssSilverTransformationResult:
        """Return a deterministic result or configured failure."""
        self.calls.append(bronze_key)

        if bronze_key == self._failing_key:
            raise RuntimeError("transformation failed")

        snapshot_date = _snapshot_date_from_key(bronze_key)

        return EpssSilverTransformationResult(
            bronze_key=bronze_key,
            silver_key=(
                f"silver/epss/snapshot_date={snapshot_date.isoformat()}/part-00000.parquet"
            ),
            snapshot_date=snapshot_date,
            row_count=2,
            size_bytes=128,
            schema_version=1,
            source_sha256="a" * 64,
            write_status=self._statuses[bronze_key],
        )


def _snapshot_date_from_key(
    key: str,
) -> date:
    """Extract the deterministic snapshot date used by test keys."""
    partition = key.split("snapshot_date=", maxsplit=1)[1]
    raw_date = partition.split("/", maxsplit=1)[0]
    return date.fromisoformat(raw_date)


def _record(
    *,
    snapshot_date: str,
) -> dict[str, object]:
    """Build one deterministic S3 ObjectCreated notification record."""
    return {
        "eventVersion": "2.1",
        "eventSource": "aws:s3",
        "eventName": "ObjectCreated:Put",
        "s3": {
            "bucket": {
                "name": BUCKET,
            },
            "object": {
                "key": (f"bronze/epss/snapshot_date%3D{snapshot_date}/epss_scores.csv.gz"),
                "sequencer": f"sequencer-{snapshot_date}",
            },
        },
    }


def _test_event(
    *,
    bucket: str = BUCKET,
) -> dict[str, object]:
    """Build one deterministic Amazon S3 test notification."""
    return {
        "Service": "Amazon S3",
        "Event": "s3:TestEvent",
        "Time": "2026-08-15T22:00:00.000Z",
        "Bucket": bucket,
        "RequestId": "TESTREQUEST123",
        "HostId": "test-host-id",
    }


def test_accepts_s3_test_event_without_transforming() -> None:
    """Accept an S3 test event without invoking Bronze transformation."""
    service = FakeTransformationService(
        statuses={},
    )
    telemetry = FakeTelemetry()

    result = execute_transformation_event(
        event=_test_event(),
        event_parser=S3ObjectCreatedEventParser(
            expected_bucket=BUCKET,
        ),
        use_case=service,
        telemetry=telemetry,
        request_id="lambda-request-123",
    )

    assert result == {
        "processed_records": 0,
        "created_records": 0,
        "already_exists_records": 0,
        "records": [],
    }

    assert service.calls == []

    assert (
        "EpssSilverS3TestEvent",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "EpssSilverTransformationInvocation",
        1.0,
        "Count",
    ) not in telemetry.metrics

    assert (
        "EpssSilverTransformationSuccess",
        1.0,
        "Count",
    ) not in telemetry.metrics

    assert telemetry.exception_events == []

    assert "Accepted S3 test event" in telemetry.info_events


def test_processes_all_records_and_returns_aggregated_result() -> None:
    """Process all records in order and aggregate created/idempotent outcomes."""
    first_key = "bronze/epss/snapshot_date=2026-08-14/epss_scores.csv.gz"
    second_key = "bronze/epss/snapshot_date=2026-08-15/epss_scores.csv.gz"

    service = FakeTransformationService(
        statuses={
            first_key: SilverRepositoryWriteStatus.CREATED,
            second_key: SilverRepositoryWriteStatus.ALREADY_EXISTS,
        }
    )
    telemetry = FakeTelemetry()

    result = execute_transformation_event(
        event={
            "Records": [
                _record(snapshot_date="2026-08-14"),
                _record(snapshot_date="2026-08-15"),
            ],
        },
        event_parser=S3ObjectCreatedEventParser(
            expected_bucket=BUCKET,
        ),
        use_case=service,
        telemetry=telemetry,
        request_id="request-123",
    )

    assert service.calls == [
        first_key,
        second_key,
    ]

    assert result["processed_records"] == 2
    assert result["created_records"] == 1
    assert result["already_exists_records"] == 1

    assert result["records"][0]["status"] == "created"
    assert result["records"][1]["status"] == "already_exists"

    assert (
        "EpssSilverTransformationSuccess",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert telemetry.exception_events == []


def test_propagates_failure_after_previous_record_succeeded() -> None:
    """Fail the invocation when any record transformation fails."""
    first_key = "bronze/epss/snapshot_date=2026-08-14/epss_scores.csv.gz"
    second_key = "bronze/epss/snapshot_date=2026-08-15/epss_scores.csv.gz"

    service = FakeTransformationService(
        statuses={
            first_key: SilverRepositoryWriteStatus.CREATED,
            second_key: SilverRepositoryWriteStatus.CREATED,
        },
        failing_key=second_key,
    )
    telemetry = FakeTelemetry()

    with pytest.raises(
        RuntimeError,
        match="transformation failed",
    ):
        execute_transformation_event(
            event={
                "Records": [
                    _record(snapshot_date="2026-08-14"),
                    _record(snapshot_date="2026-08-15"),
                ],
            },
            event_parser=S3ObjectCreatedEventParser(
                expected_bucket=BUCKET,
            ),
            use_case=service,
            telemetry=telemetry,
            request_id="request-123",
        )

    assert service.calls == [
        first_key,
        second_key,
    ]

    assert (
        "EpssSilverTransformationFailure",
        1.0,
        "Count",
    ) in telemetry.metrics

    assert (
        "EpssSilverTransformationSuccess",
        1.0,
        "Count",
    ) not in telemetry.metrics

    assert telemetry.exception_events == ["EPSS Silver transformation invocation failed"]


def test_rejects_invalid_event_before_transformation() -> None:
    """Reject malformed events before invoking the application service."""
    service = FakeTransformationService(
        statuses={},
    )
    telemetry = FakeTelemetry()

    with pytest.raises(
        ValueError,
        match="non-empty Records list",
    ):
        execute_transformation_event(
            event={},
            event_parser=S3ObjectCreatedEventParser(
                expected_bucket=BUCKET,
            ),
            use_case=service,
            telemetry=telemetry,
            request_id="request-123",
        )

    assert service.calls == []

    assert (
        "EpssSilverTransformationFailure",
        1.0,
        "Count",
    ) in telemetry.metrics
