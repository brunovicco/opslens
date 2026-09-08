"""Stable fail-closed errors for the bounded MCP authority boundary."""


class McpBoundaryValidationError(ValueError):
    """Raised when MCP identity or admission semantics violate the frozen contract."""


__all__ = ["McpBoundaryValidationError"]
