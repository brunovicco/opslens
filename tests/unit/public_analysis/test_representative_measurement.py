"""Tests for Gate 19.2 representative workload measurement contracts."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from opslens.public_analysis.application import (
    RepresentativeWorkloadPlan,
    measure_representative_workload,
)
from opslens.public_analysis.domain import (
    REPRESENTATIVE_PUBLIC_ANALYSIS_WORKLOAD_ID,
    REPRESENTATIVE_WORKLOAD_STAGE_ORDER,
    ProviderResourceUsage,
    PublicAnalysisValidationError,
    RepresentativeWorkloadStage,
)


@dataclass(slots=True)
class FakeClock:
    """Return deterministic monotonic readings one millisecond apart."""

    current_ns: int = 0
    scripted_values: list[int] = field(default_factory=lambda: list[int]())

    def monotonic_ns(self) -> int:
        """Return one scripted value or advance by one millisecond."""
        if self.scripted_values:
            return self.scripted_values.pop(0)
        self.current_ns += 1_000_000
        return self.current_ns


@dataclass(frozen=True, slots=True)
class FakeAction:
    """Return one fixed measured usage record for a representative stage."""

    stage: RepresentativeWorkloadStage
    usage: ProviderResourceUsage = field(default_factory=ProviderResourceUsage)

    def execute(self) -> ProviderResourceUsage:
        """Return the exact configured observation without external execution."""
        return self.usage


@dataclass(frozen=True, slots=True)
class FakeSerializer:
    """Return deterministic already-admitted result bytes."""

    payload: bytes = b'{"outcome":"ok"}'

    def serialize(self) -> bytes:
        """Return the configured result payload."""
        return self.payload


def _actions() -> tuple[FakeAction, ...]:
    """Build the exact Gate 19.2 stage order with representative counters."""
    usage_by_stage = {
        RepresentativeWorkloadStage.REPOSITORY_ACQUISITION: ProviderResourceUsage(
            github_http_request_count=4
        ),
        RepresentativeWorkloadStage.STRUCTURED_EVIDENCE: ProviderResourceUsage(
            athena_query_count=2,
            athena_bytes_scanned=4096,
        ),
        RepresentativeWorkloadStage.SEMANTIC_EVIDENCE: ProviderResourceUsage(
            bedrock_retrieve_count=1
        ),
        RepresentativeWorkloadStage.MODEL_REASONING: ProviderResourceUsage(
            bedrock_model_call_count=1,
            bedrock_input_tokens=320,
            bedrock_output_tokens=96,
            retry_count=1,
            throttle_count=1,
        ),
    }
    return tuple(
        FakeAction(stage=stage, usage=usage_by_stage.get(stage, ProviderResourceUsage()))
        for stage in REPRESENTATIVE_WORKLOAD_STAGE_ORDER
    )


def test_measures_complete_representative_workload() -> None:
    """Aggregate only concrete stage observations into one whole-run measurement."""
    measurement = measure_representative_workload(
        run_id="gate19-2-run-001",
        plan=RepresentativeWorkloadPlan(actions=_actions()),
        serializer=FakeSerializer(),
        clock=FakeClock(),
    )

    assert measurement.workload_id == REPRESENTATIVE_PUBLIC_ANALYSIS_WORKLOAD_ID
    assert tuple(item.stage for item in measurement.stage_measurements) == (
        REPRESENTATIVE_WORKLOAD_STAGE_ORDER
    )
    assert tuple(item.duration_ms for item in measurement.stage_measurements) == (1,) * 9
    assert measurement.end_to_end_duration_ms == 19
    assert measurement.serialized_result_bytes == len(b'{"outcome":"ok"}')
    assert measurement.provider_totals == ProviderResourceUsage(
        github_http_request_count=4,
        athena_query_count=2,
        athena_bytes_scanned=4096,
        bedrock_retrieve_count=1,
        bedrock_model_call_count=1,
        bedrock_input_tokens=320,
        bedrock_output_tokens=96,
        retry_count=1,
        throttle_count=1,
    )


def test_rejects_incomplete_or_reordered_stage_plan() -> None:
    """Keep the representative workload shape deterministic before measurement."""
    actions = _actions()
    reordered = (actions[1], actions[0], *actions[2:])

    with pytest.raises(ValueError, match="exact stage order"):
        RepresentativeWorkloadPlan(actions=reordered)


def test_rejects_negative_provider_measurement() -> None:
    """Never turn malformed counters into measured utilization evidence."""
    with pytest.raises(PublicAnalysisValidationError, match="non-negative integer"):
        ProviderResourceUsage(retry_count=-1)


def test_rejects_empty_serialized_result() -> None:
    """Require a concrete admitted result before response-size measurement is valid."""
    with pytest.raises(ValueError, match="non-empty bytes"):
        measure_representative_workload(
            run_id="gate19-2-run-empty-result",
            plan=RepresentativeWorkloadPlan(actions=_actions()),
            serializer=FakeSerializer(payload=b""),
            clock=FakeClock(),
        )


def test_rejects_clock_regression() -> None:
    """Fail closed when elapsed-time evidence cannot be trusted."""
    clock = FakeClock(scripted_values=[10, 20, 19])

    with pytest.raises(ValueError, match="moved backwards"):
        measure_representative_workload(
            run_id="gate19-2-run-bad-clock",
            plan=RepresentativeWorkloadPlan(actions=_actions()),
            serializer=FakeSerializer(),
            clock=clock,
        )
