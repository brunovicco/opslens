"""Provider-neutral result evidence for one bounded triage-to-specialist reasoning path."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256

from opslens.agent_baseline.domain.models import SingleAgentTask
from opslens.agent_baseline.domain.reasoning import AgentReasoningResult
from opslens.multi_agent.domain.errors import MultiAgentRealComparisonValidationError
from opslens.multi_agent.domain.handoff import MultiAgentHandoffDecision
from opslens.multi_agent.domain.triage_reasoning import MultiAgentTriageReasoningResult

MULTI_AGENT_TWO_MODEL_REASONING_CONTRACT_VERSION = "multi-agent-two-model-reasoning:v1"
MAX_MULTI_AGENT_MODEL_INVOCATIONS_PER_TASK = 2
MAX_MULTI_AGENT_ADAPTIVE_RETRIES = 0
MAX_MULTI_AGENT_ADAPTIVE_FALLBACKS = 0
MAX_MULTI_AGENT_CAPABILITY_EXECUTIONS = 0

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_RESULT_ID_PATTERN = re.compile(
    rf"^{re.escape(MULTI_AGENT_TWO_MODEL_REASONING_CONTRACT_VERSION)}:result:[0-9a-f]{{64}}$",
    re.ASCII,
)


class MultiAgentTwoModelOutcome(StrEnum):
    """Closed terminal outcomes before capability execution."""

    TRIAGE_ABSTAINED = "triage_abstained"
    HANDOFF_REJECTED = "handoff_rejected"
    SPECIALIST_REASONED = "specialist_reasoned"


def _canonical_sha256(value: object) -> str:
    """Return SHA-256 over deterministic canonical JSON semantics."""
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _optional_non_empty_string(value: object, *, label: str) -> str | None:
    """Validate one optional normalized evidence identifier."""
    if value is None:
        return None
    if type(value) is not str or not value.strip() or value.strip() != value:
        raise MultiAgentRealComparisonValidationError(
            f"{label} must be a normalized non-empty string or null"
        )
    return value


@dataclass(frozen=True, slots=True)
class MultiAgentTwoModelReasoningResult:
    """Bind triage, deterministic handoff, and optional specialist reasoning evidence."""

    source_task: SingleAgentTask
    triage_result: MultiAgentTriageReasoningResult
    outcome: MultiAgentTwoModelOutcome
    handoff_evidence_id: str | None
    specialist_task_id: str | None
    specialist_result: AgentReasoningResult | None
    model_invocation_count: int
    capability_executions: int
    result_sha256: str
    result_id: str

    def __post_init__(self) -> None:
        """Reject cross-task, over-bound, or internally inconsistent terminal evidence."""
        if type(self.source_task) is not SingleAgentTask:
            raise MultiAgentRealComparisonValidationError(
                "source_task must be one admitted SingleAgentTask"
            )
        if type(self.triage_result) is not MultiAgentTriageReasoningResult:
            raise MultiAgentRealComparisonValidationError(
                "triage_result must be MultiAgentTriageReasoningResult"
            )
        if self.triage_result.source_task.task_id != self.source_task.task_id:
            raise MultiAgentRealComparisonValidationError(
                "triage result is not bound to the source task"
            )
        if type(self.outcome) is not MultiAgentTwoModelOutcome:
            raise MultiAgentRealComparisonValidationError(
                "outcome must be MultiAgentTwoModelOutcome"
            )
        handoff_id = _optional_non_empty_string(
            self.handoff_evidence_id,
            label="handoff_evidence_id",
        )
        specialist_task_id = _optional_non_empty_string(
            self.specialist_task_id,
            label="specialist_task_id",
        )
        if self.specialist_result is not None and type(
            self.specialist_result
        ) is not AgentReasoningResult:
            raise MultiAgentRealComparisonValidationError(
                "specialist_result must be AgentReasoningResult or null"
            )
        if (
            type(self.model_invocation_count) is not int
            or not 1
            <= self.model_invocation_count
            <= MAX_MULTI_AGENT_MODEL_INVOCATIONS_PER_TASK
        ):
            raise MultiAgentRealComparisonValidationError(
                "model_invocation_count violates the two-model bound"
            )
        if self.capability_executions != MAX_MULTI_AGENT_CAPABILITY_EXECUTIONS:
            raise MultiAgentRealComparisonValidationError(
                "the first two-model baseline cannot execute capabilities"
            )

        triage_decision = self.triage_result.proposal.decision
        if self.outcome is MultiAgentTwoModelOutcome.TRIAGE_ABSTAINED:
            if triage_decision is not MultiAgentHandoffDecision.ABSTAIN:
                raise MultiAgentRealComparisonValidationError(
                    "triage_abstained requires an ABSTAIN proposal"
                )
            if any(
                value is not None
                for value in (handoff_id, specialist_task_id, self.specialist_result)
            ):
                raise MultiAgentRealComparisonValidationError(
                    "triage_abstained cannot carry handoff or specialist evidence"
                )
            if self.model_invocation_count != 1:
                raise MultiAgentRealComparisonValidationError(
                    "triage_abstained must contain exactly one model invocation"
                )
        elif self.outcome is MultiAgentTwoModelOutcome.HANDOFF_REJECTED:
            if triage_decision is not MultiAgentHandoffDecision.HANDOFF:
                raise MultiAgentRealComparisonValidationError(
                    "handoff_rejected requires a HANDOFF proposal"
                )
            if any(
                value is not None
                for value in (handoff_id, specialist_task_id, self.specialist_result)
            ):
                raise MultiAgentRealComparisonValidationError(
                    "handoff_rejected cannot carry admitted specialist evidence"
                )
            if self.model_invocation_count != 1:
                raise MultiAgentRealComparisonValidationError(
                    "handoff_rejected must contain exactly one model invocation"
                )
        else:
            if triage_decision is not MultiAgentHandoffDecision.HANDOFF:
                raise MultiAgentRealComparisonValidationError(
                    "specialist_reasoned requires a HANDOFF triage proposal"
                )
            if handoff_id is None or specialist_task_id is None:
                raise MultiAgentRealComparisonValidationError(
                    "specialist_reasoned requires admitted handoff and specialist task IDs"
                )
            specialist = self.specialist_result
            if specialist is None:
                raise MultiAgentRealComparisonValidationError(
                    "specialist_reasoned requires one specialist reasoning result"
                )
            if specialist.task.task_id != specialist_task_id:
                raise MultiAgentRealComparisonValidationError(
                    "specialist reasoning result is not bound to the admitted specialist task"
                )
            if self.model_invocation_count != 2:
                raise MultiAgentRealComparisonValidationError(
                    "specialist_reasoned must contain exactly two model invocations"
                )

        expected = _canonical_sha256(self._identity_payload())
        if (
            type(self.result_sha256) is not str
            or _SHA256_PATTERN.fullmatch(self.result_sha256) is None
            or self.result_sha256 != expected
        ):
            raise MultiAgentRealComparisonValidationError(
                "result_sha256 must match canonical two-model reasoning semantics"
            )
        expected_id = (
            f"{MULTI_AGENT_TWO_MODEL_REASONING_CONTRACT_VERSION}:result:{expected}"
        )
        if self.result_id != expected_id or _RESULT_ID_PATTERN.fullmatch(self.result_id) is None:
            raise MultiAgentRealComparisonValidationError(
                "result_id must match content-addressed two-model reasoning semantics"
            )

    def _identity_payload(self) -> dict[str, object]:
        """Project terminal evidence without raw model content."""
        return {
            "capability_executions": self.capability_executions,
            "contract_version": MULTI_AGENT_TWO_MODEL_REASONING_CONTRACT_VERSION,
            "handoff_evidence_id": self.handoff_evidence_id,
            "model_invocation_count": self.model_invocation_count,
            "outcome": self.outcome.value,
            "source_task_id": self.source_task.task_id,
            "specialist_result_id": (
                self.specialist_result.result_id
                if self.specialist_result is not None
                else None
            ),
            "specialist_task_id": self.specialist_task_id,
            "triage_result_id": self.triage_result.result_id,
        }

    @classmethod
    def create(
        cls,
        *,
        source_task: SingleAgentTask,
        triage_result: MultiAgentTriageReasoningResult,
        outcome: MultiAgentTwoModelOutcome,
        handoff_evidence_id: str | None,
        specialist_task_id: str | None,
        specialist_result: AgentReasoningResult | None,
        model_invocation_count: int,
    ) -> MultiAgentTwoModelReasoningResult:
        """Create one content-addressed terminal result before capability execution."""
        payload: dict[str, object] = {
            "capability_executions": MAX_MULTI_AGENT_CAPABILITY_EXECUTIONS,
            "contract_version": MULTI_AGENT_TWO_MODEL_REASONING_CONTRACT_VERSION,
            "handoff_evidence_id": handoff_evidence_id,
            "model_invocation_count": model_invocation_count,
            "outcome": outcome.value,
            "source_task_id": source_task.task_id,
            "specialist_result_id": (
                specialist_result.result_id if specialist_result is not None else None
            ),
            "specialist_task_id": specialist_task_id,
            "triage_result_id": triage_result.result_id,
        }
        digest = _canonical_sha256(payload)
        return cls(
            source_task=source_task,
            triage_result=triage_result,
            outcome=outcome,
            handoff_evidence_id=handoff_evidence_id,
            specialist_task_id=specialist_task_id,
            specialist_result=specialist_result,
            model_invocation_count=model_invocation_count,
            capability_executions=MAX_MULTI_AGENT_CAPABILITY_EXECUTIONS,
            result_sha256=digest,
            result_id=(
                f"{MULTI_AGENT_TWO_MODEL_REASONING_CONTRACT_VERSION}:result:{digest}"
            ),
        )


__all__ = [
    "MAX_MULTI_AGENT_ADAPTIVE_FALLBACKS",
    "MAX_MULTI_AGENT_ADAPTIVE_RETRIES",
    "MAX_MULTI_AGENT_CAPABILITY_EXECUTIONS",
    "MAX_MULTI_AGENT_MODEL_INVOCATIONS_PER_TASK",
    "MULTI_AGENT_TWO_MODEL_REASONING_CONTRACT_VERSION",
    "MultiAgentTwoModelOutcome",
    "MultiAgentTwoModelReasoningResult",
]
