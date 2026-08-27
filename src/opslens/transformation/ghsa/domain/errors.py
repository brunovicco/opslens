"""Domain errors for deterministic GHSA Silver normalization."""


class InvalidGhsaObservedAdvisoryVersionError(ValueError):
    """Raised when an observed GHSA advisory version is invalid."""


class InvalidGhsaAdvisoryCoreRecordError(ValueError):
    """Raised when a GHSA advisory cannot satisfy the core Silver contract."""


class InvalidGhsaAdvisoryCollectionsError(ValueError):
    """Raised when GHSA structured advisory collections are invalid."""


class InvalidGhsaVulnerabilityEntriesError(ValueError):
    """Raised when GHSA vulnerability/package evidence is invalid."""
