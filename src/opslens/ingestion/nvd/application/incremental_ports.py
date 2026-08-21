"""Application ports for NVD incremental Bronze ingestion."""

from typing import Protocol

from opslens.ingestion.nvd.application.incremental_manifest import (
    NvdIncrementalManifest,
)
from opslens.ingestion.nvd.application.models import (
    NvdBronzeWriteResult,
)
from opslens.ingestion.nvd.domain.api_page import (
    NvdCveApiPage,
)
from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)


class NvdCveApiSource(Protocol):
    """Port for retrieving exact NVD CVE API response pages."""

    def fetch_page(
        self,
        *,
        window: NvdIncrementalWindow,
        start_index: int,
    ) -> bytes:
        """Fetch one exact incremental API response."""
        ...


class NvdIncrementalBronzeRepository(Protocol):
    """Port for immutable incremental Bronze persistence."""

    def create_page(
        self,
        *,
        page: NvdCveApiPage,
        window: NvdIncrementalWindow,
        object_key: str,
    ) -> NvdBronzeWriteResult:
        """Create or verify one exact response page."""
        ...

    def create_manifest(
        self,
        *,
        manifest: NvdIncrementalManifest,
        payload: bytes,
        object_key: str,
    ) -> NvdBronzeWriteResult:
        """Create or verify one COMPLETE manifest."""
        ...
