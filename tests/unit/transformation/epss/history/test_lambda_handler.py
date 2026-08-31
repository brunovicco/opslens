"""Unit tests for the dedicated historical EPSS transformer Lambda boundary."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from datetime import date

import pytest

from opslens.transformation.epss.history.completion import (
    HistoricalEpssCompletionPersistenceResultV1,
    HistoricalEpssCompletionReplayStatus,
    HistoricalEpssCompletionStoredObjectV1,
)
from opslens.transformation.epss.history.invocation import HistoricalEpssInvocationResultV1
from opslens.transformation.epss.history.lambda_handler import execute_historical_event
from opslens.transformation.epss.history.models import (
    HistoricalEpssSilverPersistenceResultV1,
    HistoricalEpssSilverReplayStatus,
    HistoricalEpssSilverStoredObjectV1,
)


class FakeTelemetry:
    """Capture telemetry emitted by the historical transformer boundary."""

    def __init__(self) -> None:
        """Initialize telemetry collections."""
        self.info_events: list[str] = []
        self.exception_events: list[str] = []
        self.metrics: list[tuple[str, float, str]] = []
        self.spans: list[str] = []

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture an informational event."""
        self.info_events.append(message)

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture an exception event."""
        self.exception_events.append(message)

    def metric(self, name: str, value: float, unit: str) -> None:
        """Capture one metric."""
        self.metrics.append((name, value, unit))

    def span(self, name: str) -> AbstractContextManager[object]:
        """Capture one no-op span."""
        self.spans.append(name)
        return nullcontext()


class FakeHistoricalUseCase:
    """Return one deterministic historical invocation result or fail."""

    def __init__(self, *, failing: bool = False) -> None:
        """Initialize deterministic use-case behavior."""
        self._failing = failing
        self.calls: list[Mapping[str, object]] = []

    def execute(self, event: Mapping[str, object]) -> HistoricalEpssInvocationResultV1:
        """Return exact persisted evidence for one snapshot."""
        self.calls.append(event)
        if self._failing:
            raise RuntimeError("historical transform failed")

        snapshot_date = date(2021, 4, 14)
        silver = HistoricalEpssSilverStoredObjectV1(
            key="silver/epss/snapshot_date=2021-04-14/part-00000.parquet",
            version_id="silver-version-1",
            parquet_sha256="a" * 64,
            size_bytes=128,
            row_count=2,
            schema_version=2,
        )
        completion = HistoricalEpssCompletionStoredObjectV1(
            key=(
                "silver/epss-history/completions/schema_version=1/"
                "archive_commit=7ba701f5599057c496489ceecd701cbd43911f5c/"
                "snapshot_date=2021-04-14/manifest.json"
            ),
            version_id="completion-version-1",
            sha256="b" * 64,
            size_bytes=256,
        )
        return HistoricalEpssInvocationResultV1(
            snapshot_date=snapshot_date,
            silver=HistoricalEpssSilverPersistenceResultV1(
                stored_object=silver,
                replay_status=HistoricalEpssSilverReplayStatus.CREATED,
            ),
            completion=HistoricalEpssCompletionPersistenceResultV1(
                stored_object=completion,
                replay_status=HistoricalEpssCompletionReplayStatus.CREATED,
            ),
        )


def _event() -> dict[str, object]:
    """Build one exact explicit historical invocation event."""
    return {
        "schema_version": "1",
        "bronze_manifest_key": (
            "bronze/epss-history/schema_version=1/"
            "archive_commit=7ba701f5599057c496489ceecd701cbd43911f5c/"
            "snapshot_date=2021-04-14/manifest.json"
        ),
        "bronze_manifest_version_id": "manifest-version-1",
    }


def test_serializes_exact_persistence_evidence_with_lambda_request_id() -> None:
    """Return exact Silver/completion coordinates to the synchronous coordinator."""
    use_case = FakeHistoricalUseCase()
    telemetry = FakeTelemetry()
    event = _event()

    response = execute_historical_event(
        event=event,
        use_case=use_case,
        telemetry=telemetry,
        request_id="lambda-request-123",
    )

    assert use_case.calls == [event]
    assert response == {
        "request_id": "lambda-request-123",
        "snapshot_date": "2021-04-14",
        "silver_key": "silver/epss/snapshot_date=2021-04-14/part-00000.parquet",
        "silver_version_id": "silver-version-1",
        "silver_sha256": "a" * 64,
        "silver_replay_status": "created",
        "completion_key": (
            "silver/epss-history/completions/schema_version=1/"
            "archive_commit=7ba701f5599057c496489ceecd701cbd43911f5c/"
            "snapshot_date=2021-04-14/manifest.json"
        ),
        "completion_version_id": "completion-version-1",
        "completion_sha256": "b" * 64,
        "completion_replay_status": "created",
    }
    assert ("EpssHistoryTransformerSuccess", 1.0, "Count") in telemetry.metrics
    assert telemetry.exception_events == []


def test_propagates_failure_and_emits_failure_telemetry() -> None:
    """Keep deterministic transformation failure visible to RequestResponse caller."""
    telemetry = FakeTelemetry()

    with pytest.raises(RuntimeError, match="historical transform failed"):
        execute_historical_event(
            event=_event(),
            use_case=FakeHistoricalUseCase(failing=True),
            telemetry=telemetry,
            request_id="lambda-request-failure",
        )

    assert ("EpssHistoryTransformerFailure", 1.0, "Count") in telemetry.metrics
    assert "Historical EPSS transformer invocation failed" in telemetry.exception_events
    assert ("EpssHistoryTransformerSuccess", 1.0, "Count") not in telemetry.metrics
