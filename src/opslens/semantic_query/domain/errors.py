"""Fail-closed errors for the OpsLens semantic-query boundary."""


class SemanticQueryError(ValueError):
    """Base class for deterministic semantic-query failures."""


class SemanticQueryValidationError(SemanticQueryError):
    """Raised when a semantic-query value violates the frozen contract."""


class UnsupportedSemanticQueryError(SemanticQueryError):
    """Raised when a valid-looking query requests unsupported semantics."""


class SemanticQueryExecutionError(SemanticQueryError):
    """Raised when a compiled semantic query cannot execute safely."""


class SemanticQueryTimeoutError(SemanticQueryExecutionError):
    """Raised when Athena does not reach a terminal state inside the execution bound."""


class SemanticQueryResultError(SemanticQueryExecutionError):
    """Raised when Athena returns malformed or unexpectedly unbounded evidence."""
