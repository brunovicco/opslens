"""Unit tests for the bounded historical EPSS bootstrap coordinator."""

import gzip
import hashlib
from datetime import date

import pytest

from opslens.bootstrap.epss_history import (
    APPROVED_ARCHIVE_COMMIT,
    APPROVED_ROOT_TREE_SHA,
    ARCHIVE_REPOSITORY,
    CANARY_CONFIRMATION,
    CANARY_DATES,
    ExecuteHistoricalEpssCanaryV1,
    HistoricalEpssArchiveInventoryV1,
    HistoricalEpssBootstrapPlanFactoryV1,
    HistoricalEpssBronzeInvocationCoordinateV1,
    HistoricalEpssTransformerResultV1,
    HistoricalEpssWorkItemV1,
)
from opslens.ingestion.epss.domain.history import EpssModelEra, HistoricalEpssSnapshot

FORWARD_BOUNDARY = date(2026, 8, 15)


def _gzip(text: str) -> bytes:
    """Encode deterministic gzip source bytes for tests."""
    return gzip.compress(text.encode(), mtime=0)


def _source_for(snapshot_date: date) -> bytes:
    """Build one valid source shape for each frozen canary coordinate."""
    if snapshot_date == date(2021, 4, 14):
        return _gzip("cve,epss\nCVE-2020-5902,0.65117\n")
    if snapshot_date == date(2022, 2, 3):
        return _gzip("cve,epss,percentile\nCVE-2021-4034,0.04225,0.74118\n")

    model_version = {
        date(2022, 2, 4): "v2022.01.01",
        date(2023, 3, 7): "v2023.03.01",
        date(2025, 3, 17): "v2025.03.14",
        date(2026, 6, 15): "v2026.06.15",
        date(2026, 8, 14): "v2026.06.15",
    }[snapshot_date]
    return _gzip(
        f"#model_version:{model_version},score_date:{snapshot_date.isoformat()}T00:00:00+00:00\n"
        "cve,epss,percentile\n"
        "CVE-2021-12345,0.01234,0.45678\n"
    )


def _git_blob_sha1(payload: bytes) -> str:
    """Return Git blob identity for exact source bytes."""
    return hashlib.sha1(
        f"blob {len(payload)}\0".encode() + payload,
        usedforsecurity=False,
    ).hexdigest()


def _inventory() -> tuple[HistoricalEpssArchiveInventoryV1, dict[date, bytes]]:
    """Build an exact seven-snapshot pinned inventory and payload mapping."""
    sources = {snapshot_date: _source_for(snapshot_date) for snapshot_date in CANARY_DATES}
    items = tuple(
        HistoricalEpssWorkItemV1(
            snapshot_date=snapshot_date,
            archive_path=(
                f"{snapshot_date.year}/epss_scores-{snapshot_date.isoformat()}.csv.gz"
            ),
            archive_git_blob_sha1=_git_blob_sha1(sources[snapshot_date]),
            compressed_size_bytes=len(sources[snapshot_date]),
            model_era=EpssModelEra.for_snapshot_date(snapshot_date),
        )
        for snapshot_date in CANARY_DATES
    )
    return (
        HistoricalEpssArchiveInventoryV1(
            archive_repository=ARCHIVE_REPOSITORY,
            archive_commit=APPROVED_ARCHIVE_COMMIT,
            root_tree_sha=APPROVED_ROOT_TREE_SHA,
            year_tree_shas=tuple((year, f"{year - 2000:040x}") for year in range(2021, 2027)),
            snapshots=items,
            source_absent_dates=(),
        ),
        sources,
    )


class FakeBoundaryReader:
    """Return one configured forward boundary and capture read order."""

    def __init__(self, *, events: list[str], boundary: date = FORWARD_BOUNDARY) -> None:
        """Initialize deterministic boundary behavior."""
        self._events = events
        self._boundary = boundary

    def discover(self) -> date:
        """Return configured forward boundary."""
        self._events.append("boundary")
        return self._boundary


