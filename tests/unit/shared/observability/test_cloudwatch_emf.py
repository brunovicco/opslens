"""Regression tests for the bounded CloudWatch EMF adapter boundary."""

import json
from dataclasses import dataclass
from typing import cast

import pytest

from opslens.shared.observability.cloudwatch_emf import (
    CLOUDWATCH_EMF_CONTRACT_VERSION,
    CLOUDWATCH_EMF_DIMENSIONS,
    CLOUDWATCH_EMF_NAMESPACE,
    CLOUDWATCH_EMF_STORAGE_RESOLUTION_SECONDS,
    MAX_CLOUDWATCH_EMF_DOCUMENT_BYTES,
    MAX_CLOUDWATCH_EMF_TIMESTAMP_MS,
    CloudWatchEmfAdapterError,
    CloudWatchEmfAdapterFailure,
    CloudWatchEmfDocument,
    CloudWatchEmfOperationalEventSink,
    create_cloudwatch_emf_document,
)
from opslens.shared.observability.contracts import (
    OPERATIONAL_TELEMETRY_CONTRACT_VERSION,
    OPERATIONAL_TELEMETRY_OPERATION,
    OperationalEvent,
    OperationalFailureCategory,
    OperationalOutcome,
    OperationalStage,
    OperationalTelemetryValidationError,
    create_operational_event,
)

_DIGEST_A = "a" * 64
_DIGEST_B = "b" * 64
_DIGEST_C = "c" * 64
_PUBLIC_REQUEST_ID = f"public-analysis-request:v1:{_DIGEST_A}"
_SOURCE_EXECUTION_ID = f"public-repository-evidence:v1@sha256:{_DIGEST_B}"
_HANDOFF_ID = f"public-analysis-handoff:v1@sha256:{_DIGEST_C}"
_TIMESTAMP_MS = 1_788_798_000_000


@dataclass(slots=True)
class StaticClock:
    """Return one deterministic epoch-millisecond value."""

    value: int
    calls: int = 0

    def epoch_milliseconds(self) -> int:
        """Return the configured timestamp and count clock reads."""
        self.calls += 1
        return self.value


@dataclass(slots=True)
class MalformedClock:
    """Return a runtime-invalid value through a statically valid protocol shape."""

    calls: int = 0

    def epoch_milliseconds(self) -> int:
        """Return a non-integer value to exercise runtime contract admission."""
        self.calls += 1
        return cast(int, "not-an-epoch-millisecond")


@dataclass(slots=True)
class RaisingClock:
    """Raise provider-local text that must never escape the adapter boundary."""

    calls: int = 0

    def epoch_milliseconds(self) -> int:
        """Raise one content-bearing clock failure."""
        self.calls += 1
        raise RuntimeError("clock-secret provider-host.example")


class RecordingWriter:
    """Capture exact EMF lines without external delivery."""

    def __init__(self) -> None:
        """Start with no delivered lines."""
        self.lines: list[bytes] = []

    def write(self, line: bytes) -> None:
        """Record one exact line."""
        self.lines.append(line)


@dataclass(slots=True)
class RaisingWriter:
    """Fail delivery once while retaining invocation accounting."""

    calls: int = 0

    def write(self, line: bytes) -> None:
        """Raise content-bearing writer text that must remain private."""
        del line
        self.calls += 1
        raise RuntimeError("writer-secret request-token provider-host.example")


def _successful_handoff_event() -> OperationalEvent:
    """Create a fully-provenanced successful terminal event."""
    return create_operational_event(
        stage=OperationalStage.PUBLIC_HANDOFF,
        outcome=OperationalOutcome.SUCCEEDED,
        duration_ms=23,
        public_request_id=_PUBLIC_REQUEST_ID,
        source_execution_id=_SOURCE_EXECUTION_ID,
        handoff_id=_HANDOFF_ID,
    )


def test_emf_document_has_exact_aws_shape_metrics_and_dimensions() -> None:
    """Map admitted operational truth to the frozen low-cardinality EMF schema."""
    event = _successful_handoff_event()
    document = create_cloudwatch_emf_document(event, timestamp_ms=_TIMESTAMP_MS)
    payload = json.loads(document.canonical_json)

    assert payload["_aws"] == {
        "CloudWatchMetrics": [
            {
                "Dimensions": [list(CLOUDWATCH_EMF_DIMENSIONS)],
                "Metrics": [
                    {
                        "Name": "OperationalStageCount",
                        "StorageResolution": CLOUDWATCH_EMF_STORAGE_RESOLUTION_SECONDS,
                        "Unit": "Count",
                    },
                    {
                        "Name": "OperationalStageLatency",
                        "StorageResolution": CLOUDWATCH_EMF_STORAGE_RESOLUTION_SECONDS,
                        "Unit": "Milliseconds",
                    },
                ],
                "Namespace": CLOUDWATCH_EMF_NAMESPACE,
            }
        ],
        "Timestamp": _TIMESTAMP_MS,
    }
    assert payload["ContractVersion"] == OPERATIONAL_TELEMETRY_CONTRACT_VERSION
    assert payload["Operation"] == OPERATIONAL_TELEMETRY_OPERATION
    assert payload["Stage"] == "public_handoff"
    assert payload["Outcome"] == "succeeded"
    assert payload["OperationalStageCount"] == 1.0
    assert payload["OperationalStageLatency"] == 23.0


