"""Unit tests for the S3 ObjectCreated inbound event adapter."""

import pytest

from opslens.transformation.epss.adapters.inbound.s3_event import (
    InvalidS3ObjectCreatedEventError,
    S3ObjectCreatedEventParser,
)

BUCKET = "opslens-test-data"


def _record(
    *,
    bucket: str = BUCKET,
    key: str = ("bronze/epss/snapshot_date%3D2026-08-15/epss_scores.csv.gz"),
    event_version: str = "2.1",
    event_source: str = "aws:s3",
    event_name: str = "ObjectCreated:Put",
    sequencer: str = "0055AED6DCD90281E5",
) -> dict[str, object]:
    """Build one deterministic S3 ObjectCreated notification record."""
    return {
        "eventVersion": event_version,
        "eventSource": event_source,
        "eventName": event_name,
        "s3": {
            "bucket": {
                "name": bucket,
            },
            "object": {
                "key": key,
                "sequencer": sequencer,
            },
        },
    }


def test_parses_and_decodes_bronze_object_created_record() -> None:
    """Parse one valid S3 ObjectCreated event and URL-decode its key."""
    parser = S3ObjectCreatedEventParser(
        expected_bucket=BUCKET,
    )

    records = parser.parse(
        {
            "Records": [
                _record(),
            ],
        }
    )

    assert len(records) == 1

    record = records[0]

    assert record.bucket == BUCKET
    assert record.key == ("bronze/epss/snapshot_date=2026-08-15/epss_scores.csv.gz")
    assert record.event_name == "ObjectCreated:Put"
    assert record.sequencer == "0055AED6DCD90281E5"


def test_preserves_multiple_record_order() -> None:
    """Parse every S3 record while preserving notification order."""
    parser = S3ObjectCreatedEventParser(
        expected_bucket=BUCKET,
    )

    records = parser.parse(
        {
            "Records": [
                _record(
                    key=("bronze/epss/snapshot_date%3D2026-08-14/epss_scores.csv.gz"),
                    sequencer="01",
                ),
                _record(
                    key=("bronze/epss/snapshot_date%3D2026-08-15/epss_scores.csv.gz"),
                    sequencer="02",
                ),
            ],
        }
    )

    assert [record.sequencer for record in records] == [
        "01",
        "02",
    ]


def test_accepts_newer_minor_event_version() -> None:
    """Accept backward-compatible S3 event minor versions."""
    parser = S3ObjectCreatedEventParser(
        expected_bucket=BUCKET,
    )

    records = parser.parse(
        {
            "Records": [
                _record(event_version="2.3"),
            ],
        }
    )

    assert len(records) == 1


@pytest.mark.parametrize(
    ("field", "value", "expected_message"),
    [
        (
            "eventVersion",
            "3.0",
            "unsupported",
        ),
        (
            "eventSource",
            "aws:sqs",
            "eventSource",
        ),
        (
            "eventName",
            "ObjectRemoved:Delete",
            "ObjectCreated",
        ),
    ],
)
def test_rejects_unsupported_event_identity(
    field: str,
    value: str,
    expected_message: str,
) -> None:
    """Reject unsupported S3 event versions, sources, and event types."""
    kwargs = {
        "eventVersion": "2.1",
        "eventSource": "aws:s3",
        "eventName": "ObjectCreated:Put",
    }
    kwargs[field] = value

    parser = S3ObjectCreatedEventParser(
        expected_bucket=BUCKET,
    )

    with pytest.raises(
        InvalidS3ObjectCreatedEventError,
        match=expected_message,
    ):
        parser.parse(
            {
                "Records": [
                    _record(
                        event_version=kwargs["eventVersion"],
                        event_source=kwargs["eventSource"],
                        event_name=kwargs["eventName"],
                    ),
                ],
            }
        )


def test_rejects_event_from_unexpected_bucket() -> None:
    """Reject notifications for any bucket other than the configured data bucket."""
    parser = S3ObjectCreatedEventParser(
        expected_bucket=BUCKET,
    )

    with pytest.raises(
        InvalidS3ObjectCreatedEventError,
        match="configured data bucket",
    ):
        parser.parse(
            {
                "Records": [
                    _record(bucket="other-bucket"),
                ],
            }
        )


def test_rejects_object_outside_bronze_prefix() -> None:
    """Reject object notifications outside the EPSS Bronze namespace."""
    parser = S3ObjectCreatedEventParser(
        expected_bucket=BUCKET,
    )

    with pytest.raises(
        InvalidS3ObjectCreatedEventError,
        match="bronze/epss/",
    ):
        parser.parse(
            {
                "Records": [
                    _record(key=("silver/epss/snapshot_date%3D2026-08-15/part-00000.parquet")),
                ],
            }
        )


@pytest.mark.parametrize(
    "event",
    [
        {},
        {"Records": []},
        {"Records": "not-a-list"},
        {"Records": [None]},
    ],
)
def test_rejects_malformed_event_structure(
    event: dict[str, object],
) -> None:
    """Reject malformed S3 notification envelopes."""
    parser = S3ObjectCreatedEventParser(
        expected_bucket=BUCKET,
    )

    with pytest.raises(
        InvalidS3ObjectCreatedEventError,
    ):
        parser.parse(event)
