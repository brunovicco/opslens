"""Application errors for NVD Silver orchestration."""


class NvdSilverParquetAlreadyExistsError(RuntimeError):
    """Signal that a deterministic Silver key requires replay verification."""


class NvdSilverCompletionAlreadyExistsError(RuntimeError):
    """Signal that a deterministic COMPLETE key requires replay verification."""
