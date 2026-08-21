"""Domain errors for NVD Silver transformation."""


class InvalidNvdObservedCveVersionError(ValueError):
    """Raised when an observed NVD CVE violates the version identity contract."""
