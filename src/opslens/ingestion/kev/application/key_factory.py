"""Deterministic object-key generation for CISA KEV Bronze snapshots."""

from opslens.ingestion.kev.domain.models import KevCatalogSnapshot


class KevBronzeKeyFactory:
    """Build deterministic partitioned S3 keys for KEV Bronze artifacts."""

    DEFAULT_PREFIX = "bronze/kev"
    OBJECT_NAME = "known_exploited_vulnerabilities.json"

    def __init__(self, prefix: str = DEFAULT_PREFIX) -> None:
        """Initialize the key factory with a configurable Bronze prefix."""
        normalized_prefix = prefix.strip("/")

        if not normalized_prefix:
            raise ValueError("KEV Bronze prefix cannot be empty.")

        self._prefix = normalized_prefix

    def build(self, snapshot: KevCatalogSnapshot) -> str:
        """Build the deterministic key for one observed KEV catalog."""
        return (
            f"{self._prefix}/"
            f"snapshot_date={snapshot.snapshot_date}/"
            f"{self.OBJECT_NAME}"
        )
