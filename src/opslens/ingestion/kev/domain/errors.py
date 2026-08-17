"""Domain errors for CISA KEV catalog ingestion."""


class InvalidKevCatalogError(ValueError):
    """Raised when a CISA KEV artifact violates the Bronze source contract."""
