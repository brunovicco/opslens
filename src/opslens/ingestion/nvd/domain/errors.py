"""Domain errors for NVD ingestion."""


class InvalidNvdFeedMetaError(ValueError):
    """Raised when an NVD feed META artifact violates the Bronze contract."""


class InvalidNvdFeedArtifactError(ValueError):
    """Raised when an NVD gzip feed violates the Bronze integrity contract."""
