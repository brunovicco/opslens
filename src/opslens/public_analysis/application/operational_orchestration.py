"""Instrument the governed public-analysis boundary with bounded operational evidence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import NoReturn, Protocol

from opslens.public_analysis.application.evidence_orchestration import (
    PublicRepositoryEvidenceSource,
    build_public_repository_evidence,
)
from opslens.public_analysis.application.request_admission import (
    PublicAnalysisRequestAdmissionError,
    admit_public_analysis_request,
)
from opslens.public_analysis.application.semantic_planning import (
    PublicSemanticPlanAdmissionError,
    PublicSemanticPlanner,
    build_public_analysis_admission_handoff,
    build_public_semantic_planning_request,
    parse_public_semantic_plan_proposal,
    route_public_semantic_plan,
)
from opslens.public_analysis.domain import (
    PublicAnalysisAdmissionHandoff,
    PublicAnalysisValidationError,
)
from opslens.repository_intelligence.adapters.github_http import GitHubRestAcquisitionError
from opslens.repository_intelligence.domain import RepositoryIntelligenceContractError
from opslens.shared.observability.contracts import (
    OperationalEvent,
    OperationalFailureCategory,
    OperationalOutcome,
    OperationalStage,
    OperationalTelemetryValidationError,
    create_operational_event,
)

_EXPECTED_SUCCESS_STAGES = (
    OperationalStage.PUBLIC_REQUEST_ADMISSION,
    OperationalStage.REPOSITORY_EVIDENCE,
    OperationalStage.SEMANTIC_PLANNING,
    OperationalStage.HYBRID_ROUTE_ADMISSION,
    OperationalStage.PUBLIC_HANDOFF,
)


def _validate_delivery_accounting(
    *,
    events: tuple[OperationalEvent, ...],
    undelivered_event_ids: tuple[str, ...],
) -> None:
    """Require undelivered accounting to reference only admitted event identities."""
    if any(type(event) is not OperationalEvent for event in events):
        raise ValueError("operational evidence must contain only OperationalEvent objects")
    if any(type(event_id) is not str for event_id in undelivered_event_ids):
        raise ValueError("undelivered event identities must be strings")
    if len(set(undelivered_event_ids)) != len(undelivered_event_ids):
        raise ValueError("undelivered event identities cannot contain duplicates")
    admitted_ids = frozenset(event.event_id for event in events)
    if any(event_id not in admitted_ids for event_id in undelivered_event_ids):
        raise ValueError("undelivered identities must reference admitted events")


class MonotonicClock(Protocol):
    """Injected monotonic clock used only for bounded stage-duration accounting."""

    def monotonic_ns(self) -> int:
        """Return one monotonic nanosecond reading."""
        ...


class OperationalEventSink(Protocol):
    """Best-effort external delivery port for already-admitted operational events."""

    def emit(self, event: OperationalEvent) -> None:
        """Attempt delivery without acquiring business or execution authority."""
        ...


class PublicAnalysisInstrumentationFailure(StrEnum):
    """Bounded reasons why mandatory in-process instrumentation could not be built."""

    CLOCK_CONTRACT = "clock_contract"
    EVENT_CONTRACT = "event_contract"


class PublicAnalysisInstrumentationError(RuntimeError):
    """Raised when mandatory in-process operational evidence cannot be constructed."""

    def __init__(
        self,
        *,
        stage: OperationalStage,
        reason: PublicAnalysisInstrumentationFailure,
        events: tuple[OperationalEvent, ...],
        undelivered_event_ids: tuple[str, ...],
    ) -> None:
        """Preserve only bounded instrumentation state and previously admitted event IDs."""
        _validate_delivery_accounting(
            events=events,
            undelivered_event_ids=undelivered_event_ids,
        )
        super().__init__(
            f"public analysis instrumentation failed at {stage.value}: {reason.value}"
        )
        self.stage = stage
        self.reason = reason
        self.events = events
        self.undelivered_event_ids = undelivered_event_ids


class PublicAnalysisOperationalFailure(RuntimeError):
    """Raised after one governed business stage terminates with admitted evidence."""

    def __init__(
        self,
        *,
        stage: OperationalStage,
        events: tuple[OperationalEvent, ...],
        undelivered_event_ids: tuple[str, ...],
    ) -> None:
        """Expose bounded stage/event identities without copying arbitrary exception text."""
        _validate_delivery_accounting(
            events=events,
            undelivered_event_ids=undelivered_event_ids,
        )
        if not events or events[-1].stage is not stage:
            raise ValueError("operational failure requires a terminal event for its stage")
        if events[-1].outcome is OperationalOutcome.SUCCEEDED:
            raise ValueError("operational failure terminal event cannot be successful")
        super().__init__(f"public analysis stopped at {stage.value}")
        self.stage = stage
        self.events = events
        self.undelivered_event_ids = undelivered_event_ids

    @property
    def terminal_event(self) -> OperationalEvent:
        """Return the final rejected/failed event that stopped business execution."""
        return self.events[-1]


@dataclass(frozen=True, slots=True)
class PublicAnalysisOperationalExecution:
    """Successful Phase 9 handoff plus complete Gate 10.2 operational evidence."""

    handoff: PublicAnalysisAdmissionHandoff
    events: tuple[OperationalEvent, ...]
    undelivered_event_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject incomplete, reordered, failed, or cross-handoff operational evidence."""
        if type(self.handoff) is not PublicAnalysisAdmissionHandoff:
            raise ValueError("operational execution requires one admitted public handoff")
        if tuple(event.stage for event in self.events) != _EXPECTED_SUCCESS_STAGES:
            raise ValueError("successful operational execution requires the exact five stages")
        if any(event.outcome is not OperationalOutcome.SUCCEEDED for event in self.events):
            raise ValueError("successful operational execution cannot contain failed stages")
        if self.events[-1].handoff_id != self.handoff.handoff_id:
            raise ValueError("operational execution handoff identity drifted")
        _validate_delivery_accounting(
            events=self.events,
            undelivered_event_ids=self.undelivered_event_ids,
        )


