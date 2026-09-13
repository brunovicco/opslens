"""Provider-neutral deterministic contracts for one bounded multi-agent handoff."""

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import cast

from opslens.agent_baseline.domain.models import (
    SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION,
    AgentCapability,
    SingleAgentTask,
)
from opslens.multi_agent.domain.errors import MultiAgentHandoffValidationError

MULTI_AGENT_HANDOFF_CONTRACT_VERSION = "multi-agent-handoff:v1"
MAX_MULTI_AGENT_HANDOFFS_PER_TASK = 1
MAX_SPECIALIST_CAPABILITIES = 2


class MultiAgentHandoffDecision(StrEnum):
    """Closed decisions available at the triage handoff proposal boundary."""

    HANDOFF = "handoff"
    ABSTAIN = "abstain"


class AgentSpecialization(StrEnum):
    """Closed Phase 12 specialization classes with code-owned capability scopes."""

    EVIDENCE_ANALYSIS = "evidence_analysis"
    GUIDANCE_SYNTHESIS = "guidance_synthesis"


_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_TASK_ID_PATTERN = re.compile(
    rf"^{re.escape(SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION)}:task:[0-9a-f]{{64}}$",
    re.ASCII,
)
_PROPOSAL_ID_PATTERN = re.compile(
    rf"^{re.escape(MULTI_AGENT_HANDOFF_CONTRACT_VERSION)}:proposal:[0-9a-f]{{64}}$",
    re.ASCII,
)
_HANDOFF_ID_PATTERN = re.compile(
    rf"^{re.escape(MULTI_AGENT_HANDOFF_CONTRACT_VERSION)}:handoff:[0-9a-f]{{64}}$",
    re.ASCII,
)
_ABSTENTION_ID_PATTERN = re.compile(
    rf"^{re.escape(MULTI_AGENT_HANDOFF_CONTRACT_VERSION)}:abstention:[0-9a-f]{{64}}$",
    re.ASCII,
)


def _canonical_json(value: object) -> bytes:
    """Serialize one bounded handoff identity payload deterministically."""
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_sha256(value: object) -> str:
    """Hash one canonical handoff identity payload."""
    return sha256(_canonical_json(value)).hexdigest()


def _validate_digest(value: object, *, label: str, expected: str) -> str:
    """Validate one SHA-256 field against deterministic handoff semantics."""
    if (
        type(value) is not str
        or _SHA256_PATTERN.fullmatch(value) is None
        or value != expected
    ):
        raise MultiAgentHandoffValidationError(f"{label} must match canonical semantics")
    return value


def _validate_identifier(
    value: object,
    *,
    label: str,
    pattern: re.Pattern[str],
) -> str:
    """Validate one versioned content-addressed handoff identifier."""
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise MultiAgentHandoffValidationError(f"{label} violates the handoff identity contract")
    return value


def capabilities_for_specialization(
    specialization: AgentSpecialization,
) -> tuple[AgentCapability, ...]:
    """Return the immutable code-owned capability scope for one specialization."""
    if type(specialization) is not AgentSpecialization:
        raise MultiAgentHandoffValidationError(
            "specialization must be one AgentSpecialization"
        )
    if specialization is AgentSpecialization.EVIDENCE_ANALYSIS:
        return (
            AgentCapability.PUBLIC_REPOSITORY_ANALYSIS,
            AgentCapability.STRUCTURED_SECURITY_QUERY,
        )
    if specialization is AgentSpecialization.GUIDANCE_SYNTHESIS:
        return (
            AgentCapability.HYBRID_SECURITY_ANSWER,
            AgentCapability.KNOWLEDGE_GUIDANCE,
        )
    raise MultiAgentHandoffValidationError("specialization is not supported")


