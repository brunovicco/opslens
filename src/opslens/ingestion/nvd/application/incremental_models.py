"""Application result models for NVD incremental Bronze ingestion."""

from dataclasses import dataclass
from datetime import datetime

from opslens.ingestion.nvd.application.models import (
    NvdBronzeWriteResult,
)
from opslens.ingestion.nvd.application.watermark import (
    NvdWatermarkCandidate,
)


@dataclass(frozen=True, slots=True)
class NvdIncrementalIngestionResult:
    """Expose verified evidence from one incremental Bronze run.

    Attributes:
        update_id: Deterministic logical update identity.
        window_start_at: Closed lower last-modified boundary.
        window_end_at: Closed upper last-modified boundary.
        total_results: Source result count validated across all pages.
        page_keys: Deterministic persisted page keys in source order.
        page_writes: Exact S3 persistence evidence for every page.
        manifest_key: Deterministic COMPLETE manifest key.
        manifest_write: Exact S3 persistence evidence for the manifest.
        candidate: Bronze-complete candidate awaiting Silver completion.
    """

    update_id: str
    window_start_at: datetime
    window_end_at: datetime
    total_results: int
    page_keys: tuple[str, ...]
    page_writes: tuple[NvdBronzeWriteResult, ...]
    manifest_key: str
    manifest_write: NvdBronzeWriteResult
    candidate: NvdWatermarkCandidate
