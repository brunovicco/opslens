"""Application ports for CISA KEV catalog ingestion."""

from datetime import datetime
from typing import Protocol

from opslens.ingestion.kev.application.models import RepositoryWriteResult
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot


class KevCatalogSource(Protocol):
    """Port for obtaining the current raw CISA KEV catalog."""

    def fetch(self) -> bytes:
        """Fetch and return the original CISA KEV artifact bytes."""
        ...


class BronzeCatalogRepository(Protocol):
    """Port for conditionally storing a CISA KEV Bronze snapshot."""

    def create_if_absent(
        self,
        snapshot: KevCatalogSnapshot,
        object_key: str,
    ) -> RepositoryWriteResult:
        """Create the Bronze object only when its key does not already exist."""
        ...


class Clock(Protocol):
    """Port for obtaining the current application time."""

    def now(self) -> datetime:
        """Return the current timezone-aware timestamp."""
        ...
