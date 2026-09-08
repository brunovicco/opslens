"""Provider adapters for bounded OpsLens multi-agent reasoning."""

from opslens.multi_agent.adapters.bedrock_triage_reasoning import (
    BEDROCK_TRIAGE_REASONING_MAX_TOKENS,
    BEDROCK_TRIAGE_REASONING_MODEL_ID,
    BEDROCK_TRIAGE_REASONING_PROVIDER,
    BEDROCK_TRIAGE_REASONING_REGION,
    BEDROCK_TRIAGE_REASONING_TEMPERATURE,
    BedrockMultiAgentTriageModel,
    BedrockTriageConverseClient,
    BedrockTriageReasoningRuntimeError,
)

__all__ = [
    "BEDROCK_TRIAGE_REASONING_MAX_TOKENS",
    "BEDROCK_TRIAGE_REASONING_MODEL_ID",
    "BEDROCK_TRIAGE_REASONING_PROVIDER",
    "BEDROCK_TRIAGE_REASONING_REGION",
    "BEDROCK_TRIAGE_REASONING_TEMPERATURE",
    "BedrockMultiAgentTriageModel",
    "BedrockTriageConverseClient",
    "BedrockTriageReasoningRuntimeError",
]
