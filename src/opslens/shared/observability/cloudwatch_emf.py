"""Deterministic CloudWatch EMF adapter for admitted operational evidence."""

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import Final, Protocol

from opslens.shared.observability.contracts import (
    OPERATIONAL_TELEMETRY_CONTRACT_VERSION,
    OPERATIONAL_TELEMETRY_OPERATION,
    OperationalEvent,
    OperationalMetricName,
    OperationalTelemetryValidationError,
    project_operational_metrics,
)

CLOUDWATCH_EMF_CONTRACT_VERSION = "cloudwatch-emf:v1"
CLOUDWATCH_EMF_NAMESPACE = "OpsLens/Operational"
CLOUDWATCH_EMF_STORAGE_RESOLUTION_SECONDS = 60
MAX_CLOUDWATCH_EMF_DOCUMENT_BYTES = 16_384
MAX_CLOUDWATCH_EMF_TIMESTAMP_MS = 253_402_300_799_999

CLOUDWATCH_EMF_DIMENSIONS: Final[tuple[str, ...]] = (
    "ContractVersion",
    "Operation",
    "Stage",
    "Outcome",
)

_DOCUMENT_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)


class CloudWatchEmfAdapterFailure(StrEnum):
    """Content-free failure categories for the offline EMF adapter boundary."""

    CLOCK_CONTRACT = "clock_contract"
    DOCUMENT_CONTRACT = "document_contract"
    WRITER_DELIVERY = "writer_delivery"


class CloudWatchEmfAdapterError(RuntimeError):
    """Raised when EMF adaptation fails without leaking provider/writer details."""

    def __init__(self, category: CloudWatchEmfAdapterFailure) -> None:
        """Expose only one bounded adapter failure category."""
        if type(category) is not CloudWatchEmfAdapterFailure:
            raise ValueError("CloudWatch EMF failure category must be bounded")
        super().__init__(f"CloudWatch EMF adapter failed: {category.value}")
        self.category = category


class EpochMillisecondsClock(Protocol):
    """Injected wall-clock boundary required by the CloudWatch EMF timestamp contract."""

    def epoch_milliseconds(self) -> int:
        """Return milliseconds since the Unix epoch."""
        ...


class EmfLineWriter(Protocol):
    """Injected line-delivery boundary for one already-admitted EMF record."""

    def write(self, line: bytes) -> None:
        """Write one UTF-8 EMF line without gaining application authority."""
        ...


def _canonical_json(value: object) -> bytes:
    """Serialize one EMF document deterministically."""
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _validate_timestamp_ms(value: object) -> int:
    """Validate the bounded epoch-millisecond timestamp used by EMF metadata."""
    if (
        type(value) is not int
        or value < 0
        or value > MAX_CLOUDWATCH_EMF_TIMESTAMP_MS
    ):
        raise OperationalTelemetryValidationError(
            "CloudWatch EMF timestamp must be a bounded epoch-millisecond integer"
        )
    return value


