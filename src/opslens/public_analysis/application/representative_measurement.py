"""Provider-neutral non-public harness for representative workload measurement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from opslens.public_analysis.domain.representative_measurement import (
    REPRESENTATIVE_PUBLIC_ANALYSIS_WORKLOAD_ID,
    REPRESENTATIVE_WORKLOAD_STAGE_ORDER,
    ProviderResourceUsage,
    RepresentativeStageMeasurement,
    RepresentativeWorkloadMeasurement,
    RepresentativeWorkloadStage,
    sum_provider_usage,
)


class MeasurementClock(Protocol):
    """Injected monotonic clock used only for elapsed-time measurement."""

    def monotonic_ns(self) -> int:
        """Return one monotonic clock reading in nanoseconds."""
        ...


class RepresentativeStageAction(Protocol):
    """One non-public executable stage with explicit measured resource usage."""

    @property
    def stage(self) -> RepresentativeWorkloadStage:
        """Return the exact stage executed by this action."""
        ...

    def execute(self) -> ProviderResourceUsage:
        """Execute the stage and return only counters measured by that execution."""
        ...


class AdmittedResultSerializer(Protocol):
    """Serialize the final already-admitted product result for byte measurement."""

    def serialize(self) -> bytes:
        """Return the final deterministic serialized result bytes."""
        ...


@dataclass(frozen=True, slots=True)
class RepresentativeWorkloadPlan:
    """Exact ordered stage plan for one Gate 19.2 non-public run."""

    actions: tuple[RepresentativeStageAction, ...]

    def __post_init__(self) -> None:
        """Reject incomplete, duplicate, or reordered representative stage plans."""
        observed = tuple(action.stage for action in self.actions)
        if observed != REPRESENTATIVE_WORKLOAD_STAGE_ORDER:
            raise ValueError("representative workload plan must use the exact stage order")


def measure_representative_workload(
    *,
    run_id: str,
    plan: RepresentativeWorkloadPlan,
    serializer: AdmittedResultSerializer,
    clock: MeasurementClock,
) -> RepresentativeWorkloadMeasurement:
    """Execute one non-public plan and return only concrete observed measurements."""
    run_started_ns = _clock_read(clock)
    stages: list[RepresentativeStageMeasurement] = []

    for action in plan.actions:
        stage_started_ns = _clock_read(clock)
        usage = action.execute()
        stage_ended_ns = _clock_read(clock)
        stages.append(
            RepresentativeStageMeasurement(
                stage=action.stage,
                duration_ms=_elapsed_ms(stage_started_ns, stage_ended_ns),
                usage=usage,
            )
        )

    serialized_result = serializer.serialize()
    if type(serialized_result) is not bytes or not serialized_result:
        raise ValueError("admitted result serializer must return non-empty bytes")

    run_ended_ns = _clock_read(clock)
    measurements = tuple(stages)
    return RepresentativeWorkloadMeasurement(
        run_id=run_id,
        workload_id=REPRESENTATIVE_PUBLIC_ANALYSIS_WORKLOAD_ID,
        stage_measurements=measurements,
        end_to_end_duration_ms=_elapsed_ms(run_started_ns, run_ended_ns),
        serialized_result_bytes=len(serialized_result),
        provider_totals=sum_provider_usage(measurements),
    )


def _clock_read(clock: MeasurementClock) -> int:
    """Read the injected clock and reject invalid values or clock failures."""
    try:
        value = clock.monotonic_ns()
    except Exception as exc:
        raise ValueError("measurement clock failed") from exc
    if type(value) is not int or value < 0:
        raise ValueError("measurement clock must return a non-negative integer")
    return value


def _elapsed_ms(started_ns: int, ended_ns: int) -> int:
    """Convert a monotonic nanosecond interval to integer milliseconds."""
    if ended_ns < started_ns:
        raise ValueError("measurement clock moved backwards")
    return (ended_ns - started_ns) // 1_000_000
