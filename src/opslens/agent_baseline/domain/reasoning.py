"""Provider-neutral evidence contracts for bounded single-agent model reasoning."""

import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256

from opslens.agent_baseline.domain.errors import AgentReasoningValidationError
from opslens.agent_baseline.domain.models import (
    SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION,
    AgentActionProposal,
    AgentCapability,
    AgentDecision,
    SingleAgentTask,
)
from opslens.shared.evidence import canonical_json

SINGLE_AGENT_REASONING_CONTRACT_VERSION = "single-agent-reasoning:v1"
MAX_AGENT_REASONING_INVOCATIONS_PER_TASK = 1
MAX_AGENT_REASONING_ADAPTIVE_RETRIES = 0
MAX_AGENT_REASONING_OUTPUT_UTF8_BYTES = 512

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_TASK_ID_PATTERN = re.compile(
    rf"^{re.escape(SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION)}:task:[0-9a-f]{{64}}$",
    re.ASCII,
)
_EVIDENCE_ID_PATTERN = re.compile(
    rf"^{re.escape(SINGLE_AGENT_REASONING_CONTRACT_VERSION)}:invocation:[0-9a-f]{{64}}$",
    re.ASCII,
)
_RESULT_ID_PATTERN = re.compile(
    rf"^{re.escape(SINGLE_AGENT_REASONING_CONTRACT_VERSION)}:result:[0-9a-f]{{64}}$",
    re.ASCII,
)


class AgentReasoningAuthorizationOutcome(StrEnum):
    """Deterministic authorization outcomes after one model proposal."""

    AUTHORIZED = "authorized"
    ABSTAINED = "abstained"
    REJECTED = "rejected"


class AgentReasoningFailureCategory(StrEnum):
    """Content-free failures admitted into reasoning result evidence."""

    CAPABILITY_AUTHORIZATION = "capability_authorization"


def _canonical_json(value: object) -> bytes:
    """Serialize one deterministic reasoning identity payload."""
    return canonical_json(value)


def _canonical_sha256(value: object) -> str:
    """Hash one canonical reasoning identity payload."""
    return sha256(_canonical_json(value)).hexdigest()


def _validate_normalized_string(value: object, *, label: str) -> str:
    """Require one normalized non-empty metadata string."""
    if type(value) is not str or not value.strip() or value.strip() != value:
        raise AgentReasoningValidationError(f"{label} must be a normalized non-empty string")
    return value


def _validate_non_negative_int(value: object, *, label: str) -> int:
    """Require one non-negative integer runtime observation."""
    if type(value) is not int or value < 0:
        raise AgentReasoningValidationError(f"{label} must be a non-negative integer")
    return value


