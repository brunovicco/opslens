"""Unit tests for the bounded full historical EPSS backfill coordinator."""

import gzip
import hashlib
import inspect
from datetime import date

import pytest

from opslens.bootstrap.epss_history import (
    APPROVED_ARCHIVE_COMMIT,
    APPROVED_ROOT_TREE_SHA,
    ARCHIVE_REPOSITORY,
    HistoricalEpssArchiveInventoryV1,
    HistoricalEpssBootstrapPlanFactoryV1,
    HistoricalEpssBronzeInvocationCoordinateV1,
    HistoricalEpssTransformerResultV1,
    HistoricalEpssWorkItemV1,
)
from opslens.bootstrap.epss_history_backfill import (
    BACKFILL_CONFIRMATION,
    ExecuteHistoricalEpssBackfillV1,
    HistoricalEpssBackfillAuthorityV1,
)
from opslens.ingestion.epss.domain.history import EpssModelEra, HistoricalEpssSnapshot

BOUNDARY = date(2023, 3, 8)
DATES = (date(2021, 4, 14), date(2022, 2, 4), date(2023, 3, 7))


def _gzip(text: str) -> bytes:
    return gzip.compress(text.encode(), mtime=0)


def _source(snapshot_date: date) -> bytes:
    if snapshot_date == date(2021, 4, 14):
        return _gzip("cve,epss\nCVE-2020-5902,0.65117\n")
    model = "v2022.01.01" if snapshot_date.year == 2022 else "v2023.03.01"
    return _gzip(
        f"#model_version:{model},score_date:{snapshot_date.isoformat()}T00:00:00+00:00\n"
        "cve,epss,percentile\nCVE-2021-12345,0.01234,0.45678\n"
    )


def _git_blob_sha1(payload: bytes) -> str:
    return hashlib.sha1(
        f"blob {len(payload)}\0".encode() + payload,
        usedforsecurity=False,
    ).hexdigest()


def _inventory() -> tuple[HistoricalEpssArchiveInventoryV1, dict[date, bytes]]:
    sources = {value: _source(value) for value in DATES}
    items = tuple(
        HistoricalEpssWorkItemV1(
            snapshot_date=value,
            archive_path=f"{value.year}/epss_scores-{value.isoformat()}.csv.gz",
            archive_git_blob_sha1=_git_blob_sha1(sources[value]),
            compressed_size_bytes=len(sources[value]),
            model_era=EpssModelEra.for_snapshot_date(value),
        )
        for value in DATES
    )
    return (
        HistoricalEpssArchiveInventoryV1(
            archive_repository=ARCHIVE_REPOSITORY,
            archive_commit=APPROVED_ARCHIVE_COMMIT,
            root_tree_sha=APPROVED_ROOT_TREE_SHA,
            year_tree_shas=((2021, "1" * 40), (2022, "2" * 40), (2023, "3" * 40)),
            snapshots=items,
            source_absent_dates=(),
        ),
        sources,
    )


def _authority(inventory: HistoricalEpssArchiveInventoryV1) -> HistoricalEpssBackfillAuthorityV1:
    plan = HistoricalEpssBootstrapPlanFactoryV1().build(
        inventory=inventory,
        first_forward_snapshot_date=BOUNDARY,
    )
    return HistoricalEpssBackfillAuthorityV1(
        first_forward_snapshot_date=BOUNDARY,
        candidate_count=plan.candidate_count,
        candidate_compressed_bytes=plan.candidate_compressed_bytes,
        plan_id=plan.plan_id,
        source_absent_dates=(),
    )


class BoundaryReader:
    def __init__(self, events: list[str], boundary: date = BOUNDARY) -> None:
        self.events = events
        self.boundary = boundary

    def discover(self) -> date:
        self.events.append("boundary")
        return self.boundary


class InventoryReader:
    def __init__(self, events: list[str], inventory: HistoricalEpssArchiveInventoryV1) -> None:
        self.events = events
        self.inventory = inventory

    def read(self) -> HistoricalEpssArchiveInventoryV1:
        self.events.append("inventory")
        return self.inventory


class SourceReader:
    def __init__(self, events: list[str], sources: dict[date, bytes]) -> None:
        self.events = events
        self.sources = sources

    def read(self, work_item: HistoricalEpssWorkItemV1) -> bytes:
        self.events.append(f"source:{work_item.snapshot_date}")
        return self.sources[work_item.snapshot_date]


