"""Tests for NVD promotion application runtime orchestration."""

from datetime import UTC, datetime

from opslens.ingestion.nvd.application.authoritative_watermark import (
    NvdAuthoritativeWatermarkV1,
    NvdWatermarkEvidenceObjectV1,
    NvdWatermarkSilverPromotionCommitV1,
)
from opslens.ingestion.nvd.application.authoritative_watermark_store import (
    NvdPersistedAuthoritativeWatermarkV1,
)
from opslens.ingestion.nvd.application.watermark import (
    NvdWatermarkCandidate,
)
from opslens.transformation.nvd.application.watermark_promotion_evidence_loader import (
    NvdSilverCompleteRefV1,
    NvdWatermarkPromotionEvidenceV1,
)
from opslens.transformation.nvd.application.watermark_promotion_runtime import (
    NvdWatermarkPromotionRuntimeV1,
)
from opslens.transformation.nvd.application.watermark_promotion_service import (
    NvdAuthoritativeWatermarkPromotionResultV1,
)
from opslens.transformation.nvd.completion.promotion import (
    NvdPersistedObjectPayloadV1,
)

START = datetime(2026, 8, 18, 7, 0, 12, tzinfo=UTC)
END = datetime(2026, 8, 18, 7, 20, 12, tzinfo=UTC)
UPDATE_ID = "a" * 64


def _candidate() -> NvdWatermarkCandidate:
    """Build one exact candidate fixture."""
    return NvdWatermarkCandidate(
        update_id=UPDATE_ID,
        window_start_at=START,
        window_end_at=END,
        bronze_manifest_key=(
            "bronze/nvd/cve/updates/"
            f"update_id={UPDATE_ID}/manifest.json"
        ),
        bronze_manifest_version_id="bronze-version-1",
        bronze_manifest_sha256="b" * 64,
        total_results=34,
        page_count=1,
    )


def _silver_manifest() -> NvdPersistedObjectPayloadV1:
    """Build exact Silver COMPLETE payload evidence."""
    return NvdPersistedObjectPayloadV1(
        key=(
            "silver/nvd/cve/schema_version=1/source_kind=incremental/"
            f"update_id={UPDATE_ID}/manifest.json"
        ),
        version_id="silver-complete-version-1",
        raw_bytes=b"exact-silver-complete",
    )


def _silver_parquet() -> NvdPersistedObjectPayloadV1:
    """Build exact Silver Parquet payload evidence."""
    return NvdPersistedObjectPayloadV1(
        key=(
            "silver/nvd/cve/schema_version=1/source_kind=incremental/"
            f"update_id={UPDATE_ID}/part-00000.parquet"
        ),
        version_id="silver-parquet-version-1",
        raw_bytes=b"PAR1exactPAR1",
    )


def _result() -> NvdAuthoritativeWatermarkPromotionResultV1:
    """Build one exact committed watermark result."""
    candidate = _candidate()
    manifest = _silver_manifest()
    parquet = _silver_parquet()

    watermark = NvdAuthoritativeWatermarkV1(
        committed_through_at=END,
        commit_basis=NvdWatermarkSilverPromotionCommitV1(
            previous_committed_through_at=START,
            update_id=UPDATE_ID,
            bronze_manifest=NvdWatermarkEvidenceObjectV1(
                key=candidate.bronze_manifest_key,
                version_id=candidate.bronze_manifest_version_id,
                sha256=candidate.bronze_manifest_sha256,
            ),
            silver_manifest=NvdWatermarkEvidenceObjectV1(
                key=manifest.key,
                version_id=manifest.version_id,
                sha256=manifest.sha256,
            ),
            silver_parquet=NvdWatermarkEvidenceObjectV1(
                key=parquet.key,
                version_id=parquet.version_id,
                sha256=parquet.sha256,
            ),
            logical_record_set_sha256="c" * 64,
        ),
    )

    return NvdAuthoritativeWatermarkPromotionResultV1(
        status="committed",
        update_id=UPDATE_ID,
        persisted=NvdPersistedAuthoritativeWatermarkV1(
            watermark=watermark,
            version_id="watermark-version-2",
            etag='"watermark-etag-2"',
            sha256="d" * 64,
            size_bytes=900,
        ),
    )


class _EvidenceLoader:
    """Return one deterministic promotion evidence bundle."""

    def __init__(self) -> None:
        self.references: list[NvdSilverCompleteRefV1] = []

    def load(
        self,
        *,
        silver_complete: NvdSilverCompleteRefV1,
    ) -> NvdWatermarkPromotionEvidenceV1:
        """Capture the trigger and return exact persisted evidence."""
        self.references.append(silver_complete)
        return NvdWatermarkPromotionEvidenceV1(
            candidate=_candidate(),
            silver_manifest=_silver_manifest(),
            silver_parquet=_silver_parquet(),
        )


class _PromotionService:
    """Capture exact evidence forwarded to the final promotion service."""

    def __init__(self) -> None:
        self.calls: list[
            tuple[
                NvdWatermarkCandidate,
                NvdPersistedObjectPayloadV1,
                NvdPersistedObjectPayloadV1,
            ]
        ] = []

    def promote(
        self,
        *,
        candidate: NvdWatermarkCandidate,
        silver_manifest: NvdPersistedObjectPayloadV1,
        silver_parquet: NvdPersistedObjectPayloadV1,
    ) -> NvdAuthoritativeWatermarkPromotionResultV1:
        """Require and capture the exact typed promotion evidence."""
        self.calls.append(
            (
                candidate,
                silver_manifest,
                silver_parquet,
            )
        )
        return _result()


def test_runtime_loads_exact_evidence_then_promotes_it() -> None:
    """Keep the Lambda boundary free of evidence reconstruction logic."""
    loader = _EvidenceLoader()
    promoter = _PromotionService()
    reference = NvdSilverCompleteRefV1(
        key=_silver_manifest().key,
        version_id=_silver_manifest().version_id,
    )

    result = NvdWatermarkPromotionRuntimeV1(
        evidence_loader=loader,
        promotion_service=promoter,
    ).process(
        silver_complete=reference,
    )

    assert result == _result()
    assert loader.references == [reference]
    assert len(promoter.calls) == 1
    assert promoter.calls[0][0] == _candidate()
    assert promoter.calls[0][1] == _silver_manifest()
    assert promoter.calls[0][2] == _silver_parquet()
