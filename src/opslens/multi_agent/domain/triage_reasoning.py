"""Provider-neutral evidence contracts for bounded multi-agent triage reasoning."""

import re
from dataclasses import dataclass
from hashlib import sha256

from opslens.agent_baseline.domain.models import (
    SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION,
    SingleAgentTask,
)
from opslens.multi_agent.domain.errors import MultiAgentTriageReasoningValidationError
from opslens.multi_agent.domain.handoff import MultiAgentHandoffProposal
from opslens.shared.evidence import canonical_json

MULTI_AGENT_TRIAGE_REASONING_CONTRACT_VERSION = "multi-agent-triage-reasoning:v1"
MAX_MULTI_AGENT_TRIAGE_INVOCATIONS_PER_TASK = 1
MAX_MULTI_AGENT_TRIAGE_ADAPTIVE_RETRIES = 0
MAX_MULTI_AGENT_TRIAGE_OUTPUT_UTF8_BYTES = 512

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_TASK_ID_PATTERN = re.compile(
    rf"^{re.escape(SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION)}:task:[0-9a-f]{{64}}$",
    re.ASCII,
)
_INVOCATION_ID_PATTERN = re.compile(
    rf"^{re.escape(MULTI_AGENT_TRIAGE_REASONING_CONTRACT_VERSION)}:invocation:[0-9a-f]{{64}}$",
    re.ASCII,
)
_RESULT_ID_PATTERN = re.compile(
    rf"^{re.escape(MULTI_AGENT_TRIAGE_REASONING_CONTRACT_VERSION)}:result:[0-9a-f]{{64}}$",
    re.ASCII,
)


def _canonical_json(value: object) -> bytes:
    """Serialize one triage evidence payload deterministically."""
    return canonical_json(value)


def _canonical_sha256(value: object) -> str:
    """Hash one canonical triage evidence payload."""
    return sha256(_canonical_json(value)).hexdigest()


def _normalized_string(value: object, *, label: str) -> str:
    """Require one normalized non-empty metadata string."""
    if type(value) is not str or not value.strip() or value.strip() != value:
        raise MultiAgentTriageReasoningValidationError(
            f"{label} must be a normalized non-empty string"
        )
    return value


def _non_negative_int(value: object, *, label: str) -> int:
    """Require one non-negative integer runtime observation."""
    if type(value) is not int or value < 0:
        raise MultiAgentTriageReasoningValidationError(
            f"{label} must be a non-negative integer"
        )
    return value


def _validate_digest(value: object, *, label: str, expected: str) -> None:
    """Require one exact lowercase content digest."""
    if (
        type(value) is not str
        or _SHA256_PATTERN.fullmatch(value) is None
        or value != expected
    ):
        raise MultiAgentTriageReasoningValidationError(
            f"{label} must match canonical triage semantics"
        )


@dataclass(frozen=True, slots=True)
class MultiAgentTriageInvocationEvidence:
    """Content-minimized evidence for exactly one triage model invocation."""

    source_task_id: str
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
        """Reject malformed, cross-task, or forged triage invocation evidence."""
        if (
            type(self.source_task_id) is not str
            or _TASK_ID_PATTERN.fullmatch(self.source_task_id) is None
        ):
            raise MultiAgentTriageReasoningValidationError(
                "source_task_id violates the triage task binding contract"
            )
        for label, value in (
            ("provider", self.provider),
            ("model_id", self.model_id),
            ("region", self.region),
            ("request_id", self.request_id),
            ("stop_reason", self.stop_reason),
        ):
            _normalized_string(value, label=label)
        for label, value in (
            ("input_tokens", self.input_tokens),
            ("output_tokens", self.output_tokens),
            ("total_tokens", self.total_tokens),
            ("cache_read_input_tokens", self.cache_read_input_tokens),
            ("cache_write_input_tokens", self.cache_write_input_tokens),
            ("provider_latency_ms", self.provider_latency_ms),
            ("client_elapsed_ms", self.client_elapsed_ms),
            ("retry_attempts", self.retry_attempts),
        ):
            _non_negative_int(value, label=label)
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise MultiAgentTriageReasoningValidationError(
                "total_tokens must equal input_tokens plus output_tokens"
            )
        expected = _canonical_sha256(self._identity_payload())
        _validate_digest(
            self.evidence_sha256,
            label="evidence_sha256",
            expected=expected,
        )
        expected_id = (
            f"{MULTI_AGENT_TRIAGE_REASONING_CONTRACT_VERSION}:invocation:{expected}"
        )
        if (
            self.evidence_id != expected_id
            or _INVOCATION_ID_PATTERN.fullmatch(self.evidence_id) is None
        ):
            raise MultiAgentTriageReasoningValidationError(
                "evidence_id must match content-addressed triage invocation semantics"
            )

    def _identity_payload(self) -> dict[str, object]:
        """Project metadata-only semantics used for triage invocation identity."""
        return {
            "cache_read_input_tokens": self.cache_read_input_tokens,
            "cache_write_input_tokens": self.cache_write_input_tokens,
            "client_elapsed_ms": self.client_elapsed_ms,
            "contract_version": MULTI_AGENT_TRIAGE_REASONING_CONTRACT_VERSION,
            "input_tokens": self.input_tokens,
            "model_id": self.model_id,
            "output_tokens": self.output_tokens,
            "provider": self.provider,
            "provider_latency_ms": self.provider_latency_ms,
            "region": self.region,
            "request_id": self.request_id,
            "retry_attempts": self.retry_attempts,
            "source_task_id": self.source_task_id,
            "stop_reason": self.stop_reason,
            "total_tokens": self.total_tokens,
        }

    @classmethod
    def create(
        cls,
        *,
        source_task_id: str,
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
    ) -> "MultiAgentTriageInvocationEvidence":
        """Create immutable metadata-only triage invocation evidence."""
        payload: dict[str, object] = {
            "cache_read_input_tokens": cache_read_input_tokens,
            "cache_write_input_tokens": cache_write_input_tokens,
            "client_elapsed_ms": client_elapsed_ms,
            "contract_version": MULTI_AGENT_TRIAGE_REASONING_CONTRACT_VERSION,
            "input_tokens": input_tokens,
            "model_id": model_id,
            "output_tokens": output_tokens,
            "provider": provider,
            "provider_latency_ms": provider_latency_ms,
            "region": region,
            "request_id": request_id,
            "retry_attempts": retry_attempts,
            "source_task_id": source_task_id,
            "stop_reason": stop_reason,
            "total_tokens": total_tokens,
        }
        digest = _canonical_sha256(payload)
        return cls(
            source_task_id=source_task_id,
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
            evidence_id=(
                f"{MULTI_AGENT_TRIAGE_REASONING_CONTRACT_VERSION}:invocation:{digest}"
            ),
        )


