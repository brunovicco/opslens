"""Deterministic logical synchronization identity for GHSA Bronze."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from hashlib import sha256
from typing import ClassVar

from opslens.ingestion.ghsa.domain.errors import (
    InvalidGhsaSyncWindowError,
)


class GhsaSyncMode(StrEnum):
    """Supported bounded GHSA synchronization filters."""

    PUBLISHED = "published"
    MODIFIED = "modified"


def _require_utc_second_precision(
    field_name: str,
    value: object,
) -> datetime:
    """Normalize one aware timestamp to UTC and require second precision."""
    if not isinstance(value, datetime):
        raise InvalidGhsaSyncWindowError(
            f"GHSA sync {field_name} must be a datetime."
        )

    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidGhsaSyncWindowError(
            f"GHSA sync {field_name} must be timezone-aware."
        )

    normalized = value.astimezone(UTC)

    if normalized.microsecond != 0:
        raise InvalidGhsaSyncWindowError(
            f"GHSA sync {field_name} must use whole-second precision."
        )

    return normalized


def _canonical_timestamp(value: datetime) -> str:
    """Serialize one UTC timestamp using the frozen source-query form."""
    return value.astimezone(UTC).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class GhsaSyncWindow:
    """Represent one bounded closed GitHub advisory synchronization window."""

    CONTRACT_VERSION: ClassVar[str] = "1"
    API_VERSION: ClassVar[str] = "2026-03-10"
    ADVISORY_TYPE: ClassVar[str] = "reviewed"
    SORT_FIELD: ClassVar[str] = "published"
    DIRECTION: ClassVar[str] = "asc"
    PER_PAGE: ClassVar[int] = 100
    MAX_SPAN: ClassVar[timedelta] = timedelta(days=31)

    mode: GhsaSyncMode
    start_at: datetime
    end_at: datetime

    def __post_init__(self) -> None:
        """Normalize boundaries and enforce bounded closed-window invariants."""
        start_at = _require_utc_second_precision("start_at", self.start_at)
        end_at = _require_utc_second_precision("end_at", self.end_at)

        if start_at >= end_at:
            raise InvalidGhsaSyncWindowError(
                "GHSA sync start_at must be before end_at."
            )

        if end_at - start_at > self.MAX_SPAN:
            raise InvalidGhsaSyncWindowError(
                "GHSA sync window must not exceed 31 days."
            )

        object.__setattr__(self, "start_at", start_at)
        object.__setattr__(self, "end_at", end_at)

    @property
    def canonical_start_at(self) -> str:
        """Return the normalized inclusive lower boundary."""
        return _canonical_timestamp(self.start_at)

    @property
    def canonical_end_at(self) -> str:
        """Return the normalized inclusive upper boundary."""
        return _canonical_timestamp(self.end_at)

    @property
    def filter_expression(self) -> str:
        """Return the closed GitHub search-range expression."""
        return f"{self.canonical_start_at}..{self.canonical_end_at}"

    @property
    def sync_id(self) -> str:
        """Return the deterministic identity of the logical source query."""
        document: dict[str, object] = {
            "advisory_type": self.ADVISORY_TYPE,
            "api_version": self.API_VERSION,
            "contract_version": self.CONTRACT_VERSION,
            "direction": self.DIRECTION,
            "end_at": self.canonical_end_at,
            "mode": self.mode.value,
            "per_page": self.PER_PAGE,
            "sort": self.SORT_FIELD,
            "start_at": self.canonical_start_at,
        }

        payload = json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")

        return sha256(payload).hexdigest()