def _clock_read(
    clock: MonotonicClock,
    *,
    stage: OperationalStage,
    events: list[OperationalEvent],
    undelivered_event_ids: list[str],
) -> int:
    """Read one injected clock value and fail closed on exceptions or malformed values."""
    try:
        value = clock.monotonic_ns()
    except Exception:
        raise PublicAnalysisInstrumentationError(
            stage=stage,
            reason=PublicAnalysisInstrumentationFailure.CLOCK_CONTRACT,
            events=tuple(events),
            undelivered_event_ids=tuple(undelivered_event_ids),
        ) from None
    if type(value) is not int or value < 0:
        raise PublicAnalysisInstrumentationError(
            stage=stage,
            reason=PublicAnalysisInstrumentationFailure.CLOCK_CONTRACT,
            events=tuple(events),
            undelivered_event_ids=tuple(undelivered_event_ids),
        )
    return value


def _duration_ms(
    clock: MonotonicClock,
    *,
    stage: OperationalStage,
    started_ns: int,
    events: list[OperationalEvent],
    undelivered_event_ids: list[str],
) -> int:
    """Convert monotonic nanoseconds into deterministic integer milliseconds."""
    ended_ns = _clock_read(
        clock,
        stage=stage,
        events=events,
        undelivered_event_ids=undelivered_event_ids,
    )
    if ended_ns < started_ns:
        raise PublicAnalysisInstrumentationError(
            stage=stage,
            reason=PublicAnalysisInstrumentationFailure.CLOCK_CONTRACT,
            events=tuple(events),
            undelivered_event_ids=tuple(undelivered_event_ids),
        )
    return (ended_ns - started_ns) // 1_000_000