class FakeInventoryReader:
    """Return one pinned inventory and capture read order."""

    def __init__(self, *, events: list[str], inventory: HistoricalEpssArchiveInventoryV1) -> None:
        """Initialize deterministic inventory behavior."""
        self._events = events
        self._inventory = inventory

    def read(self) -> HistoricalEpssArchiveInventoryV1:
        """Return configured immutable inventory."""
        self._events.append("inventory")
        return self._inventory


class FakeSourceReader:
    """Return exact source bytes by snapshot date."""

    def __init__(self, *, events: list[str], sources: dict[date, bytes]) -> None:
        """Initialize source mapping."""
        self._events = events
        self._sources = sources

    def read(self, work_item: HistoricalEpssWorkItemV1) -> bytes:
        """Return source bytes and record sequential acquisition."""
        self._events.append(f"source:{work_item.snapshot_date.isoformat()}")
        return self._sources[work_item.snapshot_date]


class FakeBronzePublisher:
    """Return deterministic exact manifest coordinates."""

    def __init__(self, *, events: list[str]) -> None:
        """Initialize call capture."""
        self._events = events
        self.calls: list[date] = []

    def publish(
        self,
        *,
        work_item: HistoricalEpssWorkItemV1,
        snapshot: HistoricalEpssSnapshot,
    ) -> HistoricalEpssBronzeInvocationCoordinateV1:
        """Return exact deterministic invocation coordinate."""
        assert snapshot.snapshot_date == work_item.snapshot_date
        self.calls.append(work_item.snapshot_date)
        self._events.append(f"publish:{work_item.snapshot_date.isoformat()}")
        return HistoricalEpssBronzeInvocationCoordinateV1(
            snapshot_date=work_item.snapshot_date,
            manifest_key=f"manifest/{work_item.snapshot_date.isoformat()}",
            manifest_version_id=f"version-{work_item.snapshot_date.isoformat()}",
        )


class FakeTransformerInvoker:
    """Return deterministic transformation evidence and capture call order."""

    def __init__(self, *, events: list[str]) -> None:
        """Initialize call capture."""
        self._events = events
        self.calls: list[date] = []

    def invoke(
        self,
        coordinate: HistoricalEpssBronzeInvocationCoordinateV1,
    ) -> HistoricalEpssTransformerResultV1:
        """Return exact deterministic persisted evidence."""
        snapshot_date = coordinate.snapshot_date
        self.calls.append(snapshot_date)
        self._events.append(f"invoke:{snapshot_date.isoformat()}")
        suffix = snapshot_date.isoformat()
        return HistoricalEpssTransformerResultV1(
            snapshot_date=snapshot_date,
            request_id=f"request-{suffix}",
            silver_key=f"silver/epss/snapshot_date={suffix}/part-00000.parquet",
            silver_version_id=f"silver-version-{suffix}",
            silver_sha256="a" * 64,
            silver_replay_status="created",
            completion_key=f"completion/{suffix}",
            completion_version_id=f"completion-version-{suffix}",
            completion_sha256="b" * 64,
            completion_replay_status="created",
        )


def test_plan_id_is_deterministic_for_same_pinned_scope() -> None:
    """Freeze plan identity for the same inventory and forward boundary."""
    inventory, _ = _inventory()
    factory = HistoricalEpssBootstrapPlanFactoryV1()

    first = factory.build(
        inventory=inventory,
        first_forward_snapshot_date=FORWARD_BOUNDARY,
    )
    second = factory.build(
        inventory=inventory,
        first_forward_snapshot_date=FORWARD_BOUNDARY,
    )

    assert first.plan_id == second.plan_id
    assert first.canonical_bytes == second.canonical_bytes


def test_forward_boundary_is_part_of_plan_identity() -> None:
    """Require a fresh boundary change to regenerate canonical plan identity."""
    inventory, _ = _inventory()
    factory = HistoricalEpssBootstrapPlanFactoryV1()

    first = factory.build(
        inventory=inventory,
        first_forward_snapshot_date=FORWARD_BOUNDARY,
    )
    second = factory.build(
        inventory=inventory,
        first_forward_snapshot_date=date(2026, 8, 16),
    )

    assert first.plan_id != second.plan_id


