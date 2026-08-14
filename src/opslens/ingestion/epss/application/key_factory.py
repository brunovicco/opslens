"""Deterministic object-key generation for EPSS Bronze snapshots."""

from opslens.ingestion.epss.domain.models import EpssSnapshot


class EpssBronzeKeyFactory:
    """Build deterministic partitioned S3 keys for EPSS Bronze artifacts."""

    DEFAULT_PREFIX = "bronze/epss"
    OBJECT_NAME = "epss_scores.csv.gz"

    def __init__(self, prefix: str = DEFAULT_PREFIX) -> None:
        """Initialize the key factory with a configurable Bronze prefix."""
        normalized_prefix = prefix.strip("/")

        if not normalized_prefix:
            raise ValueError("EPSS Bronze prefix cannot be empty.")

        self._prefix = normalized_prefix

    def build(self, snapshot: EpssSnapshot) -> str:
        """Build the deterministic key for one EPSS source snapshot."""
        return f"{self._prefix}/snapshot_date={snapshot.snapshot_date}/{self.OBJECT_NAME}"