def _normalize_target_capabilities(value: object) -> tuple[AgentCapability, ...]:
    """Validate one narrowed specialist capability scope."""
    if type(value) is not tuple:
        raise MultiAgentHandoffValidationError("target capabilities must be a tuple")
    raw_values = cast(tuple[object, ...], value)
    if not raw_values:
        raise MultiAgentHandoffValidationError("target capabilities cannot be empty")
    if len(raw_values) > MAX_SPECIALIST_CAPABILITIES:
        raise MultiAgentHandoffValidationError(
            "target capabilities exceed the specialist capability limit"
        )
    if any(type(item) is not AgentCapability for item in raw_values):
        raise MultiAgentHandoffValidationError(
            "target capabilities must contain only AgentCapability values"
        )
    typed_values = cast(tuple[AgentCapability, ...], raw_values)
    if len(set(typed_values)) != len(typed_values):
        raise MultiAgentHandoffValidationError("target capabilities cannot contain duplicates")
    expected = tuple(sorted(typed_values, key=lambda item: item.value))
    if typed_values != expected:
        raise MultiAgentHandoffValidationError("target capabilities must be canonically ordered")
    return typed_values


def _proposal_identity_payload(
    *,
    source_task_id: str,
    decision: MultiAgentHandoffDecision,
    target_specialization: AgentSpecialization | None,
) -> dict[str, object]:
    """Return canonical semantics that own one handoff proposal identity."""
    return {
        "contract_version": MULTI_AGENT_HANDOFF_CONTRACT_VERSION,
        "decision": decision.value,
        "source_task_id": source_task_id,
        "target_specialization": (
            target_specialization.value if target_specialization is not None else None
        ),
    }


def _handoff_identity_payload(
    *,
    source_task_id: str,
    proposal_id: str,
    target_specialization: AgentSpecialization,
    target_task_id: str,
    target_capabilities: tuple[AgentCapability, ...],
) -> dict[str, object]:
    """Return canonical semantics that own one authorized handoff identity."""
    return {
        "contract_version": MULTI_AGENT_HANDOFF_CONTRACT_VERSION,
        "proposal_id": proposal_id,
        "source_task_id": source_task_id,
        "target_capabilities": [item.value for item in target_capabilities],
        "target_specialization": target_specialization.value,
        "target_task_id": target_task_id,
    }


def _abstention_identity_payload(*, source_task_id: str, proposal_id: str) -> dict[str, object]:
    """Return canonical semantics that own one handoff abstention identity."""
    return {
        "contract_version": MULTI_AGENT_HANDOFF_CONTRACT_VERSION,
        "decision": MultiAgentHandoffDecision.ABSTAIN.value,
        "proposal_id": proposal_id,
        "source_task_id": source_task_id,
    }


@dataclass(frozen=True, slots=True)
class TriageAgentTask:
    """Typed source task accepted by the one-way Phase 12 handoff boundary."""

    task: SingleAgentTask

    def __post_init__(self) -> None:
        """Reject non-admitted source task values."""
        if type(self.task) is not SingleAgentTask:
            raise MultiAgentHandoffValidationError(
                "triage task must contain one admitted SingleAgentTask"
            )


@dataclass(frozen=True, slots=True)
class MultiAgentHandoffProposal:
    """Untrusted triage proposal with no capability or executable argument authority."""

    source_task_id: str
    decision: MultiAgentHandoffDecision
    target_specialization: AgentSpecialization | None
    proposal_sha256: str
    proposal_id: str

    def __post_init__(self) -> None:
        """Validate proposal shape and content-addressed identity."""
        source_task_id = _validate_identifier(
            self.source_task_id,
            label="source_task_id",
            pattern=_TASK_ID_PATTERN,
        )
        if type(self.decision) is not MultiAgentHandoffDecision:
            raise MultiAgentHandoffValidationError(
                "decision must be MultiAgentHandoffDecision"
            )
        if self.target_specialization is not None and type(
            self.target_specialization
        ) is not AgentSpecialization:
            raise MultiAgentHandoffValidationError(
                "target specialization must be AgentSpecialization or null"
            )
        if (
            self.decision is MultiAgentHandoffDecision.HANDOFF
            and self.target_specialization is None
        ):
            raise MultiAgentHandoffValidationError(
                "HANDOFF proposals require one target specialization"
            )
        if (
            self.decision is MultiAgentHandoffDecision.ABSTAIN
            and self.target_specialization is not None
        ):
            raise MultiAgentHandoffValidationError(
                "ABSTAIN proposals cannot carry a target specialization"
            )

        expected_sha256 = _canonical_sha256(
            _proposal_identity_payload(
                source_task_id=source_task_id,
                decision=self.decision,
                target_specialization=self.target_specialization,
            )
        )
        _validate_digest(
            self.proposal_sha256,
            label="proposal_sha256",
            expected=expected_sha256,
        )
        expected_id = (
            f"{MULTI_AGENT_HANDOFF_CONTRACT_VERSION}:proposal:{expected_sha256}"
        )
        if self.proposal_id != expected_id:
            raise MultiAgentHandoffValidationError(
                "proposal_id must match the content-addressed proposal identity"
            )


