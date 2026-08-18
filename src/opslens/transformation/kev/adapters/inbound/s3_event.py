"""Parsing and validation of CISA KEV S3 ObjectCreated events."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import cast
from urllib.parse import unquote_plus


class InvalidKevS3EventError(ValueError):
    """Raised when an S3 event violates the KEV Silver runtime contract."""


@dataclass(frozen=True, slots=True)
class KevS3TestEvent:
    """Represent one validated Amazon S3 test notification."""

    bucket: str
    request_id: str


@dataclass(frozen=True, slots=True)
class KevBronzeObjectReference:
    """Represent one validated immutable KEV Bronze object reference.

    Attributes:
        bucket: S3 bucket containing the Bronze evidence.
        key: Canonical decoded KEV Bronze object key.
        version_id: Exact immutable S3 object version referenced by the event.
        etag: ETag reported by the S3 event.
        size_bytes: Object size reported by the S3 event.
        snapshot_date: UTC observation date encoded in the Bronze key.
        event_name: S3 event operation that created the object.
        sequencer: Optional S3 ordering value supplied by the event.
    """

    bucket: str
    key: str
    version_id: str
    etag: str
    size_bytes: int
    snapshot_date: date
    event_name: str
    sequencer: str | None


class KevS3EventParser:
    """Parse immutable KEV Bronze references from Amazon S3 notifications."""

    EXPECTED_EVENT_MAJOR_VERSION = 2
    MINIMUM_EVENT_MINOR_VERSION = 1

    EXPECTED_EVENT_SOURCE = "aws:s3"
    EXPECTED_EVENT_NAME = "ObjectCreated:Put"

    EXPECTED_TEST_EVENT = "s3:TestEvent"
    EXPECTED_TEST_EVENT_SERVICE = "Amazon S3"

    BRONZE_PREFIX = "bronze/kev/"
    OBJECT_NAME = "known_exploited_vulnerabilities.json"

    _KEY_PATTERN = re.compile(
        r"^bronze/kev/"
        r"snapshot_date=(?P<snapshot_date>\d{4}-\d{2}-\d{2})/"
        r"known_exploited_vulnerabilities\.json$"
    )

    def __init__(
        self,
        *,
        expected_bucket: str,
    ) -> None:
        """Initialize the parser with the allowed OpsLens data bucket.

        Args:
            expected_bucket: S3 bucket allowed to trigger KEV Silver.
        """
        normalized_bucket = expected_bucket.strip()

        if not normalized_bucket:
            raise ValueError("Expected S3 bucket name cannot be empty.")

        self._expected_bucket = normalized_bucket

    def parse_test_event(
        self,
        event: Mapping[str, object],
    ) -> KevS3TestEvent | None:
        """Parse an S3 test notification when present.

        Args:
            event: Raw Lambda event payload.

        Returns:
            Validated S3 test event, or None for regular notifications.

        Raises:
            InvalidKevS3EventError: If a test event violates the expected
                service or bucket contract.
        """
        event_name = event.get("Event")

        if event_name != self.EXPECTED_TEST_EVENT:
            return None

        service = self._require_string(
            event.get("Service"),
            path="Service",
        )

        if service != self.EXPECTED_TEST_EVENT_SERVICE:
            raise InvalidKevS3EventError(
                "S3 test event Service must be "
                f"{self.EXPECTED_TEST_EVENT_SERVICE!r}, "
                f"received {service!r}."
            )

        bucket = self._require_string(
            event.get("Bucket"),
            path="Bucket",
        )

        if bucket != self._expected_bucket:
            raise InvalidKevS3EventError(
                "S3 test event Bucket does not match the configured data bucket: "
                f"expected {self._expected_bucket!r}, received {bucket!r}."
            )

        request_id = self._require_string(
            event.get("RequestId"),
            path="RequestId",
        )

        return KevS3TestEvent(
            bucket=bucket,
            request_id=request_id,
        )

    def parse(
        self,
        event: Mapping[str, object],
    ) -> tuple[KevBronzeObjectReference, ...]:
        """Parse validated KEV Bronze references from one S3 notification.

        Args:
            event: Raw regular S3 notification payload.

        Returns:
            Immutable KEV Bronze references in event order.

        Raises:
            InvalidKevS3EventError: If the event violates the KEV runtime
                contract.
        """
        records_value = event.get("Records")

        if not isinstance(records_value, list) or not records_value:
            raise InvalidKevS3EventError("S3 event must contain a non-empty Records list.")

        records = cast(list[object], records_value)

        return tuple(
            self._parse_record(
                value=value,
                record_index=index,
            )
            for index, value in enumerate(records)
        )

    def _parse_record(
        self,
        *,
        value: object,
        record_index: int,
    ) -> KevBronzeObjectReference:
        """Parse and validate one S3 KEV ObjectCreated record."""
        path = f"Records[{record_index}]"

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
            raise InvalidKevS3EventError(
                f"{path}.eventSource must be "
                f"{self.EXPECTED_EVENT_SOURCE!r}, "
                f"received {event_source!r}."
            )

        event_name = self._require_string(
            record.get("eventName"),
            path=f"{path}.eventName",
        )

        if event_name != self.EXPECTED_EVENT_NAME:
            raise InvalidKevS3EventError(
                f"{path}.eventName must be {self.EXPECTED_EVENT_NAME!r}, received {event_name!r}."
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
            raise InvalidKevS3EventError(
                f"{path}.s3.bucket.name does not match "
                "the configured data bucket: "
                f"expected {self._expected_bucket!r}, "
                f"received {bucket_name!r}."
            )

        object_data = self._require_mapping(
            s3_data.get("object"),
            path=f"{path}.s3.object",
        )

        encoded_key = self._require_string(
            object_data.get("key"),
            path=f"{path}.s3.object.key",
        )

        decoded_key = self._decode_key(
            encoded_key,
            path=f"{path}.s3.object.key",
        )

        snapshot_date = self._parse_key(
            decoded_key,
            path=f"{path}.s3.object.key",
        )

        version_id = self._require_string(
            object_data.get("versionId"),
            path=f"{path}.s3.object.versionId",
        )

        etag = self._require_string(
            object_data.get("eTag"),
            path=f"{path}.s3.object.eTag",
        )

        size_value = object_data.get("size")

        if type(size_value) is not int or size_value <= 0:
            raise InvalidKevS3EventError(f"{path}.s3.object.size must be a positive integer.")

        sequencer_value = object_data.get("sequencer")

        sequencer = (
            None
            if sequencer_value is None
            else self._require_string(
                sequencer_value,
                path=f"{path}.s3.object.sequencer",
            )
        )

        return KevBronzeObjectReference(
            bucket=bucket_name,
            key=decoded_key,
            version_id=version_id,
            etag=etag,
            size_bytes=size_value,
            snapshot_date=snapshot_date,
            event_name=event_name,
            sequencer=sequencer,
        )

    def _parse_key(
        self,
        key: str,
        *,
        path: str,
    ) -> date:
        """Validate the exact canonical KEV Bronze object key."""
        match = self._KEY_PATTERN.fullmatch(key)

        if match is None:
            raise InvalidKevS3EventError(
                f"{path} must match the canonical KEV Bronze key contract, received {key!r}."
            )

        snapshot_date_raw = match.group("snapshot_date")

        try:
            return date.fromisoformat(snapshot_date_raw)
        except ValueError as exc:
            raise InvalidKevS3EventError(
                f"{path} contains an invalid snapshot_date {snapshot_date_raw!r}."
            ) from exc

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
            raise InvalidKevS3EventError(f"{path} is not valid URL-encoded UTF-8.") from exc

    def _validate_event_version(
        self,
        version: str,
        *,
        path: str,
    ) -> None:
        """Validate the S3 notification major and minimum minor version."""
        parts = version.split(".", maxsplit=1)

        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            raise InvalidKevS3EventError(
                f"{path} must use major.minor numeric format, received {version!r}."
            )

        major = int(parts[0])
        minor = int(parts[1])

        if major != self.EXPECTED_EVENT_MAJOR_VERSION or minor < self.MINIMUM_EVENT_MINOR_VERSION:
            raise InvalidKevS3EventError(f"{path} is unsupported: {version!r}.")

    @staticmethod
    def _require_mapping(
        value: object,
        *,
        path: str,
    ) -> Mapping[str, object]:
        """Return a string-keyed mapping or raise a contract error."""
        if not isinstance(value, Mapping):
            raise InvalidKevS3EventError(f"{path} must be an object.")

        mapping = cast(Mapping[object, object], value)

        if not all(isinstance(key, str) for key in mapping):
            raise InvalidKevS3EventError(f"{path} must contain only string keys.")

        return cast(Mapping[str, object], mapping)

    @staticmethod
    def _require_string(
        value: object,
        *,
        path: str,
    ) -> str:
        """Return a non-empty string or raise a contract error."""
        if not isinstance(value, str) or not value:
            raise InvalidKevS3EventError(f"{path} must be a non-empty string.")

        return value