def test_canary_selection_is_exactly_the_seven_frozen_dates() -> None:
    """Reject scope growth by selecting exactly the D1 canary coordinates."""
    inventory, _ = _inventory()
    plan = HistoricalEpssBootstrapPlanFactoryV1().build(
        inventory=inventory,
        first_forward_snapshot_date=FORWARD_BOUNDARY,
    )

    canary = HistoricalEpssBootstrapPlanFactoryV1.select_canary(plan)

    assert tuple(item.snapshot_date for item in canary.canary_items) == CANARY_DATES
    assert len(canary.canary_items) == 7


def test_invalid_confirmation_performs_no_reads_or_writes() -> None:
    """Fail before plan discovery when mutating confirmation is absent."""
    inventory, sources = _inventory()
    events: list[str] = []
    publisher = FakeBronzePublisher(events=events)
    invoker = FakeTransformerInvoker(events=events)
    coordinator = ExecuteHistoricalEpssCanaryV1(
        forward_boundary_reader=FakeBoundaryReader(events=events),
        archive_inventory_reader=FakeInventoryReader(events=events, inventory=inventory),
        source_reader=FakeSourceReader(events=events, sources=sources),
        bronze_publisher=publisher,
        transformer_invoker=invoker,
    )

    with pytest.raises(ValueError, match="confirmation"):
        coordinator.execute(confirmation="wrong")

    assert events == []
    assert publisher.calls == []
    assert invoker.calls == []


def test_executes_seven_snapshots_sequentially_after_plan_is_frozen() -> None:
    """Prove fresh-plan discovery occurs first and each source is invoked sequentially."""
    inventory, sources = _inventory()
    events: list[str] = []
    publisher = FakeBronzePublisher(events=events)
    invoker = FakeTransformerInvoker(events=events)
    coordinator = ExecuteHistoricalEpssCanaryV1(
        forward_boundary_reader=FakeBoundaryReader(events=events),
        archive_inventory_reader=FakeInventoryReader(events=events, inventory=inventory),
        source_reader=FakeSourceReader(events=events, sources=sources),
        bronze_publisher=publisher,
        transformer_invoker=invoker,
    )

    result = coordinator.execute(confirmation=CANARY_CONFIRMATION)

    assert events[:2] == ["boundary", "inventory"]
    expected_execution: list[str] = []
    for snapshot_date in CANARY_DATES:
        suffix = snapshot_date.isoformat()
        expected_execution.extend(
            [
                f"source:{suffix}",
                f"publish:{suffix}",
                f"invoke:{suffix}",
            ]
        )
    assert events[2:] == expected_execution
    assert tuple(publisher.calls) == CANARY_DATES
    assert tuple(invoker.calls) == CANARY_DATES
    assert len(result.items) == 7
    assert result.first_forward_snapshot_date == FORWARD_BOUNDARY


def test_git_blob_mismatch_fails_before_first_bronze_write() -> None:
    """Reject changed archive bytes before any historical AWS mutation boundary."""
    inventory, sources = _inventory()
    first_date = CANARY_DATES[0]
    original = sources[first_date]
    sources[first_date] = original[:-1] + bytes([original[-1] ^ 1])
    events: list[str] = []
    publisher = FakeBronzePublisher(events=events)
    coordinator = ExecuteHistoricalEpssCanaryV1(
        forward_boundary_reader=FakeBoundaryReader(events=events),
        archive_inventory_reader=FakeInventoryReader(events=events, inventory=inventory),
        source_reader=FakeSourceReader(events=events, sources=sources),
        bronze_publisher=publisher,
        transformer_invoker=FakeTransformerInvoker(events=events),
    )

    with pytest.raises(ValueError, match="Git blob identity"):
        coordinator.execute(confirmation=CANARY_CONFIRMATION)

    assert publisher.calls == []