@dataclass(frozen=True, slots=True)
class AuthorizedMultiAgentHandoff:
    """Deterministically admitted specialization handoff, still not capability authority."""

    source_task_id: str
    proposal_id: str
    target_specialization: AgentSpecialization
    target_task_id: str
    target_capabilities: tuple[AgentCapability, ...]
    handoff_sha256: str
    handoff_id: str

    def __post_init__(self) -> None:
        """Validate the bounded target scope and content-addressed handoff identity."""
        source_task_id = _validate_identifier(
            self.source_task_id,
            label="source_task_id",
            pattern=_TASK_ID_PATTERN,
        )
        proposal_id = _validate_identifier(
            self.proposal_id,
            label="proposal_id",
            pattern=_PROPOSAL_ID_PATTERN,
        )
        if type(self.target_specialization) is not AgentSpecialization:
            raise MultiAgentHandoffValidationError(
                "target specialization must be AgentSpecialization"
            )
        target_task_id = _validate_identifier(
            self.target_task_id,
            label="target_task_id",
            pattern=_TASK_ID_PATTERN,
        )
        target_capabilities = _normalize_target_capabilities(self.target_capabilities)
        specialization_scope = capabilities_for_specialization(self.target_specialization)
        if not set(target_capabilities).issubset(specialization_scope):
            raise MultiAgentHandoffValidationError(
                "target capabilities exceed the code-owned specialization scope"
            )

        expected_sha256 = _canonical_sha256(
            _handoff_identity_payload(
                source_task_id=source_task_id,
                proposal_id=proposal_id,
                target_specialization=self.target_specialization,
                target_task_id=target_task_id,
                target_capabilities=target_capabilities,
            )
        )
        _validate_digest(
            self.handoff_sha256,
            label="handoff_sha256",
            expected=expected_sha256,
        )
        expected_id = f"{MULTI_AGENT_HANDOFF_CONTRACT_VERSION}:handoff:{expected_sha256}"
        if self.handoff_id != expected_id:
            raise MultiAgentHandoffValidationError(
                "handoff_id must match the content-addressed handoff identity"
            )


@dataclass(frozen=True, slots=True)
class MultiAgentHandoffAbstention:
    """Content-addressed triage abstention that creates no specialist task."""

    source_task_id: str
    proposal_id: str
    abstention_sha256: str
    abstention_id: str

    def __post_init__(self) -> None:
        """Validate one explicit handoff abstention identity."""
        source_task_id = _validate_identifier(
            self.source_task_id,
            label="source_task_id",
            pattern=_TASK_ID_PATTERN,
        )
        proposal_id = _validate_identifier(
            self.proposal_id,
            label="proposal_id",
            pattern=_PROPOSAL_ID_PATTERN,
        )
        expected_sha256 = _canonical_sha256(
            _abstention_identity_payload(
                source_task_id=source_task_id,
                proposal_id=proposal_id,
            )
        )
        _validate_digest(
            self.abstention_sha256,
            label="abstention_sha256",
            expected=expected_sha256,
        )
        expected_id = (
            f"{MULTI_AGENT_HANDOFF_CONTRACT_VERSION}:abstention:{expected_sha256}"
        )
        if self.abstention_id != expected_id:
            raise MultiAgentHandoffValidationError(
                "abstention_id must match the content-addressed abstention identity"
            )


