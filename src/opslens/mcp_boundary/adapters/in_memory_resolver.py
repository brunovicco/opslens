"""In-memory resolver for offline MCP interoperability validation."""

from __future__ import annotations

from collections.abc import Iterable

from opslens.agent_baseline.domain import AgentCapabilityInvocation, capability_for_invocation
from opslens.mcp_boundary.domain import McpBoundaryValidationError, McpInvocationReference


class InMemoryMcpInvocationResolver:
    """Resolve only invocations explicitly admitted into an in-memory test registry."""

    def __init__(self, invocations: Iterable[AgentCapabilityInvocation]) -> None:
        """Build a closed registry and reject ambiguous invocation identities."""
        registry: dict[str, AgentCapabilityInvocation] = {}
        for invocation in invocations:
            capability_for_invocation(invocation)
            if invocation.invocation_id in registry:
                raise McpBoundaryValidationError("duplicate MCP invocation_id in resolver registry")
            registry[invocation.invocation_id] = invocation
        self._registry = registry

    def resolve(
        self,
        invocation_id: str,
        invocation_sha256: str,
    ) -> AgentCapabilityInvocation:
        """Resolve one exact content-addressed invocation reference or fail closed."""
        reference = McpInvocationReference(
            invocation_id=invocation_id,
            invocation_sha256=invocation_sha256,
        )
        invocation = self._registry.get(reference.invocation_id)
        if invocation is None:
            raise McpBoundaryValidationError("MCP invocation reference was not found")
        if invocation.invocation_sha256 != reference.invocation_sha256:
            raise McpBoundaryValidationError("MCP invocation reference identity mismatch")
        capability_for_invocation(invocation)
        return invocation


__all__ = ["InMemoryMcpInvocationResolver"]
