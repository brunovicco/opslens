"""Application ports for NVD ingestion."""

from typing import Protocol

from opslens.ingestion.nvd.application.manifest import NvdBootstrapManifest
from opslens.ingestion.nvd.application.models import NvdBronzeWriteResult
from opslens.ingestion.nvd.domain.feed_artifact import NvdFeedArtifact
from opslens.ingestion.nvd.domain.source_identity import (
    NvdBootstrapSourceIdentity,
)


class NvdYearlyFeedSource(Protocol):
    """Port for obtaining original NVD yearly-feed source artifacts."""

    def fetch_meta(self, feed_year: int) -> bytes:
        """Fetch the exact NVD META artifact for one yearly feed."""
        ...

    def fetch_gzip(self, feed_year: int) -> bytes:
        """Fetch the exact NVD gzip artifact for one yearly feed."""
        ...


class NvdBootstrapBronzeRepository(Protocol):
    """Port for immutably persisting NVD Bootstrap Bronze evidence."""

    def create_feed(
        self,
        *,
        artifact: NvdFeedArtifact,
        identity: NvdBootstrapSourceIdentity,
        object_key: str,
    ) -> NvdBronzeWriteResult:
        """Create or verify the exact NVD gzip Bronze object."""
        ...

    def create_meta(
        self,
        *,
        identity: NvdBootstrapSourceIdentity,
        object_key: str,
    ) -> NvdBronzeWriteResult:
        """Create or verify the exact NVD META Bronze object."""
        ...

    def create_manifest(
        self,
        *,
        manifest: NvdBootstrapManifest,
        payload: bytes,
        object_key: str,
    ) -> NvdBronzeWriteResult:
        """Create or verify one immutable COMPLETE manifest object."""
        ...
