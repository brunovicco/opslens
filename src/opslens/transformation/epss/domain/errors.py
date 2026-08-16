"""Domain errors raised while transforming EPSS data into Silver records."""


class InvalidEpssSilverSourceError(ValueError):
    """Represent invalid EPSS source data discovered during Silver transformation."""
