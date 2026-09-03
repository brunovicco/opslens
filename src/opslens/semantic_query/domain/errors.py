"""Fail-closed errors for the OpsLens semantic-query boundary."""


class SemanticQueryError(ValueError):
    """Base class for deterministic semantic-query failures."""


class SemanticQueryValidationError(SemanticQueryError):
    """Raised when a semantic-query value violates the frozen contract."""


class UnsupportedSemanticQueryError(SemanticQueryError):
    """Raised when a valid-looking query requests unsupported semantics."""
