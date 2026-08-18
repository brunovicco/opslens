"""Canonical S3 object-key generation for CISA KEV Silver artifacts."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class KevSilverKeyFactory:
    """Build deterministic partitioned keys for KEV Silver artifacts."""

    prefix: str = "silver/kev"

    def __post_init__(self) -> None:
        """Validate the configured Silver prefix."""
        normalized_prefix = self.prefix.strip("/")

        if not normalized_prefix:
            raise ValueError("KEV Silver prefix cannot be empty.")

        if normalized_prefix != self.prefix:
            raise ValueError("KEV Silver prefix must not contain leading or trailing slashes.")

    def build(
        self,
        snapshot_date: date,
    ) -> str:
        """Build the canonical Parquet key for one KEV observation date."""
        return f"{self.prefix}/snapshot_date={snapshot_date.isoformat()}/part-00000.parquet"
