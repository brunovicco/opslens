"""Execute bounded hybrid synthesis for the representative non-public workload."""

from collections.abc import Callable
from dataclasses import dataclass

from opslens.hybrid_retrieval.adapters.bedrock_synthesis import (
    BedrockHybridSynthesisExecution,
)
from opslens.hybrid_retrieval.domain import HybridEvidenceEnvelope, HybridSynthesisRequest
from opslens.public_analysis.domain import ProviderResourceUsage

REPRESENTATIVE_SYNTHESIS_QUESTION = (
    "What should be prioritized and how should the highest-priority vulnerability be remediated?"
)

type RepresentativeHybridSynthesizer = Callable[
    [HybridSynthesisRequest], BedrockHybridSynthesisExecution
]


@dataclass(frozen=True, slots=True)
class RepresentativeModelReasoning:
    """One admitted hybrid synthesis execution plus measured provider counters."""

    request: HybridSynthesisRequest
    execution: BedrockHybridSynthesisExecution
    usage: ProviderResourceUsage

    def __post_init__(self) -> None:
        """Keep admitted model output and resource counters bound to the exact request."""
        if self.execution.result.request_sha256 != self.request.request_sha256:
            raise ValueError("model result must reference the exact representative request")
        evidence = self.execution.evidence
        if evidence.request_sha256 != self.request.request_sha256:
            raise ValueError("model invocation evidence must reference the exact request")
        expected_usage = ProviderResourceUsage(
            bedrock_model_call_count=1,
            bedrock_input_tokens=evidence.input_tokens,
            bedrock_output_tokens=evidence.output_tokens,
            bedrock_model_client_elapsed_ms=evidence.client_elapsed_ms,
            bedrock_model_latency_ms=evidence.bedrock_latency_ms,
            retry_count=evidence.retry_attempts,
        )
        if self.usage != expected_usage:
            raise ValueError("model provider usage must match exact invocation evidence")


def execute_representative_model_reasoning(
    *,
    envelope: HybridEvidenceEnvelope,
    synthesizer: RepresentativeHybridSynthesizer,
) -> RepresentativeModelReasoning:
    """Invoke exactly one injected bounded synthesizer over already-admitted evidence."""
    if type(envelope) is not HybridEvidenceEnvelope:
        raise TypeError("envelope must be HybridEvidenceEnvelope")
    request = HybridSynthesisRequest.create(
        question=REPRESENTATIVE_SYNTHESIS_QUESTION,
        envelope=envelope,
    )
    execution = synthesizer(request)
    if type(execution) is not BedrockHybridSynthesisExecution:
        raise TypeError("representative synthesizer must return BedrockHybridSynthesisExecution")
    evidence = execution.evidence
    usage = ProviderResourceUsage(
        bedrock_model_call_count=1,
        bedrock_input_tokens=evidence.input_tokens,
        bedrock_output_tokens=evidence.output_tokens,
        bedrock_model_client_elapsed_ms=evidence.client_elapsed_ms,
        bedrock_model_latency_ms=evidence.bedrock_latency_ms,
        retry_count=evidence.retry_attempts,
    )
    return RepresentativeModelReasoning(
        request=request,
        execution=execution,
        usage=usage,
    )


__all__ = [
    "REPRESENTATIVE_SYNTHESIS_QUESTION",
    "RepresentativeHybridSynthesizer",
    "RepresentativeModelReasoning",
    "execute_representative_model_reasoning",
]
