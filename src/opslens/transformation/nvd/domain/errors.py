"""Domain errors for NVD Silver transformation."""


class InvalidNvdObservedCveVersionError(ValueError):
    """Raised when an observed NVD CVE violates the version identity contract."""


class InvalidNvdCveCoreRecordError(ValueError):
    """Raised when an NVD CVE violates the Silver core-record contract."""


class InvalidNvdCveCollectionsError(ValueError):
    """Raised when NVD collection fields violate the Silver contract."""
