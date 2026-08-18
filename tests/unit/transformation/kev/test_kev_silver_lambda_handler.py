"""Unit tests for the CISA KEV Silver Lambda event boundary."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext

import pytest

from opslens.transformation.kev.adapters.inbound.s3_event import (
    KevBronzeObjectReference,
    KevS3EventParser,
)
from opslens.transformation.kev.application.runtime_models import (
    KevSilverRepositoryWriteStatus,
    KevSilverTransformationResult,
)
from opslens.transformation.kev.lambda_handler import (
    execute_transformation_event,
)

BUCKET = "opslens-dev-data-487757851499-us-east-1"

ENCODED_KEY = "bronze/kev/snapshot_date%3D2026-08-17/known_exploited_vulnerabilities.json"

DECODED_KEY = "bronze/kev/snapshot_date=2026-08-17/known_exploited_vulnerabilities.json"


class FakeTelemetry:
    """Capture operational telemetry emitted by the Lambda boundary."""

    def __init__(self) -> None:
        """Initialize telemetry capture."""
        self.metrics: list[str] = []
        self.exceptions: list[tuple[str, dict[str, object]]] = []

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Accept informational telemetry."""
        del message, fields

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture exception telemetry."""
        self.exceptions.append(
            (
                message,
                dict(fields or {}),
            )
        )

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Capture emitted metric names."""
        del value, unit
        self.metrics.append(name)

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Return a no-op tracing span."""
        del name
        return nullcontext()


class FakeProcessor:
    """Return configured outcomes for parsed KEV object references."""

    def __init__(
        self,
        statuses: list[KevSilverRepositoryWriteStatus],
    ) -> None:
        """Initialize processor outcomes."""
        self._statuses = statuses
        self.references: list[KevBronzeObjectReference] = []

    def process(
        self,
        reference: KevBronzeObjectReference,
    ) -> KevSilverTransformationResult:
        """Capture the reference and return the next configured outcome."""
        self.references.append(reference)

        status = self._statuses[len(self.references) - 1]

        return KevSilverTransformationResult(
            bronze_key=reference.key,
            bronze_version_id=reference.version_id,
            silver_key=("silver/kev/snapshot_date=2026-08-17/part-00000.parquet"),
            snapshot_date="2026-08-17",
            row_count=1665,
            size_bytes=257331,
            schema_version=1,
            source_sha256="a" * 64,
            write_status=status,
        )


class RaisingProcessor:
    """Fail on a configured object-processing invocation."""

    def __init__(
        self,
        *,
        fail_on_call: int,
    ) -> None:
        """Initialize the failing processor."""
        self._fail_on_call = fail_on_call
        self.references: list[KevBronzeObjectReference] = []

    def process(
        self,
        reference: KevBronzeObjectReference,
    ) -> KevSilverTransformationResult:
        """Raise on the configured call and succeed otherwise."""
        self.references.append(reference)

        if len(self.references) == self._fail_on_call:
            raise RuntimeError("processing failure")

        return KevSilverTransformationResult(
            bronze_key=reference.key,
            bronze_version_id=reference.version_id,
            silver_key=("silver/kev/snapshot_date=2026-08-17/part-00000.parquet"),
            snapshot_date="2026-08-17",
            row_count=1665,
            size_bytes=257331,
            schema_version=1,
            source_sha256="a" * 64,
            write_status=KevSilverRepositoryWriteStatus.CREATED,
        )


def _record(
    *,
    version_id: str,
    sequencer: str,
) -> dict[str, object]:
    """Build one strict versioned KEV S3 ObjectCreated record."""
    return {
        "eventVersion": "2.1",
        "eventSource": "aws:s3",
        "eventName": "ObjectCreated:Put",
        "s3": {
            "bucket": {
                "name": BUCKET,
            },
            "object": {
                "key": ENCODED_KEY,
                "size": 1_583_171,
                "eTag": "4d6ebe76c67bfe50649db3de0ebc1d6a",
                "versionId": version_id,
                "sequencer": sequencer,
            },
        },
    }


def _event(
    *records: dict[str, object],
) -> dict[str, object]:
    """Build one regular S3 notification."""
    return {
        "Records": list(records),
    }


def test_accepts_s3_test_event_without_processing_objects() -> None:
    """Treat S3 notification validation events as successful no-op calls."""
    telemetry = FakeTelemetry()
    processor = FakeProcessor([])

    result = execute_transformation_event(
        event={
            "Service": "Amazon S3",
            "Event": "s3:TestEvent",
            "Bucket": BUCKET,
            "RequestId": "s3-request-123",
        },
        event_parser=KevS3EventParser(
            expected_bucket=BUCKET,
        ),
        processor=processor,
        telemetry=telemetry,
        request_id="lambda-request-123",
    )

    assert result == {
        "processed_records": 0,
        "created_records": 0,
        "already_exists_records": 0,
        "records": [],
    }

    assert processor.references == []
    assert "KevSilverS3TestEvent" in telemetry.metrics


def test_processes_created_record_with_exact_version_reference() -> None:
    """Pass complete versioned S3 identity into the object processor."""
    processor = FakeProcessor(
        [
            KevSilverRepositoryWriteStatus.CREATED,
        ]
    )

    result = execute_transformation_event(
        event=_event(
            _record(
                version_id="version-123",
                sequencer="001",
            )
        ),
        event_parser=KevS3EventParser(
            expected_bucket=BUCKET,
        ),
        processor=processor,
        telemetry=FakeTelemetry(),
        request_id="lambda-request-123",
    )

    assert result["processed_records"] == 1
    assert result["created_records"] == 1
    assert result["already_exists_records"] == 0

    assert len(processor.references) == 1

    reference = processor.references[0]

    assert reference.key == DECODED_KEY
    assert reference.version_id == "version-123"
    assert reference.size_bytes == 1_583_171

    assert result["records"][0]["bronze_version_id"] == "version-123"
    assert result["records"][0]["status"] == "created"


def test_counts_created_and_idempotent_replay_separately() -> None:
    """Preserve CREATED and ALREADY_EXISTS outcomes across one invocation."""
    processor = FakeProcessor(
        [
            KevSilverRepositoryWriteStatus.CREATED,
            KevSilverRepositoryWriteStatus.ALREADY_EXISTS,
        ]
    )

    result = execute_transformation_event(
        event=_event(
            _record(
                version_id="version-1",
                sequencer="001",
            ),
            _record(
                version_id="version-2",
                sequencer="002",
            ),
        ),
        event_parser=KevS3EventParser(
            expected_bucket=BUCKET,
        ),
        processor=processor,
        telemetry=FakeTelemetry(),
        request_id="lambda-request-123",
    )

    assert result["processed_records"] == 2
    assert result["created_records"] == 1
    assert result["already_exists_records"] == 1

    assert [item["status"] for item in result["records"]] == [
        "created",
        "already_exists",
    ]


def test_propagates_processing_failure_and_stops_remaining_records() -> None:
    """Fail the invocation so Lambda asynchronous retry remains available."""
    telemetry = FakeTelemetry()
    processor = RaisingProcessor(
        fail_on_call=2,
    )

    event = _event(
        _record(
            version_id="version-1",
            sequencer="001",
        ),
        _record(
            version_id="version-2",
            sequencer="002",
        ),
        _record(
            version_id="version-3",
            sequencer="003",
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="processing failure",
    ):
        execute_transformation_event(
            event=event,
            event_parser=KevS3EventParser(
                expected_bucket=BUCKET,
            ),
            processor=processor,
            telemetry=telemetry,
            request_id="lambda-request-123",
        )

    assert len(processor.references) == 2

    assert "KevSilverTransformationFailure" in telemetry.metrics
    assert "KevSilverTransformationSuccess" not in telemetry.metrics

    assert len(telemetry.exceptions) == 1

    _, failure_fields = telemetry.exceptions[0]

    assert failure_fields["record_index"] == 1
    assert failure_fields["bronze_key"] == DECODED_KEY
    assert failure_fields["bronze_version_id"] == "version-2"


def test_rejects_invalid_event_and_records_failure_metric() -> None:
    """Expose malformed event failures to the Lambda runtime."""
    telemetry = FakeTelemetry()

    with pytest.raises(
        ValueError,
        match="Records",
    ):
        execute_transformation_event(
            event={
                "Records": [],
            },
            event_parser=KevS3EventParser(
                expected_bucket=BUCKET,
            ),
            processor=FakeProcessor([]),
            telemetry=telemetry,
            request_id="lambda-request-123",
        )

    assert "KevSilverTransformationFailure" in telemetry.metrics
