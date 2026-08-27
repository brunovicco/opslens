"""Tests for the permanent NVD analytics projection inbound boundary."""

from typing import cast
from urllib.parse import quote_plus

import pytest

from opslens.transformation.nvd.adapters.inbound.analytics_projection_invocation import (
    InvalidNvdAnalyticsProjectionInvocationError,
    NvdAnalyticsBootstrapSeedInvocationV1,
    NvdAnalyticsIncrementalWatermarkEventV1,
    NvdAnalyticsProjectionInvocationParserV1,
    NvdAnalyticsS3TestEventV1,
)
from opslens.transformation.nvd.application.analytics_projection_evidence_loader import (
    NVD_ANALYTICS_INCREMENTAL_WATERMARK_KEY,
    NVD_ANALYTICS_MAX_WATERMARK_BYTES,
)

BUCKET = "opslens-test-data"
WATERMARK_VERSION = "watermark-version"
FEED_REVISION = f"20260822T070013Z-{'a' * 64}"
BOOTSTRAP_KEY = (
    "silver/nvd/cve/schema_version=1/source_kind=bootstrap/"
    "feed_year=2026/"
    f"feed_revision={FEED_REVISION}/manifest.json"
)


def _parser() -> NvdAnalyticsProjectionInvocationParserV1:
    """Build one parser with exact production-style coordinates."""
    return NvdAnalyticsProjectionInvocationParserV1(
        expected_bucket=BUCKET,
    )


def _s3_event(
    *,
    bucket: str = BUCKET,
    key: str = NVD_ANALYTICS_INCREMENTAL_WATERMARK_KEY,
    version_id: str = WATERMARK_VERSION,
    size: int = 2048,
    event_name: str = "ObjectCreated:Put",
    records: int = 1,
) -> dict[str, object]:
    """Build one minimal versioned S3 ObjectCreated notification."""
    record: dict[str, object] = {
        "eventVersion": "2.1",
        "eventSource": "aws:s3",
        "eventName": event_name,
        "s3": {
            "s3SchemaVersion": "1.0",
            "bucket": {
                "name": bucket,
            },
            "object": {
                "key": quote_plus(key),
                "size": size,
                "versionId": version_id,
            },
        },
    }
    return {
        "Records": [record for _ in range(records)],
    }


def test_parse_incremental_accepts_exact_versioned_watermark_put() -> None:
    """Select exact watermark VersionId only from the canonical S3 trigger."""
    parsed = _parser().parse(_s3_event())

    assert isinstance(
        parsed,
        NvdAnalyticsIncrementalWatermarkEventV1,
    )
    assert parsed.bucket == BUCKET
    assert parsed.watermark_key == NVD_ANALYTICS_INCREMENTAL_WATERMARK_KEY
    assert parsed.watermark_version_id == WATERMARK_VERSION
    assert parsed.object_size_bytes == 2048


def test_parse_incremental_rejects_wrong_watermark_key() -> None:
    """Do not allow arbitrary control objects to become analytics authority."""
    with pytest.raises(
        InvalidNvdAnalyticsProjectionInvocationError,
        match="authoritative watermark",
    ):
        _parser().parse(
            _s3_event(
                key="control/nvd/cve/incremental/other.json"
            )
        )


def test_parse_incremental_requires_version_id() -> None:
    """Reject S3 events that cannot pin the exact watermark object version."""
    event = _s3_event()
    records = cast(list[object], event["Records"])
    record = cast(dict[str, object], records[0])
    s3_data = cast(dict[str, object], record["s3"])
    object_data = cast(dict[str, object], s3_data["object"])
    object_data.pop("versionId")

    with pytest.raises(
        InvalidNvdAnalyticsProjectionInvocationError,
        match="versionId",
    ):
        _parser().parse(event)


def test_parse_incremental_rejects_multiple_records() -> None:
    """Keep one Lambda invocation bound to one authoritative event only."""
    with pytest.raises(
        InvalidNvdAnalyticsProjectionInvocationError,
        match="exactly one record",
    ):
        _parser().parse(
            _s3_event(records=2)
        )


def test_parse_incremental_rejects_non_put_event() -> None:
    """Accept only the ObjectCreated:Put transition owned by watermark promotion."""
    with pytest.raises(
        InvalidNvdAnalyticsProjectionInvocationError,
        match="ObjectCreated:Put",
    ):
        _parser().parse(
            _s3_event(
                event_name="ObjectCreated:Copy"
            )
        )


def test_parse_incremental_rejects_watermark_above_byte_bound() -> None:
    """Reject oversized event evidence before exact S3 reading."""
    with pytest.raises(
        InvalidNvdAnalyticsProjectionInvocationError,
        match="byte bound",
    ):
        _parser().parse(
            _s3_event(
                size=NVD_ANALYTICS_MAX_WATERMARK_BYTES + 1
            )
        )


def test_parse_bootstrap_accepts_explicit_exact_complete_seed() -> None:
    """Keep Bootstrap analytics eligibility explicit and exact-versioned."""
    parsed = _parser().parse(
        {
            "mode": "bootstrap_seed",
            "silver_complete_key": BOOTSTRAP_KEY,
            "silver_complete_version_id": "bootstrap-complete-version",
        }
    )

    assert isinstance(
        parsed,
        NvdAnalyticsBootstrapSeedInvocationV1,
    )
    assert parsed.silver_complete_key == BOOTSTRAP_KEY
    assert (
        parsed.silver_complete_version_id
        == "bootstrap-complete-version"
    )


def test_parse_bootstrap_rejects_extra_fields() -> None:
    """Reject hidden authority coordinates in the explicit Bootstrap shape."""
    with pytest.raises(
        InvalidNvdAnalyticsProjectionInvocationError,
        match="must contain exactly",
    ):
        _parser().parse(
            {
                "mode": "bootstrap_seed",
                "silver_complete_key": BOOTSTRAP_KEY,
                "silver_complete_version_id": "bootstrap-complete-version",
                "source_parquet_key": "untrusted.parquet",
            }
        )


def test_parse_rejects_mixed_s3_and_explicit_mode() -> None:
    """Fail closed instead of choosing precedence between trigger types."""
    event = _s3_event()
    event["mode"] = "bootstrap_seed"

    with pytest.raises(
        InvalidNvdAnalyticsProjectionInvocationError,
        match="cannot mix",
    ):
        _parser().parse(event)


def test_parse_s3_test_event_does_not_select_authority() -> None:
    """Accept bucket-notification test traffic without projection work."""
    parsed = _parser().parse(
        {
            "Event": "s3:TestEvent",
            "Bucket": BUCKET,
            "RequestId": "test-request-id",
        }
    )

    assert isinstance(
        parsed,
        NvdAnalyticsS3TestEventV1,
    )
    assert parsed.bucket == BUCKET
    assert parsed.request_id == "test-request-id"
