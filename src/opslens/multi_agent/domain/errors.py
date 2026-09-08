"""Stable failures for bounded multi-agent authority and evaluation."""


class MultiAgentHandoffValidationError(ValueError):
    """Raised when a multi-agent handoff contract is structurally invalid."""


class MultiAgentHandoffAuthorizationError(ValueError):
    """Raised when a proposed handoff has no code-authorized target scope."""


class MultiAgentComparisonValidationError(ValueError):
    """Raised when a comparative multi-agent evaluation contract is invalid."""


class MultiAgentTriageReasoningValidationError(ValueError):
    """Raised when bounded triage reasoning evidence or output is invalid."""


class MultiAgentRealComparisonValidationError(ValueError):
    """Raised when the first real two-model comparison contract is invalid."""


__all__ = [
    "MultiAgentComparisonValidationError",
    "MultiAgentHandoffAuthorizationError",
    "MultiAgentHandoffValidationError",
    "MultiAgentRealComparisonValidationError",
    "MultiAgentTriageReasoningValidationError",
]
