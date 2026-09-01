"""Bounded Phase 2.5D-5 historical EPSS full-backfill coordination."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from typing import Callable
from uuid import UUID, uuid4

from opslens.bootstrap.epss_history import (
    APPROVED_ARCHIVE_COMMIT,
    HistoricalEpssArchiveInventoryReader,
    HistoricalEpssBootstrapPlanFactoryV1,
    HistoricalEpssBootstrapPlanV1,
    HistoricalEpssBronzePublisher,
    HistoricalEpssForwardBoundaryReader,
    HistoricalEpssSourceReader,
    HistoricalEpssTransformerInvoker,
    HistoricalEpssTransformerResultV1,
    HistoricalEpssWorkItemV1,
)
from opslens.ingestion.epss.domain.history import HistoricalEpssSnapshot, HistoricalEpssSnapshotParser

BACKFILL_CONFIRMATION = "EPSS-HISTORY-FULL-1939"
FROZEN_FIRST_FORWARD_SNAPSHOT_DATE = date(2026, 8, 14)
FROZEN_CANDIDATE_COUNT = 1939
FROZEN_CANDIDATE_COMPRESSED_BYTES = 2_537_138_865
FROZEN_PLAN_ID = "3b3c8c58009f46b61f6bb9e82f6b6c0bcf675e72b940326d7fcccf962d7bd4de"
FROZEN_SOURCE_ABSENT_DATES = (
    date(2021, 4, 22),
    date(2021, 4, 23),
    date(2021, 4, 24),
    date(2021, 4, 25),
    date(2021, 4, 26),
    date(2021, 6, 7),
    date(2021, 6, 18),
    date(2022, 7, 14),
    date(2024, 12, 1),
)


@dataclass(frozen=True, slots=True)
class HistoricalEpssBackfillAuthorityV1:
    """Represent the reviewed immutable authority required before mutation."""

    first_forward_snapshot_date: date = FROZEN_FIRST_FORWARD_SNAPSHOT_DATE
    candidate_count: int = FROZEN_CANDIDATE_COUNT
    candidate_compressed_bytes: int = FROZEN_CANDIDATE_COMPRESSED_BYTES
    plan_id: str = FROZEN_PLAN_ID
    source_absent_dates: tuple[date, ...] = FROZEN_SOURCE_ABSENT_DATES

    def validate(self, plan: HistoricalEpssBootstrapPlanV1) -> None:
        """Fail closed when fresh evidence differs from the reviewed authority."""
        mismatches: list[str] = []
        if plan.first_forward_snapshot_date != self.first_forward_snapshot_date:
            mismatches.append("first_forward_snapshot_date")
        if plan.candidate_count != self.candidate_count:
            mismatches.append("candidate_count")
        if plan.candidate_compressed_bytes != self.candidate_compressed_bytes:
            mismatches.append("candidate_compressed_bytes")
        if plan.plan_id != self.plan_id:
            mismatches.append("plan_id")
        if plan.source_absent_dates != self.source_absent_dates:
            mismatches.append("source_absent_dates")
        if mismatches:
            raise ValueError(
                "Historical EPSS full-backfill fresh plan differs from frozen authority: "
                + ", ".join(mismatches)
            )


@dataclass(frozen=True, slots=True)
class HistoricalEpssBackfillItemResultV1:
    """Bind one work item to exact persisted transformation evidence."""

    ordinal: int
    total: int
    work_item: HistoricalEpssWorkItemV1
    source_sha256: str
    bronze_manifest_key: str
    bronze_manifest_version_id: str
    transformer: HistoricalEpssTransformerResultV1

    def __post_init__(self) -> None:
        """Validate progress identity and work-result alignment."""
        if self.ordinal < 1 or self.total < 1 or self.ordinal > self.total:
            raise ValueError("Historical EPSS backfill ordinal is invalid.")
        if self.transformer.snapshot_date != self.work_item.snapshot_date:
            raise ValueError("Historical EPSS backfill transformer snapshot does not match work item.")
        if len(self.source_sha256) != 64:
            raise ValueError("Historical EPSS backfill source SHA-256 is invalid.")
        if not self.bronze_manifest_key.strip() or not self.bronze_manifest_version_id.strip():
            raise ValueError("Historical EPSS backfill Bronze manifest evidence is incomplete.")


@dataclass(frozen=True, slots=True)
class HistoricalEpssBackfillRunResultV1:
    """Represent one complete deterministic full-backfill execution attempt."""

    plan_id: str
    run_id: str
    first_forward_snapshot_date: date
    processed_snapshots: int
    failed_snapshots: int
    items: tuple[HistoricalEpssBackfillItemResultV1, ...]

    def __post_init__(self) -> None:
        """Validate terminal execution evidence."""
        try:
            UUID(self.run_id)
        except ValueError as exc:
            raise ValueError("Historical EPSS backfill run_id must be a UUID.") from exc
        if self.processed_snapshots != len(self.items):
            raise ValueError("Historical EPSS backfill processed count does not match results.")
        if self.failed_snapshots != 0:
            raise ValueError("Successful historical EPSS backfill result cannot contain failures.")


ProgressReporter = Callable[[HistoricalEpssBackfillItemResultV1], None]


class ExecuteHistoricalEpssBackfillV1:
    """Execute every frozen historical candidate sequentially and fail on first error."""

    def __init__(
        self,
        *,
        forward_boundary_reader: HistoricalEpssForwardBoundaryReader,
        archive_inventory_reader: HistoricalEpssArchiveInventoryReader,
        source_reader: HistoricalEpssSourceReader,
        bronze_publisher: HistoricalEpssBronzePublisher,
        transformer_invoker: HistoricalEpssTransformerInvoker,
        plan_factory: HistoricalEpssBootstrapPlanFactoryV1 | None = None,
        snapshot_parser: HistoricalEpssSnapshotParser | None = None,
        authority: HistoricalEpssBackfillAuthorityV1 | None = None,
    ) -> None:
        """Initialize fixed-scope dependencies; no subset or concurrency input exists."""
        self._forward_boundary_reader = forward_boundary_reader
        self._archive_inventory_reader = archive_inventory_reader
        self._source_reader = source_reader
        self._bronze_publisher = bronze_publisher
        self._transformer_invoker = transformer_invoker
        self._plan_factory = plan_factory or HistoricalEpssBootstrapPlanFactoryV1()
        self._snapshot_parser = snapshot_parser or HistoricalEpssSnapshotParser()
        self._authority = authority or HistoricalEpssBackfillAuthorityV1()

    def prepare(self) -> HistoricalEpssBootstrapPlanV1:
        """Rebuild the full plan from fresh boundary plus immutable Git inventory."""
        first_forward_snapshot_date = self._forward_boundary_reader.discover()
        inventory = self._archive_inventory_reader.read()
        plan = self._plan_factory.build(
            inventory=inventory,
            first_forward_snapshot_date=first_forward_snapshot_date,
        )
        self._authority.validate(plan)
        return plan

    def execute(
        self,
        *,
        confirmation: str,
        progress_reporter: ProgressReporter | None = None,
    ) -> HistoricalEpssBackfillRunResultV1:
        """Execute all plan work items in ascending order with coordinator concurrency one."""
        if confirmation != BACKFILL_CONFIRMATION:
            raise ValueError("Historical EPSS full-backfill execution confirmation is invalid.")

        plan = self.prepare()
        run_id = str(uuid4())
        total = plan.candidate_count
        results: list[HistoricalEpssBackfillItemResultV1] = []

        for ordinal, work_item in enumerate(plan.work_items, start=1):
            source_bytes = self._source_reader.read(work_item)
            snapshot = self._validate_source(work_item=work_item, source_bytes=source_bytes)
            coordinate = self._bronze_publisher.publish(
                work_item=work_item,
                snapshot=snapshot,
            )
            if coordinate.snapshot_date != work_item.snapshot_date:
                raise ValueError(
                    "Historical EPSS Bronze coordinate snapshot date does not match work item."
                )
            transformer = self._transformer_invoker.invoke(coordinate)
            result = HistoricalEpssBackfillItemResultV1(
                ordinal=ordinal,
                total=total,
                work_item=work_item,
                source_sha256=snapshot.sha256,
                bronze_manifest_key=coordinate.manifest_key,
                bronze_manifest_version_id=coordinate.manifest_version_id,
                transformer=transformer,
            )
            results.append(result)
            if progress_reporter is not None:
                progress_reporter(result)

        return HistoricalEpssBackfillRunResultV1(
            plan_id=plan.plan_id,
            run_id=run_id,
            first_forward_snapshot_date=plan.first_forward_snapshot_date,
            processed_snapshots=len(results),
            failed_snapshots=0,
            items=tuple(results),
        )

    def _validate_source(
        self,
        *,
        work_item: HistoricalEpssWorkItemV1,
        source_bytes: bytes,
    ) -> HistoricalEpssSnapshot:
        """Verify size, Git blob identity, parser contract, and model era before Bronze."""
        if len(source_bytes) != work_item.compressed_size_bytes:
            raise ValueError("Historical EPSS source size does not match pinned Git metadata.")
        git_blob_sha1 = hashlib.sha1(
            f"blob {len(source_bytes)}\0".encode() + source_bytes,
            usedforsecurity=False,
        ).hexdigest()
        if git_blob_sha1 != work_item.archive_git_blob_sha1:
            raise ValueError("Historical EPSS source Git blob identity does not match pinned metadata.")
        snapshot = self._snapshot_parser.parse(
            source_bytes,
            snapshot_date=work_item.snapshot_date,
        )
        if snapshot.model_era is not work_item.model_era:
            raise ValueError("Historical EPSS parsed model era does not match work item.")
        return snapshot


def frozen_backfill_plan_summary(plan: HistoricalEpssBootstrapPlanV1) -> dict[str, object]:
    """Serialize read-only full-plan evidence for the D5-B gate."""
    return {
        "mode": "plan",
        "archive_commit": APPROVED_ARCHIVE_COMMIT,
        "first_forward_snapshot_date": plan.first_forward_snapshot_date.isoformat(),
        "candidate_count": plan.candidate_count,
        "candidate_compressed_bytes": plan.candidate_compressed_bytes,
        "source_absent_dates": [value.isoformat() for value in plan.source_absent_dates],
        "plan_id": plan.plan_id,
        "execution_order": "snapshot_date_ascending",
        "coordinator_concurrency": 1,
    }
