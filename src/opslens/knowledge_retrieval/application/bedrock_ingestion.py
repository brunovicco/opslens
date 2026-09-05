"""Application-owned bounded orchestration for one Bedrock Knowledge Base ingestion job."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol, cast

_TERMINAL_SUCCESS = frozenset({"COMPLETE"})
_TERMINAL_FAILURE = frozenset({"FAILED", "STOPPED"})
_ALLOWED_ACTIVE = frozenset({"STARTING", "IN_PROGRESS", "STOPPING"})
_ALLOWED_STATISTICS = (
    "numberOfDocumentsScanned",
    "numberOfNewDocumentsIndexed",
    "numberOfModifiedDocumentsIndexed",
    "numberOfDocumentsDeleted",
    "numberOfDocumentsFailed",
)


class BedrockIngestionValidationError(ValueError):
    """Raised when ingestion inputs or provider-neutral evidence are invalid."""


class BedrockIngestionFailed(RuntimeError):
    """Raised when the remote ingestion job reaches an unsuccessful terminal state."""


class BedrockIngestionTimeout(RuntimeError):
    """Raised when the bounded polling budget is exhausted before a terminal state."""


def _require_trimmed(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise BedrockIngestionValidationError(f"{field} must be one trimmed non-empty string")
    if len(value) > 128:
        raise BedrockIngestionValidationError(f"{field} must be at most 128 characters")
    return value


def _require_nonnegative_int(value: object, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise BedrockIngestionValidationError(f"{field} must be a non-negative integer")
    return value


def _require_statistics(value: object) -> dict[str, int]:
    if not isinstance(value, Mapping):
        raise BedrockIngestionValidationError("statistics must be an object")
    raw = cast(Mapping[object, object], value)
    result: dict[str, int] = {}
    for field in _ALLOWED_STATISTICS:
        if field in raw:
            result[field] = _require_nonnegative_int(raw[field], field=f"statistics.{field}")
    unknown = {key for key in raw if not isinstance(key, str) or key not in _ALLOWED_STATISTICS}
    if unknown:
        raise BedrockIngestionValidationError("statistics contains unsupported fields")
    return result


def _require_failure_reasons(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise BedrockIngestionValidationError("failure_reasons must be a list or tuple")
    items = cast(list[object] | tuple[object, ...], value)
    if len(items) > 20:
        raise BedrockIngestionValidationError("failure_reasons exceeds the bounded evidence limit")
    return tuple(_require_trimmed(item, field="failure_reason") for item in items)


@dataclass(frozen=True, slots=True)
class IngestionJobEvidence:
    """Provider-neutral state for one exact Bedrock ingestion job."""

    knowledge_base_id: str
    data_source_id: str
    ingestion_job_id: str
    status: str
    statistics: dict[str, int]
    failure_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "knowledge_base_id", _require_trimmed(self.knowledge_base_id, field="knowledge_base_id")
        )
        object.__setattr__(self, "data_source_id", _require_trimmed(self.data_source_id, field="data_source_id"))
        object.__setattr__(
            self, "ingestion_job_id", _require_trimmed(self.ingestion_job_id, field="ingestion_job_id")
        )
        status = _require_trimmed(self.status, field="status")
        if status not in _TERMINAL_SUCCESS | _TERMINAL_FAILURE | _ALLOWED_ACTIVE:
            raise BedrockIngestionValidationError(f"unsupported ingestion status {status!r}")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "statistics", _require_statistics(self.statistics))
        object.__setattr__(self, "failure_reasons", _require_failure_reasons(self.failure_reasons))


class IngestionJobControl(Protocol):
    """Minimal provider-neutral authority required by Gate 7.3 ingestion."""

    def start(self, *, knowledge_base_id: str, data_source_id: str) -> IngestionJobEvidence:
        """Start one ingestion job for the exact knowledge base and data source."""
        ...

    def get(
        self,
        *,
        knowledge_base_id: str,
        data_source_id: str,
        ingestion_job_id: str,
    ) -> IngestionJobEvidence:
        """Read one exact ingestion job."""
        ...


def run_bounded_ingestion(
    control: IngestionJobControl,
    *,
    knowledge_base_id: str,
    data_source_id: str,
    max_polls: int = 30,
    poll_interval_seconds: float = 5.0,
    sleeper: Callable[[float], None] = time.sleep,
) -> IngestionJobEvidence:
    """Start one job and poll serially until success, failure, or the bounded budget expires."""
    kb_id = _require_trimmed(knowledge_base_id, field="knowledge_base_id")
    ds_id = _require_trimmed(data_source_id, field="data_source_id")
    if type(max_polls) is not int or not 1 <= max_polls <= 120:
        raise BedrockIngestionValidationError("max_polls must be an integer between 1 and 120")
    if isinstance(poll_interval_seconds, bool) or not isinstance(poll_interval_seconds, (int, float)):
        raise BedrockIngestionValidationError("poll_interval_seconds must be numeric")
    interval = float(poll_interval_seconds)
    if not 0 <= interval <= 60:
        raise BedrockIngestionValidationError("poll_interval_seconds must be between 0 and 60")

    evidence = control.start(knowledge_base_id=kb_id, data_source_id=ds_id)
    if evidence.knowledge_base_id != kb_id or evidence.data_source_id != ds_id:
        raise BedrockIngestionValidationError("started ingestion evidence does not match requested target")

    for poll_index in range(max_polls + 1):
        if evidence.status in _TERMINAL_SUCCESS:
            return evidence
        if evidence.status in _TERMINAL_FAILURE:
            reasons = "; ".join(evidence.failure_reasons) or "no failure reason returned"
            raise BedrockIngestionFailed(
                f"ingestion job {evidence.ingestion_job_id} ended as {evidence.status}: {reasons}"
            )
        if poll_index == max_polls:
            break
        if interval:
            sleeper(interval)
        evidence = control.get(
            knowledge_base_id=kb_id,
            data_source_id=ds_id,
            ingestion_job_id=evidence.ingestion_job_id,
        )
        if evidence.knowledge_base_id != kb_id or evidence.data_source_id != ds_id:
            raise BedrockIngestionValidationError("polled ingestion evidence does not match requested target")

    raise BedrockIngestionTimeout(
        f"ingestion job {evidence.ingestion_job_id} did not reach a terminal state after {max_polls} polls"
    )
