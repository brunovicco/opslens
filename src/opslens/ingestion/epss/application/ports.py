"""Application ports for EPSS snapshot ingestion."""

from typing import Protocol

from opslens.ingestion.epss.application.models import RepositoryWriteResult
from opslens.ingestion.epss.domain.models import EpssSnapshot


class EpssSnapshotSource(Protocol):
    """Port for obtaining the current raw EPSS source artifact."""

    def fetch(self) -> bytes:
        """Fetch and return the original EPSS artifact bytes."""
        ...


class BronzeSnapshotRepository(Protocol):
    """Port for conditionally storing an EPSS Bronze snapshot."""

    def create_if_absent(
        self,
        snapshot: EpssSnapshot,
        object_key: str,
    ) -> RepositoryWriteResult:
        """Create the Bronze object only when the key does not already exist."""
        ...
