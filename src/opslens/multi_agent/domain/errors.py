"""Stable failures for bounded multi-agent handoff admission."""


class MultiAgentHandoffValidationError(ValueError):
    """Raised when a multi-agent handoff contract is structurally invalid."""


class MultiAgentHandoffAuthorizationError(ValueError):
    """Raised when a proposed handoff has no code-authorized target scope."""


__all__ = [
    "MultiAgentHandoffAuthorizationError",
    "MultiAgentHandoffValidationError",
]