def test_high_cardinality_identities_are_metadata_never_metric_dimensions() -> None:
    """Keep request/source/handoff/event identities out of CloudWatch dimensions."""
    event = _successful_handoff_event()
    payload = json.loads(
        create_cloudwatch_emf_document(event, timestamp_ms=_TIMESTAMP_MS).canonical_json
    )

    dimension_names = payload["_aws"]["CloudWatchMetrics"][0]["Dimensions"][0]
    assert dimension_names == list(CLOUDWATCH_EMF_DIMENSIONS)
    assert payload["EventId"] == event.event_id
    assert payload["PublicRequestId"] == _PUBLIC_REQUEST_ID
    assert payload["SourceExecutionId"] == _SOURCE_EXECUTION_ID
    assert payload["HandoffId"] == _HANDOFF_ID

    forbidden_dimension_names = {
        "EventId",
        "PublicRequestId",
        "SourceExecutionId",
        "HandoffId",
    }
    assert forbidden_dimension_names.isdisjoint(dimension_names)


def test_emf_schema_has_no_arbitrary_attribute_bag() -> None:
    """Expose only frozen EMF metadata rather than arbitrary content-bearing fields."""
    payload = json.loads(
        create_cloudwatch_emf_document(
            _successful_handoff_event(),
            timestamp_ms=_TIMESTAMP_MS,
        ).canonical_json
    )

    assert set(payload) == {
        "_aws",
        "AttemptCount",
        "ContractVersion",
        "EmfContractVersion",
        "EventId",
        "FailureCategory",
        "HandoffId",
        "Operation",
        "OperationalStageCount",
        "OperationalStageLatency",
        "Outcome",
        "PublicRequestId",
        "SourceExecutionId",
        "Stage",
    }
    rendered = json.dumps(payload, sort_keys=True)
    for forbidden in (
        "repository_url",
        "dependency_name",
        "prompt",
        "sql",
        "credential",
        "provider_message",
    ):
        assert forbidden not in rendered


def test_document_identity_is_deterministic_and_binds_timestamp() -> None:
    """Bind exact event plus EMF wall-clock timestamp into content-addressed identity."""
    event = _successful_handoff_event()
    first = create_cloudwatch_emf_document(event, timestamp_ms=_TIMESTAMP_MS)
    second = create_cloudwatch_emf_document(event, timestamp_ms=_TIMESTAMP_MS)
    later = create_cloudwatch_emf_document(event, timestamp_ms=_TIMESTAMP_MS + 1)

    assert first == second
    assert first.document_id == (
        f"{CLOUDWATCH_EMF_CONTRACT_VERSION}@sha256:{first.document_sha256}"
    )
    assert first.document_id != later.document_id
    assert len(first.canonical_json) <= MAX_CLOUDWATCH_EMF_DOCUMENT_BYTES


def test_rejected_and_failed_events_preserve_bounded_failure_metadata() -> None:
    """Preserve only the admitted failure category for non-success outcomes."""
    rejected = create_operational_event(
        stage=OperationalStage.PUBLIC_REQUEST_ADMISSION,
        outcome=OperationalOutcome.REJECTED,
        duration_ms=3,
        failure_category=OperationalFailureCategory.REQUEST_CONTRACT,
    )
    failed = create_operational_event(
        stage=OperationalStage.SEMANTIC_PLANNING,
        outcome=OperationalOutcome.FAILED,
        duration_ms=9,
        public_request_id=_PUBLIC_REQUEST_ID,
        source_execution_id=_SOURCE_EXECUTION_ID,
        failure_category=OperationalFailureCategory.PLANNER_INVOCATION,
    )

    rejected_payload = json.loads(
        create_cloudwatch_emf_document(rejected, timestamp_ms=_TIMESTAMP_MS).canonical_json
    )
    failed_payload = json.loads(
        create_cloudwatch_emf_document(failed, timestamp_ms=_TIMESTAMP_MS).canonical_json
    )

    assert rejected_payload["Outcome"] == "rejected"
    assert rejected_payload["FailureCategory"] == "request_contract"
    assert failed_payload["Outcome"] == "failed"
    assert failed_payload["FailureCategory"] == "planner_invocation"


