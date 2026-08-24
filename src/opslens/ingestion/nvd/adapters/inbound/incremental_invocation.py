"""Strict explicit invocation envelope for NVD incremental runtime."""

from collections.abc import Mapping
from datetime import datetime

from opslens.ingestion.nvd.application.incremental_runtime_plan import (
    NvdIncrementalRuntimeRequestV1,
)


class InvalidNvdIncrementalInvocationError(ValueError):
    """Raised when an NVD incremental invocation envelope is invalid."""


class NvdIncrementalInvocationParserV1:
    """Parse one strict versioned NVD incremental invocation envelope."""

    REQUIRED_FIELDS = frozenset(
        {
            "schema_version",
            "target_end_at",
        }
    )

    def parse(
        self,
        event: Mapping[str, object],
    ) -> NvdIncrementalRuntimeRequestV1:
        """Parse one caller-controlled incremental runtime request."""
        actual_fields = frozenset(event)

        missing = self.REQUIRED_FIELDS - actual_fields
        unexpected = actual_fields - self.REQUIRED_FIELDS

        if missing:
            formatted = ", ".join(sorted(missing))
            raise InvalidNvdIncrementalInvocationError(
                "NVD incremental invocation is missing required fields: "
                f"{formatted}."
            )

        if unexpected:
            formatted = ", ".join(sorted(unexpected))
            raise InvalidNvdIncrementalInvocationError(
                "NVD incremental invocation contains unsupported fields: "
                f"{formatted}."
            )

        schema_version = self._required_string(
            event,
            "schema_version",
        )

        if schema_version != "1":
            raise InvalidNvdIncrementalInvocationError(
                "NVD incremental invocation schema_version must be '1'."
            )

        target_end_at_text = self._required_string(
            event,
            "target_end_at",
        )

        target_end_at = self._parse_timestamp(
            target_end_at_text,
        )

        return NvdIncrementalRuntimeRequestV1(
            target_end_at=target_end_at,
        )

    @staticmethod
    def _required_string(
        event: Mapping[str, object],
        field_name: str,
    ) -> str:
        """Read one required non-empty invocation string."""
        value = event.get(field_name)

        if not isinstance(value, str) or not value.strip():
            raise InvalidNvdIncrementalInvocationError(
                f"NVD incremental invocation {field_name} "
                "must be a non-empty string."
            )

        return value.strip()

    @staticmethod
    def _parse_timestamp(
        value: str,
    ) -> datetime:
        """Parse one explicit timezone-aware ISO-8601 timestamp."""
        normalized = (
            f"{value[:-1]}+00:00"
            if value.endswith("Z")
            else value
        )

        try:
            timestamp = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise InvalidNvdIncrementalInvocationError(
                "NVD incremental invocation target_end_at "
                "must be a valid ISO-8601 timestamp."
            ) from exc

        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise InvalidNvdIncrementalInvocationError(
                "NVD incremental invocation target_end_at "
                "must be timezone-aware."
            )

        return timestamp
