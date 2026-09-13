"""Provider-neutral port for one bounded multi-agent triage model invocation."""

from dataclasses import dataclass
from typing import Protocol

from opslens.agent_baseline.domain.models import SingleAgentTask
from opslens.multi_agent.domain.triage_reasoning import MultiAgentTriageInvocationEvidence


@dataclass(frozen=True, slots=True)
class MultiAgentTriageReasoningModelResponse:
    """Transient triage model text plus separately admitted invocation evidence."""

    output_text: str
    evidence: MultiAgentTriageInvocationEvidence

    def __post_init__(self) -> None:
        """Keep arbitrary model output transient until deterministic parsing."""
        if type(self.output_text) is not str:
            raise TypeError("output_text must be a string")
        if type(self.evidence) is not MultiAgentTriageInvocationEvidence:
            raise TypeError("evidence must be MultiAgentTriageInvocationEvidence")


class MultiAgentTriageReasoningModel(Protocol):
    """Generate one untrusted specialization proposal for an admitted source task."""

    def generate(self, task: SingleAgentTask) -> MultiAgentTriageReasoningModelResponse:
        """Return one transient triage response without granting handoff authority."""
        ...


__all__ = [
    "MultiAgentTriageReasoningModel",
    "MultiAgentTriageReasoningModelResponse",
]
