"""Domain contracts for the bounded single-agent baseline."""

from opslens.agent_baseline.domain.errors import (
    AgentAuthorityValidationError,
    AgentCapabilityAuthorizationError,
)
from opslens.agent_baseline.domain.models import (
    MAX_AGENT_ADAPTIVE_RETRIES,
    MAX_AGENT_ALLOWED_CAPABILITIES,
    MAX_AGENT_AUTHORIZATION_STEPS,
    MAX_AGENT_CAPABILITY_EXECUTIONS,
    MAX_AGENT_PROPOSALS_PER_TASK,
    MAX_AGENT_TASK_UTF8_BYTES,
    SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION,
    AgentAbstention,
    AgentActionProposal,
    AgentCapability,
    AgentDecision,
    AuthorizedAgentAction,
    SingleAgentTask,
    create_agent_abstention,
    create_agent_action_proposal,
    create_authorized_agent_action,
    create_single_agent_task,
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
    "AgentAuthorityValidationError",
    "AgentCapability",
    "AgentCapabilityAuthorizationError",
    "AgentDecision",
    "AuthorizedAgentAction",
    "SingleAgentTask",
    "create_agent_abstention",
    "create_agent_action_proposal",
    "create_authorized_agent_action",
    "create_single_agent_task",
]
