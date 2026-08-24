"""Application orchestration for one exact NVD Silver watermark promotion."""

from typing import Protocol

from opslens.ingestion.nvd.application.watermark import (
    NvdWatermarkCandidate,
)
from opslens.transformation.nvd.application.watermark_promotion_evidence_loader import (
    NvdSilverCompleteRefV1,
    NvdWatermarkPromotionEvidenceV1,
)
from opslens.transformation.nvd.application.watermark_promotion_service import (
    NvdAuthoritativeWatermarkPromotionResultV1,
)
from opslens.transformation.nvd.completion.promotion import (
    NvdPersistedObjectPayloadV1,
)


class NvdPromotionEvidenceLoaderUseCase(Protocol):
    """Load exact immutable evidence selected by a Silver COMPLETE reference."""

    def load(
        self,
        *,
        silver_complete: NvdSilverCompleteRefV1,
    ) -> NvdWatermarkPromotionEvidenceV1:
        """Return exact evidence required for authoritative promotion."""
        ...


class NvdPromotionCommitUseCase(Protocol):
    """Commit one verified candidate to the authoritative watermark."""

    def promote(
        self,
        *,
        candidate: NvdWatermarkCandidate,
        silver_manifest: NvdPersistedObjectPayloadV1,
        silver_parquet: NvdPersistedObjectPayloadV1,
    ) -> NvdAuthoritativeWatermarkPromotionResultV1:
        """Promote one exact Silver-complete candidate."""
        ...


class NvdWatermarkPromotionRuntimeV1:
    """Coordinate exact evidence loading and the final promotion service."""

    def __init__(
        self,
        *,
        evidence_loader: NvdPromotionEvidenceLoaderUseCase,
        promotion_service: NvdPromotionCommitUseCase,
    ) -> None:
        """Initialize explicit application dependencies."""
        self._evidence_loader = evidence_loader
        self._promotion_service = promotion_service

    def process(
        self,
        *,
        silver_complete: NvdSilverCompleteRefV1,
    ) -> NvdAuthoritativeWatermarkPromotionResultV1:
        """Load exact persisted evidence and attempt one authoritative commit."""
        evidence = self._evidence_loader.load(
            silver_complete=silver_complete,
        )

        return self._promotion_service.promote(
            candidate=evidence.candidate,
            silver_manifest=evidence.silver_manifest,
            silver_parquet=evidence.silver_parquet,
        )
