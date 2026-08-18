"""Unit tests for the strict CISA KEV S3 event parser."""

from datetime import date

import pytest

from opslens.transformation.kev.adapters.inbound.s3_event import (
    InvalidKevS3EventError,
    KevS3EventParser,
)

BUCKET = "opslens-dev-data-487757851499-us-east-1"

CANONICAL_KEY = "bronze/kev/snapshot_date=2026-08-17/known_exploited_vulnerabilities.json"

ENCODED_KEY = "bronze/kev/snapshot_date%3D2026-08-17/known_exploited_vulnerabilities.json"


def _record(
    *,
    bucket: str = BUCKET,
    key: str = ENCODED_KEY,
    event_version: str = "2.1",
    event_source: str = "aws:s3",
    event_name: str = "ObjectCreated:Put",
    version_id: object = "version-123",
    etag: object = "4d6ebe76c67bfe50649db3de0ebc1d6a",
    size: object = 1_583_171,
    sequencer: object = "0068A13F1234567890",
) -> dict[str, object]:
    """Build one representative S3 ObjectCreated notification record."""
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
                "size": size,
                "eTag": etag,
                "versionId": version_id,
                "sequencer": sequencer,
            },
        },
    }


def _event(
    *records: dict[str, object],
) -> dict[str, object]:
    """Build a regular S3 notification containing supplied records."""
    return {
        "Records": list(records or (_record(),)),
    }


def test_parses_canonical_versioned_kev_object_reference() -> None:
    """Parse all evidence references required by KEV Silver runtime."""
    parser = KevS3EventParser(expected_bucket=BUCKET)

    references = parser.parse(_event())

    assert len(references) == 1

    reference = references[0]

    assert reference.bucket == BUCKET
    assert reference.key == CANONICAL_KEY
    assert reference.version_id == "version-123"
    assert reference.etag == "4d6ebe76c67bfe50649db3de0ebc1d6a"
    assert reference.size_bytes == 1_583_171
    assert reference.snapshot_date == date(2026, 8, 17)
    assert reference.event_name == "ObjectCreated:Put"
    assert reference.sequencer == "0068A13F1234567890"


@pytest.mark.parametrize(
    "event_version",
    [
        "2.1",
        "2.2",
        "2.3",
        "2.4",
        "2.5",
        "2.99",
    ],
)
def test_accepts_supported_event_minor_versions(
    event_version: str,
) -> None:
    """Accept compatible S3 notification minor-version evolution."""
    parser = KevS3EventParser(expected_bucket=BUCKET)

    references = parser.parse(
        _event(
            _record(event_version=event_version),
        )
    )

    assert len(references) == 1


@pytest.mark.parametrize(
    "event_version",
    [
        "2.0",
        "3.0",
        "invalid",
    ],
)
def test_rejects_unsupported_event_versions(
    event_version: str,
) -> None:
    """Reject incompatible S3 event schema versions."""
    parser = KevS3EventParser(expected_bucket=BUCKET)

    with pytest.raises(
        InvalidKevS3EventError,
        match="eventVersion",
    ):
        parser.parse(
            _event(
                _record(event_version=event_version),
            )
        )


def test_rejects_wrong_event_source() -> None:
    """Reject events not produced by Amazon S3."""
    parser = KevS3EventParser(expected_bucket=BUCKET)

    with pytest.raises(
        InvalidKevS3EventError,
        match="eventSource",
    ):
        parser.parse(
            _event(
                _record(event_source="aws:sns"),
            )
        )


@pytest.mark.parametrize(
    "event_name",
    [
        "ObjectCreated:Copy",
        "ObjectCreated:Post",
        "ObjectCreated:CompleteMultipartUpload",
        "ObjectRemoved:Delete",
    ],
)
def test_rejects_non_put_events(
    event_name: str,
) -> None:
    """Accept only the PutObject creation path used by KEV Bronze."""
    parser = KevS3EventParser(expected_bucket=BUCKET)

    with pytest.raises(
        InvalidKevS3EventError,
        match="eventName",
    ):
        parser.parse(
            _event(
                _record(event_name=event_name),
            )
        )


def test_rejects_unexpected_bucket() -> None:
    """Reject an object reference from any bucket outside the contract."""
    parser = KevS3EventParser(expected_bucket=BUCKET)

    with pytest.raises(
        InvalidKevS3EventError,
        match="configured data bucket",
    ):
        parser.parse(
            _event(
                _record(bucket="unexpected-bucket"),
            )
        )