def _admit_and_deliver_event(
    *,
    stage: OperationalStage,
    outcome: OperationalOutcome,
    duration_ms: int,
    sink: OperationalEventSink,
    events: list[OperationalEvent],
    undelivered_event_ids: list[str],
    public_request_id: str | None = None,
    source_execution_id: str | None = None,
    handoff_id: str | None = None,
    failure_category: OperationalFailureCategory | None = None,
) -> OperationalEvent:
    """Construct mandatory evidence first, then attempt best-effort external delivery."""
    try:
        event = create_operational_event(
            stage=stage,
            outcome=outcome,
            duration_ms=duration_ms,
            public_request_id=public_request_id,
            source_execution_id=source_execution_id,
            handoff_id=handoff_id,
            failure_category=failure_category,
        )
    except OperationalTelemetryValidationError:
        raise PublicAnalysisInstrumentationError(
            stage=stage,
            reason=PublicAnalysisInstrumentationFailure.EVENT_CONTRACT,
            events=tuple(events),
            undelivered_event_ids=tuple(undelivered_event_ids),
        ) from None

    events.append(event)
    try:
        sink.emit(event)
    except Exception:
        undelivered_event_ids.append(event.event_id)
    return event


def _record_terminal_failure(
    *,
    stage: OperationalStage,
    outcome: OperationalOutcome,
    category: OperationalFailureCategory,
    started_ns: int,
    clock: MonotonicClock,
    sink: OperationalEventSink,
    events: list[OperationalEvent],
    undelivered_event_ids: list[str],
    public_request_id: str | None = None,
    source_execution_id: str | None = None,
) -> NoReturn:
    """Admit one terminal event and raise bounded operational failure evidence."""
    duration_ms = _duration_ms(
        clock,
        stage=stage,
        started_ns=started_ns,
        events=events,
        undelivered_event_ids=undelivered_event_ids,
    )
    _admit_and_deliver_event(
        stage=stage,
        outcome=outcome,
        duration_ms=duration_ms,
        sink=sink,
        events=events,
        undelivered_event_ids=undelivered_event_ids,
        public_request_id=public_request_id,
        source_execution_id=source_execution_id,
        failure_category=category,
    )
    raise PublicAnalysisOperationalFailure(
        stage=stage,
        events=tuple(events),
        undelivered_event_ids=tuple(undelivered_event_ids),
    ) from None


