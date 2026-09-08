"""Application service for bounded MCP protocol-reference admission."""

from __future__ import annotations

from dataclasses import dataclass

from opslens.agent_baseline.domain import AgentCapabilityInvocation
from opslens.mcp_boundary.application.admission import admit_mcp_tool_call
from opslens.mcp_boundary.domain import (
    MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION,
    McpBoundaryValidationError,
    McpInvocationReference,
    McpToolCallAdmission,
    McpToolName,
)
from opslens.mcp_boundary.ports import McpInvocationResolver


@dataclass(frozen=True, slots=True)
class McpAdmissionProjection:
    """Content-minimized protocol projection of deterministic Gate 13.1 admission."""

    contract_version: str
    tool_name: str
    capability: str
    action_id: str
    invocation_id: str
    invocation_sha256: str
    admission_id: str
    admission_sha256: str

    @classmethod
    def from_admission(cls, admission: McpToolCallAdmission) -> McpAdmissionProjection:
        """Project only deterministic admission identity fields onto the protocol."""
        if type(admission) is not McpToolCallAdmission:
            raise McpBoundaryValidationError(
                "MCP protocol projection requires deterministic admission evidence"
            )
        return cls(
            contract_version=MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION,
            tool_name=admission.tool_name.value,
            capability=admission.capability.value,
            action_id=admission.action_id,
            invocation_id=admission.invocation_id,
            invocation_sha256=admission.invocation_sha256,
            admission_id=admission.admission_id,
            admission_sha256=admission.admission_sha256,
        )


def _validate_resolved_invocation(
    *,
    reference: McpInvocationReference,
    invocation: AgentCapabilityInvocation,
) -> AgentCapabilityInvocation:
    """Require a resolver hit to preserve the exact requested invocation identity."""
    if invocation.invocation_id != reference.invocation_id:
        raise McpBoundaryValidationError("MCP resolver returned a different invocation_id")
    if invocation.invocation_sha256 != reference.invocation_sha256:
        raise McpBoundaryValidationError("MCP resolver returned a different invocation_sha256")
    return invocation


def resolve_mcp_invocation_reference(
    *,
    invocation_id: str,
    invocation_sha256: str,
    resolver: McpInvocationResolver,
) -> AgentCapabilityInvocation:
    """Resolve one exact content-addressed MCP reference to its existing typed invocation."""
    reference = McpInvocationReference(
        invocation_id=invocation_id,
        invocation_sha256=invocation_sha256,
    )
    resolved = resolver.resolve(reference.invocation_id, reference.invocation_sha256)
    return _validate_resolved_invocation(reference=reference, invocation=resolved)


def admit_mcp_invocation_reference(
    *,
    tool_name: McpToolName,
    invocation_id: str,
    invocation_sha256: str,
    resolver: McpInvocationResolver,
) -> McpAdmissionProjection:
    """Resolve and admit one existing typed invocation, stopping before capability execution."""
    if type(tool_name) is not McpToolName:
        raise McpBoundaryValidationError("tool_name must be McpToolName")

    invocation = resolve_mcp_invocation_reference(
        invocation_id=invocation_id,
        invocation_sha256=invocation_sha256,
        resolver=resolver,
    )
    admission = admit_mcp_tool_call(tool_name=tool_name, invocation=invocation)
    return McpAdmissionProjection.from_admission(admission)


__all__ = [
    "McpAdmissionProjection",
    "admit_mcp_invocation_reference",
    "resolve_mcp_invocation_reference",
]
