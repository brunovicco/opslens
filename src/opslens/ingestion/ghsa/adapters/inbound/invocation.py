"""Strict manual invocation contract for GHSA Bronze Lambda execution."""

import re
from collections.abc import Mapping
from datetime import UTC, datetime

from opslens.ingestion.ghsa.domain.sync import GhsaSyncMode, GhsaSyncWindow

_UTC_SECOND_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class InvalidGhsaInvocationError(ValueError):
    """Raised when a Lambda invocation violates the frozen GHSA input contract."""


class GhsaBronzeInvocationParserV1:
    """Parse one explicit bounded GHSA Bronze synchronization request."""

    SCHEMA_VERSION = 1
    REQUIRED_FIELDS = frozenset(
        {
            "schema_version",
            "mode",
            "start_at",
            "end_at",
        }
    )

    def parse(self, event: Mapping[str, object]) -> GhsaSyncWindow:
        """Return one validated sync window from the exact v1 event shape."""
        event_fields = set(event)
        missing = self.REQUIRED_FIELDS - event_fields
        unknown = event_fields - self.REQUIRED_FIELDS

        if missing:
            formatted = ", ".join(sorted(missing))
            raise InvalidGhsaInvocationError(
                f"GHSA invocation is missing required fields: {formatted}."
            )

        if unknown:
            formatted = ", ".join(sorted(unknown))
            raise InvalidGhsaInvocationError(
                f"GHSA invocation contains unsupported fields: {formatted}."
            )

        schema_version = event["schema_version"]

        if type(schema_version) is not int or schema_version != self.SCHEMA_VERSION:
            raise InvalidGhsaInvocationError("GHSA invocation schema_version must equal 1.")

        mode_value = event["mode"]

        if not isinstance(mode_value, str):
            raise InvalidGhsaInvocationError("GHSA invocation mode must be a string.")

        try:
            mode = GhsaSyncMode(mode_value)
        except ValueError as exc:
            raise InvalidGhsaInvocationError(
                "GHSA invocation mode must be 'published' or 'modified'."
            ) from exc

        start_at = self._parse_timestamp("start_at", event["start_at"])
        end_at = self._parse_timestamp("end_at", event["end_at"])

        try:
            return GhsaSyncWindow(
                mode=mode,
                start_at=start_at,
                end_at=end_at,
            )
        except ValueError as exc:
            raise InvalidGhsaInvocationError(
                f"GHSA invocation window is invalid: {exc}"
            ) from exc

    @staticmethod
    def _parse_timestamp(field_name: str, value: object) -> datetime:
        """Require canonical UTC whole-second timestamps ending in Z."""
        if not isinstance(value, str) or _UTC_SECOND_PATTERN.fullmatch(value) is None:
            raise InvalidGhsaInvocationError(
                f"GHSA invocation {field_name} must use YYYY-MM-DDTHH:MM:SSZ."
            )

        try:
            parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError as exc:
            raise InvalidGhsaInvocationError(
                f"GHSA invocation {field_name} is not a valid UTC timestamp."
            ) from exc

        return parsed.replace(tzinfo=UTC)
