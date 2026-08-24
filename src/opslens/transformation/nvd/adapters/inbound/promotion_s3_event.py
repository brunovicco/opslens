"""Strict Amazon S3 event boundary for NVD watermark promotion."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast
from urllib.parse import unquote_plus

from opslens.transformation.nvd.application.watermark_promotion_evidence_loader import (
    NvdSilverCompleteRefV1,
)

_UPDATE_ID_PATTERN = r"[0-9a-f]{64}"
_SILVER_COMPLETE_KEY_PATTERN = re.compile(
    rf"^silver/nvd/cve/schema_version=1/source_kind=incremental/"
    rf"update_id=({_UPDATE_ID_PATTERN})/manifest\.json$"
)
_EVENT_VERSION_PATTERN = re.compile(r"^2\.[0-9]+$")
_PERCENT_ESCAPE_PATTERN = re.compile(r"%[0-9A-Fa-f]{2}")


class InvalidNvdPromotionS3EventError(ValueError):
    """Raised when an S3 notification cannot select promotion evidence safely."""


@dataclass(frozen=True, slots=True)
class NvdPromotionS3ObjectCreatedV1:
    """Represent one validated S3 trigger for exact Silver COMPLETE evidence."""

    bucket: str
    silver_complete: NvdSilverCompleteRefV1
    object_size_bytes: int


@dataclass(frozen=True, slots=True)
class NvdPromotionS3TestEventV1:
    """Represent an accepted Amazon S3 test notification."""

    bucket: str
    request_id: str


class NvdPromotionS3EventParserV1:
    """Parse only the exact S3 notification shape allowed for promotion."""

    EXPECTED_EVENT_NAME = "ObjectCreated:Put"
    EXPECTED_EVENT_SOURCE = "aws:s3"
    EXPECTED_S3_SCHEMA_VERSION = "1.0"
    EXPECTED_TEST_EVENT = "s3:TestEvent"

    def __init__(
        self,
        *,
        expected_bucket: str,
    ) -> None:
        """Initialize the strict event boundary with one allowed data bucket."""
        normalized = expected_bucket.strip()
        if not normalized:
            raise ValueError(
                "NVD promotion expected S3 bucket cannot be empty."
            )

        self._expected_bucket = normalized

    def parse_test_event(
        self,
        event: Mapping[str, object],
    ) -> NvdPromotionS3TestEventV1 | None:
        """Parse the special S3 test notification without loading evidence."""
        if event.get("Event") != self.EXPECTED_TEST_EVENT:
            return None

        bucket = self._require_exact_string(
            event.get("Bucket"),
            path="Bucket",
        )
        if bucket != self._expected_bucket:
            raise InvalidNvdPromotionS3EventError(
                "NVD promotion S3 test event bucket does not match configuration."
            )

        request_id = self._require_exact_string(
            event.get("RequestId"),
            path="RequestId",
        )

        return NvdPromotionS3TestEventV1(
            bucket=bucket,
            request_id=request_id,
        )

    def parse(
        self,
        event: Mapping[str, object],
    ) -> NvdPromotionS3ObjectCreatedV1:
        """Parse exactly one canonical incremental Silver COMPLETE Put event."""
        records_value = event.get("Records")
        if not isinstance(records_value, list):
            raise InvalidNvdPromotionS3EventError(
                "NVD promotion S3 event must contain a Records array."
            )

        records = cast(list[object], records_value)
        if len(records) != 1:
            raise InvalidNvdPromotionS3EventError(
                "NVD promotion S3 event must contain exactly one record."
            )

        record_value = records[0]
        if not isinstance(record_value, dict):
            raise InvalidNvdPromotionS3EventError(
                "Records[0] must be an object."
            )

        record = cast(dict[str, object], record_value)
        path = "Records[0]"

        event_version = self._require_exact_string(
            record.get("eventVersion"),
            path=f"{path}.eventVersion",
        )
        if _EVENT_VERSION_PATTERN.fullmatch(event_version) is None:
            raise InvalidNvdPromotionS3EventError(
                f"{path}.eventVersion must be from the supported S3 2.x family."
            )

        event_source = self._require_exact_string(
            record.get("eventSource"),
            path=f"{path}.eventSource",
        )
        if event_source != self.EXPECTED_EVENT_SOURCE:
            raise InvalidNvdPromotionS3EventError(
                f"{path}.eventSource must be {self.EXPECTED_EVENT_SOURCE!r}."
            )

        event_name = self._require_exact_string(
            record.get("eventName"),
            path=f"{path}.eventName",
        )
        if event_name != self.EXPECTED_EVENT_NAME:
            raise InvalidNvdPromotionS3EventError(
                f"{path}.eventName must be {self.EXPECTED_EVENT_NAME!r}."
            )

        s3_value = record.get("s3")
        if not isinstance(s3_value, dict):
            raise InvalidNvdPromotionS3EventError(
                f"{path}.s3 must be an object."
            )
        s3_data = cast(dict[str, object], s3_value)

        schema_version = self._require_exact_string(
            s3_data.get("s3SchemaVersion"),
            path=f"{path}.s3.s3SchemaVersion",
        )
        if schema_version != self.EXPECTED_S3_SCHEMA_VERSION:
            raise InvalidNvdPromotionS3EventError(
                f"{path}.s3.s3SchemaVersion must be "
                f"{self.EXPECTED_S3_SCHEMA_VERSION!r}."
            )

        bucket_value = s3_data.get("bucket")
        if not isinstance(bucket_value, dict):
            raise InvalidNvdPromotionS3EventError(
                f"{path}.s3.bucket must be an object."
            )
        bucket_data = cast(dict[str, object], bucket_value)

        bucket = self._require_exact_string(
            bucket_data.get("name"),
            path=f"{path}.s3.bucket.name",
        )
        if bucket != self._expected_bucket:
            raise InvalidNvdPromotionS3EventError(
                f"{path}.s3.bucket.name does not match the configured data bucket."
            )

        object_value = s3_data.get("object")
        if not isinstance(object_value, dict):
            raise InvalidNvdPromotionS3EventError(
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

        if _SILVER_COMPLETE_KEY_PATTERN.fullmatch(decoded_key) is None:
            raise InvalidNvdPromotionS3EventError(
                f"{path}.s3.object.key is not the canonical incremental "
                "NVD Silver COMPLETE path."
            )

        version_id = self._require_exact_string(
            object_data.get("versionId"),
            path=f"{path}.s3.object.versionId",
        )

        size_value = object_data.get("size")
        if type(size_value) is not int or size_value <= 0:
            raise InvalidNvdPromotionS3EventError(
                f"{path}.s3.object.size must be a positive integer."
            )

        return NvdPromotionS3ObjectCreatedV1(
            bucket=bucket,
            silver_complete=NvdSilverCompleteRefV1(
                key=decoded_key,
                version_id=version_id,
            ),
            object_size_bytes=size_value,
        )

    @staticmethod
    def _require_exact_string(
        value: object,
        *,
        path: str,
    ) -> str:
        """Require a non-empty string without hidden boundary whitespace."""
        if not isinstance(value, str) or not value or value != value.strip():
            raise InvalidNvdPromotionS3EventError(
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
                raise InvalidNvdPromotionS3EventError(
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
            raise InvalidNvdPromotionS3EventError(
                f"{path} is not valid URL-encoded UTF-8."
            ) from exc

        if not decoded:
            raise InvalidNvdPromotionS3EventError(
                f"{path} decodes to an empty key."
            )

        return decoded