def _emf_payload(event: OperationalEvent, timestamp_ms: int) -> bytes:
    """Render one canonical EMF document from existing operational truth only."""
    if type(event) is not OperationalEvent:
        raise OperationalTelemetryValidationError(
            "CloudWatch EMF adaptation requires one admitted OperationalEvent"
        )
    timestamp = _validate_timestamp_ms(timestamp_ms)
    count_metric, latency_metric = project_operational_metrics(event)

    if count_metric.name is not OperationalMetricName.STAGE_COUNT:
        raise OperationalTelemetryValidationError(
            "CloudWatch EMF count metric projection drifted"
        )
    if latency_metric.name is not OperationalMetricName.STAGE_LATENCY:
        raise OperationalTelemetryValidationError(
            "CloudWatch EMF latency metric projection drifted"
        )
    if count_metric.dimensions != latency_metric.dimensions:
        raise OperationalTelemetryValidationError(
            "CloudWatch EMF metric dimension projections disagree"
        )

    dimension_values = dict(count_metric.dimensions)
    if frozenset(dimension_values) != frozenset(CLOUDWATCH_EMF_DIMENSIONS):
        raise OperationalTelemetryValidationError(
            "CloudWatch EMF dimensions must match the frozen low-cardinality set"
        )
    if len(dimension_values) != len(CLOUDWATCH_EMF_DIMENSIONS):
        raise OperationalTelemetryValidationError(
            "CloudWatch EMF dimensions cannot contain duplicate targets"
        )

    metric_definitions = [
        {
            "Name": count_metric.name.value,
            "StorageResolution": CLOUDWATCH_EMF_STORAGE_RESOLUTION_SECONDS,
            "Unit": count_metric.unit.value,
        },
        {
            "Name": latency_metric.name.value,
            "StorageResolution": CLOUDWATCH_EMF_STORAGE_RESOLUTION_SECONDS,
            "Unit": latency_metric.unit.value,
        },
    ]

    root: dict[str, object] = {
        "_aws": {
            "CloudWatchMetrics": [
                {
                    "Dimensions": [list(CLOUDWATCH_EMF_DIMENSIONS)],
                    "Metrics": metric_definitions,
                    "Namespace": CLOUDWATCH_EMF_NAMESPACE,
                }
            ],
            "Timestamp": timestamp,
        },
        "AttemptCount": event.attempt_count,
        "EmfContractVersion": CLOUDWATCH_EMF_CONTRACT_VERSION,
        "EventId": event.event_id,
        "FailureCategory": (
            event.failure_category.value if event.failure_category is not None else None
        ),
        "OperationalStageCount": count_metric.value,
        "OperationalStageLatency": latency_metric.value,
    }
    for dimension_name in CLOUDWATCH_EMF_DIMENSIONS:
        root[dimension_name] = dimension_values[dimension_name]

    if event.public_request_id is not None:
        root["PublicRequestId"] = event.public_request_id
    if event.source_execution_id is not None:
        root["SourceExecutionId"] = event.source_execution_id
    if event.handoff_id is not None:
        root["HandoffId"] = event.handoff_id

    if root["ContractVersion"] != OPERATIONAL_TELEMETRY_CONTRACT_VERSION:
        raise OperationalTelemetryValidationError(
            "CloudWatch EMF operational contract version drifted"
        )
    if root["Operation"] != OPERATIONAL_TELEMETRY_OPERATION:
        raise OperationalTelemetryValidationError(
            "CloudWatch EMF operation projection drifted"
        )

    payload = _canonical_json(root)
    if len(payload) > MAX_CLOUDWATCH_EMF_DOCUMENT_BYTES:
        raise OperationalTelemetryValidationError(
            "CloudWatch EMF document exceeds the OpsLens hard byte limit"
        )
    return payload


@dataclass(frozen=True, slots=True)
class CloudWatchEmfDocument:
    """Content-addressed deterministic EMF representation for one admitted event."""

    event: OperationalEvent
    timestamp_ms: int
    payload: bytes
    document_sha256: str
    document_id: str

    def __post_init__(self) -> None:
        """Reject forged payloads, timestamps, or document identities."""
        if type(self.event) is not OperationalEvent:
            raise OperationalTelemetryValidationError(
                "CloudWatch EMF document requires one admitted OperationalEvent"
            )
        timestamp = _validate_timestamp_ms(self.timestamp_ms)
        if type(self.payload) is not bytes:
            raise OperationalTelemetryValidationError(
                "CloudWatch EMF document payload must be bytes"
            )
        if len(self.payload) > MAX_CLOUDWATCH_EMF_DOCUMENT_BYTES:
            raise OperationalTelemetryValidationError(
                "CloudWatch EMF document exceeds the OpsLens hard byte limit"
            )
        expected_payload = _emf_payload(self.event, timestamp)
        if self.payload != expected_payload:
            raise OperationalTelemetryValidationError(
                "CloudWatch EMF document payload does not match admitted semantics"
            )
        expected_sha256 = sha256(expected_payload).hexdigest()
        if (
            type(self.document_sha256) is not str
            or _DOCUMENT_SHA256_PATTERN.fullmatch(self.document_sha256) is None
            or self.document_sha256 != expected_sha256
        ):
            raise OperationalTelemetryValidationError(
                "CloudWatch EMF document SHA-256 does not match canonical payload"
            )
        expected_id = (
            f"{CLOUDWATCH_EMF_CONTRACT_VERSION}@sha256:{expected_sha256}"
        )
        if self.document_id != expected_id:
            raise OperationalTelemetryValidationError(
                "CloudWatch EMF document ID does not match canonical payload"
            )

    @property
    def canonical_json(self) -> bytes:
        """Return the exact EMF JSON payload without a transport newline."""
        return self.payload


