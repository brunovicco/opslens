"""Errors for the bounded single-agent authority, execution, and evaluation contracts."""


class AgentAuthorityValidationError(ValueError):
    """Raised when one single-agent authority object violates its contract."""


class AgentCapabilityAuthorizationError(RuntimeError):
    """Raised when a valid proposal requests capability authority it does not own."""


class AgentCapabilityExecutionValidationError(ValueError):
    """Raised when typed capability invocation or execution evidence is invalid."""


class AgentEvaluationValidationError(ValueError):
    """Raised when offline single-agent evaluation evidence violates its contract."""
