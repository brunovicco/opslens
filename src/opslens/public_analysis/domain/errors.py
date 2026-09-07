"""Domain errors for the public analysis request boundary."""


class PublicAnalysisValidationError(ValueError):
    """Raised when a public analysis value violates the frozen v1 contract."""
