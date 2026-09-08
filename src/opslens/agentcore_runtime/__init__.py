"""Bounded Amazon Bedrock AgentCore Runtime boundary for OpsLens."""

from opslens.agentcore_runtime.application import (
    admit_agentcore_runtime_request,
    handle_agentcore_runtime_invocation,
)
from opslens.agentcore_runtime.domain import (
    AGENTCORE_RUNTIME_INVOCATION_CONTRACT_VERSION,
    MAX_AGENTCORE_RUNTIME_ADAPTIVE_FALLBACKS,
    MAX_AGENTCORE_RUNTIME_ADAPTIVE_RETRIES,
    MAX_AGENTCORE_RUNTIME_CAPABILITY_EXECUTIONS,
    MAX_AGENTCORE_RUNTIME_MODEL_INVOCATIONS,
    MAX_AGENTCORE_RUNTIME_REQUEST_UTF8_BYTES,
    AgentCoreReasoningProjection,
    AgentCoreRuntimeValidationError,
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
    "admit_agentcore_runtime_request",
    "handle_agentcore_runtime_invocation",
]