@dataclass(frozen=True, slots=True)
class AgentReasoningInvocationEvidence:
    """Content-minimized metadata for exactly one reasoning-provider invocation."""

    task_id: str
    provider: str
    model_id: str
    region: str
    request_id: str
    stop_reason: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cache_read_input_tokens: int
    cache_write_input_tokens: int
    provider_latency_ms: int
    client_elapsed_ms: int
    retry_attempts: int
    evidence_sha256: str
    evidence_id: str

    def __post_init__(self) -> None:
        """Reject malformed or forged runtime evidence."""
        if type(self.task_id) is not str or _TASK_ID_PATTERN.fullmatch(self.task_id) is None:
            raise AgentReasoningValidationError("task_id violates the reasoning binding contract")

        for field_name, value in (
            ("provider", self.provider),
            ("model_id", self.model_id),
            ("region", self.region),
            ("request_id", self.request_id),
            ("stop_reason", self.stop_reason),
        ):
            _validate_normalized_string(value, label=field_name)

        for field_name, value in (
            ("input_tokens", self.input_tokens),
            ("output_tokens", self.output_tokens),
            ("total_tokens", self.total_tokens),
            ("cache_read_input_tokens", self.cache_read_input_tokens),
            ("cache_write_input_tokens", self.cache_write_input_tokens),
            ("provider_latency_ms", self.provider_latency_ms),
            ("client_elapsed_ms", self.client_elapsed_ms),
            ("retry_attempts", self.retry_attempts),
        ):
            _validate_non_negative_int(value, label=field_name)

        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise AgentReasoningValidationError(
                "total_tokens must equal input_tokens plus output_tokens"
            )

        expected = _canonical_sha256(self._identity_payload())
        if (
            type(self.evidence_sha256) is not str
            or _SHA256_PATTERN.fullmatch(self.evidence_sha256) is None
            or self.evidence_sha256 != expected
        ):
            raise AgentReasoningValidationError(
                "evidence_sha256 must match canonical reasoning invocation semantics"
            )
        expected_id = f"{SINGLE_AGENT_REASONING_CONTRACT_VERSION}:invocation:{expected}"
        if (
            self.evidence_id != expected_id
            or _EVIDENCE_ID_PATTERN.fullmatch(self.evidence_id) is None
        ):
            raise AgentReasoningValidationError(
                "evidence_id must match content-addressed invocation semantics"
            )

    def _identity_payload(self) -> dict[str, object]:
        """Return metadata-only semantics used for invocation identity."""
        return {
            "cache_read_input_tokens": self.cache_read_input_tokens,
            "cache_write_input_tokens": self.cache_write_input_tokens,
            "client_elapsed_ms": self.client_elapsed_ms,
            "contract_version": SINGLE_AGENT_REASONING_CONTRACT_VERSION,
            "input_tokens": self.input_tokens,
            "model_id": self.model_id,
            "output_tokens": self.output_tokens,
            "provider": self.provider,
            "provider_latency_ms": self.provider_latency_ms,
            "region": self.region,
            "request_id": self.request_id,
            "retry_attempts": self.retry_attempts,
            "stop_reason": self.stop_reason,
            "task_id": self.task_id,
            "total_tokens": self.total_tokens,
        }

    @classmethod
    def create(
        cls,
        *,
        task_id: str,
        provider: str,
        model_id: str,
        region: str,
        request_id: str,
        stop_reason: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        cache_read_input_tokens: int,
        cache_write_input_tokens: int,
        provider_latency_ms: int,
        client_elapsed_ms: int,
        retry_attempts: int,
    ) -> "AgentReasoningInvocationEvidence":
        """Create immutable metadata-only evidence for one provider invocation."""
        provisional = cls.__new__(cls)
        object.__setattr__(provisional, "task_id", task_id)
        object.__setattr__(provisional, "provider", provider)
        object.__setattr__(provisional, "model_id", model_id)
        object.__setattr__(provisional, "region", region)
        object.__setattr__(provisional, "request_id", request_id)
        object.__setattr__(provisional, "stop_reason", stop_reason)
        object.__setattr__(provisional, "input_tokens", input_tokens)
        object.__setattr__(provisional, "output_tokens", output_tokens)
        object.__setattr__(provisional, "total_tokens", total_tokens)
        object.__setattr__(provisional, "cache_read_input_tokens", cache_read_input_tokens)
        object.__setattr__(provisional, "cache_write_input_tokens", cache_write_input_tokens)
        object.__setattr__(provisional, "provider_latency_ms", provider_latency_ms)
        object.__setattr__(provisional, "client_elapsed_ms", client_elapsed_ms)
        object.__setattr__(provisional, "retry_attempts", retry_attempts)
        digest = _canonical_sha256(provisional._identity_payload())
        return cls(
            task_id=task_id,
            provider=provider,
            model_id=model_id,
            region=region,
            request_id=request_id,
            stop_reason=stop_reason,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cache_read_input_tokens=cache_read_input_tokens,
            cache_write_input_tokens=cache_write_input_tokens,
            provider_latency_ms=provider_latency_ms,
            client_elapsed_ms=client_elapsed_ms,
            retry_attempts=retry_attempts,
            evidence_sha256=digest,
            evidence_id=f"{SINGLE_AGENT_REASONING_CONTRACT_VERSION}:invocation:{digest}",
        )