@dataclass(frozen=True, slots=True)
class MultiAgentTriageReasoningResult:
    """Bind one triage proposal to exact provider evidence without admitting a handoff."""

    source_task: SingleAgentTask
    proposal: MultiAgentHandoffProposal
    invocation_evidence: MultiAgentTriageInvocationEvidence
    invocation_count: int
    result_sha256: str
    result_id: str

    def __post_init__(self) -> None:
        """Reject cross-task, over-bound, or forged triage reasoning results."""
        if type(self.source_task) is not SingleAgentTask:
            raise MultiAgentTriageReasoningValidationError(
                "source_task must be one admitted SingleAgentTask"
            )
        if type(self.proposal) is not MultiAgentHandoffProposal:
            raise MultiAgentTriageReasoningValidationError(
                "proposal must be one MultiAgentHandoffProposal"
            )
        if type(self.invocation_evidence) is not MultiAgentTriageInvocationEvidence:
            raise MultiAgentTriageReasoningValidationError(
                "invocation_evidence must be MultiAgentTriageInvocationEvidence"
            )
        if self.proposal.source_task_id != self.source_task.task_id:
            raise MultiAgentTriageReasoningValidationError(
                "triage proposal is not bound to the source task"
            )
        if self.invocation_evidence.source_task_id != self.source_task.task_id:
            raise MultiAgentTriageReasoningValidationError(
                "triage invocation evidence is not bound to the source task"
            )
        if self.invocation_count != MAX_MULTI_AGENT_TRIAGE_INVOCATIONS_PER_TASK:
            raise MultiAgentTriageReasoningValidationError(
                "admitted triage result must represent exactly one model invocation"
            )
        expected = _canonical_sha256(self._identity_payload())
        _validate_digest(self.result_sha256, label="result_sha256", expected=expected)
        expected_id = f"{MULTI_AGENT_TRIAGE_REASONING_CONTRACT_VERSION}:result:{expected}"
        if self.result_id != expected_id or _RESULT_ID_PATTERN.fullmatch(self.result_id) is None:
            raise MultiAgentTriageReasoningValidationError(
                "result_id must match content-addressed triage reasoning semantics"
            )

    def _identity_payload(self) -> dict[str, object]:
        """Project the triage result identity without raw model content."""
        return {
            "contract_version": MULTI_AGENT_TRIAGE_REASONING_CONTRACT_VERSION,
            "invocation_count": self.invocation_count,
            "invocation_evidence_id": self.invocation_evidence.evidence_id,
            "proposal_id": self.proposal.proposal_id,
            "source_task_id": self.source_task.task_id,
        }

    @classmethod
    def create(
        cls,
        *,
        source_task: SingleAgentTask,
        proposal: MultiAgentHandoffProposal,
        invocation_evidence: MultiAgentTriageInvocationEvidence,
    ) -> "MultiAgentTriageReasoningResult":
        """Create a content-addressed triage result after deterministic parsing."""
        payload: dict[str, object] = {
            "contract_version": MULTI_AGENT_TRIAGE_REASONING_CONTRACT_VERSION,
            "invocation_count": MAX_MULTI_AGENT_TRIAGE_INVOCATIONS_PER_TASK,
            "invocation_evidence_id": invocation_evidence.evidence_id,
            "proposal_id": proposal.proposal_id,
            "source_task_id": source_task.task_id,
        }
        digest = _canonical_sha256(payload)
        return cls(
            source_task=source_task,
            proposal=proposal,
            invocation_evidence=invocation_evidence,
            invocation_count=MAX_MULTI_AGENT_TRIAGE_INVOCATIONS_PER_TASK,
            result_sha256=digest,
            result_id=f"{MULTI_AGENT_TRIAGE_REASONING_CONTRACT_VERSION}:result:{digest}",
        )


__all__ = [
    "MAX_MULTI_AGENT_TRIAGE_ADAPTIVE_RETRIES",
    "MAX_MULTI_AGENT_TRIAGE_INVOCATIONS_PER_TASK",
    "MAX_MULTI_AGENT_TRIAGE_OUTPUT_UTF8_BYTES",
    "MULTI_AGENT_TRIAGE_REASONING_CONTRACT_VERSION",
    "MultiAgentTriageInvocationEvidence",
    "MultiAgentTriageReasoningResult",
]
