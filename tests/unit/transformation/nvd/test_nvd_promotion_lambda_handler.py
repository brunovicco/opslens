"""Tests for the authoritative NVD watermark-promotion Lambda boundary."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime
from urllib.parse import quote_plus

import pytest

from opslens.ingestion.nvd.application.authoritative_watermark import (
    NvdAuthoritativeWatermarkV1,
    NvdWatermarkEvidenceObjectV1,
    NvdWatermarkSilverPromotionCommitV1,
)
from opslens.ingestion.nvd.application.authoritative_watermark_store import (
    NvdPersistedAuthoritativeWatermarkV1,
)
from opslens.transformation.nvd.adapters.inbound.promotion_s3_event import (
    NvdPromotionS3EventParserV1,
    NvdPromotionS3ObjectCreatedV1,
    NvdPromotionS3TestEventV1,
)
from opslens.transformation.nvd.application.watermark_promotion_evidence_loader import (
    NvdSilverCompleteRefV1,
)
from opslens.transformation.nvd.application.watermark_promotion_service import (
    NvdAuthoritativeWatermarkPromotionResultV1,
)
from opslens.transformation.nvd.promotion_lambda_handler import (
    execute_promotion_request,
    parse_lambda_event,
)

BUCKET = "opslens-test-data"
UPDATE_ID = "a" * 64
KEY = (
    "silver/nvd/cve/schema_version=1/source_kind=incremental/"
    f"update_id={UPDATE_ID}/manifest.json"
)
VERSION_ID = "silver-complete-version-1"
START = datetime(2026, 8, 18, 7, 0, 12, tzinfo=UTC)
END = datetime(2026, 8, 18, 7, 20, 12, tzinfo=UTC)


class _Telemetry:
    """Capture operational events emitted by the Lambda execution boundary."""

    def __init__(self) -> None:
        self.metrics: list[tuple[str, float, str]] = []
        self.info_messages: list[str] = []
        self.exception_messages: list[str] = []

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture informational telemetry."""
        del fields
        self.info_messages.append(message)

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture exception telemetry."""
        del fields
        self.exception_messages.append(message)

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
        """Return one no-op tracing span."""
        del name
        return nullcontext()


def _event() -> dict[str, object]:
    """Build one exact Silver COMPLETE ObjectCreated:Put event."""
    return {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "s3SchemaVersion": "1.0",
                    "bucket": {
                        "name": BUCKET,
                    },
                    "object": {
                        "key": quote_plus(
                            KEY,
                            safe="/=",
                        ),
                        "size": 900,
                        "versionId": VERSION_ID,
                    },
                },
            }
        ]
    }


def _result(
    *,
    status: str = "committed",
) -> NvdAuthoritativeWatermarkPromotionResultV1:
    """Build one deterministic persisted promotion result."""
    watermark = NvdAuthoritativeWatermarkV1(
        committed_through_at=END,
        commit_basis=NvdWatermarkSilverPromotionCommitV1(
            previous_committed_through_at=START,
            update_id=UPDATE_ID,
            bronze_manifest=NvdWatermarkEvidenceObjectV1(
                key="bronze-manifest",
                version_id="bronze-version",
                sha256="b" * 64,
            ),
            silver_manifest=NvdWatermarkEvidenceObjectV1(
                key=KEY,
                version_id=VERSION_ID,
                sha256="c" * 64,
            ),
            silver_parquet=NvdWatermarkEvidenceObjectV1(
                key="silver-parquet",
                version_id="silver-parquet-version",
                sha256="d" * 64,
            ),
            logical_record_set_sha256="e" * 64,
        ),
    )

    if status not in {"committed", "already_committed"}:
        raise AssertionError("Unsupported test status.")

    return NvdAuthoritativeWatermarkPromotionResultV1(
        status=(
            "committed"
            if status == "committed"
            else "already_committed"
        ),
        update_id=UPDATE_ID,
        persisted=NvdPersistedAuthoritativeWatermarkV1(
            watermark=watermark,
            version_id="watermark-version-2",
            etag='"watermark-etag-2"',
            sha256="f" * 64,
            size_bytes=900,
        ),
    )


class _Processor:
    """Return one deterministic promotion result."""

    def __init__(
        self,
        result: NvdAuthoritativeWatermarkPromotionResultV1,
    ) -> None:
        self.result = result
        self.references: list[NvdSilverCompleteRefV1] = []

    def process(
        self,
        *,
        silver_complete: NvdSilverCompleteRefV1,
    ) -> NvdAuthoritativeWatermarkPromotionResultV1:
        """Capture the exact selected COMPLETE reference."""
        self.references.append(silver_complete)
        return self.result


class _FailingProcessor:
    """Raise one deterministic application failure."""

    def process(
        self,
        *,
        silver_complete: NvdSilverCompleteRefV1,
    ) -> NvdAuthoritativeWatermarkPromotionResultV1:
        """Fail after receiving the exact trigger reference."""
        del silver_complete
        raise RuntimeError("promotion failed")


def test_parse_lambda_event_returns_exact_trigger_coordinate() -> None:
    """Keep the S3 event as a trigger coordinate only."""
    parsed = parse_lambda_event(
        event=_event(),
        s3_event_parser=NvdPromotionS3EventParserV1(
            expected_bucket=BUCKET,
        ),
    )

    assert isinstance(
        parsed,
        NvdPromotionS3ObjectCreatedV1,
    )
    assert parsed.silver_complete == NvdSilverCompleteRefV1(
        key=KEY,
        version_id=VERSION_ID,
    )


def test_parse_lambda_event_accepts_s3_test_notification() -> None:
    """Handle configuration test events without initializing promotion state."""
    parsed = parse_lambda_event(
        event={
            "Event": "s3:TestEvent",
            "Bucket": BUCKET,
            "RequestId": "test-request-id",
        },
        s3_event_parser=NvdPromotionS3EventParserV1(
            expected_bucket=BUCKET,
        ),
    )

    assert isinstance(
        parsed,
        NvdPromotionS3TestEventV1,
    )
    assert parsed.request_id == "test-request-id"
    assert parsed.bucket == BUCKET


@pytest.mark.parametrize(
    ("status", "expected_metric"),
    [
        (
            "committed",
            "NvdPromotionCommitted",
        ),
        (
            "already_committed",
            "NvdPromotionAlreadyCommitted",
        ),
    ],
)
def test_execute_promotion_request_serializes_commit_result(
    status: str,
    expected_metric: str,
) -> None:
    """Expose exact committed persistence identity without hiding idempotency."""
    telemetry = _Telemetry()
    processor = _Processor(
        _result(status=status),
    )
    trigger = NvdPromotionS3EventParserV1(
        expected_bucket=BUCKET,
    ).parse(
        _event()
    )

    response = execute_promotion_request(
        trigger=trigger,
        processor=processor,
        telemetry=telemetry,
        request_id="lambda-request-id",
    )

    assert response["status"] == status
    assert response["update_id"] == UPDATE_ID
    assert response["silver_complete_key"] == KEY
    assert response["silver_complete_version_id"] == VERSION_ID
    assert response["committed_through_at"] == "2026-08-18T07:20:12Z"
    assert response["watermark_version_id"] == "watermark-version-2"
    assert response["watermark_etag"] == '"watermark-etag-2"'
    assert response["watermark_sha256"] == "f" * 64
    assert processor.references == [
        NvdSilverCompleteRefV1(
            key=KEY,
            version_id=VERSION_ID,
        )
    ]
    assert (
        expected_metric,
        1.0,
        "Count",
    ) in telemetry.metrics


def test_execute_promotion_request_emits_failure_and_reraises() -> None:
    """Do not convert a failed authoritative transition into success."""
    telemetry = _Telemetry()
    trigger = NvdPromotionS3EventParserV1(
        expected_bucket=BUCKET,
    ).parse(
        _event()
    )

    with pytest.raises(
        RuntimeError,
        match="promotion failed",
    ):
        execute_promotion_request(
            trigger=trigger,
            processor=_FailingProcessor(),
            telemetry=telemetry,
            request_id="lambda-request-id",
        )

    assert (
        "NvdPromotionFailure",
        1.0,
        "Count",
    ) in telemetry.metrics
    assert telemetry.exception_messages == [
        "Authoritative NVD watermark promotion failed"
    ]
