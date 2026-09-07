"""Errors for bounded single-agent authority, execution, evaluation, and reasoning."""


class AgentAuthorityValidationError(ValueError):
    """Raised when one single-agent authority object violates its contract."""


class AgentCapabilityAuthorizationError(RuntimeError):
    """Raised when a valid proposal requests capability authority it does not own."""


class AgentCapabilityExecutionValidationError(ValueError):
    """Raised when typed capability invocation or execution evidence is invalid."""


class AgentEvaluationValidationError(ValueError):
    """Raised when offline single-agent evaluation evidence violates its contract."""


class AgentReasoningValidationError(ValueError):
    """Raised when bounded single-agent reasoning data violates its contract."""
