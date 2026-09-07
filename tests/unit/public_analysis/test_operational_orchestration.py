"""Tests for Gate 10.2 governed public-analysis operational instrumentation."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from hashlib import sha256

import pytest

import opslens.public_analysis.application.operational_orchestration as orchestration_module
from opslens.hybrid_retrieval.domain import HybridRouteDecision
from opslens.public_analysis.application import (
    PublicAnalysisInstrumentationError,
    PublicAnalysisInstrumentationFailure,
    PublicAnalysisOperationalFailure,
    PublicSemanticPlanAdmissionError,
    execute_instrumented_public_analysis,
)
from opslens.public_analysis.domain import (
    PUBLIC_ANALYSIS_V1_REQUIRED_EVIDENCE_NEEDS,
    PublicAnalysisAdmissionHandoff,
    PublicRepositoryEvidenceExecution,
    PublicSemanticPlanningRequest,
    PublicSemanticPlanProposal,
)
from opslens.repository_intelligence.adapters.github_http import GitHubRestAcquisitionError
from opslens.repository_intelligence.domain import compute_git_blob_sha1
from opslens.shared.observability.contracts import (
    OperationalEvent,
    OperationalFailureCategory,
    OperationalOutcome,
    OperationalStage,
)

_REPOSITORY_ID = 1_333_092_779
_COMMIT_SHA = "3f75a4fc2bd22589df0a5ffe98a8442fda81c8d3"
_TREE_SHA = "01ac6fe03f1db867ef29c6652311ee43b1f63afb"
_RAW_REQUEST = b'{"repository_url":"https://github.com/brunovicco/opslens"}'


def _uv_lock_content() -> bytes:
    """Return inert dependency evidence that must never leak into telemetry."""
    return (
        b"version = 1\n"
        b"revision = 3\n"
        b'[[package]]\n'
        b'name = "Requests"\n'
        b'version = "2.31.0"\n'
        b'source = { registry = "https://pypi.org/simple" }\n'
    )


def _uv_lock_payload() -> dict[str, object]:
    """Build the exact bounded GitHub Contents fixture admitted by Phase 4."""
    content = _uv_lock_content()
    return {
        "type": "file",
        "path": "uv.lock",
        "name": "uv.lock",
        "encoding": "base64",
        "size": len(content),
        "sha": compute_git_blob_sha1(content),
        "content": base64.encodebytes(content).decode("ascii"),
    }


@dataclass(slots=True)
class FakeRepositorySource:
    """Provide bounded public GitHub evidence or one configured transport/contract failure."""

    private: bool = False
    transport_failure: bool = False
    repository_calls: int = 0
    commit_calls: int = 0
    file_calls: int = 0

    def get_repository(self, owner: str, name: str) -> dict[str, object]:
        """Return source-confirmed repository metadata without network access."""
        self.repository_calls += 1
        if self.transport_failure:
            raise GitHubRestAcquisitionError("provider-secret-detail")
        return {
            "id": _REPOSITORY_ID,
            "name": name,
            "full_name": f"{owner}/{name}",
            "private": self.private,
            "visibility": "private" if self.private else "public",
            "default_branch": "main",
            "owner": {"login": owner},
        }

    def get_commit(self, owner: str, name: str, ref: str) -> dict[str, object]:
        """Return immutable commit/tree source evidence."""
        self.commit_calls += 1
        assert (owner, name, ref) == ("brunovicco", "opslens", "main")
        return {
            "sha": _COMMIT_SHA,
            "commit": {"tree": {"sha": _TREE_SHA}},
        }

    def get_uv_lock(
        self,
        owner: str,
        name: str,
        commit_sha: str,
    ) -> dict[str, object]:
        """Return exact-commit inert lock evidence."""
        self.file_calls += 1
        assert (owner, name, commit_sha) == ("brunovicco", "opslens", _COMMIT_SHA)
        return _uv_lock_payload()


def _required_need_values() -> tuple[str, ...]:
    """Return exact public-v1 evidence-need values in canonical order."""
    return tuple(need.value for need in PUBLIC_ANALYSIS_V1_REQUIRED_EVIDENCE_NEEDS)


@dataclass(slots=True)
class FakePlanner:
    """Return one bounded proposal or fail exactly once when configured."""

    evidence_needs: tuple[str, ...] = field(default_factory=_required_need_values)
    raw_response: bytes | None = None
    fail: bool = False
    calls: list[bytes] = field(default_factory=lambda: list[bytes]())

    def plan(self, request_json: bytes) -> bytes:
        """Return one proposal bound to the exact content-free planning request."""
        self.calls.append(request_json)
        if self.fail:
            raise RuntimeError("model-provider-secret-detail")
        if self.raw_response is not None:
            return self.raw_response
        return json.dumps(
            {
                "planning_request_sha256": sha256(request_json).hexdigest(),
                "evidence_needs": list(self.evidence_needs),
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode()


@dataclass(slots=True)
class FakeClock:
    """Return deterministic monotonic readings without accessing a global clock."""

    scripted_values: list[int] = field(default_factory=lambda: list[int]())
    current_ns: int = 0

    def monotonic_ns(self) -> int:
        """Return one scripted reading or advance by one millisecond."""
        if self.scripted_values:
            return self.scripted_values.pop(0)
        self.current_ns += 1_000_000
        return self.current_ns


@dataclass(slots=True)
class FakeSink:
    """Record delivery attempts and optionally fail without changing application authority."""

    fail: bool = False
    events: list[OperationalEvent] = field(default_factory=lambda: list[OperationalEvent]())

    def emit(self, event: OperationalEvent) -> None:
        """Record the admitted event before one optional external-delivery failure."""
        self.events.append(event)
        if self.fail:
            raise RuntimeError("sink-secret-detail")


def _run(
    *,
    source: FakeRepositorySource | None = None,
    planner: FakePlanner | None = None,
    clock: FakeClock | None = None,
    sink: FakeSink | None = None,
    raw_body: bytes = _RAW_REQUEST,
):
    """Execute the real Gate 10.2 application orchestration with injected fakes."""
    return execute_instrumented_public_analysis(
        raw_body,
        source or FakeRepositorySource(),
        planner or FakePlanner(),
        clock=clock or FakeClock(),
        sink=sink or FakeSink(),
    )


def test_success_emits_exact_five_ordered_events_with_identity_progression() -> None:
    """Successful Phase 9 handoff produces exactly five content-minimized success events."""
    sink = FakeSink()

    result = _run(sink=sink)

    assert tuple(event.stage for event in result.events) == (
        OperationalStage.PUBLIC_REQUEST_ADMISSION,
        OperationalStage.REPOSITORY_EVIDENCE,
        OperationalStage.SEMANTIC_PLANNING,
        OperationalStage.HYBRID_ROUTE_ADMISSION,
        OperationalStage.PUBLIC_HANDOFF,
    )
    assert all(event.outcome is OperationalOutcome.SUCCEEDED for event in result.events)
    assert result.events[0].public_request_id is not None
    assert result.events[0].source_execution_id is None
    assert result.events[1].source_execution_id == result.handoff.source_execution.execution_id
    assert result.events[3].handoff_id is None
    assert result.events[4].handoff_id == result.handoff.handoff_id
    assert sink.events == list(result.events)
    assert result.undelivered_event_ids == ()


def test_invalid_request_stops_before_source_or_planner_work() -> None:
    """Request rejection emits one terminal event and authorizes no later stage."""
    source = FakeRepositorySource()
    planner = FakePlanner()

    with pytest.raises(PublicAnalysisOperationalFailure) as exc_info:
        _run(source=source, planner=planner, raw_body=b"{}")

    failure = exc_info.value
    assert failure.stage is OperationalStage.PUBLIC_REQUEST_ADMISSION
    assert len(failure.events) == 1
    assert failure.terminal_event.outcome is OperationalOutcome.REJECTED
    assert failure.terminal_event.failure_category is OperationalFailureCategory.REQUEST_CONTRACT
    assert failure.terminal_event.public_request_id is None
    assert source.repository_calls == 0
    assert planner.calls == []


def test_source_transport_failure_is_distinct_and_content_minimized() -> None:
    """Provider transport failure maps to source_resolution without provider text leakage."""
    source = FakeRepositorySource(transport_failure=True)
    planner = FakePlanner()

    with pytest.raises(PublicAnalysisOperationalFailure) as exc_info:
        _run(source=source, planner=planner)

    failure = exc_info.value
    assert failure.stage is OperationalStage.REPOSITORY_EVIDENCE
    assert len(failure.events) == 2
    assert failure.terminal_event.outcome is OperationalOutcome.FAILED
    assert failure.terminal_event.failure_category is OperationalFailureCategory.SOURCE_RESOLUTION
    assert b"provider-secret-detail" not in failure.terminal_event.canonical_json
    assert "provider-secret-detail" not in str(failure)
    assert source.commit_calls == 0
    assert planner.calls == []


def test_repository_contract_rejection_is_not_mislabeled_as_source_failure() -> None:
    """Source-confirmed private repository is evidence rejection, not transport failure."""
    source = FakeRepositorySource(private=True)

    with pytest.raises(PublicAnalysisOperationalFailure) as exc_info:
        _run(source=source)

    failure = exc_info.value
    assert failure.stage is OperationalStage.REPOSITORY_EVIDENCE
    assert failure.terminal_event.outcome is OperationalOutcome.REJECTED
    assert failure.terminal_event.failure_category is OperationalFailureCategory.EVIDENCE_CONTRACT
    assert source.commit_calls == 0
    assert source.file_calls == 0


def test_planner_invocation_and_output_rejection_remain_distinct() -> None:
    """Provider invocation failure and malformed proposal receive different bounded categories."""
    with pytest.raises(PublicAnalysisOperationalFailure) as invocation_info:
        _run(planner=FakePlanner(fail=True))
    invocation = invocation_info.value
    assert invocation.stage is OperationalStage.SEMANTIC_PLANNING
    assert invocation.terminal_event.outcome is OperationalOutcome.FAILED
    assert invocation.terminal_event.failure_category is (
        OperationalFailureCategory.PLANNER_INVOCATION
    )
    assert b"model-provider-secret-detail" not in invocation.terminal_event.canonical_json

    with pytest.raises(PublicAnalysisOperationalFailure) as output_info:
        _run(planner=FakePlanner(raw_response=b"not-json"))
    output = output_info.value
    assert output.stage is OperationalStage.SEMANTIC_PLANNING
    assert output.terminal_event.outcome is OperationalOutcome.REJECTED
    assert output.terminal_event.failure_category is (
        OperationalFailureCategory.PLANNER_OUTPUT_CONTRACT
    )


def test_under_scoped_plan_reaches_route_stage_then_fails_closed() -> None:
    """Structurally valid under-scoping is rejected only by deterministic route admission."""
    planner = FakePlanner(
        evidence_needs=(
            PUBLIC_ANALYSIS_V1_REQUIRED_EVIDENCE_NEEDS[0].value,
            PUBLIC_ANALYSIS_V1_REQUIRED_EVIDENCE_NEEDS[1].value,
        )
    )

    with pytest.raises(PublicAnalysisOperationalFailure) as exc_info:
        _run(planner=planner)

    failure = exc_info.value
    assert failure.stage is OperationalStage.HYBRID_ROUTE_ADMISSION
    assert tuple(event.outcome for event in failure.events[:3]) == (
        OperationalOutcome.SUCCEEDED,
        OperationalOutcome.SUCCEEDED,
        OperationalOutcome.SUCCEEDED,
    )
    assert failure.terminal_event.outcome is OperationalOutcome.REJECTED
    assert failure.terminal_event.failure_category is OperationalFailureCategory.ROUTE_AUTHORITY
    assert len(failure.events) == 4


def test_handoff_binding_failure_is_terminal_after_successful_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Final binding rejection emits only the handoff failure after route success."""

    def reject_handoff(
        *,
        source_execution: PublicRepositoryEvidenceExecution,
        planning_request: PublicSemanticPlanningRequest,
        proposal: PublicSemanticPlanProposal,
        route_decision: HybridRouteDecision,
    ) -> PublicAnalysisAdmissionHandoff:
        """Simulate one deterministic final-binding rejection without external calls."""
        del source_execution, planning_request, proposal, route_decision
        raise PublicSemanticPlanAdmissionError("untrusted-detail-that-must-not-leak")

    monkeypatch.setattr(
        orchestration_module,
        "build_public_analysis_admission_handoff",
        reject_handoff,
    )

    with pytest.raises(PublicAnalysisOperationalFailure) as exc_info:
        _run()

    failure = exc_info.value
    assert failure.stage is OperationalStage.PUBLIC_HANDOFF
    assert len(failure.events) == 5
    assert failure.events[-2].outcome is OperationalOutcome.SUCCEEDED
    assert failure.events[-2].stage is OperationalStage.HYBRID_ROUTE_ADMISSION
    assert failure.terminal_event.outcome is OperationalOutcome.REJECTED
    assert failure.terminal_event.failure_category is OperationalFailureCategory.HANDOFF_CONTRACT
    assert b"untrusted-detail-that-must-not-leak" not in failure.terminal_event.canonical_json


