"""Errors for the bounded A2A interoperability boundary."""


class A2ABoundaryError(Exception):
    """Base error for bounded A2A interoperability failures."""


class A2ABoundaryValidationError(A2ABoundaryError):
    """Raised when A2A protocol or reference data violates the frozen contract."""


class A2AReferenceNotFoundError(A2ABoundaryError):
    """Raised when a content-addressed A2A reference is not registered."""


class A2AReplayError(A2ABoundaryError):
    """Raised when a request/message identity is replayed ambiguously."""


__all__ = [
    "A2ABoundaryError",
    "A2ABoundaryValidationError",
    "A2AReferenceNotFoundError",
    "A2AReplayError",
]
