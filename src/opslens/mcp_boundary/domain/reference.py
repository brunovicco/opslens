"""Validated invocation references admitted from the MCP protocol boundary."""

from __future__ import annotations

import re
from dataclasses import dataclass

from opslens.mcp_boundary.domain.errors import McpBoundaryValidationError

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_INVOCATION_ID_PATTERN = re.compile(
    r"^single-agent-execution:v1:invocation:[0-9a-f]{64}$",
    re.ASCII,
)


@dataclass(frozen=True, slots=True)
class McpInvocationReference:
    """Content-minimized reference to one existing typed capability invocation."""

    invocation_id: str
    invocation_sha256: str

    def __post_init__(self) -> None:
        """Reject malformed or internally contradictory invocation references."""
        if type(self.invocation_id) is not str or _INVOCATION_ID_PATTERN.fullmatch(
            self.invocation_id
        ) is None:
            raise McpBoundaryValidationError("MCP invocation_id violates the invocation contract")
        if type(self.invocation_sha256) is not str or _SHA256_PATTERN.fullmatch(
            self.invocation_sha256
        ) is None:
            raise McpBoundaryValidationError("MCP invocation_sha256 must be lowercase SHA-256")
        if not self.invocation_id.endswith(self.invocation_sha256):
            raise McpBoundaryValidationError(
                "MCP invocation reference id and digest must identify the same invocation"
            )


__all__ = ["McpInvocationReference"]
