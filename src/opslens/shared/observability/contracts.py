"""Provider-neutral operational telemetry contract for bounded public analysis."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from types import MappingProxyType
from typing import Final, Mapping

OPERATIONAL_TELEMETRY_CONTRACT_VERSION = "operational-telemetry:v1"
OPERATIONAL_TELEMETRY_OPERATION = "analyze_public_repository"
MAX_OPERATIONAL_DURATION_MS = 900_000
MAX_OPERATIONAL_ATTEMPTS = 3

_SHA256_PATTERN = r"[0-9a-f]{64}"
_PUBLIC_REQUEST_ID_PATTERN = re.compile(
    rf"^public-analysis-request:v1:{_SHA256_PATTERN}$",
    re.ASCII,
)
_SOURCE_EXECUTION_ID_PATTERN = re.compile(
    rf"^public-repository-evidence:v1@sha256:{_SHA256_PATTERN}$",
    re.ASCII,
)
_HANDOFF_ID_PATTERN = re.compile(
    rf"^public-analysis-handoff:v1@sha256:{_SHA256_PATTERN}$",
    re.ASCII,
)
_EVENT_SHA256_PATTERN = re.compile(rf"^{_SHA256_PATTERN}$", re.ASCII)


class OperationalTelemetryValidationError(ValueError):
    """Raised when operational telemetry violates the frozen v1 contract."""


class OperationalStage(StrEnum):
    """Bounded stages in the currently validated Phase 9 public-analysis path."""

    PUBLIC_REQUEST_ADMISSION = "public_request_admission"
    REPOSITORY_EVIDENCE = "repository_evidence"
    SEMANTIC_PLANNING = "semantic_planning"
    HYBRID_ROUTE_ADMISSION = "hybrid_route_admission"
    PUBLIC_HANDOFF = "public_handoff"


class OperationalOutcome(StrEnum):
    """Bounded outcomes emitted by one operational stage."""

    SUCCEEDED = "succeeded"
    REJECTED = "rejected"
    FAILED = "failed"


class OperationalFailureCategory(StrEnum):
    """Content-free failure categories used only for diagnosis."""

    REQUEST_CONTRACT = "request_contract"
    SOURCE_RESOLUTION = "source_resolution"
    EVIDENCE_CONTRACT = "evidence_contract"
    PLANNER_INVOCATION = "planner_invocation"
    PLANNER_OUTPUT_CONTRACT = "planner_output_contract"
    ROUTE_AUTHORITY = "route_authority"
    HANDOFF_CONTRACT = "handoff_contract"
    UNEXPECTED_INTERNAL = "unexpected_internal"


class OperationalMetricName(StrEnum):
    """Low-cardinality metrics projected from one admitted event."""

    STAGE_COUNT = "OperationalStageCount"
    STAGE_LATENCY = "OperationalStageLatency"


class OperationalMetricUnit(StrEnum):
    """Metric units supported by the v1 projection."""

    COUNT = "Count"
    MILLISECONDS = "Milliseconds"


_ALLOWED_FAILURES_BY_STAGE: Final[
    Mapping[OperationalStage, frozenset[OperationalFailureCategory]]
] = MappingProxyType(
    {
        OperationalStage.PUBLIC_REQUEST_ADMISSION: frozenset(
            {
                OperationalFailureCategory.REQUEST_CONTRACT,
                OperationalFailureCategory.UNEXPECTED_INTERNAL,
            }
        ),
        OperationalStage.REPOSITORY_EVIDENCE: frozenset(
            {
                OperationalFailureCategory.SOURCE_RESOLUTION,
                OperationalFailureCategory.EVIDENCE_CONTRACT,
                OperationalFailureCategory.UNEXPECTED_INTERNAL,
            }
        ),
        OperationalStage.SEMANTIC_PLANNING: frozenset(
            {
                OperationalFailureCategory.PLANNER_INVOCATION,
                OperationalFailureCategory.PLANNER_OUTPUT_CONTRACT,
                OperationalFailureCategory.UNEXPECTED_INTERNAL,
            }
        ),
        OperationalStage.HYBRID_ROUTE_ADMISSION: frozenset(
            {
                OperationalFailureCategory.ROUTE_AUTHORITY,
                OperationalFailureCategory.UNEXPECTED_INTERNAL,
            }
        ),
        OperationalStage.PUBLIC_HANDOFF: frozenset(
            {
                OperationalFailureCategory.HANDOFF_CONTRACT,
                OperationalFailureCategory.UNEXPECTED_INTERNAL,
            }
        ),
    }
)


def _canonical_json(value: object) -> bytes:
    """Serialize telemetry identity semantics deterministically."""
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _validate_optional_identity(
    value: object,
    *,
    field: str,
    pattern: re.Pattern[str],
) -> str | None:
    """Admit only known content-addressed identifiers, never arbitrary text."""
    if value is None:
        return None
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise OperationalTelemetryValidationError(
            f"{field} must be one admitted content-addressed identifier or null"
        )
    return value


def _identity_payload(
    *,
    stage: OperationalStage,
    outcome: OperationalOutcome,
    duration_ms: int,
    attempt_count: int,
    public_request_id: str | None,
    source_execution_id: str | None,
    handoff_id: str | None,
    failure_category: OperationalFailureCategory | None,
) -> dict[str, object]:
    """Return the complete v1 identity payload without arbitrary content fields."""
    return {
        "attempt_count": attempt_count,
        "contract_version": OPERATIONAL_TELEMETRY_CONTRACT_VERSION,
        "duration_ms": duration_ms,
        "failure_category": (
            failure_category.value if failure_category is not None else None
        ),
        "handoff_id": handoff_id,
        "operation": OPERATIONAL_TELEMETRY_OPERATION,
        "outcome": outcome.value,
        "public_request_id": public_request_id,
        "source_execution_id": source_execution_id,
        "stage": stage.value,
    }


def _validate_event_semantics(
    *,
    stage: object,
    outcome: object,
    duration_ms: object,
    attempt_count: object,
    public_request_id: object,
    source_execution_id: object,
    handoff_id: object,
    failure_category: object,
) -> tuple[
    OperationalStage,
    OperationalOutcome,
    int,
    int,
    str | None,
    str | None,
    str | None,
    OperationalFailureCategory | None,
]:
    """Validate one event before identity construction or direct admission."""
    if type(stage) is not OperationalStage:
        raise OperationalTelemetryValidationError("stage must be OperationalStage")
    if type(outcome) is not OperationalOutcome:
        raise OperationalTelemetryValidationError("outcome must be OperationalOutcome")
    if (
        type(duration_ms) is not int
        or duration_ms < 0
        or duration_ms > MAX_OPERATIONAL_DURATION_MS
    ):
        raise OperationalTelemetryValidationError(
            "duration_ms must be an integer within the v1 hard limit"
        )
    if (
        type(attempt_count) is not int
        or attempt_count < 1
        or attempt_count > MAX_OPERATIONAL_ATTEMPTS
    ):
        raise OperationalTelemetryValidationError(
            "attempt_count must be between 1 and the v1 hard limit"
        )

    validated_public_request_id = _validate_optional_identity(
        public_request_id,
        field="public_request_id",
        pattern=_PUBLIC_REQUEST_ID_PATTERN,
    )
    validated_source_execution_id = _validate_optional_identity(
        source_execution_id,
        field="source_execution_id",
        pattern=_SOURCE_EXECUTION_ID_PATTERN,
    )
    validated_handoff_id = _validate_optional_identity(
        handoff_id,
        field="handoff_id",
        pattern=_HANDOFF_ID_PATTERN,
    )

    if failure_category is not None and type(failure_category) is not OperationalFailureCategory:
        raise OperationalTelemetryValidationError(
            "failure_category must be OperationalFailureCategory or null"
        )
    validated_failure_category = failure_category

    if outcome is OperationalOutcome.SUCCEEDED:
        if validated_failure_category is not None:
            raise OperationalTelemetryValidationError(
                "successful events cannot carry a failure category"
            )
    elif validated_failure_category is None:
        raise OperationalTelemetryValidationError(
            "rejected and failed events require a bounded failure category"
        )

    if (
        validated_failure_category is not None
        and validated_failure_category not in _ALLOWED_FAILURES_BY_STAGE[stage]
    ):
        raise OperationalTelemetryValidationError(
            "failure category is not authorized for the selected stage"
        )

    if stage is OperationalStage.PUBLIC_REQUEST_ADMISSION:
        if (
            outcome is OperationalOutcome.SUCCEEDED
            and validated_public_request_id is None
        ):
            raise OperationalTelemetryValidationError(
                "successful request admission requires public_request_id"
            )
        if (
            validated_source_execution_id is not None
            or validated_handoff_id is not None
        ):
            raise OperationalTelemetryValidationError(
                "request admission cannot reference later-stage identities"
            )
    elif validated_public_request_id is None:
        raise OperationalTelemetryValidationError(
            "post-admission stages require public_request_id"
        )

    if stage is OperationalStage.REPOSITORY_EVIDENCE:
        if (
            outcome is OperationalOutcome.SUCCEEDED
            and validated_source_execution_id is None
        ):
            raise OperationalTelemetryValidationError(
                "successful repository evidence requires source_execution_id"
            )
        if validated_handoff_id is not None:
            raise OperationalTelemetryValidationError(
                "repository evidence cannot reference a later handoff"
            )
    elif stage in (
        OperationalStage.SEMANTIC_PLANNING,
        OperationalStage.HYBRID_ROUTE_ADMISSION,
    ):
        if validated_source_execution_id is None:
            raise OperationalTelemetryValidationError(
                "planning and route stages require source_execution_id"
            )
        if validated_handoff_id is not None:
            raise OperationalTelemetryValidationError(
                "planning and route stages cannot reference a later handoff"
            )
    elif stage is OperationalStage.PUBLIC_HANDOFF:
        if validated_source_execution_id is None:
            raise OperationalTelemetryValidationError(
                "public handoff requires source_execution_id"
            )
        if outcome is OperationalOutcome.SUCCEEDED and validated_handoff_id is None:
            raise OperationalTelemetryValidationError(
                "successful public handoff requires handoff_id"
            )

    return (
        stage,
        outcome,
        duration_ms,
        attempt_count,
        validated_public_request_id,
        validated_source_execution_id,
        validated_handoff_id,
        validated_failure_category,
    )


@dataclass(frozen=True, slots=True)
class OperationalEvent:
    """Content-addressed operational evidence for one bounded application stage."""

    stage: OperationalStage
    outcome: OperationalOutcome
    duration_ms: int
    attempt_count: int
    public_request_id: str | None
    source_execution_id: str | None
    handoff_id: str | None
    failure_category: OperationalFailureCategory | None
    event_sha256: str
    event_id: str

    def __post_init__(self) -> None:
        """Reject content-bearing, forged, or semantically inconsistent events."""
        (
            stage,
            outcome,
            duration_ms,
            attempt_count,
            public_request_id,
            source_execution_id,
            handoff_id,
            failure_category,
        ) = _validate_event_semantics(
            stage=self.stage,
            outcome=self.outcome,
            duration_ms=self.duration_ms,
            attempt_count=self.attempt_count,
            public_request_id=self.public_request_id,
            source_execution_id=self.source_execution_id,
            handoff_id=self.handoff_id,
            failure_category=self.failure_category,
        )
        payload = _identity_payload(
            stage=stage,
            outcome=outcome,
            duration_ms=duration_ms,
            attempt_count=attempt_count,
            public_request_id=public_request_id,
            source_execution_id=source_execution_id,
            handoff_id=handoff_id,
            failure_category=failure_category,
        )
        expected_sha256 = sha256(_canonical_json(payload)).hexdigest()
        if (
            type(self.event_sha256) is not str
            or _EVENT_SHA256_PATTERN.fullmatch(self.event_sha256) is None
            or self.event_sha256 != expected_sha256
        ):
            raise OperationalTelemetryValidationError(
                "event_sha256 must match the canonical operational event semantics"
            )
        expected_event_id = (
            f"{OPERATIONAL_TELEMETRY_CONTRACT_VERSION}@sha256:{expected_sha256}"
        )
        if self.event_id != expected_event_id:
            raise OperationalTelemetryValidationError(
                "event_id must match the content-addressed operational event identity"
            )

    @property
    def canonical_json(self) -> bytes:
        """Return the bounded content-free canonical event representation."""
        return _canonical_json(
            _identity_payload(
                stage=self.stage,
                outcome=self.outcome,
                duration_ms=self.duration_ms,
                attempt_count=self.attempt_count,
                public_request_id=self.public_request_id,
                source_execution_id=self.source_execution_id,
                handoff_id=self.handoff_id,
                failure_category=self.failure_category,
            )
        )


@dataclass(frozen=True, slots=True)
class OperationalMetricPoint:
    """One low-cardinality metric projection with a fixed dimension set."""

    name: OperationalMetricName
    value: float
    unit: OperationalMetricUnit
    stage: OperationalStage
    outcome: OperationalOutcome

    def __post_init__(self) -> None:
        """Reject forged metric names, units, dimensions, or unbounded values."""
        if type(self.name) is not OperationalMetricName:
            raise OperationalTelemetryValidationError(
                "metric name must be OperationalMetricName"
            )
        if type(self.unit) is not OperationalMetricUnit:
            raise OperationalTelemetryValidationError(
                "metric unit must be OperationalMetricUnit"
            )
        if type(self.stage) is not OperationalStage:
            raise OperationalTelemetryValidationError(
                "metric stage must be OperationalStage"
            )
        if type(self.outcome) is not OperationalOutcome:
            raise OperationalTelemetryValidationError(
                "metric outcome must be OperationalOutcome"
            )
        if type(self.value) is not float or not math.isfinite(self.value):
            raise OperationalTelemetryValidationError(
                "metric value must be one finite float"
            )
        if self.name is OperationalMetricName.STAGE_COUNT:
            if self.unit is not OperationalMetricUnit.COUNT or self.value != 1.0:
                raise OperationalTelemetryValidationError(
                    "stage count metric must be exactly 1 Count"
                )
        elif (
            self.unit is not OperationalMetricUnit.MILLISECONDS
            or self.value < 0.0
            or self.value > float(MAX_OPERATIONAL_DURATION_MS)
        ):
            raise OperationalTelemetryValidationError(
                "stage latency metric must be bounded Milliseconds"
            )

    @property
    def dimensions(self) -> Mapping[str, str]:
        """Return only bounded dimensions; never high-cardinality request/source IDs."""
        return MappingProxyType(
            {
                "ContractVersion": OPERATIONAL_TELEMETRY_CONTRACT_VERSION,
                "Operation": OPERATIONAL_TELEMETRY_OPERATION,
                "Outcome": self.outcome.value,
                "Stage": self.stage.value,
            }
        )


def create_operational_event(
    *,
    stage: OperationalStage,
    outcome: OperationalOutcome,
    duration_ms: int,
    attempt_count: int = 1,
    public_request_id: str | None = None,
    source_execution_id: str | None = None,
    handoff_id: str | None = None,
    failure_category: OperationalFailureCategory | None = None,
) -> OperationalEvent:
    """Create one validated content-addressed operational event."""
    (
        validated_stage,
        validated_outcome,
        validated_duration_ms,
        validated_attempt_count,
        validated_public_request_id,
        validated_source_execution_id,
        validated_handoff_id,
        validated_failure_category,
    ) = _validate_event_semantics(
        stage=stage,
        outcome=outcome,
        duration_ms=duration_ms,
        attempt_count=attempt_count,
        public_request_id=public_request_id,
        source_execution_id=source_execution_id,
        handoff_id=handoff_id,
        failure_category=failure_category,
    )
    payload = _identity_payload(
        stage=validated_stage,
        outcome=validated_outcome,
        duration_ms=validated_duration_ms,
        attempt_count=validated_attempt_count,
        public_request_id=validated_public_request_id,
        source_execution_id=validated_source_execution_id,
        handoff_id=validated_handoff_id,
        failure_category=validated_failure_category,
    )
    digest = sha256(_canonical_json(payload)).hexdigest()
    return OperationalEvent(
        stage=validated_stage,
        outcome=validated_outcome,
        duration_ms=validated_duration_ms,
        attempt_count=validated_attempt_count,
        public_request_id=validated_public_request_id,
        source_execution_id=validated_source_execution_id,
        handoff_id=validated_handoff_id,
        failure_category=validated_failure_category,
        event_sha256=digest,
        event_id=f"{OPERATIONAL_TELEMETRY_CONTRACT_VERSION}@sha256:{digest}",
    )


def project_operational_metrics(
    event: OperationalEvent,
) -> tuple[OperationalMetricPoint, OperationalMetricPoint]:
    """Project deterministic low-cardinality count and latency metrics."""
    if type(event) is not OperationalEvent:
        raise OperationalTelemetryValidationError(
            "metric projection requires one admitted OperationalEvent"
        )
    return (
        OperationalMetricPoint(
            name=OperationalMetricName.STAGE_COUNT,
            value=1.0,
            unit=OperationalMetricUnit.COUNT,
            stage=event.stage,
            outcome=event.outcome,
        ),
        OperationalMetricPoint(
            name=OperationalMetricName.STAGE_LATENCY,
            value=float(event.duration_ms),
            unit=OperationalMetricUnit.MILLISECONDS,
            stage=event.stage,
            outcome=event.outcome,
        ),
    )


__all__ = [
    "MAX_OPERATIONAL_ATTEMPTS",
    "MAX_OPERATIONAL_DURATION_MS",
    "OPERATIONAL_TELEMETRY_CONTRACT_VERSION",
    "OPERATIONAL_TELEMETRY_OPERATION",
    "OperationalEvent",
    "OperationalFailureCategory",
    "OperationalMetricName",
    "OperationalMetricPoint",
    "OperationalMetricUnit",
    "OperationalOutcome",
    "OperationalStage",
    "OperationalTelemetryValidationError",
    "create_operational_event",
    "project_operational_metrics",
]
