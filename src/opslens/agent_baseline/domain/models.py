"""Provider-neutral contracts for bounded single-agent capability authority."""

import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import cast

from opslens.agent_baseline.domain.errors import AgentAuthorityValidationError
from opslens.shared.evidence import canonical_json

SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION = "single-agent-authority:v1"
MAX_AGENT_TASK_UTF8_BYTES = 2_048
MAX_AGENT_ALLOWED_CAPABILITIES = 4
MAX_AGENT_PROPOSALS_PER_TASK = 1
MAX_AGENT_AUTHORIZATION_STEPS = 1
MAX_AGENT_CAPABILITY_EXECUTIONS = 0
MAX_AGENT_ADAPTIVE_RETRIES = 0


class AgentCapability(StrEnum):
    """Closed capability classes available to the Phase 11 single-agent baseline."""

    STRUCTURED_SECURITY_QUERY = "structured_security_query"
    KNOWLEDGE_GUIDANCE = "knowledge_guidance"
    HYBRID_SECURITY_ANSWER = "hybrid_security_answer"
    PUBLIC_REPOSITORY_ANALYSIS = "public_repository_analysis"


class AgentDecision(StrEnum):
    """Only decisions recognized at the Gate 11.1 proposal boundary."""

    ACT = "act"
    ABSTAIN = "abstain"


_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_TASK_ID_PATTERN = re.compile(
    rf"^{re.escape(SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION)}:task:[0-9a-f]{{64}}$",
    re.ASCII,
)
_PROPOSAL_ID_PATTERN = re.compile(
    rf"^{re.escape(SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION)}:proposal:[0-9a-f]{{64}}$",
    re.ASCII,
)
_ACTION_ID_PATTERN = re.compile(
    rf"^{re.escape(SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION)}:action:[0-9a-f]{{64}}$",
    re.ASCII,
)
_ABSTENTION_ID_PATTERN = re.compile(
    rf"^{re.escape(SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION)}:abstention:[0-9a-f]{{64}}$",
    re.ASCII,
)


def _canonical_json(value: object) -> bytes:
    """Serialize one deterministic single-agent identity payload."""
    return canonical_json(value)


def _canonical_sha256(value: object) -> str:
    """Hash one canonical JSON payload."""
    return sha256(_canonical_json(value)).hexdigest()


def _validate_digest(value: object, *, label: str, expected: str) -> str:
    """Validate one caller-visible SHA-256 field against deterministic semantics."""
    if (
        type(value) is not str
        or _SHA256_PATTERN.fullmatch(value) is None
        or value != expected
    ):
        raise AgentAuthorityValidationError(f"{label} must match canonical semantics")
    return value


def _validate_identifier(value: object, *, label: str, pattern: re.Pattern[str]) -> str:
    """Validate one bounded versioned content-addressed identifier."""
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise AgentAuthorityValidationError(f"{label} violates the authority identity contract")
    return value


def _normalize_task_text(value: object) -> str:
    """Validate bounded untrusted task text without treating it as executable authority."""
    if type(value) is not str:
        raise AgentAuthorityValidationError("task text must be a string")
    if not value.strip():
        raise AgentAuthorityValidationError("task text cannot be empty")
    if len(value.encode("utf-8")) > MAX_AGENT_TASK_UTF8_BYTES:
        raise AgentAuthorityValidationError("task text exceeds the UTF-8 byte limit")
    return value


def _normalize_capabilities(value: object) -> tuple[AgentCapability, ...]:
    """Validate and canonically order one explicit capability allowlist."""
    if type(value) is not tuple:
        raise AgentAuthorityValidationError("allowed capabilities must be a tuple")
    raw_values = cast(tuple[object, ...], value)
    if not raw_values:
        raise AgentAuthorityValidationError("allowed capabilities cannot be empty")
    if len(raw_values) > MAX_AGENT_ALLOWED_CAPABILITIES:
        raise AgentAuthorityValidationError("allowed capabilities exceed the v1 limit")
    if any(type(item) is not AgentCapability for item in raw_values):
        raise AgentAuthorityValidationError(
            "allowed capabilities must contain only AgentCapability values"
        )
    typed_values = cast(tuple[AgentCapability, ...], raw_values)
    if len(set(typed_values)) != len(typed_values):
        raise AgentAuthorityValidationError("allowed capabilities cannot contain duplicates")
    return tuple(sorted(typed_values, key=lambda item: item.value))


def _task_identity_payload(
    *,
    text: str,
    allowed_capabilities: tuple[AgentCapability, ...],
) -> dict[str, object]:
    """Return canonical semantics that own task identity."""
    return {
        "allowed_capabilities": [item.value for item in allowed_capabilities],
        "contract_version": SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION,
        "text": text,
    }


def _proposal_identity_payload(
    *,
    task_id: str,
    decision: AgentDecision,
    capability: AgentCapability | None,
) -> dict[str, object]:
    """Return canonical semantics that own proposal identity."""
    return {
        "capability": capability.value if capability is not None else None,
        "contract_version": SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION,
        "decision": decision.value,
        "task_id": task_id,
    }


