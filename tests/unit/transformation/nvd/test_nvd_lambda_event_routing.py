"""Tests for NVD Silver Lambda event-shape routing."""

from opslens.transformation.nvd.adapters.inbound.s3_event import (
    NvdS3TestEvent,
    NvdSilverS3EventParserV1,
)
from opslens.transformation.nvd.application.runtime_models import (
    NvdSilverRuntimeRequestV1,
)
from opslens.transformation.nvd.lambda_handler import (
    parse_lambda_event,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)

BUCKET = "opslens-dev-data-example-us-east-1"
UPDATE_ID = "a" * 64

MANIFEST_KEY = f"bronze/nvd/cve/updates/update_id={UPDATE_ID}/manifest.json"


def test_preserves_explicit_invocation_envelope() -> None:
    """Keep the direct validation route available after S3 eventing."""
    parsed = parse_lambda_event(
        event={
            "schema_version": "1",
            "source_kind": "incremental",
            "manifest_key": MANIFEST_KEY,
            "manifest_version_id": "direct-version-1",
        },
        s3_event_parser=None,
    )

    assert isinstance(
        parsed,
        NvdSilverRuntimeRequestV1,
    )

    assert parsed.source_kind is NvdSilverSourceKind.INCREMENTAL
    assert parsed.manifest_key == MANIFEST_KEY
    assert parsed.manifest_version_id == "direct-version-1"


def test_routes_s3_event_into_same_runtime_request() -> None:
    """Translate an S3 event into the existing runtime request model."""
    parsed = parse_lambda_event(
        event={
            "Records": [
                {
                    "eventVersion": "2.5",
                    "eventSource": "aws:s3",
                    "eventName": "ObjectCreated:Put",
                    "s3": {
                        "bucket": {
                            "name": BUCKET,
                        },
                        "object": {
                            "key": MANIFEST_KEY,
                            "size": 100,
                            "versionId": "s3-version-1",
                        },
                    },
                }
            ]
        },
        s3_event_parser=NvdSilverS3EventParserV1(
            expected_bucket=BUCKET,
        ),
    )

    assert isinstance(
        parsed,
        NvdSilverRuntimeRequestV1,
    )

    assert parsed.source_kind is NvdSilverSourceKind.INCREMENTAL
    assert parsed.manifest_key == MANIFEST_KEY
    assert parsed.manifest_version_id == "s3-version-1"


def test_routes_s3_test_event_without_runtime_request() -> None:
    """Do not initialize the heavy transformation for an S3 test event."""
    parsed = parse_lambda_event(
        event={
            "Service": "Amazon S3",
            "Event": "s3:TestEvent",
            "Bucket": BUCKET,
            "RequestId": "test-request-1",
        },
        s3_event_parser=NvdSilverS3EventParserV1(
            expected_bucket=BUCKET,
        ),
    )

    assert isinstance(
        parsed,
        NvdS3TestEvent,
    )

    assert parsed.request_id == "test-request-1"
