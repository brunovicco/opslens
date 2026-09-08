"""Deterministic contracts for the bounded AgentCore Runtime invocation boundary."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from opslens.agent_baseline.domain.models import AgentCapability, AgentDecision
from opslens.agent_baseline.domain.reasoning import (
    AgentReasoningAuthorizationOutcome,
    AgentReasoningFailureCategory,
    AgentReasoningInvocationEvidence,
    AgentReasoningResult,
)

AGENTCORE_RUNTIME_INVOCATION_CONTRACT_VERSION = "agentcore-runtime-invocation:v1"
MAX_AGENTCORE_RUNTIME_REQUEST_UTF8_BYTES = 4_096
MAX_AGENTCORE_RUNTIME_MODEL_INVOCATIONS = 1
MAX_AGENTCORE_RUNTIME_CAPABILITY_EXECUTIONS = 0
MAX_AGENTCORE_RUNTIME_ADAPTIVE_RETRIES = 0
MAX_AGENTCORE_RUNTIME_ADAPTIVE_FALLBACKS = 0

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_PROJECTION_ID_PATTERN = re.compile(
    rf"^{re.escape(AGENTCORE_RUNTIME_INVOCATION_CONTRACT_VERSION)}:projection:[0-9a-f]{{64}}$",
    re.ASCII,
)


class AgentCoreRuntimeValidationError(ValueError):
    """Raised when untrusted runtime input or projection violates the frozen contract."""


def _canonical_json(value: object) -> bytes:
    """Serialize one deterministic AgentCore runtime identity payload."""
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_sha256(value: object) -> str:
    """Hash one canonical AgentCore runtime identity payload."""
    return sha256(_canonical_json(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class AgentCoreReasoningProjection:
    """Content-minimized projection of one already-admitted reasoning result."""

    task_id: str
    reasoning_result_id: str
    authorization_outcome: AgentReasoningAuthorizationOutcome
    decision: AgentDecision
    capability: AgentCapability | None
    authorization_evidence_id: str | None
    failure_category: AgentReasoningFailureCategory | None
    invocation_evidence: AgentReasoningInvocationEvidence
    projection_sha256: str
    projection_id: str

    def __post_init__(self) -> None:
        """Reject malformed or forged runtime projections."""
        if type(self.task_id) is not str or not self.task_id:
            raise AgentCoreRuntimeValidationError("task_id must be a non-empty string")
        if type(self.reasoning_result_id) is not str or not self.reasoning_result_id:
            raise AgentCoreRuntimeValidationError(
                "reasoning_result_id must be a non-empty string"
            )
        if type(self.authorization_outcome) is not AgentReasoningAuthorizationOutcome:
            raise AgentCoreRuntimeValidationError(
                "authorization_outcome must be AgentReasoningAuthorizationOutcome"
            )
        if type(self.decision) is not AgentDecision:
            raise AgentCoreRuntimeValidationError("decision must be AgentDecision")
        if self.capability is not None and type(self.capability) is not AgentCapability:
            raise AgentCoreRuntimeValidationError(
                "capability must be AgentCapability or null"
            )
        if (
            self.authorization_evidence_id is not None
            and type(self.authorization_evidence_id) is not str
        ):
            raise AgentCoreRuntimeValidationError(
                "authorization_evidence_id must be a string or null"
            )
        if (
            self.failure_category is not None
            and type(self.failure_category) is not AgentReasoningFailureCategory
        ):
            raise AgentCoreRuntimeValidationError(
                "failure_category must be AgentReasoningFailureCategory or null"
            )
        if type(self.invocation_evidence) is not AgentReasoningInvocationEvidence:
            raise AgentCoreRuntimeValidationError(
                "invocation_evidence must be AgentReasoningInvocationEvidence"
            )
        if self.invocation_evidence.task_id != self.task_id:
            raise AgentCoreRuntimeValidationError(
                "invocation evidence must be bound to the projected task"
            )

        expected = _canonical_sha256(self._identity_payload())
        if (
            type(self.projection_sha256) is not str
            or _SHA256_PATTERN.fullmatch(self.projection_sha256) is None
            or self.projection_sha256 != expected
        ):
            raise AgentCoreRuntimeValidationError(
                "projection_sha256 must match canonical runtime projection semantics"
            )
        expected_id = (
            f"{AGENTCORE_RUNTIME_INVOCATION_CONTRACT_VERSION}:projection:{expected}"
        )
        if (
            self.projection_id != expected_id
            or _PROJECTION_ID_PATTERN.fullmatch(self.projection_id) is None
        ):
            raise AgentCoreRuntimeValidationError(
                "projection_id must match content-addressed runtime projection semantics"
            )

    def _identity_payload(self) -> dict[str, object]:
        """Return the closed semantics that own projection identity."""
        return {
            "authorization_evidence_id": self.authorization_evidence_id,
            "authorization_outcome": self.authorization_outcome.value,
            "capability": self.capability.value if self.capability is not None else None,
            "contract_version": AGENTCORE_RUNTIME_INVOCATION_CONTRACT_VERSION,
            "decision": self.decision.value,
            "failure_category": (
                self.failure_category.value if self.failure_category is not None else None
            ),
            "invocation_evidence_id": self.invocation_evidence.evidence_id,
            "reasoning_result_id": self.reasoning_result_id,
            "task_id": self.task_id,
        }

    def to_payload(self) -> dict[str, object]:
        """Return the bounded protocol projection without raw model or business content."""
        evidence = self.invocation_evidence
        return {
            "authorization_evidence_id": self.authorization_evidence_id,
            "authorization_outcome": self.authorization_outcome.value,
            "capability": self.capability.value if self.capability is not None else None,
            "contract_version": AGENTCORE_RUNTIME_INVOCATION_CONTRACT_VERSION,
            "decision": self.decision.value,
            "failure_category": (
                self.failure_category.value if self.failure_category is not None else None
            ),
            "invocation_evidence": {
                "cache_read_input_tokens": evidence.cache_read_input_tokens,
                "cache_write_input_tokens": evidence.cache_write_input_tokens,
                "client_elapsed_ms": evidence.client_elapsed_ms,
                "evidence_id": evidence.evidence_id,
                "evidence_sha256": evidence.evidence_sha256,
                "input_tokens": evidence.input_tokens,
                "model_id": evidence.model_id,
                "output_tokens": evidence.output_tokens,
                "provider": evidence.provider,
                "provider_latency_ms": evidence.provider_latency_ms,
                "region": evidence.region,
                "request_id": evidence.request_id,
                "retry_attempts": evidence.retry_attempts,
                "stop_reason": evidence.stop_reason,
                "total_tokens": evidence.total_tokens,
            },
            "projection_id": self.projection_id,
            "projection_sha256": self.projection_sha256,
            "reasoning_result_id": self.reasoning_result_id,
            "task_id": self.task_id,
        }

    @classmethod
    def create(cls, result: AgentReasoningResult) -> AgentCoreReasoningProjection:
        """Project one admitted reasoning result into the runtime protocol contract."""
        if type(result) is not AgentReasoningResult:
            raise AgentCoreRuntimeValidationError(
                "result must be one admitted AgentReasoningResult"
            )
        payload = {
            "authorization_evidence_id": result.authorization_evidence_id,
            "authorization_outcome": result.authorization_outcome.value,
            "capability": (
                result.proposal.capability.value
                if result.proposal.capability is not None
                else None
            ),
            "contract_version": AGENTCORE_RUNTIME_INVOCATION_CONTRACT_VERSION,
            "decision": result.proposal.decision.value,
            "failure_category": (
                result.failure_category.value if result.failure_category is not None else None
            ),
            "invocation_evidence_id": result.invocation_evidence.evidence_id,
            "reasoning_result_id": result.result_id,
            "task_id": result.task.task_id,
        }
        digest = _canonical_sha256(payload)
        return cls(
            task_id=result.task.task_id,
            reasoning_result_id=result.result_id,
            authorization_outcome=result.authorization_outcome,
            decision=result.proposal.decision,
            capability=result.proposal.capability,
            authorization_evidence_id=result.authorization_evidence_id,
            failure_category=result.failure_category,
            invocation_evidence=result.invocation_evidence,
            projection_sha256=digest,
            projection_id=(
                f"{AGENTCORE_RUNTIME_INVOCATION_CONTRACT_VERSION}:projection:{digest}"
            ),
        )


__all__ = [
    "AGENTCORE_RUNTIME_INVOCATION_CONTRACT_VERSION",
    "MAX_AGENTCORE_RUNTIME_ADAPTIVE_FALLBACKS",
    "MAX_AGENTCORE_RUNTIME_ADAPTIVE_RETRIES",
    "MAX_AGENTCORE_RUNTIME_CAPABILITY_EXECUTIONS",
    "MAX_AGENTCORE_RUNTIME_MODEL_INVOCATIONS",
    "MAX_AGENTCORE_RUNTIME_REQUEST_UTF8_BYTES",
    "AgentCoreReasoningProjection",
    "AgentCoreRuntimeValidationError",
]
