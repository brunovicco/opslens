"""Provider-neutral resolver contract for existing typed MCP invocation references."""

from __future__ import annotations

from typing import Protocol

from opslens.agent_baseline.domain import AgentCapabilityInvocation


class McpInvocationResolver(Protocol):
    """Resolve one exact existing typed invocation without authoring new semantics."""

    def resolve(
        self,
        invocation_id: str,
        invocation_sha256: str,
    ) -> AgentCapabilityInvocation:
        """Resolve one invocation by exact content-addressed identity."""
        ...


__all__ = ["McpInvocationResolver"]