def test_sink_failure_never_changes_business_or_route_authority() -> None:
    """Best-effort external delivery can fail for every event while handoff still succeeds."""
    sink = FakeSink(fail=True)

    result = _run(sink=sink)

    assert result.handoff.handoff_id == result.events[-1].handoff_id
    assert tuple(result.undelivered_event_ids) == tuple(
        event.event_id for event in result.events
    )
    assert len(sink.events) == 5
    assert all(b"sink-secret-detail" not in event.canonical_json for event in result.events)


def test_clock_regression_fails_instrumentation_closed_before_downstream_work() -> None:
    """A decreasing monotonic clock cannot fabricate a duration or authorize source work."""
    source = FakeRepositorySource()
    planner = FakePlanner()
    clock = FakeClock(scripted_values=[10, 9])

    with pytest.raises(PublicAnalysisInstrumentationError) as exc_info:
        _run(source=source, planner=planner, clock=clock)

    failure = exc_info.value
    assert failure.stage is OperationalStage.PUBLIC_REQUEST_ADMISSION
    assert failure.reason is PublicAnalysisInstrumentationFailure.CLOCK_CONTRACT
    assert failure.events == ()
    assert source.repository_calls == 0
    assert planner.calls == []


def test_operational_event_contract_failure_stops_before_repository_work() -> None:
    """An out-of-budget duration cannot be emitted or ignored after request admission."""
    source = FakeRepositorySource()
    clock = FakeClock(scripted_values=[0, 901_000_000_000])

    with pytest.raises(PublicAnalysisInstrumentationError) as exc_info:
        _run(source=source, clock=clock)

    failure = exc_info.value
    assert failure.stage is OperationalStage.PUBLIC_REQUEST_ADMISSION
    assert failure.reason is PublicAnalysisInstrumentationFailure.EVENT_CONTRACT
    assert failure.events == ()
    assert source.repository_calls == 0


def test_success_telemetry_contains_only_bounded_identity_semantics() -> None:
    """Raw request, dependency, prompt, SQL, provider, and credential text never enter events."""
    result = _run()
    serialized = b"\n".join(event.canonical_json for event in result.events)

    assert b"https://github.com" not in serialized
    assert b"Requests" not in serialized
    assert b"2.31.0" not in serialized
    assert b"repository_url" not in serialized
    assert b"prompt" not in serialized.lower()
    assert b"sql" not in serialized.lower()
    assert b"credential" not in serialized.lower()
    assert b"provider" not in serialized.lower()
