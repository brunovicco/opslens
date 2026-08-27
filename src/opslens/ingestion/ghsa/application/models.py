"""Persistence-result models for GHSA Bronze evidence."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GhsaBronzeWriteResult:
    """Represent the exact version created for one immutable Bronze object."""

    key: str
    version_id: str

    def __post_init__(self) -> None:
        """Require exact key and versioned persistence evidence."""
        if not self.key.strip():
            raise ValueError("GHSA Bronze write result requires a non-empty key.")

        if not self.version_id.strip():
            raise ValueError("GHSA Bronze write result requires a non-empty VersionId.")