@dataclass(frozen=True, slots=True)
class SpecialistAgentTask:
    """One narrowed specialist task produced only after deterministic handoff admission."""

    task: SingleAgentTask
    specialization: AgentSpecialization
    handoff: AuthorizedMultiAgentHandoff

    def __post_init__(self) -> None:
        """Bind the specialist task exactly to its admitted handoff evidence."""
        if type(self.task) is not SingleAgentTask:
            raise MultiAgentHandoffValidationError(
                "specialist task must contain one admitted SingleAgentTask"
            )
        if type(self.specialization) is not AgentSpecialization:
            raise MultiAgentHandoffValidationError(
                "specialization must be AgentSpecialization"
            )
        if type(self.handoff) is not AuthorizedMultiAgentHandoff:
            raise MultiAgentHandoffValidationError(
                "specialist task must contain AuthorizedMultiAgentHandoff evidence"
            )
        if self.handoff.target_task_id != self.task.task_id:
            raise MultiAgentHandoffValidationError(
                "specialist task identity must match the admitted handoff"
            )
        if self.handoff.target_capabilities != self.task.allowed_capabilities:
            raise MultiAgentHandoffValidationError(
                "specialist capabilities must match the admitted handoff"
            )
        if self.handoff.target_specialization is not self.specialization:
            raise MultiAgentHandoffValidationError(
                "specialist specialization must match the admitted handoff"
            )


def create_triage_agent_task(*, task: SingleAgentTask) -> TriageAgentTask:
    """Create the only source task type accepted by the v1 handoff boundary."""
    if type(task) is not SingleAgentTask:
        raise MultiAgentHandoffValidationError(
            "task must be one admitted SingleAgentTask"
        )
    return TriageAgentTask(task=task)


def create_multi_agent_handoff_proposal(
    *,
    source_task_id: str,
    decision: MultiAgentHandoffDecision,
    target_specialization: AgentSpecialization | None,
) -> MultiAgentHandoffProposal:
    """Create one structurally valid untrusted handoff proposal."""
    source_task_id = _validate_identifier(
        source_task_id,
        label="source_task_id",
        pattern=_TASK_ID_PATTERN,
    )
    if type(decision) is not MultiAgentHandoffDecision:
        raise MultiAgentHandoffValidationError(
            "decision must be MultiAgentHandoffDecision"
        )
    if target_specialization is not None and type(
        target_specialization
    ) is not AgentSpecialization:
        raise MultiAgentHandoffValidationError(
            "target specialization must be AgentSpecialization or null"
        )
    if decision is MultiAgentHandoffDecision.HANDOFF and target_specialization is None:
        raise MultiAgentHandoffValidationError(
            "HANDOFF proposals require one target specialization"
        )
    if decision is MultiAgentHandoffDecision.ABSTAIN and target_specialization is not None:
        raise MultiAgentHandoffValidationError(
            "ABSTAIN proposals cannot carry a target specialization"
        )

    digest = _canonical_sha256(
        _proposal_identity_payload(
            source_task_id=source_task_id,
            decision=decision,
            target_specialization=target_specialization,
        )
    )
    return MultiAgentHandoffProposal(
        source_task_id=source_task_id,
        decision=decision,
        target_specialization=target_specialization,
        proposal_sha256=digest,
        proposal_id=f"{MULTI_AGENT_HANDOFF_CONTRACT_VERSION}:proposal:{digest}",
    )


