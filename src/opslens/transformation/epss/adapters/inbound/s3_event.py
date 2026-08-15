"""Parsing and validation of Amazon S3 ObjectCreated events."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast
from urllib.parse import unquote_plus


class InvalidS3ObjectCreatedEventError(ValueError):
    """Raised when an S3 event violates the Silver runtime contract."""


@dataclass(frozen=True, slots=True)
class S3ObjectCreatedRecord:
    """Represent one validated S3 ObjectCreated notification record."""

    bucket: str
    key: str
    event_name: str
    sequencer: str | None


class S3ObjectCreatedEventParser:
    """Parse validated Bronze object references from S3 notifications."""

    EXPECTED_EVENT_MAJOR_VERSION = 2
    MINIMUM_EVENT_MINOR_VERSION = 1
    EXPECTED_EVENT_SOURCE = "aws:s3"
    EXPECTED_EVENT_NAME_PREFIX = "ObjectCreated:"
    BRONZE_PREFIX = "bronze/epss/"

    def __init__(
        self,
        *,
        expected_bucket: str,
    ) -> None:
        """Initialize the parser with the expected OpsLens data bucket.

        Args:
            expected_bucket: S3 bucket allowed to trigger transformation.
        """
        normalized_bucket = expected_bucket.strip()

        if not normalized_bucket:
            raise ValueError("Expected S3 bucket name cannot be empty.")

        self._expected_bucket = normalized_bucket

    def parse(
        self,
        event: Mapping[str, object],
    ) -> tuple[S3ObjectCreatedRecord, ...]:
        """Parse all S3 ObjectCreated records from one Lambda event.

        Args:
            event: Raw Lambda event payload.

        Returns:
            Validated object-created records in source order.

        Raises:
            InvalidS3ObjectCreatedEventError: If the event structure or any
                record violates the expected S3 Bronze contract.
        """
        records_value = event.get("Records")

        if not isinstance(records_value, list) or not records_value:
            raise InvalidS3ObjectCreatedEventError(
                "S3 event must contain a non-empty Records list."
            )

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
    ) -> S3ObjectCreatedRecord:
        """Parse and validate one S3 notification record."""
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
            raise InvalidS3ObjectCreatedEventError(
                f"{path}.eventSource must be {self.EXPECTED_EVENT_SOURCE!r}, "
                f"received {event_source!r}."
            )

        event_name = self._require_string(
            record.get("eventName"),
            path=f"{path}.eventName",
        )

        if not event_name.startswith(self.EXPECTED_EVENT_NAME_PREFIX):
            raise InvalidS3ObjectCreatedEventError(
                f"{path}.eventName must describe an ObjectCreated event, received {event_name!r}."
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
            raise InvalidS3ObjectCreatedEventError(
                f"{path}.s3.bucket.name does not match the configured data bucket: "
                f"expected {self._expected_bucket!r}, received {bucket_name!r}."
            )

        object_data = self._require_mapping(
            s3_data.get("object"),
            path=f"{path}.s3.object",
        )

        encoded_key = self._require_string(
            object_data.get("key"),
            path=f"{path}.s3.object.key",
        )

        try:
            decoded_key = unquote_plus(
                encoded_key,
                encoding="utf-8",
                errors="strict",
            )
        except UnicodeDecodeError as exc:
            raise InvalidS3ObjectCreatedEventError(
                f"{path}.s3.object.key is not valid URL-encoded UTF-8."
            ) from exc

        if not decoded_key.startswith(self.BRONZE_PREFIX):
            raise InvalidS3ObjectCreatedEventError(
                f"{path}.s3.object.key must be under "
                f"{self.BRONZE_PREFIX!r}, received {decoded_key!r}."
            )

        sequencer_value = object_data.get("sequencer")

        sequencer = (
            None
            if sequencer_value is None
            else self._require_string(
                sequencer_value,
                path=f"{path}.s3.object.sequencer",
            )
        )

        return S3ObjectCreatedRecord(
            bucket=bucket_name,
            key=decoded_key,
            event_name=event_name,
            sequencer=sequencer,
        )

    def _validate_event_version(
        self,
        version: str,
        *,
        path: str,
    ) -> None:
        """Validate S3 notification major and minimum minor versions."""
        parts = version.split(".", maxsplit=1)

        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            raise InvalidS3ObjectCreatedEventError(
                f"{path} must use major.minor numeric format, received {version!r}."
            )

        major = int(parts[0])
        minor = int(parts[1])

        if major != self.EXPECTED_EVENT_MAJOR_VERSION or minor < self.MINIMUM_EVENT_MINOR_VERSION:
            raise InvalidS3ObjectCreatedEventError(f"{path} is unsupported: {version!r}.")

    @staticmethod
    def _require_mapping(
        value: object,
        *,
        path: str,
    ) -> Mapping[str, object]:
        """Return a string-keyed mapping or raise an event-contract error."""
        if not isinstance(value, Mapping):
            raise InvalidS3ObjectCreatedEventError(f"{path} must be an object.")

        mapping = cast(Mapping[object, object], value)

        if not all(isinstance(key, str) for key in mapping):
            raise InvalidS3ObjectCreatedEventError(f"{path} must contain only string keys.")

        return cast(Mapping[str, object], mapping)

    @staticmethod
    def _require_string(
        value: object,
        *,
        path: str,
    ) -> str:
        """Return a non-empty string or raise an event-contract error."""
        if not isinstance(value, str) or not value:
            raise InvalidS3ObjectCreatedEventError(f"{path} must be a non-empty string.")

        return value
