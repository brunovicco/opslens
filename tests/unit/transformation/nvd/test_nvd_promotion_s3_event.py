"""Tests for the strict NVD promotion S3 event boundary."""

from typing import cast
from urllib.parse import quote_plus

import pytest

from opslens.transformation.nvd.adapters.inbound.promotion_s3_event import (
    InvalidNvdPromotionS3EventError,
    NvdPromotionS3EventParserV1,
)

BUCKET = "opslens-test-data"
UPDATE_ID = "a" * 64
KEY = (
    "silver/nvd/cve/schema_version=1/source_kind=incremental/"
    f"update_id={UPDATE_ID}/manifest.json"
)
VERSION_ID = "silver-complete-version-1"


def _event(
    *,
    bucket: str = BUCKET,
    key: str = KEY,
    version_id: object = VERSION_ID,
    size: object = 822,
    event_name: str = "ObjectCreated:Put",
    event_version: str = "2.1",
) -> dict[str, object]:
    """Build one S3 notification fixture."""
    return {
        "Records": [
            {
                "eventVersion": event_version,
                "eventSource": "aws:s3",
                "eventName": event_name,
                "s3": {
                    "s3SchemaVersion": "1.0",
                    "bucket": {
                        "name": bucket,
                    },
                    "object": {
                        "key": quote_plus(key, safe="/="),
                        "size": size,
                        "versionId": version_id,
                    },
                },
            }
        ]
    }


def test_parse_accepts_exact_incremental_silver_complete_put() -> None:
    """Select only the exact persisted COMPLETE coordinate from the event."""
    parsed = NvdPromotionS3EventParserV1(
        expected_bucket=BUCKET,
    ).parse(_event())

    assert parsed.bucket == BUCKET
    assert parsed.object_size_bytes == 822
    assert parsed.silver_complete.key == KEY
    assert parsed.silver_complete.version_id == VERSION_ID


def test_parse_requires_exactly_one_record() -> None:
    """Reject batched notifications so one invocation owns one CAS attempt."""
    event = _event()
    records_value = event["Records"]
    assert isinstance(records_value, list)
    records = cast(list[object], records_value)
    records.append(records[0])

    with pytest.raises(
        InvalidNvdPromotionS3EventError,
        match="exactly one record",
    ):
        NvdPromotionS3EventParserV1(
            expected_bucket=BUCKET,
        ).parse(event)


def test_parse_requires_configured_bucket() -> None:
    """Reject notifications from any other S3 bucket."""
    with pytest.raises(
        InvalidNvdPromotionS3EventError,
        match="configured data bucket",
    ):
        NvdPromotionS3EventParserV1(
            expected_bucket=BUCKET,
        ).parse(
            _event(bucket="other-bucket"),
        )


def test_parse_requires_object_created_put() -> None:
    """Reject copy, multipart-complete, restore, and other event names."""
    with pytest.raises(
        InvalidNvdPromotionS3EventError,
        match="ObjectCreated:Put",
    ):
        NvdPromotionS3EventParserV1(
            expected_bucket=BUCKET,
        ).parse(
            _event(event_name="ObjectCreated:CompleteMultipartUpload"),
        )


def test_parse_requires_version_id() -> None:
    """Never allow a current-key read to replace exact-version evidence."""
    with pytest.raises(
        InvalidNvdPromotionS3EventError,
        match="versionId",
    ):
        NvdPromotionS3EventParserV1(
            expected_bucket=BUCKET,
        ).parse(
            _event(version_id=None),
        )


def test_parse_rejects_non_incremental_silver_complete_key() -> None:
    """Bootstrap Silver is not an authoritative incremental candidate."""
    bootstrap_key = (
        "silver/nvd/cve/schema_version=1/source_kind=bootstrap/"
        "feed_year=2026/feed_revision=test/manifest.json"
    )

    with pytest.raises(
        InvalidNvdPromotionS3EventError,
        match="canonical incremental",
    ):
        NvdPromotionS3EventParserV1(
            expected_bucket=BUCKET,
        ).parse(
            _event(key=bootstrap_key),
        )


def test_parse_rejects_noncanonical_update_id() -> None:
    """Require the logical update identity to remain a lowercase SHA-256."""
    bad_key = (
        "silver/nvd/cve/schema_version=1/source_kind=incremental/"
        f"update_id={'A' * 64}/manifest.json"
    )

    with pytest.raises(
        InvalidNvdPromotionS3EventError,
        match="canonical incremental",
    ):
        NvdPromotionS3EventParserV1(
            expected_bucket=BUCKET,
        ).parse(
            _event(key=bad_key),
        )


def test_parse_rejects_invalid_percent_escape() -> None:
    """Fail closed instead of normalizing malformed URL encoding."""
    event = _event()
    records_value = event["Records"]
    assert isinstance(records_value, list)
    records = cast(list[object], records_value)

    record_value = records[0]
    assert isinstance(record_value, dict)
    record = cast(dict[str, object], record_value)

    s3_value = record["s3"]
    assert isinstance(s3_value, dict)
    s3_data = cast(dict[str, object], s3_value)

    object_value = s3_data["object"]
    assert isinstance(object_value, dict)
    object_data = cast(dict[str, object], object_value)
    object_data["key"] = "silver/nvd/%ZZ/manifest.json"

    with pytest.raises(
        InvalidNvdPromotionS3EventError,
        match="invalid percent escape",
    ):
        NvdPromotionS3EventParserV1(
            expected_bucket=BUCKET,
        ).parse(event)


def test_parse_requires_supported_s3_event_version_family() -> None:
    """Reject an event schema family that the parser was not written for."""
    with pytest.raises(
        InvalidNvdPromotionS3EventError,
        match=r"supported S3 2\.x family",
    ):
        NvdPromotionS3EventParserV1(
            expected_bucket=BUCKET,
        ).parse(
            _event(event_version="3.0"),
        )


def test_parse_requires_positive_object_size() -> None:
    """Reject impossible empty COMPLETE object evidence at the boundary."""
    with pytest.raises(
        InvalidNvdPromotionS3EventError,
        match="positive integer",
    ):
        NvdPromotionS3EventParserV1(
            expected_bucket=BUCKET,
        ).parse(
            _event(size=0),
        )


def test_parse_test_event_accepts_expected_bucket_without_runtime_evidence() -> None:
    """Handle S3 configuration test events without fabricating object evidence."""
    parsed = NvdPromotionS3EventParserV1(
        expected_bucket=BUCKET,
    ).parse_test_event(
        {
            "Event": "s3:TestEvent",
            "Bucket": BUCKET,
            "RequestId": "s3-test-request-id",
        }
    )

    assert parsed is not None
    assert parsed.bucket == BUCKET
    assert parsed.request_id == "s3-test-request-id"