def test_factory_rejects_timestamp_outside_bounded_epoch_contract() -> None:
    """Reject malformed wall-clock values before EMF document admission."""
    event = _successful_handoff_event()

    with pytest.raises(OperationalTelemetryValidationError, match="timestamp"):
        create_cloudwatch_emf_document(event, timestamp_ms=-1)

    with pytest.raises(OperationalTelemetryValidationError, match="timestamp"):
        create_cloudwatch_emf_document(
            event,
            timestamp_ms=MAX_CLOUDWATCH_EMF_TIMESTAMP_MS + 1,
        )


def test_sink_classifies_runtime_invalid_clock_value_as_clock_contract() -> None:
    """Treat malformed injected wall-clock output as a clock-boundary failure."""
    clock = MalformedClock()
    writer = RecordingWriter()
    sink = CloudWatchEmfOperationalEventSink(clock=clock, writer=writer)

    with pytest.raises(CloudWatchEmfAdapterError) as exc_info:
        sink.emit(_successful_handoff_event())

    assert exc_info.value.category is CloudWatchEmfAdapterFailure.CLOCK_CONTRACT
    assert clock.calls == 1
    assert writer.lines == []


def test_sink_clock_exception_is_content_free_and_stops_before_writer() -> None:
    """Do not copy clock/provider exception text into the adapter failure."""
    clock = RaisingClock()
    writer = RecordingWriter()
    sink = CloudWatchEmfOperationalEventSink(clock=clock, writer=writer)

    with pytest.raises(CloudWatchEmfAdapterError) as exc_info:
        sink.emit(_successful_handoff_event())

    assert exc_info.value.category is CloudWatchEmfAdapterFailure.CLOCK_CONTRACT
    assert "clock-secret" not in str(exc_info.value)
    assert "provider-host.example" not in str(exc_info.value)
    assert clock.calls == 1
    assert writer.lines == []


def test_sink_writer_failure_is_content_free_and_never_retried() -> None:
    """Attempt external line delivery exactly once and expose only bounded failure type."""
    clock = StaticClock(_TIMESTAMP_MS)
    writer = RaisingWriter()
    sink = CloudWatchEmfOperationalEventSink(clock=clock, writer=writer)

    with pytest.raises(CloudWatchEmfAdapterError) as exc_info:
        sink.emit(_successful_handoff_event())

    assert exc_info.value.category is CloudWatchEmfAdapterFailure.WRITER_DELIVERY
    assert "writer-secret" not in str(exc_info.value)
    assert "request-token" not in str(exc_info.value)
    assert "provider-host.example" not in str(exc_info.value)
    assert clock.calls == 1
    assert writer.calls == 1


def test_sink_writes_one_exact_canonical_emf_line() -> None:
    """Write one admitted canonical JSON record plus one transport newline."""
    event = _successful_handoff_event()
    clock = StaticClock(_TIMESTAMP_MS)
    writer = RecordingWriter()
    sink = CloudWatchEmfOperationalEventSink(clock=clock, writer=writer)

    sink.emit(event)

    expected = create_cloudwatch_emf_document(
        event,
        timestamp_ms=_TIMESTAMP_MS,
    ).canonical_json + b"\n"
    assert clock.calls == 1
    assert writer.lines == [expected]


def test_sink_rejects_non_event_before_clock_or_writer() -> None:
    """Do not let arbitrary objects reach the clock/writer delivery path."""
    clock = StaticClock(_TIMESTAMP_MS)
    writer = RecordingWriter()
    sink = CloudWatchEmfOperationalEventSink(clock=clock, writer=writer)

    with pytest.raises(CloudWatchEmfAdapterError) as exc_info:
        sink.emit(cast(OperationalEvent, object()))

    assert exc_info.value.category is CloudWatchEmfAdapterFailure.DOCUMENT_CONTRACT
    assert clock.calls == 0
    assert writer.lines == []


def test_direct_document_construction_rejects_forged_and_oversized_payloads() -> None:
    """Prevent callers from bypassing canonical factory and byte-budget admission."""
    event = _successful_handoff_event()
    admitted = create_cloudwatch_emf_document(event, timestamp_ms=_TIMESTAMP_MS)

    with pytest.raises(
        OperationalTelemetryValidationError,
        match="payload does not match admitted semantics",
    ):
        CloudWatchEmfDocument(
            event=event,
            timestamp_ms=_TIMESTAMP_MS,
            payload=admitted.payload + b" ",
            document_sha256=admitted.document_sha256,
            document_id=admitted.document_id,
        )

    with pytest.raises(
        OperationalTelemetryValidationError,
        match="exceeds the OpsLens hard byte limit",
    ):
        CloudWatchEmfDocument(
            event=event,
            timestamp_ms=_TIMESTAMP_MS,
            payload=b"x" * (MAX_CLOUDWATCH_EMF_DOCUMENT_BYTES + 1),
            document_sha256="0" * 64,
            document_id=f"{CLOUDWATCH_EMF_CONTRACT_VERSION}@sha256:{'0' * 64}",
        )
