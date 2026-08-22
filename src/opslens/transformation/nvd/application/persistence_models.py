"""Persistence evidence models for NVD Silver runtime orchestration."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NvdSilverStoredCompletionV1:
    """Describe one exact persisted Silver COMPLETE manifest."""

    key: str
    version_id: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        """Validate immutable COMPLETE persistence evidence."""
        if not self.key.strip():
            raise ValueError("NVD Silver COMPLETE key cannot be empty.")

        if not self.version_id.strip():
            raise ValueError("NVD Silver COMPLETE VersionId cannot be empty.")

        if len(self.sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.sha256
        ):
            raise ValueError("NVD Silver COMPLETE SHA-256 is invalid.")

        if type(self.size_bytes) is not int or self.size_bytes <= 0:
            raise ValueError("NVD Silver COMPLETE size must be positive.")
