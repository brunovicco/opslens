"""Application ports for NVD ingestion."""

from typing import Protocol


class NvdYearlyFeedSource(Protocol):
    """Port for obtaining original NVD yearly-feed source artifacts."""

    def fetch_meta(self, feed_year: int) -> bytes:
        """Fetch the exact NVD META artifact for one yearly feed."""
        ...

    def fetch_gzip(self, feed_year: int) -> bytes:
        """Fetch the exact NVD gzip artifact for one yearly feed."""
        ...
