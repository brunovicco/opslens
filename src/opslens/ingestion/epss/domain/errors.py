"""Domain exceptions for EPSS snapshot processing."""


class InvalidEpssSnapshotError(ValueError):
    """Raised when an EPSS snapshot violates the expected source contract."""
