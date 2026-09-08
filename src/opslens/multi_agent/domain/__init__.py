"""Domain contracts for bounded OpsLens multi-agent coordination."""

from opslens.multi_agent.domain.errors import (
    MultiAgentHandoffAuthorizationError,
    MultiAgentHandoffValidationError,
)
from opslens.multi_agent.domain.handoff import (
    MAX_MULTI_AGENT_HANDOFFS_PER_TASK,
    MAX_SPECIALIST_CAPABILITIES,
    MULTI_AGENT_HANDOFF_CONTRACT_VERSION,
    AgentSpecialization,
    AuthorizedMultiAgentHandoff,
    MultiAgentHandoffAbstention,
    MultiAgentHandoffDecision,
    MultiAgentHandoffProposal,
    SpecialistAgentTask,
    TriageAgentTask,
    capabilities_for_specialization,
    create_authorized_multi_agent_handoff,
    create_multi_agent_handoff_abstention,
    create_multi_agent_handoff_proposal,
    create_triage_agent_task,
)

__all__ = [
    "MAX_MULTI_AGENT_HANDOFFS_PER_TASK",
    "MAX_SPECIALIST_CAPABILITIES",
    "MULTI_AGENT_HANDOFF_CONTRACT_VERSION",
    "AgentSpecialization",
    "AuthorizedMultiAgentHandoff",
    "MultiAgentHandoffAbstention",
    "MultiAgentHandoffAuthorizationError",
    "MultiAgentHandoffDecision",
    "MultiAgentHandoffProposal",
    "MultiAgentHandoffValidationError",
    "SpecialistAgentTask",
    "TriageAgentTask",
    "capabilities_for_specialization",
    "create_authorized_multi_agent_handoff",
    "create_multi_agent_handoff_abstention",
    "create_multi_agent_handoff_proposal",
    "create_triage_agent_task",
]
