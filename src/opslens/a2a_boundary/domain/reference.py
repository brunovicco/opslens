"""Content-addressed references for the bounded A2A interoperability experiment."""

import re
from dataclasses import dataclass
from hashlib import sha256

from opslens.a2a_boundary.domain.errors import A2ABoundaryValidationError
from opslens.multi_agent.domain.handoff import SpecialistAgentTask
from opslens.shared.evidence import canonical_json

A2A_REFERENCE_INTEROPERABILITY_CONTRACT_VERSION = "a2a-reference-interoperability:v1"

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_HANDOFF_ID_PATTERN = re.compile(
    r"^multi-agent-handoff:v1:handoff:[0-9a-f]{64}$",
    re.ASCII,
)
_SPECIALIST_TASK_ID_PATTERN = re.compile(
    r"^single-agent-authority:v1:task:[0-9a-f]{64}$",
    re.ASCII,
)
_REFERENCE_ID_PATTERN = re.compile(
    rf"^{re.escape(A2A_REFERENCE_INTEROPERABILITY_CONTRACT_VERSION)}:reference:[0-9a-f]{{64}}$",
    re.ASCII,
)


def _canonical_json(value: object) -> bytes:
    """Serialize one bounded reference identity payload deterministically."""
    return canonical_json(value)


def _reference_payload(*, handoff_id: str, specialist_task_id: str) -> dict[str, str]:
    """Return the only semantics that own one protocol reference identity."""
    return {
        "contract_version": A2A_REFERENCE_INTEROPERABILITY_CONTRACT_VERSION,
        "handoff_id": handoff_id,
        "specialist_task_id": specialist_task_id,
    }


def _reference_digest(*, handoff_id: str, specialist_task_id: str) -> str:
    """Hash one canonical A2A reference payload."""
    return sha256(
        _canonical_json(
            _reference_payload(
                handoff_id=handoff_id,
                specialist_task_id=specialist_task_id,
            )
        )
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class A2AReference:
    """Reference to one already-admitted specialist task, with no execution authority."""

    handoff_id: str
    specialist_task_id: str
    reference_sha256: str
    reference_id: str

    def __post_init__(self) -> None:
        """Reject malformed or contradictory reference identities."""
        if type(self.handoff_id) is not str or _HANDOFF_ID_PATTERN.fullmatch(
            self.handoff_id
        ) is None:
            raise A2ABoundaryValidationError(
                "A2A handoff_id violates the retained handoff contract"
            )
        if (
            type(self.specialist_task_id) is not str
            or _SPECIALIST_TASK_ID_PATTERN.fullmatch(self.specialist_task_id) is None
        ):
            raise A2ABoundaryValidationError(
                "A2A specialist_task_id violates the retained task contract"
            )
        expected_digest = _reference_digest(
            handoff_id=self.handoff_id,
            specialist_task_id=self.specialist_task_id,
        )
        if (
            type(self.reference_sha256) is not str
            or _SHA256_PATTERN.fullmatch(self.reference_sha256) is None
            or self.reference_sha256 != expected_digest
        ):
            raise A2ABoundaryValidationError(
                "A2A reference_sha256 must match canonical reference semantics"
            )
        expected_id = (
            f"{A2A_REFERENCE_INTEROPERABILITY_CONTRACT_VERSION}:reference:{expected_digest}"
        )
        if (
            type(self.reference_id) is not str
            or _REFERENCE_ID_PATTERN.fullmatch(self.reference_id) is None
            or self.reference_id != expected_id
        ):
            raise A2ABoundaryValidationError(
                "A2A reference_id must match the content-addressed reference identity"
            )


def create_a2a_reference(*, specialist_task: SpecialistAgentTask) -> A2AReference:
    """Create a protocol reference only from one admitted Gate 12 specialist task."""
    if type(specialist_task) is not SpecialistAgentTask:
        raise A2ABoundaryValidationError(
            "specialist_task must be one admitted SpecialistAgentTask"
        )

    handoff_id = specialist_task.handoff.handoff_id
    specialist_task_id = specialist_task.task.task_id
    digest = _reference_digest(
        handoff_id=handoff_id,
        specialist_task_id=specialist_task_id,
    )
    return A2AReference(
        handoff_id=handoff_id,
        specialist_task_id=specialist_task_id,
        reference_sha256=digest,
        reference_id=(
            f"{A2A_REFERENCE_INTEROPERABILITY_CONTRACT_VERSION}:reference:{digest}"
        ),
    )


__all__ = [
    "A2A_REFERENCE_INTEROPERABILITY_CONTRACT_VERSION",
    "A2AReference",
    "create_a2a_reference",
]
