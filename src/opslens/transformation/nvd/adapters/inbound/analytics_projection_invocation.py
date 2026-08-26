"""Strict inbound boundary for permanent NVD analytics projection."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast
from urllib.parse import unquote_plus

from opslens.transformation.nvd.application.analytics_projection_evidence_loader import (
    NVD_ANALYTICS_INCREMENTAL_WATERMARK_KEY,
    NVD_ANALYTICS_MAX_WATERMARK_BYTES,
)

_EVENT_VERSION_PATTERN = re.compile(r"^2\.[0-9]+$")
_PERCENT_ESCAPE_PATTERN = re.compile(r"%[0-9A-Fa-f]{2}")
_BOOTSTRAP_COMPLETE_KEY_PATTERN = re.compile(
    r"^silver/nvd/cve/schema_version=1/source_kind=bootstrap/"
    r"feed_year=[0-9]{4}/"
    r"feed_revision=[0-9]{8}T[0-9]{6}Z-[0-9a-f]{64}/"
    r"manifest\.json$"
)


class InvalidNvdAnalyticsProjectionInvocationError(ValueError):
    """Raised when an invocation cannot select analytics authority safely."""


@dataclass(frozen=True, slots=True)
class NvdAnalyticsIncrementalWatermarkEventV1:
    """Represent one exact authoritative-watermark ObjectCreated trigger."""

    bucket: str
    watermark_key: str
    watermark_version_id: str
    object_size_bytes: int


@dataclass(frozen=True, slots=True)
class NvdAnalyticsBootstrapSeedInvocationV1:
    """Represent one explicit exact Bootstrap Silver COMPLETE seed request."""

    silver_complete_key: str
    silver_complete_version_id: str


@dataclass(frozen=True, slots=True)
class NvdAnalyticsS3TestEventV1:
    """Represent an accepted Amazon S3 test notification."""

    bucket: str
    request_id: str


type NvdAnalyticsProjectionInvocationV1 = (
    NvdAnalyticsIncrementalWatermarkEventV1
    | NvdAnalyticsBootstrapSeedInvocationV1
    | NvdAnalyticsS3TestEventV1
)


class NvdAnalyticsProjectionInvocationParserV1:
    """Parse only the two permanent analytics projection trigger shapes."""

    EXPECTED_EVENT_NAME = "ObjectCreated:Put"
    EXPECTED_EVENT_SOURCE = "aws:s3"
    EXPECTED_S3_SCHEMA_VERSION = "1.0"
    EXPECTED_TEST_EVENT = "s3:TestEvent"
    BOOTSTRAP_MODE = "bootstrap_seed"

    def __init__(
        self,
        *,
        expected_bucket: str,
        expected_watermark_key: str = NVD_ANALYTICS_INCREMENTAL_WATERMARK_KEY,
    ) -> None:
        """Initialize one exact data-bucket and watermark allowlist."""
        bucket = self._require_configured_string(
            expected_bucket,
            label="expected bucket",
        )
        watermark_key = self._require_configured_string(
            expected_watermark_key,
            label="expected watermark key",
        )

        if watermark_key != NVD_ANALYTICS_INCREMENTAL_WATERMARK_KEY:
            raise ValueError(
                "NVD analytics incremental watermark key must remain canonical."
            )

        self._expected_bucket = bucket
        self._expected_watermark_key = watermark_key

    def parse(
        self,
        event: Mapping[str, object],
    ) -> NvdAnalyticsProjectionInvocationV1:
        """Resolve S3 test, incremental watermark, or explicit Bootstrap seed."""
        test_event = self._parse_test_event(event)
        if test_event is not None:
            return test_event

        has_records = "Records" in event
        has_mode = "mode" in event

        if has_records and has_mode:
            raise InvalidNvdAnalyticsProjectionInvocationError(
                "NVD analytics invocation cannot mix S3 Records with explicit mode."
            )

        if has_mode:
            return self._parse_bootstrap_seed(event)

        if has_records:
            return self._parse_incremental_s3_event(event)

        raise InvalidNvdAnalyticsProjectionInvocationError(
            "NVD analytics invocation is neither an S3 event nor bootstrap_seed."
        )

    def _parse_test_event(
        self,
        event: Mapping[str, object],
    ) -> NvdAnalyticsS3TestEventV1 | None:
        """Accept only the S3 test notification for the configured bucket."""
        if event.get("Event") != self.EXPECTED_TEST_EVENT:
            return None

        if "Records" in event or "mode" in event:
            raise InvalidNvdAnalyticsProjectionInvocationError(
                "NVD analytics S3 test event cannot contain runtime trigger fields."
            )

        bucket = self._require_exact_string(
            event.get("Bucket"),
            path="Bucket",
        )
        if bucket != self._expected_bucket:
            raise InvalidNvdAnalyticsProjectionInvocationError(
                "NVD analytics S3 test bucket does not match configuration."
            )

        request_id = self._require_exact_string(
            event.get("RequestId"),
            path="RequestId",
        )

        return NvdAnalyticsS3TestEventV1(
            bucket=bucket,
            request_id=request_id,
        )

    def _parse_bootstrap_seed(
        self,
        event: Mapping[str, object],
    ) -> NvdAnalyticsBootstrapSeedInvocationV1:
        """Parse one explicit exact Bootstrap Silver COMPLETE coordinate."""
        allowed_keys = {
            "mode",
            "silver_complete_key",
            "silver_complete_version_id",
        }
        if set(event) != allowed_keys:
            raise InvalidNvdAnalyticsProjectionInvocationError(
                "NVD analytics bootstrap_seed must contain exactly mode, "
                "silver_complete_key, and silver_complete_version_id."
            )

        mode = self._require_exact_string(
            event.get("mode"),
            path="mode",
        )
        if mode != self.BOOTSTRAP_MODE:
            raise InvalidNvdAnalyticsProjectionInvocationError(
                f"NVD analytics mode must be {self.BOOTSTRAP_MODE!r}."
            )

        key = self._require_exact_string(
            event.get("silver_complete_key"),
            path="silver_complete_key",
        )
        if _BOOTSTRAP_COMPLETE_KEY_PATTERN.fullmatch(key) is None:
            raise InvalidNvdAnalyticsProjectionInvocationError(
                "NVD analytics bootstrap_seed key is not a canonical "
                "Bootstrap Silver COMPLETE path."
            )

        version_id = self._require_exact_string(
            event.get("silver_complete_version_id"),
            path="silver_complete_version_id",
        )

        return NvdAnalyticsBootstrapSeedInvocationV1(
            silver_complete_key=key,
            silver_complete_version_id=version_id,
        )

    def _parse_incremental_s3_event(
        self,
        event: Mapping[str, object],
    ) -> NvdAnalyticsIncrementalWatermarkEventV1:
        """Parse exactly one canonical authoritative-watermark Put event."""
        records_value = event.get("Records")
        if not isinstance(records_value, list):
            raise InvalidNvdAnalyticsProjectionInvocationError(
                "NVD analytics S3 event must contain a Records array."
            )

        records = cast(list[object], records_value)
        if len(records) != 1:
            raise InvalidNvdAnalyticsProjectionInvocationError(
                "NVD analytics S3 event must contain exactly one record."
            )

        record_value = records[0]
        if not isinstance(record_value, dict):
            raise InvalidNvdAnalyticsProjectionInvocationError(
                "Records[0] must be an object."
            )
        record = cast(dict[str, object], record_value)
        path = "Records[0]"

        event_version = self._require_exact_string(
            record.get("eventVersion"),
            path=f"{path}.eventVersion",
        )
        if _EVENT_VERSION_PATTERN.fullmatch(event_version) is None:
            raise InvalidNvdAnalyticsProjectionInvocationError(
                f"{path}.eventVersion must be from the supported S3 2.x family."
            )

        event_source = self._require_exact_string(
            record.get("eventSource"),
            path=f"{path}.eventSource",
        )
        if event_source != self.EXPECTED_EVENT_SOURCE:
            raise InvalidNvdAnalyticsProjectionInvocationError(
                f"{path}.eventSource must be {self.EXPECTED_EVENT_SOURCE!r}."
            )

        event_name = self._require_exact_string(
            record.get("eventName"),
            path=f"{path}.eventName",
        )
        if event_name != self.EXPECTED_EVENT_NAME:
            raise InvalidNvdAnalyticsProjectionInvocationError(
                f"{path}.eventName must be {self.EXPECTED_EVENT_NAME!r}."
            )

        s3_value = record.get("s3")
        if not isinstance(s3_value, dict):
            raise InvalidNvdAnalyticsProjectionInvocationError(
                f"{path}.s3 must be an object."
            )
        s3_data = cast(dict[str, object], s3_value)

        schema_version = self._require_exact_string(
            s3_data.get("s3SchemaVersion"),
            path=f"{path}.s3.s3SchemaVersion",
        )
        if schema_version != self.EXPECTED_S3_SCHEMA_VERSION:
            raise InvalidNvdAnalyticsProjectionInvocationError(
                f"{path}.s3.s3SchemaVersion must be "
                f"{self.EXPECTED_S3_SCHEMA_VERSION!r}."
            )

        bucket_value = s3_data.get("bucket")
        if not isinstance(bucket_value, dict):
            raise InvalidNvdAnalyticsProjectionInvocationError(
                f"{path}.s3.bucket must be an object."
            )
        bucket_data = cast(dict[str, object], bucket_value)
        bucket = self._require_exact_string(
            bucket_data.get("name"),
            path=f"{path}.s3.bucket.name",
        )
        if bucket != self._expected_bucket:
            raise InvalidNvdAnalyticsProjectionInvocationError(
                f"{path}.s3.bucket.name does not match the configured data bucket."
            )

        object_value = s3_data.get("object")
        if not isinstance(object_value, dict):
            raise InvalidNvdAnalyticsProjectionInvocationError(
                f"{path}.s3.object must be an object."
            )
        object_data = cast(dict[str, object], object_value)

        encoded_key = self._require_exact_string(
            object_data.get("key"),
            path=f"{path}.s3.object.key",
        )
        decoded_key = self._decode_s3_key(
            encoded_key,
            path=f"{path}.s3.object.key",
        )
        if decoded_key != self._expected_watermark_key:
            raise InvalidNvdAnalyticsProjectionInvocationError(
                f"{path}.s3.object.key is not the canonical NVD authoritative watermark."
            )

        version_id = self._require_exact_string(
            object_data.get("versionId"),
            path=f"{path}.s3.object.versionId",
        )

        size_value = object_data.get("size")
        if (
            type(size_value) is not int
            or size_value <= 0
            or size_value > NVD_ANALYTICS_MAX_WATERMARK_BYTES
        ):
            raise InvalidNvdAnalyticsProjectionInvocationError(
                f"{path}.s3.object.size must be a positive integer within "
                "the analytics watermark byte bound."
            )

        return NvdAnalyticsIncrementalWatermarkEventV1(
            bucket=bucket,
            watermark_key=decoded_key,
            watermark_version_id=version_id,
            object_size_bytes=size_value,
        )

    @staticmethod
    def _require_configured_string(
        value: str,
        *,
        label: str,
    ) -> str:
        """Require exact non-empty composition configuration."""
        if not value or value != value.strip():
            raise ValueError(
                f"NVD analytics {label} must be exact and non-empty."
            )
        return value

    @staticmethod
    def _require_exact_string(
        value: object,
        *,
        path: str,
    ) -> str:
        """Require a non-empty string without hidden boundary whitespace."""
        if not isinstance(value, str) or not value or value != value.strip():
            raise InvalidNvdAnalyticsProjectionInvocationError(
                f"{path} must be an exact non-empty string."
            )
        return value

    @staticmethod
    def _decode_s3_key(
        encoded_key: str,
        *,
        path: str,
    ) -> str:
        """URL-decode an S3 notification key with strict percent escapes."""
        index = 0
        while index < len(encoded_key):
            if encoded_key[index] != "%":
                index += 1
                continue

            escape = encoded_key[index : index + 3]
            if _PERCENT_ESCAPE_PATTERN.fullmatch(escape) is None:
                raise InvalidNvdAnalyticsProjectionInvocationError(
                    f"{path} contains an invalid percent escape."
                )
            index += 3

        try:
            decoded = unquote_plus(
                encoded_key,
                encoding="utf-8",
                errors="strict",
            )
        except UnicodeDecodeError as exc:
            raise InvalidNvdAnalyticsProjectionInvocationError(
                f"{path} is not valid URL-encoded UTF-8."
            ) from exc

        if not decoded:
            raise InvalidNvdAnalyticsProjectionInvocationError(
                f"{path} decodes to an empty key."
            )

        return decoded
