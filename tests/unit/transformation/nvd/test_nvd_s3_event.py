"""Tests for strict NVD Silver Amazon S3 COMPLETE events."""

from typing import cast
from urllib.parse import quote_plus

import pytest

from opslens.transformation.nvd.adapters.inbound.s3_event import (
    InvalidNvdSilverS3EventError,
    NvdSilverS3EventParserV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)

BUCKET = "opslens-dev-data-example-us-east-1"

BOOTSTRAP_KEY = (
    "bronze/nvd/cve/bootstrap/"
    "feed_year=2026/"
    "feed_revision="
    "20260818T070012Z-" + "a" * 64 + "/manifest.json"
)

INCREMENTAL_KEY = "bronze/nvd/cve/updates/update_id=" + "b" * 64 + "/manifest.json"


def _event(
    *,
    key: str,
    version_id: str = "version-1",
    bucket: str = BUCKET,
    event_name: str = "ObjectCreated:Put",
) -> dict[str, object]:
    """Build one realistic versioned S3 ObjectCreated notification."""
    return {
        "Records": [
            {
                "eventVersion": "2.5",
                "eventSource": "aws:s3",
                "eventName": event_name,
                "s3": {
                    "bucket": {
                        "name": bucket,
                    },
                    "object": {
                        "key": quote_plus(
                            key,
                            safe="/",
                        ),
                        "size": 1107,
                        "eTag": "etag",
                        "versionId": version_id,
                        "sequencer": "001",
                    },
                },
            }
        ]
    }


def _records(
    event: dict[str, object],
) -> list[object]:
    """Return the controlled S3 records fixture with explicit typing."""
    return cast(
        list[object],
        event["Records"],
    )


def _object_data(
    event: dict[str, object],
) -> dict[str, object]:
    """Return the controlled S3 object fixture with explicit typing."""
    records = _records(event)

    record = cast(
        dict[str, object],
        records[0],
    )

    s3_data = cast(
        dict[str, object],
        record["s3"],
    )

    return cast(
        dict[str, object],
        s3_data["object"],
    )


def test_parses_exact_bootstrap_complete_coordinate() -> None:
    """Derive bootstrap source kind and exact VersionId from S3."""
    request = NvdSilverS3EventParserV1(
        expected_bucket=BUCKET,
    ).parse(
        _event(
            key=BOOTSTRAP_KEY,
            version_id="bootstrap-version-1",
        )
    )

    assert request.source_kind is NvdSilverSourceKind.BOOTSTRAP
    assert request.manifest_key == BOOTSTRAP_KEY
    assert request.manifest_version_id == "bootstrap-version-1"


def test_parses_exact_incremental_complete_coordinate() -> None:
    """Derive incremental source kind from the canonical COMPLETE key."""
    request = NvdSilverS3EventParserV1(
        expected_bucket=BUCKET,
    ).parse(
        _event(
            key=INCREMENTAL_KEY,
            version_id="incremental-version-1",
        )
    )

    assert request.source_kind is NvdSilverSourceKind.INCREMENTAL
    assert request.manifest_key == INCREMENTAL_KEY
    assert request.manifest_version_id == "incremental-version-1"


def test_decodes_url_encoded_object_key() -> None:
    """Decode the form-encoded key before canonical validation."""
    event = _event(
        key=INCREMENTAL_KEY,
    )

    object_data = _object_data(event)

    object_data["key"] = quote_plus(
        INCREMENTAL_KEY,
        safe="",
    )

    request = NvdSilverS3EventParserV1(
        expected_bucket=BUCKET,
    ).parse(
        event,
    )

    assert request.manifest_key == INCREMENTAL_KEY


def test_rejects_missing_exact_version_id() -> None:
    """Never turn an unversioned notification into runtime authority."""
    event = _event(
        key=INCREMENTAL_KEY,
    )

    object_data = _object_data(event)

    del object_data["versionId"]

    with pytest.raises(
        InvalidNvdSilverS3EventError,
        match="versionId",
    ):
        NvdSilverS3EventParserV1(
            expected_bucket=BUCKET,
        ).parse(
            event,
        )


def test_rejects_wrong_bucket() -> None:
    """Constrain the event to the configured OpsLens data bucket."""
    with pytest.raises(
        InvalidNvdSilverS3EventError,
        match="bucket",
    ):
        NvdSilverS3EventParserV1(
            expected_bucket=BUCKET,
        ).parse(
            _event(
                key=INCREMENTAL_KEY,
                bucket="unexpected-bucket",
            )
        )


def test_rejects_non_complete_object_key() -> None:
    """Only Bronze COMPLETE manifests may trigger NVD Silver."""
    page_key = "bronze/nvd/cve/updates/update_id=" + "b" * 64 + "/page_start=000000/response.json"

    with pytest.raises(
        InvalidNvdSilverS3EventError,
        match="COMPLETE",
    ):
        NvdSilverS3EventParserV1(
            expected_bucket=BUCKET,
        ).parse(
            _event(
                key=page_key,
            )
        )


def test_rejects_multiple_records() -> None:
    """Keep one heavy NVD transform per Lambda invocation."""
    event = _event(
        key=INCREMENTAL_KEY,
    )

    records = _records(event)

    records.append(
        records[0],
    )

    with pytest.raises(
        InvalidNvdSilverS3EventError,
        match="exactly one",
    ):
        NvdSilverS3EventParserV1(
            expected_bucket=BUCKET,
        ).parse(
            event,
        )


def test_rejects_non_put_event() -> None:
    """Require the same ObjectCreated operation configured in Terraform."""
    with pytest.raises(
        InvalidNvdSilverS3EventError,
        match="eventName",
    ):
        NvdSilverS3EventParserV1(
            expected_bucket=BUCKET,
        ).parse(
            _event(
                key=INCREMENTAL_KEY,
                event_name="ObjectCreated:Copy",
            )
        )


def test_accepts_s3_test_event_without_transforming() -> None:
    """Recognize the S3 destination-validation notification."""
    test_event = NvdSilverS3EventParserV1(
        expected_bucket=BUCKET,
    ).parse_test_event(
        {
            "Service": "Amazon S3",
            "Event": "s3:TestEvent",
            "Time": "2026-08-22T19:00:00Z",
            "Bucket": BUCKET,
            "RequestId": "request-1",
            "HostId": "host-1",
        }
    )

    assert test_event is not None
    assert test_event.bucket == BUCKET
    assert test_event.request_id == "request-1"
