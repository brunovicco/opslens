"""Domain errors raised while transforming CISA KEV Bronze evidence."""


class InvalidKevSilverSourceError(ValueError):
    """Raised when KEV Bronze evidence cannot satisfy the Silver contract."""
