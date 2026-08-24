"""Orchestrate one NVD incremental runtime attempt from authoritative state."""

from dataclasses import dataclass
from typing import Protocol

from opslens.ingestion.nvd.application.authoritative_watermark_store import (
    NvdPersistedAuthoritativeWatermarkV1,
)
from opslens.ingestion.nvd.application.incremental_models import (
    NvdIncrementalIngestionResult,
)
from opslens.ingestion.nvd.application.incremental_runtime_plan import (
    NvdIncrementalRuntimePlannerV1,
    NvdIncrementalRuntimePlanStatus,
    NvdIncrementalRuntimePlanV1,
    NvdIncrementalRuntimeRequestV1,
)
from opslens.ingestion.nvd.domain.incremental import NvdIncrementalWindow


class NvdAuthoritativeWatermarkReaderV1(Protocol):
    """Expose only the authority capability required by incremental runtime."""

    def load(self) -> NvdPersistedAuthoritativeWatermarkV1:
        """Load the current authoritative watermark."""
        ...


class NvdIncrementalWindowIngestorV1(Protocol):
    """Execute one already-authorized incremental Bronze window."""

    def execute(
        self,
        *,
        window: NvdIncrementalWindow,
    ) -> NvdIncrementalIngestionResult:
        """Ingest one deterministic incremental window."""
        ...


@dataclass(frozen=True, slots=True)
class NvdIncrementalRuntimeResultV1:
    """Expose authority, planning, and optional Bronze completion evidence."""

    watermark_snapshot: NvdPersistedAuthoritativeWatermarkV1
    plan: NvdIncrementalRuntimePlanV1
    ingestion: NvdIncrementalIngestionResult | None

    def __post_init__(self) -> None:
        """Require execution evidence to match the planning outcome."""
        if (
            self.plan.status
            is NvdIncrementalRuntimePlanStatus.NOOP_ALREADY_CURRENT
        ):
            if self.ingestion is not None:
                raise ValueError(
                    "NVD incremental NOOP runtime result must not contain "
                    "ingestion evidence."
                )
            return

        if self.plan.status is NvdIncrementalRuntimePlanStatus.WINDOW_READY:
            if self.ingestion is None:
                raise ValueError(
                    "NVD incremental WINDOW_READY runtime result requires "
                    "ingestion evidence."
                )
            return

        raise ValueError(
            "Unsupported NVD incremental runtime result status."
        )


class RunNvdIncrementalRuntimeV1:
    """Run at most one incremental window from current temporal authority."""

    def __init__(
        self,
        *,
        watermark_reader: NvdAuthoritativeWatermarkReaderV1,
        planner: NvdIncrementalRuntimePlannerV1,
        ingestor: NvdIncrementalWindowIngestorV1,
    ) -> None:
        """Initialize explicit runtime dependencies."""
        self._watermark_reader = watermark_reader
        self._planner = planner
        self._ingestor = ingestor

    def execute(
        self,
        *,
        request: NvdIncrementalRuntimeRequestV1,
    ) -> NvdIncrementalRuntimeResultV1:
        """Read authority, plan one bounded window, and optionally ingest it."""
        watermark_snapshot = self._watermark_reader.load()

        plan = self._planner.plan(
            committed_through_at=(
                watermark_snapshot.watermark.committed_through_at
            ),
            request=request,
        )

        if (
            plan.status
            is NvdIncrementalRuntimePlanStatus.NOOP_ALREADY_CURRENT
        ):
            return NvdIncrementalRuntimeResultV1(
                watermark_snapshot=watermark_snapshot,
                plan=plan,
                ingestion=None,
            )

        window = plan.window

        if window is None:
            raise RuntimeError(
                "NVD incremental WINDOW_READY plan is missing its window."
            )

        ingestion = self._ingestor.execute(
            window=window,
        )

        return NvdIncrementalRuntimeResultV1(
            watermark_snapshot=watermark_snapshot,
            plan=plan,
            ingestion=ingestion,
        )
