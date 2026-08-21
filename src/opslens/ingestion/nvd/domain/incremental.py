"""Deterministic incremental-window identity for NVD CVE API ingestion."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import ClassVar


def _require_aware_datetime(
    field_name: str,
    value: object,
) -> datetime:
    """Validate one timezone-aware datetime input."""
    if not isinstance(value, datetime):
        raise ValueError(f"NVD incremental {field_name} must be a datetime.")

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"NVD incremental {field_name} must be timezone-aware.")

    return value.astimezone(UTC)


def _canonical_timestamp(value: datetime) -> str:
    """Serialize one UTC timestamp deterministically."""
    timespec = "microseconds" if value.microsecond else "seconds"

    return value.astimezone(UTC).isoformat(timespec=timespec).replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class NvdIncrementalWindow:
    """Represent one deterministic closed NVD CVE API update window.

    The window identity is derived only from the normalized UTC boundaries.
    Runtime timestamps, request IDs, retrieval timestamps, and infrastructure
    metadata are intentionally excluded from the logical identity.

    Attributes:
        start_at: Inclusive lower last-modified boundary.
        end_at: Closed upper last-modified boundary.
    """

    MAX_SPAN: ClassVar[timedelta] = timedelta(days=120)

    start_at: datetime
    end_at: datetime

    def __post_init__(self) -> None:
        """Normalize boundaries and enforce incremental-window invariants."""
        start_at = _require_aware_datetime(
            "start_at",
            self.start_at,
        )
        end_at = _require_aware_datetime(
            "end_at",
            self.end_at,
        )

        if start_at >= end_at:
            raise ValueError("NVD incremental start_at must be before end_at.")

        if end_at - start_at > self.MAX_SPAN:
            raise ValueError("NVD incremental window must not exceed 120 days.")

        object.__setattr__(self, "start_at", start_at)
        object.__setattr__(self, "end_at", end_at)

    @property
    def canonical_start_at(self) -> str:
        """Return the normalized lower boundary."""
        return _canonical_timestamp(self.start_at)

    @property
    def canonical_end_at(self) -> str:
        """Return the normalized upper boundary."""
        return _canonical_timestamp(self.end_at)

    @property
    def update_id(self) -> str:
        """Return the deterministic identity for this logical update run."""
        identity_payload = (
            f"start={self.canonical_start_at}\nend={self.canonical_end_at}\n"
        ).encode()

        return sha256(identity_payload).hexdigest()