def execute_instrumented_public_analysis(
    raw_body: bytes,
    source: PublicRepositoryEvidenceSource,
    planner: PublicSemanticPlanner,
    *,
    clock: MonotonicClock,
    sink: OperationalEventSink,
) -> PublicAnalysisOperationalExecution:
    """Run the existing Phase 9 authority path while emitting bounded Gate 10.2 evidence."""
    events: list[OperationalEvent] = []
    undelivered_event_ids: list[str] = []

    stage = OperationalStage.PUBLIC_REQUEST_ADMISSION
    started_ns = _clock_read(
        clock,
        stage=stage,
        events=events,
        undelivered_event_ids=undelivered_event_ids,
    )
    try:
        admission = admit_public_analysis_request(raw_body)
    except PublicAnalysisRequestAdmissionError:
        _record_terminal_failure(
            stage=stage,
            outcome=OperationalOutcome.REJECTED,
            category=OperationalFailureCategory.REQUEST_CONTRACT,
            started_ns=started_ns,
            clock=clock,
            sink=sink,
            events=events,
            undelivered_event_ids=undelivered_event_ids,
        )
    except Exception:
        _record_terminal_failure(
            stage=stage,
            outcome=OperationalOutcome.FAILED,
            category=OperationalFailureCategory.UNEXPECTED_INTERNAL,
            started_ns=started_ns,
            clock=clock,
            sink=sink,
            events=events,
            undelivered_event_ids=undelivered_event_ids,
        )
    public_request_id = admission.request.request_id
    _admit_and_deliver_event(
        stage=stage,
        outcome=OperationalOutcome.SUCCEEDED,
        duration_ms=_duration_ms(
            clock,
            stage=stage,
            started_ns=started_ns,
            events=events,
            undelivered_event_ids=undelivered_event_ids,
        ),
        sink=sink,
        events=events,
        undelivered_event_ids=undelivered_event_ids,
        public_request_id=public_request_id,
    )

    stage = OperationalStage.REPOSITORY_EVIDENCE
    started_ns = _clock_read(
        clock,
        stage=stage,
        events=events,
        undelivered_event_ids=undelivered_event_ids,
    )
    try:
        execution = build_public_repository_evidence(admission.request, source)
    except GitHubRestAcquisitionError:
        _record_terminal_failure(
            stage=stage,
            outcome=OperationalOutcome.FAILED,
            category=OperationalFailureCategory.SOURCE_RESOLUTION,
            started_ns=started_ns,
            clock=clock,
            sink=sink,
            events=events,
            undelivered_event_ids=undelivered_event_ids,
            public_request_id=public_request_id,
        )
    except (RepositoryIntelligenceContractError, PublicAnalysisValidationError):
        _record_terminal_failure(
            stage=stage,
            outcome=OperationalOutcome.REJECTED,
            category=OperationalFailureCategory.EVIDENCE_CONTRACT,
            started_ns=started_ns,
            clock=clock,
            sink=sink,
            events=events,
            undelivered_event_ids=undelivered_event_ids,
            public_request_id=public_request_id,
        )
    except Exception:
        _record_terminal_failure(
            stage=stage,
            outcome=OperationalOutcome.FAILED,
            category=OperationalFailureCategory.UNEXPECTED_INTERNAL,
            started_ns=started_ns,
            clock=clock,
            sink=sink,
            events=events,
            undelivered_event_ids=undelivered_event_ids,
            public_request_id=public_request_id,
        )
    source_execution_id = execution.execution_id
    _admit_and_deliver_event(
        stage=stage,
        outcome=OperationalOutcome.SUCCEEDED,
        duration_ms=_duration_ms(
            clock,
            stage=stage,
            started_ns=started_ns,
            events=events,
            undelivered_event_ids=undelivered_event_ids,
        ),
        sink=sink,
        events=events,
        undelivered_event_ids=undelivered_event_ids,
        public_request_id=public_request_id,
        source_execution_id=source_execution_id,
    )

    stage = OperationalStage.SEMANTIC_PLANNING
    started_ns = _clock_read(
        clock,
        stage=stage,
        events=events,
        undelivered_event_ids=undelivered_event_ids,
    )
    try:
        planning_request = build_public_semantic_planning_request(execution)
    except Exception:
        _record_terminal_failure(
            stage=stage,
            outcome=OperationalOutcome.FAILED,
            category=OperationalFailureCategory.UNEXPECTED_INTERNAL,
            started_ns=started_ns,
            clock=clock,
            sink=sink,
            events=events,
            undelivered_event_ids=undelivered_event_ids,
            public_request_id=public_request_id,
            source_execution_id=source_execution_id,
        )
    try:
        raw_plan = planner.plan(planning_request.canonical_json)
    except Exception:
        _record_terminal_failure(
            stage=stage,
            outcome=OperationalOutcome.FAILED,
            category=OperationalFailureCategory.PLANNER_INVOCATION,
            started_ns=started_ns,
            clock=clock,
            sink=sink,
            events=events,
            undelivered_event_ids=undelivered_event_ids,
            public_request_id=public_request_id,
            source_execution_id=source_execution_id,
        )
    try:
        proposal = parse_public_semantic_plan_proposal(
            raw_plan,
            planning_request=planning_request,
        )
    except PublicSemanticPlanAdmissionError:
        _record_terminal_failure(
            stage=stage,
            outcome=OperationalOutcome.REJECTED,
            category=OperationalFailureCategory.PLANNER_OUTPUT_CONTRACT,
            started_ns=started_ns,
            clock=clock,
            sink=sink,
            events=events,
            undelivered_event_ids=undelivered_event_ids,
            public_request_id=public_request_id,
            source_execution_id=source_execution_id,
        )
    except Exception:
        _record_terminal_failure(
            stage=stage,
            outcome=OperationalOutcome.FAILED,
            category=OperationalFailureCategory.UNEXPECTED_INTERNAL,
            started_ns=started_ns,
            clock=clock,
            sink=sink,
            events=events,
            undelivered_event_ids=undelivered_event_ids,
            public_request_id=public_request_id,
            source_execution_id=source_execution_id,
        )
    _admit_and_deliver_event(
        stage=stage,
        outcome=OperationalOutcome.SUCCEEDED,
        duration_ms=_duration_ms(
            clock,
            stage=stage,
            started_ns=started_ns,
            events=events,
            undelivered_event_ids=undelivered_event_ids,
        ),
        sink=sink,
        events=events,
        undelivered_event_ids=undelivered_event_ids,
        public_request_id=public_request_id,
        source_execution_id=source_execution_id,
    )

    stage = OperationalStage.HYBRID_ROUTE_ADMISSION
    started_ns = _clock_read(
        clock,
        stage=stage,
        events=events,
        undelivered_event_ids=undelivered_event_ids,
    )
    try:
        route_decision = route_public_semantic_plan(
            proposal,
            planning_request=planning_request,
        )
    except PublicSemanticPlanAdmissionError:
        _record_terminal_failure(
            stage=stage,
            outcome=OperationalOutcome.REJECTED,
            category=OperationalFailureCategory.ROUTE_AUTHORITY,
            started_ns=started_ns,
            clock=clock,
            sink=sink,
            events=events,
            undelivered_event_ids=undelivered_event_ids,
            public_request_id=public_request_id,
            source_execution_id=source_execution_id,
        )
    except Exception:
        _record_terminal_failure(
            stage=stage,
            outcome=OperationalOutcome.FAILED,
            category=OperationalFailureCategory.UNEXPECTED_INTERNAL,
            started_ns=started_ns,
            clock=clock,
            sink=sink,
            events=events,
            undelivered_event_ids=undelivered_event_ids,
            public_request_id=public_request_id,
            source_execution_id=source_execution_id,
        )
    _admit_and_deliver_event(
        stage=stage,
        outcome=OperationalOutcome.SUCCEEDED,
        duration_ms=_duration_ms(
            clock,
            stage=stage,
            started_ns=started_ns,
            events=events,
            undelivered_event_ids=undelivered_event_ids,
        ),
        sink=sink,
        events=events,
        undelivered_event_ids=undelivered_event_ids,
        public_request_id=public_request_id,
        source_execution_id=source_execution_id,
    )

    stage = OperationalStage.PUBLIC_HANDOFF
    started_ns = _clock_read(
        clock,
        stage=stage,
        events=events,
        undelivered_event_ids=undelivered_event_ids,
    )
    try:
        handoff = build_public_analysis_admission_handoff(
            source_execution=execution,
            planning_request=planning_request,
            proposal=proposal,
            route_decision=route_decision,
        )
    except PublicSemanticPlanAdmissionError:
        _record_terminal_failure(
            stage=stage,
            outcome=OperationalOutcome.REJECTED,
            category=OperationalFailureCategory.HANDOFF_CONTRACT,
            started_ns=started_ns,
            clock=clock,
            sink=sink,
            events=events,
            undelivered_event_ids=undelivered_event_ids,
            public_request_id=public_request_id,
            source_execution_id=source_execution_id,
        )
    except Exception:
        _record_terminal_failure(
            stage=stage,
            outcome=OperationalOutcome.FAILED,
            category=OperationalFailureCategory.UNEXPECTED_INTERNAL,
            started_ns=started_ns,
            clock=clock,
            sink=sink,
            events=events,
            undelivered_event_ids=undelivered_event_ids,
            public_request_id=public_request_id,
            source_execution_id=source_execution_id,
        )
    _admit_and_deliver_event(
        stage=stage,
        outcome=OperationalOutcome.SUCCEEDED,
        duration_ms=_duration_ms(
            clock,
            stage=stage,
            started_ns=started_ns,
            events=events,
            undelivered_event_ids=undelivered_event_ids,
        ),
        sink=sink,
        events=events,
        undelivered_event_ids=undelivered_event_ids,
        public_request_id=public_request_id,
        source_execution_id=source_execution_id,
        handoff_id=handoff.handoff_id,
    )

    return PublicAnalysisOperationalExecution(
        handoff=handoff,
        events=tuple(events),
        undelivered_event_ids=tuple(undelivered_event_ids),
    )


__all__ = [
    "MonotonicClock",
    "OperationalEventSink",
    "PublicAnalysisInstrumentationError",
    "PublicAnalysisInstrumentationFailure",
    "PublicAnalysisOperationalExecution",
    "PublicAnalysisOperationalFailure",
    "execute_instrumented_public_analysis",
]