def create_authorized_multi_agent_handoff(
    *,
    source_task: SingleAgentTask,
    proposal: MultiAgentHandoffProposal,
    target_task: SingleAgentTask,
) -> AuthorizedMultiAgentHandoff:
    """Create admitted handoff evidence after deterministic scope narrowing."""
    if type(source_task) is not SingleAgentTask:
        raise MultiAgentHandoffValidationError(
            "source task must be one admitted SingleAgentTask"
        )
    if type(proposal) is not MultiAgentHandoffProposal:
        raise MultiAgentHandoffValidationError(
            "proposal must be one MultiAgentHandoffProposal"
        )
    if type(target_task) is not SingleAgentTask:
        raise MultiAgentHandoffValidationError(
            "target task must be one admitted SingleAgentTask"
        )
    if proposal.source_task_id != source_task.task_id:
        raise MultiAgentHandoffValidationError(
            "proposal source task identity does not match the admitted source task"
        )
    if proposal.decision is not MultiAgentHandoffDecision.HANDOFF:
        raise MultiAgentHandoffValidationError(
            "authorized handoff requires a HANDOFF proposal"
        )
    specialization = proposal.target_specialization
    if specialization is None:
        raise MultiAgentHandoffValidationError(
            "authorized handoff requires one target specialization"
        )
    expected_capabilities = tuple(
        capability
        for capability in source_task.allowed_capabilities
        if capability in capabilities_for_specialization(specialization)
    )
    if not expected_capabilities:
        raise MultiAgentHandoffValidationError(
            "authorized handoff target capabilities cannot be empty"
        )
    if target_task.text != source_task.text:
        raise MultiAgentHandoffValidationError(
            "target specialist task must preserve the bounded source task text"
        )
    if target_task.allowed_capabilities != expected_capabilities:
        raise MultiAgentHandoffValidationError(
            "target specialist task must use the deterministic narrowed capability scope"
        )

    digest = _canonical_sha256(
        _handoff_identity_payload(
            source_task_id=source_task.task_id,
            proposal_id=proposal.proposal_id,
            target_specialization=specialization,
            target_task_id=target_task.task_id,
            target_capabilities=target_task.allowed_capabilities,
        )
    )
    return AuthorizedMultiAgentHandoff(
        source_task_id=source_task.task_id,
        proposal_id=proposal.proposal_id,
        target_specialization=specialization,
        target_task_id=target_task.task_id,
        target_capabilities=target_task.allowed_capabilities,
        handoff_sha256=digest,
        handoff_id=f"{MULTI_AGENT_HANDOFF_CONTRACT_VERSION}:handoff:{digest}",
    )


def create_multi_agent_handoff_abstention(
    *,
    source_task: SingleAgentTask,
    proposal: MultiAgentHandoffProposal,
) -> MultiAgentHandoffAbstention:
    """Create content-addressed evidence for an explicit triage abstention."""
    if type(source_task) is not SingleAgentTask:
        raise MultiAgentHandoffValidationError(
            "source task must be one admitted SingleAgentTask"
        )
    if type(proposal) is not MultiAgentHandoffProposal:
        raise MultiAgentHandoffValidationError(
            "proposal must be one MultiAgentHandoffProposal"
        )
    if proposal.source_task_id != source_task.task_id:
        raise MultiAgentHandoffValidationError(
            "proposal source task identity does not match the admitted source task"
        )
    if proposal.decision is not MultiAgentHandoffDecision.ABSTAIN:
        raise MultiAgentHandoffValidationError(
            "handoff abstention requires an ABSTAIN proposal"
        )

    digest = _canonical_sha256(
        _abstention_identity_payload(
            source_task_id=source_task.task_id,
            proposal_id=proposal.proposal_id,
        )
    )
    return MultiAgentHandoffAbstention(
        source_task_id=source_task.task_id,
        proposal_id=proposal.proposal_id,
        abstention_sha256=digest,
        abstention_id=f"{MULTI_AGENT_HANDOFF_CONTRACT_VERSION}:abstention:{digest}",
    )


__all__ = [
    "MAX_MULTI_AGENT_HANDOFFS_PER_TASK",
    "MAX_SPECIALIST_CAPABILITIES",
    "MULTI_AGENT_HANDOFF_CONTRACT_VERSION",
    "AgentSpecialization",
    "AuthorizedMultiAgentHandoff",
    "MultiAgentHandoffAbstention",
    "MultiAgentHandoffDecision",
    "MultiAgentHandoffProposal",
    "SpecialistAgentTask",
    "TriageAgentTask",
    "capabilities_for_specialization",
    "create_authorized_multi_agent_handoff",
    "create_multi_agent_handoff_abstention",
    "create_multi_agent_handoff_proposal",
    "create_triage_agent_task",
]