def create_cloudwatch_emf_document(
    event: OperationalEvent,
    *,
    timestamp_ms: int,
) -> CloudWatchEmfDocument:
    """Create one deterministic content-addressed EMF document."""
    payload = _emf_payload(event, timestamp_ms)
    digest = sha256(payload).hexdigest()
    return CloudWatchEmfDocument(
        event=event,
        timestamp_ms=timestamp_ms,
        payload=payload,
        document_sha256=digest,
        document_id=f"{CLOUDWATCH_EMF_CONTRACT_VERSION}@sha256:{digest}",
    )


@dataclass(frozen=True, slots=True)
class CloudWatchEmfOperationalEventSink:
    """Offline-first OperationalEventSink adapter that writes one canonical EMF line."""

    clock: EpochMillisecondsClock
    writer: EmfLineWriter

    def emit(self, event: OperationalEvent) -> None:
        """Adapt and write one event exactly once, with no application retry."""
        if type(event) is not OperationalEvent:
            raise CloudWatchEmfAdapterError(
                CloudWatchEmfAdapterFailure.DOCUMENT_CONTRACT
            )
        try:
            raw_timestamp_ms = self.clock.epoch_milliseconds()
        except Exception:
            raise CloudWatchEmfAdapterError(
                CloudWatchEmfAdapterFailure.CLOCK_CONTRACT
            ) from None
        try:
            timestamp_ms = _validate_timestamp_ms(raw_timestamp_ms)
        except OperationalTelemetryValidationError:
            raise CloudWatchEmfAdapterError(
                CloudWatchEmfAdapterFailure.CLOCK_CONTRACT
            ) from None
        try:
            document = create_cloudwatch_emf_document(
                event,
                timestamp_ms=timestamp_ms,
            )
        except OperationalTelemetryValidationError:
            raise CloudWatchEmfAdapterError(
                CloudWatchEmfAdapterFailure.DOCUMENT_CONTRACT
            ) from None
        try:
            self.writer.write(document.canonical_json + b"\n")
        except Exception:
            raise CloudWatchEmfAdapterError(
                CloudWatchEmfAdapterFailure.WRITER_DELIVERY
            ) from None


__all__ = [
    "CLOUDWATCH_EMF_CONTRACT_VERSION",
    "CLOUDWATCH_EMF_DIMENSIONS",
    "CLOUDWATCH_EMF_NAMESPACE",
    "CLOUDWATCH_EMF_STORAGE_RESOLUTION_SECONDS",
    "MAX_CLOUDWATCH_EMF_DOCUMENT_BYTES",
    "MAX_CLOUDWATCH_EMF_TIMESTAMP_MS",
    "CloudWatchEmfAdapterError",
    "CloudWatchEmfAdapterFailure",
    "CloudWatchEmfDocument",
    "CloudWatchEmfOperationalEventSink",
    "EmfLineWriter",
    "EpochMillisecondsClock",
    "create_cloudwatch_emf_document",
]
