"""Strict Amazon S3 COMPLETE-event boundary for NVD Silver."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast
from urllib.parse import unquote_plus

from opslens.transformation.nvd.application.runtime_models import (
    NvdSilverRuntimeRequestV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)


class InvalidNvdSilverS3EventError(ValueError):
    """Raised when an S3 event violates the NVD Silver runtime contract."""


@dataclass(frozen=True, slots=True)
class NvdS3TestEvent:
    """Represent one validated Amazon S3 test notification."""

    bucket: str
    request_id: str


class NvdSilverS3EventParserV1:
    """Parse one exact versioned NVD Bronze COMPLETE S3 event."""

    EXPECTED_EVENT_MAJOR_VERSION = 2
    MINIMUM_EVENT_MINOR_VERSION = 1

    EXPECTED_EVENT_SOURCE = "aws:s3"
    EXPECTED_EVENT_NAME = "ObjectCreated:Put"

    EXPECTED_TEST_EVENT = "s3:TestEvent"
    EXPECTED_TEST_EVENT_SERVICE = "Amazon S3"

    _BOOTSTRAP_KEY_PATTERN = re.compile(
        r"^bronze/nvd/cve/bootstrap/"
        r"feed_year=\d{4}/"
        r"feed_revision=\d{8}T\d{6}Z-[0-9a-f]{64}/"
        r"manifest\.json$"
    )

    _INCREMENTAL_KEY_PATTERN = re.compile(
        r"^bronze/nvd/cve/updates/"
        r"update_id=[0-9a-f]{64}/"
        r"manifest\.json$"
    )

    def __init__(
        self,
        *,
        expected_bucket: str,
    ) -> None:
        """Initialize the parser with the only allowed data bucket."""
        normalized_bucket = expected_bucket.strip()

        if not normalized_bucket:
            raise ValueError("Expected NVD Silver S3 bucket name cannot be empty.")

        self._expected_bucket = normalized_bucket

    def parse_test_event(
        self,
        event: Mapping[str, object],
    ) -> NvdS3TestEvent | None:
        """Parse an Amazon S3 test event when present."""
        event_name = event.get("Event")

        if event_name != self.EXPECTED_TEST_EVENT:
            return None

        service = self._require_string(
            event.get("Service"),
            path="Service",
        )

        if service != self.EXPECTED_TEST_EVENT_SERVICE:
            raise InvalidNvdSilverS3EventError("S3 test event Service does not match Amazon S3.")

        bucket = self._require_string(
            event.get("Bucket"),
            path="Bucket",
        )

        if bucket != self._expected_bucket:
            raise InvalidNvdSilverS3EventError(
                "S3 test event Bucket does not match the configured NVD data bucket."
            )

        request_id = self._require_string(
            event.get("RequestId"),
            path="RequestId",
        )

        return NvdS3TestEvent(
            bucket=bucket,
            request_id=request_id,
        )

    def parse(
        self,
        event: Mapping[str, object],
    ) -> NvdSilverRuntimeRequestV1:
        """Parse exactly one NVD Bronze COMPLETE ObjectCreated record."""
        records_value = event.get("Records")

        if not isinstance(records_value, list):
            raise InvalidNvdSilverS3EventError("NVD Silver S3 event must contain a Records array.")

        records = cast(
            list[object],
            records_value,
        )

        if len(records) != 1:
            raise InvalidNvdSilverS3EventError(
                "NVD Silver S3 event must contain exactly one record."
            )

        return self._parse_record(
            records[0],
        )

    def _parse_record(
        self,
        value: object,
    ) -> NvdSilverRuntimeRequestV1:
        """Parse one exact immutable NVD COMPLETE object reference."""
        path = "Records[0]"

        record = self._require_mapping(
            value,
            path=path,
        )

        event_version = self._require_string(
            record.get("eventVersion"),
            path=f"{path}.eventVersion",
        )

        self._validate_event_version(
            event_version,
            path=f"{path}.eventVersion",
        )

        event_source = self._require_string(
            record.get("eventSource"),
            path=f"{path}.eventSource",
        )

        if event_source != self.EXPECTED_EVENT_SOURCE:
            raise InvalidNvdSilverS3EventError(
                f"{path}.eventSource must be {self.EXPECTED_EVENT_SOURCE!r}."
            )

        event_name = self._require_string(
            record.get("eventName"),
            path=f"{path}.eventName",
        )

        if event_name != self.EXPECTED_EVENT_NAME:
            raise InvalidNvdSilverS3EventError(
                f"{path}.eventName must be {self.EXPECTED_EVENT_NAME!r}."
            )

        s3_data = self._require_mapping(
            record.get("s3"),
            path=f"{path}.s3",
        )

        bucket_data = self._require_mapping(
            s3_data.get("bucket"),
            path=f"{path}.s3.bucket",
        )

        bucket_name = self._require_string(
            bucket_data.get("name"),
            path=f"{path}.s3.bucket.name",
        )

        if bucket_name != self._expected_bucket:
            raise InvalidNvdSilverS3EventError(
                f"{path}.s3.bucket.name does not match the configured NVD data bucket."
            )

        object_data = self._require_mapping(
            s3_data.get("object"),
            path=f"{path}.s3.object",
        )

        encoded_key = self._require_string(
            object_data.get("key"),
            path=f"{path}.s3.object.key",
        )

        manifest_key = self._decode_key(
            encoded_key,
            path=f"{path}.s3.object.key",
        )

        source_kind = self._source_kind_from_key(
            manifest_key,
            path=f"{path}.s3.object.key",
        )

        manifest_version_id = self._require_string(
            object_data.get("versionId"),
            path=f"{path}.s3.object.versionId",
        )

        size_value = object_data.get("size")

        if type(size_value) is not int or size_value <= 0:
            raise InvalidNvdSilverS3EventError(f"{path}.s3.object.size must be a positive integer.")

        return NvdSilverRuntimeRequestV1(
            source_kind=source_kind,
            manifest_key=manifest_key,
            manifest_version_id=manifest_version_id,
        )

    @classmethod
    def _source_kind_from_key(
        cls,
        key: str,
        *,
        path: str,
    ) -> NvdSilverSourceKind:
        """Map one canonical COMPLETE key to its NVD source kind."""
        if cls._BOOTSTRAP_KEY_PATTERN.fullmatch(key) is not None:
            return NvdSilverSourceKind.BOOTSTRAP

        if cls._INCREMENTAL_KEY_PATTERN.fullmatch(key) is not None:
            return NvdSilverSourceKind.INCREMENTAL

        raise InvalidNvdSilverS3EventError(
            f"{path} does not reference a canonical NVD Bronze COMPLETE manifest."
        )

    @staticmethod
    def _decode_key(
        value: str,
        *,
        path: str,
    ) -> str:
        """Decode one S3 notification object key as UTF-8."""
        try:
            return unquote_plus(
                value,
                encoding="utf-8",
                errors="strict",
            )
        except UnicodeDecodeError as exc:
            raise InvalidNvdSilverS3EventError(f"{path} is not valid URL-encoded UTF-8.") from exc

    def _validate_event_version(
        self,
        version: str,
        *,
        path: str,
    ) -> None:
        """Accept the expected major and compatible newer minor versions."""
        parts = version.split(
            ".",
            maxsplit=1,
        )

        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            raise InvalidNvdSilverS3EventError(f"{path} must use major.minor numeric format.")

        major = int(parts[0])
        minor = int(parts[1])

        if major != self.EXPECTED_EVENT_MAJOR_VERSION or minor < self.MINIMUM_EVENT_MINOR_VERSION:
            raise InvalidNvdSilverS3EventError(f"{path} uses an unsupported S3 event version.")

    @staticmethod
    def _require_mapping(
        value: object,
        *,
        path: str,
    ) -> Mapping[str, object]:
        """Return one string-keyed mapping from untrusted event data."""
        if not isinstance(value, Mapping):
            raise InvalidNvdSilverS3EventError(f"{path} must be an object.")

        mapping = cast(
            Mapping[object, object],
            value,
        )

        if not all(isinstance(key, str) for key in mapping):
            raise InvalidNvdSilverS3EventError(f"{path} must contain only string keys.")

        return cast(
            Mapping[str, object],
            mapping,
        )

    @staticmethod
    def _require_string(
        value: object,
        *,
        path: str,
    ) -> str:
        """Return one required non-empty event string."""
        if not isinstance(value, str) or not value.strip():
            raise InvalidNvdSilverS3EventError(f"{path} must be a non-empty string.")

        return value
