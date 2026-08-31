"""Deterministic Phase 2.5D historical EPSS bootstrap coordination."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID, uuid4

from opslens.ingestion.epss.domain.history import (
    EpssModelEra,
    HistoricalEpssSnapshot,
    HistoricalEpssSnapshotParser,
)

ARCHIVE_REPOSITORY = "empiricalsec/epss_scores"
APPROVED_ARCHIVE_COMMIT = "7ba701f5599057c496489ceecd701cbd43911f5c"
APPROVED_ROOT_TREE_SHA = "2a12b2030cda9b94573bca01b67a6f0d72ab71e8"
CANARY_CONFIRMATION = "EPSS-HISTORY-CANARY-7"
CANARY_DATES = (
    date(2021, 4, 14),
    date(2022, 2, 3),
    date(2022, 2, 4),
    date(2023, 3, 7),
    date(2025, 3, 17),
    date(2026, 6, 15),
    date(2026, 8, 14),
)
CANARY_MAX_SOURCE_BYTES = 10 * 1024 * 1024
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class HistoricalEpssWorkItemV1:
    """Represent one immutable historical EPSS archive work coordinate."""

    snapshot_date: date
    archive_path: str
    archive_git_blob_sha1: str
    compressed_size_bytes: int
    model_era: EpssModelEra

    def __post_init__(self) -> None:
        """Validate immutable archive coordinates."""
        expected_path = (
            f"{self.snapshot_date.year}/epss_scores-{self.snapshot_date.isoformat()}.csv.gz"
        )
        if self.archive_path != expected_path:
            raise ValueError("Historical EPSS work item archive path is not canonical.")
        if _SHA1_RE.fullmatch(self.archive_git_blob_sha1) is None:
            raise ValueError("Historical EPSS work item Git blob SHA-1 is invalid.")
        if self.compressed_size_bytes <= 0:
            raise ValueError("Historical EPSS work item compressed size must be positive.")
        if self.model_era is not EpssModelEra.for_snapshot_date(self.snapshot_date):
            raise ValueError("Historical EPSS work item model era does not match snapshot date.")


@dataclass(frozen=True, slots=True)
class HistoricalEpssArchiveInventoryV1:
    """Represent exact pinned Git metadata used to build a bootstrap plan."""

    archive_repository: str
    archive_commit: str
    root_tree_sha: str
    year_tree_shas: tuple[tuple[int, str], ...]
    snapshots: tuple[HistoricalEpssWorkItemV1, ...]
    source_absent_dates: tuple[date, ...]

    def __post_init__(self) -> None:
        """Validate the pinned inventory authority."""
        if self.archive_repository != ARCHIVE_REPOSITORY:
            raise ValueError("Historical EPSS inventory repository is not approved.")
        if self.archive_commit != APPROVED_ARCHIVE_COMMIT:
            raise ValueError("Historical EPSS inventory commit is not approved.")
        if self.root_tree_sha != APPROVED_ROOT_TREE_SHA:
            raise ValueError("Historical EPSS inventory root tree is not approved.")
        years = [year for year, _ in self.year_tree_shas]
        if years != sorted(set(years)):
            raise ValueError("Historical EPSS year tree coordinates must be unique and sorted.")
        for _, tree_sha in self.year_tree_shas:
            if _SHA1_RE.fullmatch(tree_sha) is None:
                raise ValueError("Historical EPSS year tree SHA is invalid.")
        snapshot_dates = [item.snapshot_date for item in self.snapshots]
        if snapshot_dates != sorted(set(snapshot_dates)):
            raise ValueError("Historical EPSS snapshots must be unique and sorted.")
        absent_dates = list(self.source_absent_dates)
        if absent_dates != sorted(set(absent_dates)):
            raise ValueError("Historical EPSS source absences must be unique and sorted.")
        if set(snapshot_dates).intersection(absent_dates):
            raise ValueError("Historical EPSS snapshot cannot also be a source absence.")


@dataclass(frozen=True, slots=True)
class HistoricalEpssBootstrapPlanV1:
    """Represent one deterministic full historical bootstrap plan."""

    first_forward_snapshot_date: date
    work_items: tuple[HistoricalEpssWorkItemV1, ...]
    source_absent_dates: tuple[date, ...]
    candidate_compressed_bytes: int
    root_tree_sha: str
    year_tree_shas: tuple[tuple[int, str], ...]
    canonical_bytes: bytes
    plan_id: str

    def __post_init__(self) -> None:
        """Validate deterministic plan identity and workload totals."""
        if not self.work_items:
            raise ValueError("Historical EPSS bootstrap plan cannot be empty.")
        if self.candidate_compressed_bytes != sum(
            item.compressed_size_bytes for item in self.work_items
        ):
            raise ValueError("Historical EPSS bootstrap compressed-byte total is inconsistent.")
        if self.plan_id != hashlib.sha256(self.canonical_bytes).hexdigest():
            raise ValueError("Historical EPSS bootstrap plan_id does not match canonical bytes.")
        if _SHA256_RE.fullmatch(self.plan_id) is None:
            raise ValueError("Historical EPSS bootstrap plan_id is invalid.")
        if any(item.snapshot_date >= self.first_forward_snapshot_date for item in self.work_items):
            raise ValueError("Historical EPSS bootstrap plan overlaps forward authority.")

    @property
    def candidate_count(self) -> int:
        """Return the number of executable historical snapshots."""
        return len(self.work_items)


@dataclass(frozen=True, slots=True)
class HistoricalEpssCanaryPlanV1:
    """Bind the full deterministic plan to the frozen seven-snapshot slice."""

    plan: HistoricalEpssBootstrapPlanV1
    canary_items: tuple[HistoricalEpssWorkItemV1, ...]

    def __post_init__(self) -> None:
        """Require exactly the D1-authorized sequential canary scope."""
        if tuple(item.snapshot_date for item in self.canary_items) != CANARY_DATES:
            raise ValueError("Historical EPSS canary must contain exactly the seven frozen dates.")
        if sum(item.compressed_size_bytes for item in self.canary_items) > CANARY_MAX_SOURCE_BYTES:
            raise ValueError("Historical EPSS canary source bytes exceed the D1 cost guardrail.")


@dataclass(frozen=True, slots=True)
class HistoricalEpssBronzeInvocationCoordinateV1:
    """Represent exact Bronze manifest authority passed to the transformer."""

    snapshot_date: date
    manifest_key: str
    manifest_version_id: str

    def __post_init__(self) -> None:
        """Validate exact invocation coordinates."""
        if not self.manifest_key.strip() or not self.manifest_version_id.strip():
            raise ValueError("Historical EPSS Bronze invocation coordinate cannot be empty.")


@dataclass(frozen=True, slots=True)
class HistoricalEpssTransformerResultV1:
    """Represent the exact persisted result returned by one transformer invocation."""

    snapshot_date: date
    request_id: str
    silver_key: str
    silver_version_id: str
    silver_sha256: str
    silver_replay_status: str
    completion_key: str
    completion_version_id: str
    completion_sha256: str
    completion_replay_status: str

    def __post_init__(self) -> None:
        """Validate serialized transformer evidence."""
        for value in (
            self.request_id,
            self.silver_key,
            self.silver_version_id,
            self.silver_replay_status,
            self.completion_key,
            self.completion_version_id,
            self.completion_replay_status,
        ):
            if not value.strip():
                raise ValueError("Historical EPSS transformer result contains an empty field.")
        if _SHA256_RE.fullmatch(self.silver_sha256) is None:
            raise ValueError("Historical EPSS transformer Silver SHA-256 is invalid.")
        if _SHA256_RE.fullmatch(self.completion_sha256) is None:
            raise ValueError("Historical EPSS transformer completion SHA-256 is invalid.")


@dataclass(frozen=True, slots=True)
class HistoricalEpssCanaryItemResultV1:
    """Bind one canary work coordinate to its exact transformation evidence."""

    work_item: HistoricalEpssWorkItemV1
    source_sha256: str
    transformer: HistoricalEpssTransformerResultV1

    def __post_init__(self) -> None:
        """Require the transformer response to match the submitted snapshot."""
        if self.transformer.snapshot_date != self.work_item.snapshot_date:
            raise ValueError(
                "Historical EPSS transformer result snapshot date does not match work."
            )
        if _SHA256_RE.fullmatch(self.source_sha256) is None:
            raise ValueError("Historical EPSS canary source SHA-256 is invalid.")


@dataclass(frozen=True, slots=True)
class HistoricalEpssCanaryRunResultV1:
    """Represent one bounded seven-snapshot execution attempt."""

    plan_id: str
    run_id: str
    first_forward_snapshot_date: date
    items: tuple[HistoricalEpssCanaryItemResultV1, ...]

    def __post_init__(self) -> None:
        """Validate bounded run identity and result count."""
        if _SHA256_RE.fullmatch(self.plan_id) is None:
            raise ValueError("Historical EPSS canary run plan_id is invalid.")
        try:
            UUID(self.run_id)
        except ValueError as exc:
            raise ValueError("Historical EPSS canary run_id must be a UUID.") from exc
        if len(self.items) != len(CANARY_DATES):
            raise ValueError("Historical EPSS canary run must contain exactly seven results.")


class HistoricalEpssForwardBoundaryReader(Protocol):
    """Discover the earliest canonical forward EPSS snapshot in the target environment."""

    def discover(self) -> date:
        """Return the current earliest forward-authority snapshot date."""
        ...


class HistoricalEpssArchiveInventoryReader(Protocol):
    """Read immutable Git metadata for the approved historical archive pin."""

    def read(self) -> HistoricalEpssArchiveInventoryV1:
        """Return the exact sorted archive inventory."""
        ...


class HistoricalEpssSourceReader(Protocol):
    """Fetch one exact source artifact from the immutable archive coordinate."""

    def read(self, work_item: HistoricalEpssWorkItemV1) -> bytes:
        """Return exact compressed source bytes."""
        ...


class HistoricalEpssBronzePublisher(Protocol):
    """Persist exact source bytes and manifest evidence in historical Bronze."""

    def publish(
        self,
        *,
        work_item: HistoricalEpssWorkItemV1,
        snapshot: HistoricalEpssSnapshot,
    ) -> HistoricalEpssBronzeInvocationCoordinateV1:
        """Create or exact-replay-verify source and manifest evidence."""
        ...


class HistoricalEpssTransformerInvoker(Protocol):
    """Invoke the dedicated one-snapshot historical transformer synchronously."""

    def invoke(
        self,
        coordinate: HistoricalEpssBronzeInvocationCoordinateV1,
    ) -> HistoricalEpssTransformerResultV1:
        """Return exact synchronous transformer evidence."""
        ...


class HistoricalEpssBootstrapPlanFactoryV1:
    """Build canonical plan bytes from one pinned inventory and fresh boundary."""

    SCHEMA_VERSION = 1

    def build(
        self,
        *,
        inventory: HistoricalEpssArchiveInventoryV1,
        first_forward_snapshot_date: date,
    ) -> HistoricalEpssBootstrapPlanV1:
        """Filter the pinned archive strictly below fresh forward authority."""
        work_items = tuple(
            item
            for item in inventory.snapshots
            if item.snapshot_date < first_forward_snapshot_date
        )
        if not work_items:
            raise ValueError("Fresh forward boundary leaves no historical EPSS candidates.")

        source_absent_dates = tuple(
            snapshot_date
            for snapshot_date in inventory.source_absent_dates
            if snapshot_date < first_forward_snapshot_date
        )
        compressed_bytes = sum(item.compressed_size_bytes for item in work_items)
        document = {
            "archive_commit": inventory.archive_commit,
            "archive_repository": inventory.archive_repository,
            "candidate_compressed_bytes": compressed_bytes,
            "candidate_count": len(work_items),
            "first_forward_snapshot_date": first_forward_snapshot_date.isoformat(),
            "root_tree_sha": inventory.root_tree_sha,
            "schema_version": self.SCHEMA_VERSION,
            "source_absent_dates": [value.isoformat() for value in source_absent_dates],
            "work_items": [
                {
                    "archive_git_blob_sha1": item.archive_git_blob_sha1,
                    "archive_path": item.archive_path,
                    "compressed_size_bytes": item.compressed_size_bytes,
                    "model_era": item.model_era.value,
                    "snapshot_date": item.snapshot_date.isoformat(),
                }
                for item in work_items
            ],
            "year_tree_shas": [
                {"tree_sha": tree_sha, "year": year}
                for year, tree_sha in inventory.year_tree_shas
            ],
        }
        text = json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        canonical_bytes = f"{text}\n".encode()

        return HistoricalEpssBootstrapPlanV1(
            first_forward_snapshot_date=first_forward_snapshot_date,
            work_items=work_items,
            source_absent_dates=source_absent_dates,
            candidate_compressed_bytes=compressed_bytes,
            root_tree_sha=inventory.root_tree_sha,
            year_tree_shas=inventory.year_tree_shas,
            canonical_bytes=canonical_bytes,
            plan_id=hashlib.sha256(canonical_bytes).hexdigest(),
        )

    @staticmethod
    def select_canary(plan: HistoricalEpssBootstrapPlanV1) -> HistoricalEpssCanaryPlanV1:
        """Select exactly the seven D1-authorized snapshots from a full plan."""
        by_date = {item.snapshot_date: item for item in plan.work_items}
        missing = [
            snapshot_date
            for snapshot_date in CANARY_DATES
            if snapshot_date not in by_date
        ]
        if missing:
            formatted = ", ".join(value.isoformat() for value in missing)
            raise ValueError(
                "Historical EPSS canary dates are unavailable in fresh plan: "
                f"{formatted}."
            )
        return HistoricalEpssCanaryPlanV1(
            plan=plan,
            canary_items=tuple(by_date[snapshot_date] for snapshot_date in CANARY_DATES),
        )


class ExecuteHistoricalEpssCanaryV1:
    """Execute only the frozen seven-snapshot canary, sequentially and fail closed."""

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
    ) -> None:
        """Initialize explicit coordinator dependencies."""
        self._forward_boundary_reader = forward_boundary_reader
        self._archive_inventory_reader = archive_inventory_reader
        self._source_reader = source_reader
        self._bronze_publisher = bronze_publisher
        self._transformer_invoker = transformer_invoker
        self._plan_factory = plan_factory or HistoricalEpssBootstrapPlanFactoryV1()
        self._snapshot_parser = snapshot_parser or HistoricalEpssSnapshotParser()

    def prepare(self) -> HistoricalEpssCanaryPlanV1:
        """Revalidate target boundary and freeze a canonical plan before mutation."""
        first_forward_snapshot_date = self._forward_boundary_reader.discover()
        inventory = self._archive_inventory_reader.read()
        plan = self._plan_factory.build(
            inventory=inventory,
            first_forward_snapshot_date=first_forward_snapshot_date,
        )
        return self._plan_factory.select_canary(plan)

    def execute(self, *, confirmation: str) -> HistoricalEpssCanaryRunResultV1:
        """Execute exactly seven snapshots in deterministic sequential order."""
        if confirmation != CANARY_CONFIRMATION:
            raise ValueError("Historical EPSS canary execution confirmation is invalid.")

        canary = self.prepare()
        run_id = str(uuid4())
        results: list[HistoricalEpssCanaryItemResultV1] = []

        for work_item in canary.canary_items:
            source_bytes = self._source_reader.read(work_item)
            snapshot = self._validate_source(work_item=work_item, source_bytes=source_bytes)
            coordinate = self._bronze_publisher.publish(
                work_item=work_item,
                snapshot=snapshot,
            )
            if coordinate.snapshot_date != work_item.snapshot_date:
                raise ValueError(
                    "Historical EPSS Bronze coordinate snapshot date does not match work."
                )
            transformer = self._transformer_invoker.invoke(coordinate)
            results.append(
                HistoricalEpssCanaryItemResultV1(
                    work_item=work_item,
                    source_sha256=snapshot.sha256,
                    transformer=transformer,
                )
            )

        return HistoricalEpssCanaryRunResultV1(
            plan_id=canary.plan.plan_id,
            run_id=run_id,
            first_forward_snapshot_date=canary.plan.first_forward_snapshot_date,
            items=tuple(results),
        )

    def _validate_source(
        self,
        *,
        work_item: HistoricalEpssWorkItemV1,
        source_bytes: bytes,
    ) -> HistoricalEpssSnapshot:
        """Verify exact source size, Git identity, parser shape, and model era."""
        if len(source_bytes) != work_item.compressed_size_bytes:
            raise ValueError("Historical EPSS source size does not match pinned Git metadata.")
        git_blob_sha1 = hashlib.sha1(
            f"blob {len(source_bytes)}\0".encode() + source_bytes,
            usedforsecurity=False,
        ).hexdigest()
        if git_blob_sha1 != work_item.archive_git_blob_sha1:
            raise ValueError(
                "Historical EPSS source Git blob identity does not match pinned metadata."
            )
        snapshot = self._snapshot_parser.parse(
            source_bytes,
            snapshot_date=work_item.snapshot_date,
        )
        if snapshot.model_era is not work_item.model_era:
            raise ValueError("Historical EPSS parsed model era does not match work item.")
        return snapshot
