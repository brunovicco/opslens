"""Provider-neutral port for one bounded single-agent reasoning invocation."""

from dataclasses import dataclass
from typing import Protocol

from opslens.agent_baseline.domain.models import SingleAgentTask
from opslens.agent_baseline.domain.reasoning import AgentReasoningInvocationEvidence


@dataclass(frozen=True, slots=True)
class AgentReasoningModelResponse:
    """Transient model text plus separately admitted invocation evidence."""

    output_text: str
    evidence: AgentReasoningInvocationEvidence

    def __post_init__(self) -> None:
        """Keep arbitrary model output transient and bounded before deterministic parsing."""
        if type(self.output_text) is not str:
            raise TypeError("output_text must be a string")
        if type(self.evidence) is not AgentReasoningInvocationEvidence:
            raise TypeError("evidence must be AgentReasoningInvocationEvidence")


class AgentReasoningModel(Protocol):
    """Generate exactly one untrusted capability-selection decision for an admitted task."""

    def generate(self, task: SingleAgentTask) -> AgentReasoningModelResponse:
        """Return one transient model response without granting capability authority."""
        ...


__all__ = ["AgentReasoningModel", "AgentReasoningModelResponse"]
