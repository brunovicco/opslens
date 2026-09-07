"""Errors for the bounded single-agent authority and execution contracts."""


class AgentAuthorityValidationError(ValueError):
    """Raised when one single-agent authority object violates its contract."""


class AgentCapabilityAuthorizationError(RuntimeError):
    """Raised when a valid proposal requests capability authority it does not own."""


class AgentCapabilityExecutionValidationError(ValueError):
    """Raised when typed capability invocation or execution evidence is invalid."""