class Publisher:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def publish(
        self,
        *,
        work_item: HistoricalEpssWorkItemV1,
        snapshot: HistoricalEpssSnapshot,
    ) -> HistoricalEpssBronzeInvocationCoordinateV1:
        assert snapshot.snapshot_date == work_item.snapshot_date
        self.events.append(f"publish:{work_item.snapshot_date}")
        return HistoricalEpssBronzeInvocationCoordinateV1(
            snapshot_date=work_item.snapshot_date,
            manifest_key=f"manifest/{work_item.snapshot_date}",
            manifest_version_id=f"version-{work_item.snapshot_date}",
        )


class Invoker:
    def __init__(
        self,
        events: list[str],
        *,
        fail_on: date | None = None,
        replay_dates: frozenset[date] = frozenset(),
    ) -> None:
        self.events = events
        self.fail_on = fail_on
        self.replay_dates = replay_dates

    def invoke(
        self,
        coordinate: HistoricalEpssBronzeInvocationCoordinateV1,
    ) -> HistoricalEpssTransformerResultV1:
        snapshot_date = coordinate.snapshot_date
        self.events.append(f"invoke:{snapshot_date}")
        if snapshot_date == self.fail_on:
            raise RuntimeError("synthetic transformer failure")
        replay = "replay_verified" if snapshot_date in self.replay_dates else "created"
        suffix = snapshot_date.isoformat()
        return HistoricalEpssTransformerResultV1(
            snapshot_date=snapshot_date,
            request_id=f"request-{suffix}",
            silver_key=f"silver/epss/snapshot_date={suffix}/part-00000.parquet",
            silver_version_id=f"silver-version-{suffix}",
            silver_sha256="a" * 64,
            silver_replay_status=replay,
            completion_key=f"completion/{suffix}",
            completion_version_id=f"completion-version-{suffix}",
            completion_sha256="b" * 64,
            completion_replay_status=replay,
        )


def _coordinator(
    *,
    events: list[str],
    inventory: HistoricalEpssArchiveInventoryV1,
    sources: dict[date, bytes],
    boundary: date = BOUNDARY,
    invoker: Invoker | None = None,
) -> ExecuteHistoricalEpssBackfillV1:
    return ExecuteHistoricalEpssBackfillV1(
        forward_boundary_reader=BoundaryReader(events, boundary),
        archive_inventory_reader=InventoryReader(events, inventory),
        source_reader=SourceReader(events, sources),
        bronze_publisher=Publisher(events),
        transformer_invoker=invoker or Invoker(events),
        authority=_authority(inventory),
    )


def test_boundary_drift_fails_closed_before_source_or_write() -> None:
    inventory, sources = _inventory()
    events: list[str] = []
    coordinator = _coordinator(
        events=events,
        inventory=inventory,
        sources=sources,
        boundary=date(2023, 3, 9),
    )

    with pytest.raises(ValueError, match="frozen authority"):
        coordinator.execute(confirmation=BACKFILL_CONFIRMATION)

    assert events == ["boundary", "inventory"]


def test_executor_api_has_no_subset_or_concurrency_controls() -> None:
    init_parameters = inspect.signature(ExecuteHistoricalEpssBackfillV1.__init__).parameters
    execute_parameters = inspect.signature(ExecuteHistoricalEpssBackfillV1.execute).parameters

    assert "concurrency" not in init_parameters
    assert "work_items" not in init_parameters
    assert "dates" not in init_parameters
    assert set(execute_parameters) == {"self", "confirmation", "progress_reporter"}


def test_first_error_stops_before_later_snapshot() -> None:
    inventory, sources = _inventory()
    events: list[str] = []
    coordinator = _coordinator(
        events=events,
        inventory=inventory,
        sources=sources,
        invoker=Invoker(events, fail_on=DATES[1]),
    )

    with pytest.raises(RuntimeError, match="synthetic transformer failure"):
        coordinator.execute(confirmation=BACKFILL_CONFIRMATION)

    assert f"source:{DATES[2]}" not in events
    assert f"publish:{DATES[2]}" not in events
    assert f"invoke:{DATES[2]}" not in events


def test_resume_replays_completed_items_then_continues_in_order() -> None:
    inventory, sources = _inventory()
    events: list[str] = []
    coordinator = _coordinator(
        events=events,
        inventory=inventory,
        sources=sources,
        invoker=Invoker(events, replay_dates=frozenset({DATES[0]})),
    )

    result = coordinator.execute(confirmation=BACKFILL_CONFIRMATION)

    assert result.processed_snapshots == 3
    assert result.failed_snapshots == 0
    assert result.items[0].transformer.silver_replay_status == "replay_verified"
    assert result.items[0].transformer.completion_replay_status == "replay_verified"
    assert [item.work_item.snapshot_date for item in result.items] == list(DATES)
