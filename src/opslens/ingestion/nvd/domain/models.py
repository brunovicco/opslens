"""Domain models for NVD yearly-feed source metadata."""

import re
from dataclasses import dataclass
from datetime import datetime

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class NvdFeedMeta:
    """Represent validated source metadata for one NVD yearly feed.

    Attributes:
        raw_bytes: Original META artifact bytes received from NVD.
        last_modified_at: Source feed revision timestamp declared by NVD.
        uncompressed_size_bytes: Size of the uncompressed JSON artifact.
        zip_size_bytes: Size of the ZIP artifact declared by NVD.
        gzip_size_bytes: Size of the gzip artifact declared by NVD.
        source_sha256: NVD SHA-256 for the uncompressed JSON payload.
    """

    raw_bytes: bytes
    last_modified_at: datetime
    uncompressed_size_bytes: int
    zip_size_bytes: int
    gzip_size_bytes: int
    source_sha256: str

    def __post_init__(self) -> None:
        """Validate invariants required by every NVD META observation."""
        if not self.raw_bytes:
            raise ValueError("NVD feed META payload cannot be empty.")

        if self.last_modified_at.tzinfo is None:
            raise ValueError("NVD feed lastModifiedDate must be timezone-aware.")

        if self.uncompressed_size_bytes <= 0:
            raise ValueError("NVD feed uncompressed size must be positive.")

        if self.zip_size_bytes <= 0:
            raise ValueError("NVD feed ZIP size must be positive.")

        if self.gzip_size_bytes <= 0:
            raise ValueError("NVD feed gzip size must be positive.")

        if not _SHA256_PATTERN.fullmatch(self.source_sha256):
            raise ValueError(
                "NVD source SHA-256 must contain exactly 64 lowercase hexadecimal characters."
            )