def _action_identity_payload(
    *,
    task_id: str,
    proposal_id: str,
    capability: AgentCapability,
) -> dict[str, object]:
    """Return canonical semantics that own authorized-action identity."""
    return {
        "capability": capability.value,
        "contract_version": SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION,
        "proposal_id": proposal_id,
        "task_id": task_id,
    }


def _abstention_identity_payload(*, task_id: str, proposal_id: str) -> dict[str, object]:
    """Return canonical semantics that own an explicit abstention identity."""
    return {
        "contract_version": SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION,
        "decision": AgentDecision.ABSTAIN.value,
        "proposal_id": proposal_id,
        "task_id": task_id,
    }


@dataclass(frozen=True, slots=True)
class SingleAgentTask:
    """Content-addressed task plus the deterministic capability allowlist."""

    text: str
    allowed_capabilities: tuple[AgentCapability, ...]
    task_sha256: str
    task_id: str

    def __post_init__(self) -> None:
        """Reject forged task identities and unsupported capability surfaces."""
        normalized_text = _normalize_task_text(self.text)
        normalized_capabilities = _normalize_capabilities(self.allowed_capabilities)
        object.__setattr__(self, "text", normalized_text)
        object.__setattr__(self, "allowed_capabilities", normalized_capabilities)

        expected_sha256 = _canonical_sha256(
            _task_identity_payload(
                text=normalized_text,
                allowed_capabilities=normalized_capabilities,
            )
        )
        _validate_digest(self.task_sha256, label="task_sha256", expected=expected_sha256)
        expected_id = f"{SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION}:task:{expected_sha256}"
        if self.task_id != expected_id:
            raise AgentAuthorityValidationError(
                "task_id must match the content-addressed task identity"
            )


@dataclass(frozen=True, slots=True)
class AgentActionProposal:
    """Untrusted one-step agent proposal with no executable argument surface."""

    task_id: str
    decision: AgentDecision
    capability: AgentCapability | None
    proposal_sha256: str
    proposal_id: str

    def __post_init__(self) -> None:
        """Validate proposal shape without granting capability authority."""
        task_id = _validate_identifier(
            self.task_id,
            label="task_id",
            pattern=_TASK_ID_PATTERN,
        )
        if type(self.decision) is not AgentDecision:
            raise AgentAuthorityValidationError("decision must be AgentDecision")
        if self.capability is not None and type(self.capability) is not AgentCapability:
            raise AgentAuthorityValidationError(
                "capability must be AgentCapability or null"
            )
        if self.decision is AgentDecision.ACT and self.capability is None:
            raise AgentAuthorityValidationError("ACT proposals require one capability")
        if self.decision is AgentDecision.ABSTAIN and self.capability is not None:
            raise AgentAuthorityValidationError("ABSTAIN proposals cannot carry a capability")

        expected_sha256 = _canonical_sha256(
            _proposal_identity_payload(
                task_id=task_id,
                decision=self.decision,
                capability=self.capability,
            )
        )
        _validate_digest(
            self.proposal_sha256,
            label="proposal_sha256",
            expected=expected_sha256,
        )
        expected_id = (
            f"{SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION}:proposal:{expected_sha256}"
        )
        if self.proposal_id != expected_id:
            raise AgentAuthorityValidationError(
                "proposal_id must match the content-addressed proposal identity"
            )


@dataclass(frozen=True, slots=True)
class AuthorizedAgentAction:
    """Deterministically authorized capability selection, still not an execution result."""

    task_id: str
    proposal_id: str
    capability: AgentCapability
    action_sha256: str
    action_id: str

    def __post_init__(self) -> None:
        """Reject forged authorized-action identities."""
        task_id = _validate_identifier(
            self.task_id,
            label="task_id",
            pattern=_TASK_ID_PATTERN,
        )
        proposal_id = _validate_identifier(
            self.proposal_id,
            label="proposal_id",
            pattern=_PROPOSAL_ID_PATTERN,
        )
        if type(self.capability) is not AgentCapability:
            raise AgentAuthorityValidationError("capability must be AgentCapability")
        expected_sha256 = _canonical_sha256(
            _action_identity_payload(
                task_id=task_id,
                proposal_id=proposal_id,
                capability=self.capability,
            )
        )
        _validate_digest(
            self.action_sha256,
            label="action_sha256",
            expected=expected_sha256,
        )
        expected_id = f"{SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION}:action:{expected_sha256}"
        if self.action_id != expected_id:
            raise AgentAuthorityValidationError(
                "action_id must match the content-addressed action identity"
            )


