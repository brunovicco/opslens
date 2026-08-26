"""Unit tests for authoritative NVD incremental runtime orchestration."""

from datetime import UTC, datetime, timedelta
from typing import cast

from opslens.ingestion.nvd.application.authoritative_watermark import (
    NvdAuthoritativeWatermarkV1,
    NvdWatermarkBootstrapRecoverySeedV1,
    NvdWatermarkEvidenceObjectV1,
)
from opslens.ingestion.nvd.application.authoritative_watermark_store import (
    NvdPersistedAuthoritativeWatermarkV1,
)
from opslens.ingestion.nvd.application.incremental_models import (
    NvdIncrementalIngestionResult,
)
from opslens.ingestion.nvd.application.incremental_runtime_plan import (
    NvdIncrementalRuntimePlannerV1,
    NvdIncrementalRuntimePlanStatus,
    NvdIncrementalRuntimeRequestV1,
)
from opslens.ingestion.nvd.application.incremental_runtime_service import (
    RunNvdIncrementalRuntimeV1,
)
from opslens.ingestion.nvd.domain.incremental import NvdIncrementalWindow


def _persisted_watermark(
    committed_through_at: datetime,
) -> NvdPersistedAuthoritativeWatermarkV1:
    """Build one realistic persisted authority snapshot."""
    bootstrap_manifest = NvdWatermarkEvidenceObjectV1(
        key=(
            "bronze/nvd/cve/bootstrap/"
            "feed_year=2026/feed_revision=test/manifest.json"
        ),
        version_id="bootstrap-manifest-version-1",
        sha256="a" * 64,
    )

    watermark = NvdAuthoritativeWatermarkV1(
        committed_through_at=committed_through_at,
        commit_basis=NvdWatermarkBootstrapRecoverySeedV1(
            source_revision_at=committed_through_at,
            bootstrap_manifest=bootstrap_manifest,
        ),
    )

    return NvdPersistedAuthoritativeWatermarkV1(
        watermark=watermark,
        version_id="watermark-version-1",
        etag='"watermark-etag-1"',
        sha256="b" * 64,
        size_bytes=621,
    )


class FakeWatermarkReader:
    """Return one controlled authoritative watermark snapshot."""

    def __init__(
        self,
        persisted: NvdPersistedAuthoritativeWatermarkV1,
    ) -> None:
        """Initialize the reader with one persisted authority snapshot."""
        self.persisted = persisted
        self.load_calls = 0

    def load(self) -> NvdPersistedAuthoritativeWatermarkV1:
        """Load the configured snapshot."""
        self.load_calls += 1
        return self.persisted


class FakeIncrementalIngestor:
    """Record windows submitted to Bronze ingestion."""

    def __init__(self) -> None:
        """Initialize an empty record of submitted windows."""
        self.windows: list[NvdIncrementalWindow] = []
        self.result = cast(
            NvdIncrementalIngestionResult,
            object(),
        )

    def execute(
        self,
        *,
        window: NvdIncrementalWindow,
    ) -> NvdIncrementalIngestionResult:
        """Record and accept one planned window."""
        self.windows.append(window)
        return self.result
    

def test_noop_reads_authority_without_running_ingestion() -> None:
    """Do no source or Bronze work when requested target is already committed."""
    committed_at = datetime(2026, 8, 18, 7, 0, 12, tzinfo=UTC)
    persisted = _persisted_watermark(committed_at)

    reader = FakeWatermarkReader(persisted)
    ingestor = FakeIncrementalIngestor()

    result = RunNvdIncrementalRuntimeV1(
        watermark_reader=reader,
        planner=NvdIncrementalRuntimePlannerV1(),
        ingestor=ingestor,
    ).execute(
        request=NvdIncrementalRuntimeRequestV1(
            target_end_at=committed_at,
        ),
    )

    assert reader.load_calls == 1
    assert ingestor.windows == []
    assert (
        result.plan.status
        is NvdIncrementalRuntimePlanStatus.NOOP_ALREADY_CURRENT
    )
    assert result.ingestion is None
    assert result.watermark_snapshot is persisted


def test_runtime_window_starts_from_authoritative_watermark() -> None:
    """Derive T0 only from the current persisted authority."""
    committed_at = datetime(2026, 8, 18, 7, 0, 12, tzinfo=UTC)
    target_end_at = datetime(2026, 8, 22, 23, 0, tzinfo=UTC)

    reader = FakeWatermarkReader(
        _persisted_watermark(committed_at)
    )
    ingestor = FakeIncrementalIngestor()

    result = RunNvdIncrementalRuntimeV1(
        watermark_reader=reader,
        planner=NvdIncrementalRuntimePlannerV1(),
        ingestor=ingestor,
    ).execute(
        request=NvdIncrementalRuntimeRequestV1(
            target_end_at=target_end_at,
        ),
    )

    assert reader.load_calls == 1
    assert ingestor.windows == [
        NvdIncrementalWindow(
            start_at=committed_at,
            end_at=target_end_at,
        )
    ]
    assert (
        result.plan.status
        is NvdIncrementalRuntimePlanStatus.WINDOW_READY
    )
    assert result.ingestion is ingestor.result


def test_runtime_executes_only_one_120_day_window_for_backlog() -> None:
    """Do not automatically chain multiple source windows in one invocation."""
    committed_at = datetime(2026, 1, 1, tzinfo=UTC)
    target_end_at = committed_at + timedelta(days=250)

    reader = FakeWatermarkReader(
        _persisted_watermark(committed_at)
    )
    ingestor = FakeIncrementalIngestor()

    RunNvdIncrementalRuntimeV1(
        watermark_reader=reader,
        planner=NvdIncrementalRuntimePlannerV1(),
        ingestor=ingestor,
    ).execute(
        request=NvdIncrementalRuntimeRequestV1(
            target_end_at=target_end_at,
        ),
    )

    assert ingestor.windows == [
        NvdIncrementalWindow(
            start_at=committed_at,
            end_at=committed_at + timedelta(days=120),
        )
    ]