@pytest.mark.parametrize(
    "key",
    [
        ("bronze/kev/snapshot_date%3D2026-08-17/different.json"),
        ("bronze/epss/snapshot_date%3D2026-08-17/known_exploited_vulnerabilities.json"),
        ("bronze/kev/snapshot_date%3Dnot-a-date/known_exploited_vulnerabilities.json"),
        ("silver/kev/snapshot_date%3D2026-08-17/known_exploited_vulnerabilities.json"),
    ],
)
def test_rejects_noncanonical_object_key(
    key: str,
) -> None:
    """Reject objects outside the exact KEV Bronze key contract."""
    parser = KevS3EventParser(expected_bucket=BUCKET)

    with pytest.raises(
        InvalidKevS3EventError,
        match=r"object\.key",
    ):
        parser.parse(
            _event(
                _record(key=key),
            )
        )


@pytest.mark.parametrize(
    ("version_id", "etag", "message"),
    [
        (None, "4d6ebe76c67bfe50649db3de0ebc1d6a", "versionId"),
        ("", "4d6ebe76c67bfe50649db3de0ebc1d6a", "versionId"),
        ("version-123", None, "eTag"),
        ("version-123", "", "eTag"),
    ],
)
def test_rejects_missing_object_identity_evidence(
    version_id: object,
    etag: object,
    message: str,
) -> None:
    """Reject events missing immutable object identity evidence."""
    parser = KevS3EventParser(expected_bucket=BUCKET)

    with pytest.raises(
        InvalidKevS3EventError,
        match=message,
    ):
        parser.parse(
            _event(
                _record(
                    version_id=version_id,
                    etag=etag,
                ),
            )
        )


@pytest.mark.parametrize(
    "size",
    [
        None,
        0,
        -1,
        "1583171",
        True,
    ],
)
def test_rejects_invalid_object_size(
    size: object,
) -> None:
    """Reject missing, non-numeric, or non-positive object sizes."""
    parser = KevS3EventParser(expected_bucket=BUCKET)

    with pytest.raises(
        InvalidKevS3EventError,
        match="positive integer",
    ):
        parser.parse(
            _event(
                _record(size=size),
            )
        )


def test_allows_missing_sequencer() -> None:
    """Treat the event sequencer as optional operational evidence."""
    parser = KevS3EventParser(expected_bucket=BUCKET)

    reference = parser.parse(
        _event(
            _record(sequencer=None),
        )
    )[0]

    assert reference.sequencer is None


def test_preserves_multiple_records_in_source_order() -> None:
    """Preserve record ordering when an event contains multiple entries."""
    parser = KevS3EventParser(expected_bucket=BUCKET)

    references = parser.parse(
        _event(
            _record(version_id="version-1"),
            _record(version_id="version-2"),
        )
    )

    assert [reference.version_id for reference in references] == [
        "version-1",
        "version-2",
    ]


def test_parses_valid_s3_test_event() -> None:
    """Recognize the distinct S3 notification test-event shape."""
    parser = KevS3EventParser(expected_bucket=BUCKET)

    result = parser.parse_test_event(
        {
            "Service": "Amazon S3",
            "Event": "s3:TestEvent",
            "Bucket": BUCKET,
            "RequestId": "request-123",
        }
    )

    assert result is not None
    assert result.bucket == BUCKET
    assert result.request_id == "request-123"


def test_regular_event_is_not_a_test_event() -> None:
    """Return None when test-event parsing receives a regular event."""
    parser = KevS3EventParser(expected_bucket=BUCKET)

    assert parser.parse_test_event(_event()) is None


def test_rejects_test_event_from_unexpected_bucket() -> None:
    """Reject S3 test notifications for any other data bucket."""
    parser = KevS3EventParser(expected_bucket=BUCKET)

    with pytest.raises(
        InvalidKevS3EventError,
        match="configured data bucket",
    ):
        parser.parse_test_event(
            {
                "Service": "Amazon S3",
                "Event": "s3:TestEvent",
                "Bucket": "unexpected-bucket",
                "RequestId": "request-123",
            }
        )


def test_rejects_empty_records_list() -> None:
    """Reject regular S3 notifications without object records."""
    parser = KevS3EventParser(expected_bucket=BUCKET)

    with pytest.raises(
        InvalidKevS3EventError,
        match="non-empty Records",
    ):
        parser.parse(
            {
                "Records": [],
            }
        )
