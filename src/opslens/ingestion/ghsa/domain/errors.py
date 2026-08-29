"""Domain errors for deterministic GHSA Bronze ingestion."""


class GhsaIngestionError(ValueError):
    """Base class for deterministic GHSA ingestion contract failures."""


class InvalidGhsaSyncWindowError(GhsaIngestionError):
    """Raised when a logical GHSA synchronization window is invalid."""


class InvalidGhsaRequestUrlError(GhsaIngestionError):
    """Raised when a GHSA request or pagination URL violates the allowlist."""


class InvalidGhsaApiPageError(GhsaIngestionError):
    """Raised when a GHSA API response page violates the Bronze contract."""


class InvalidGhsaPaginationError(GhsaIngestionError):
    """Raised when a GHSA page sequence is incomplete or inconsistent."""