@dataclass(frozen=True, slots=True)
class AgentReasoningResult:
    """Bind one admitted model proposal to deterministic authorization evidence."""

    task: SingleAgentTask
    proposal: AgentActionProposal
    invocation_evidence: AgentReasoningInvocationEvidence
    authorization_outcome: AgentReasoningAuthorizationOutcome
    authorization_evidence_id: str | None
    failure_category: AgentReasoningFailureCategory | None
    invocation_count: int
    result_sha256: str
    result_id: str

    def __post_init__(self) -> None:
        """Recompute result semantics and reject cross-task or forged evidence."""
        if type(self.task) is not SingleAgentTask:
            raise AgentReasoningValidationError("task must be one SingleAgentTask")
        if type(self.proposal) is not AgentActionProposal:
            raise AgentReasoningValidationError("proposal must be one AgentActionProposal")
        if type(self.invocation_evidence) is not AgentReasoningInvocationEvidence:
            raise AgentReasoningValidationError(
                "invocation_evidence must be AgentReasoningInvocationEvidence"
            )
        if self.proposal.task_id != self.task.task_id:
            raise AgentReasoningValidationError("proposal is not bound to the reasoning task")
        if self.invocation_evidence.task_id != self.task.task_id:
            raise AgentReasoningValidationError(
                "invocation evidence is not bound to the reasoning task"
            )
        if type(self.authorization_outcome) is not AgentReasoningAuthorizationOutcome:
            raise AgentReasoningValidationError(
                "authorization_outcome must be AgentReasoningAuthorizationOutcome"
            )
        if (
            self.failure_category is not None
            and type(self.failure_category) is not AgentReasoningFailureCategory
        ):
            raise AgentReasoningValidationError(
                "failure_category must be AgentReasoningFailureCategory or null"
            )
        if (
            self.authorization_evidence_id is not None
            and type(self.authorization_evidence_id) is not str
        ):
            raise AgentReasoningValidationError(
                "authorization_evidence_id must be a string or null"
            )
        if type(self.invocation_count) is not int or not (
            0 <= self.invocation_count <= MAX_AGENT_REASONING_INVOCATIONS_PER_TASK
        ):
            raise AgentReasoningValidationError("invocation_count exceeds the reasoning bound")

        if self.authorization_outcome is AgentReasoningAuthorizationOutcome.REJECTED:
            if self.authorization_evidence_id is not None:
                raise AgentReasoningValidationError(
                    "rejected reasoning cannot carry authorization evidence"
                )
            if self.failure_category is not AgentReasoningFailureCategory.CAPABILITY_AUTHORIZATION:
                raise AgentReasoningValidationError(
                    "rejected reasoning requires capability_authorization failure"
                )
        else:
            if self.authorization_evidence_id is None:
                raise AgentReasoningValidationError(
                    "authorized or abstained reasoning requires authorization evidence"
                )
            if self.failure_category is not None:
                raise AgentReasoningValidationError(
                    "authorized or abstained reasoning cannot carry a failure category"
                )

        if self.invocation_count != 1:
            raise AgentReasoningValidationError(
                "an admitted reasoning result must represent exactly one model invocation"
            )

        expected = _canonical_sha256(self._identity_payload())
        if (
            type(self.result_sha256) is not str
            or _SHA256_PATTERN.fullmatch(self.result_sha256) is None
            or self.result_sha256 != expected
        ):
            raise AgentReasoningValidationError(
                "result_sha256 must match canonical reasoning result semantics"
            )
        expected_id = f"{SINGLE_AGENT_REASONING_CONTRACT_VERSION}:result:{expected}"
        if self.result_id != expected_id or _RESULT_ID_PATTERN.fullmatch(self.result_id) is None:
            raise AgentReasoningValidationError(
                "result_id must match content-addressed reasoning result semantics"
            )

    def _identity_payload(self) -> dict[str, object]:
        """Project the bounded result identity without raw model content."""
        return {
            "authorization_evidence_id": self.authorization_evidence_id,
            "authorization_outcome": self.authorization_outcome.value,
            "contract_version": SINGLE_AGENT_REASONING_CONTRACT_VERSION,
            "failure_category": (
                self.failure_category.value if self.failure_category is not None else None
            ),
            "invocation_count": self.invocation_count,
            "invocation_evidence_id": self.invocation_evidence.evidence_id,
            "proposal_id": self.proposal.proposal_id,
            "task_id": self.task.task_id,
        }

    @classmethod
    def create(
        cls,
        *,
        task: SingleAgentTask,
        proposal: AgentActionProposal,
        invocation_evidence: AgentReasoningInvocationEvidence,
        authorization_outcome: AgentReasoningAuthorizationOutcome,
        authorization_evidence_id: str | None,
        failure_category: AgentReasoningFailureCategory | None,
    ) -> "AgentReasoningResult":
        """Create one content-addressed result after deterministic authorization."""
        payload = {
            "authorization_evidence_id": authorization_evidence_id,
            "authorization_outcome": authorization_outcome.value,
            "contract_version": SINGLE_AGENT_REASONING_CONTRACT_VERSION,
            "failure_category": failure_category.value if failure_category is not None else None,
            "invocation_count": 1,
            "invocation_evidence_id": invocation_evidence.evidence_id,
            "proposal_id": proposal.proposal_id,
            "task_id": task.task_id,
        }
        digest = _canonical_sha256(payload)
        return cls(
            task=task,
            proposal=proposal,
            invocation_evidence=invocation_evidence,
            authorization_outcome=authorization_outcome,
            authorization_evidence_id=authorization_evidence_id,
            failure_category=failure_category,
            invocation_count=1,
            result_sha256=digest,
            result_id=f"{SINGLE_AGENT_REASONING_CONTRACT_VERSION}:result:{digest}",
        )


__all__ = [
    "MAX_AGENT_REASONING_ADAPTIVE_RETRIES",
    "MAX_AGENT_REASONING_INVOCATIONS_PER_TASK",
    "MAX_AGENT_REASONING_OUTPUT_UTF8_BYTES",
    "SINGLE_AGENT_REASONING_CONTRACT_VERSION",
    "AgentCapability",
    "AgentDecision",
    "AgentReasoningAuthorizationOutcome",
    "AgentReasoningFailureCategory",
    "AgentReasoningInvocationEvidence",
    "AgentReasoningResult",
]
