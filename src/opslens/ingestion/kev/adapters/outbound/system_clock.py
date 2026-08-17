"""System clock adapter for CISA KEV ingestion."""

from datetime import UTC, datetime


class SystemClock:
    """Provide the current wall-clock time in UTC."""

    def now(self) -> datetime:
        """Return the current timezone-aware UTC timestamp."""
        return datetime.now(UTC)