@dataclass(frozen=True, slots=True)
class AgentAbstention:
    """Explicit content-addressed abstention with no capability authority."""

    task_id: str
    proposal_id: str
    abstention_sha256: str
    abstention_id: str

    def __post_init__(self) -> None:
        """Reject forged abstention identities."""
        task_id = _validate_identifier(
            self.task_id,
            label="task_id",
            pattern=_TASK_ID_PATTERN,
        )
        proposal_id = _validate_identifier(
            self.proposal_id,
            label="proposal_id",
            pattern=_PROPOSAL_ID_PATTERN,
        )
        expected_sha256 = _canonical_sha256(
            _abstention_identity_payload(task_id=task_id, proposal_id=proposal_id)
        )
        _validate_digest(
            self.abstention_sha256,
            label="abstention_sha256",
            expected=expected_sha256,
        )
        expected_id = (
            f"{SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION}:abstention:{expected_sha256}"
        )
        if self.abstention_id != expected_id:
            raise AgentAuthorityValidationError(
                "abstention_id must match the content-addressed abstention identity"
            )


def create_single_agent_task(
    *,
    text: str,
    allowed_capabilities: tuple[AgentCapability, ...],
) -> SingleAgentTask:
    """Create one deterministic task from code-owned capability authorization."""
    normalized_text = _normalize_task_text(text)
    normalized_capabilities = _normalize_capabilities(allowed_capabilities)
    digest = _canonical_sha256(
        _task_identity_payload(
            text=normalized_text,
            allowed_capabilities=normalized_capabilities,
        )
    )
    return SingleAgentTask(
        text=normalized_text,
        allowed_capabilities=normalized_capabilities,
        task_sha256=digest,
        task_id=f"{SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION}:task:{digest}",
    )


def create_agent_action_proposal(
    *,
    task_id: str,
    decision: AgentDecision,
    capability: AgentCapability | None,
) -> AgentActionProposal:
    """Create a structurally valid proposal without authorizing the selected capability."""
    normalized_task_id = _validate_identifier(
        task_id,
        label="task_id",
        pattern=_TASK_ID_PATTERN,
    )
    if type(decision) is not AgentDecision:
        raise AgentAuthorityValidationError("decision must be AgentDecision")
    if capability is not None and type(capability) is not AgentCapability:
        raise AgentAuthorityValidationError("capability must be AgentCapability or null")
    if decision is AgentDecision.ACT and capability is None:
        raise AgentAuthorityValidationError("ACT proposals require one capability")
    if decision is AgentDecision.ABSTAIN and capability is not None:
        raise AgentAuthorityValidationError("ABSTAIN proposals cannot carry a capability")

    digest = _canonical_sha256(
        _proposal_identity_payload(
            task_id=normalized_task_id,
            decision=decision,
            capability=capability,
        )
    )
    return AgentActionProposal(
        task_id=normalized_task_id,
        decision=decision,
        capability=capability,
        proposal_sha256=digest,
        proposal_id=f"{SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION}:proposal:{digest}",
    )


def create_authorized_agent_action(
    *,
    task_id: str,
    proposal_id: str,
    capability: AgentCapability,
) -> AuthorizedAgentAction:
    """Create a content-addressed action after deterministic authorization succeeds."""
    task_id = _validate_identifier(task_id, label="task_id", pattern=_TASK_ID_PATTERN)
    proposal_id = _validate_identifier(
        proposal_id,
        label="proposal_id",
        pattern=_PROPOSAL_ID_PATTERN,
    )
    if type(capability) is not AgentCapability:
        raise AgentAuthorityValidationError("capability must be AgentCapability")
    digest = _canonical_sha256(
        _action_identity_payload(
            task_id=task_id,
            proposal_id=proposal_id,
            capability=capability,
        )
    )
    return AuthorizedAgentAction(
        task_id=task_id,
        proposal_id=proposal_id,
        capability=capability,
        action_sha256=digest,
        action_id=f"{SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION}:action:{digest}",
    )


def create_agent_abstention(*, task_id: str, proposal_id: str) -> AgentAbstention:
    """Create a content-addressed explicit abstention with no execution authority."""
    task_id = _validate_identifier(task_id, label="task_id", pattern=_TASK_ID_PATTERN)
    proposal_id = _validate_identifier(
        proposal_id,
        label="proposal_id",
        pattern=_PROPOSAL_ID_PATTERN,
    )
    digest = _canonical_sha256(
        _abstention_identity_payload(task_id=task_id, proposal_id=proposal_id)
    )
    return AgentAbstention(
        task_id=task_id,
        proposal_id=proposal_id,
        abstention_sha256=digest,
        abstention_id=f"{SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION}:abstention:{digest}",
    )


__all__ = [
    "MAX_AGENT_ADAPTIVE_RETRIES",
    "MAX_AGENT_ALLOWED_CAPABILITIES",
    "MAX_AGENT_AUTHORIZATION_STEPS",
    "MAX_AGENT_CAPABILITY_EXECUTIONS",
    "MAX_AGENT_PROPOSALS_PER_TASK",
    "MAX_AGENT_TASK_UTF8_BYTES",
    "SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION",
    "AgentAbstention",
    "AgentActionProposal",
    "AgentCapability",
    "AgentDecision",
    "AuthorizedAgentAction",
    "SingleAgentTask",
    "create_agent_abstention",
    "create_agent_action_proposal",
    "create_authorized_agent_action",
    "create_single_agent_task",
]
