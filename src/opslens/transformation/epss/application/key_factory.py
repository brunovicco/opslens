"""Canonical object-key generation for EPSS Silver artifacts."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class EpssSilverKeyFactory:
    """Build deterministic S3-compatible keys for EPSS Silver artifacts."""

    prefix: str = "silver/epss"

    def __post_init__(self) -> None:
        """Validate the configured Silver object prefix."""
        normalized_prefix = self.prefix.strip("/")

        if not normalized_prefix:
            raise ValueError("EPSS Silver prefix cannot be empty.")

        if normalized_prefix != self.prefix:
            raise ValueError("EPSS Silver prefix must not contain leading or trailing slashes.")

    def build(self, snapshot_date: date) -> str:
        """Build the canonical Parquet key for one EPSS snapshot date.

        Args:
            snapshot_date: Source snapshot date represented by the artifact.

        Returns:
            Deterministic Hive-style partitioned Silver object key.
        """
        return f"{self.prefix}/snapshot_date={snapshot_date.isoformat()}/part-00000.parquet"
