"""Domain model for a validated NVD yearly-feed artifact."""

import re
from dataclasses import dataclass

from opslens.ingestion.nvd.domain.models import NvdFeedMeta

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class NvdFeedArtifact:
    """Represent one integrity-verified NVD yearly gzip feed.

    Attributes:
        raw_gzip_bytes: Exact gzip bytes received from NVD.
        meta: Validated NVD META evidence associated with the feed.
        bronze_object_sha256: SHA-256 of the exact gzip bytes observed by
            OpsLens.
    """

    raw_gzip_bytes: bytes
    meta: NvdFeedMeta
    bronze_object_sha256: str

    def __post_init__(self) -> None:
        """Validate invariants of an integrity-verified NVD feed."""
        if not self.raw_gzip_bytes:
            raise ValueError("NVD gzip feed payload cannot be empty.")

        if not _SHA256_PATTERN.fullmatch(self.bronze_object_sha256):
            raise ValueError(
                "NVD Bronze object SHA-256 must contain exactly 64 "
                "lowercase hexadecimal characters."
            )

    @property
    def gzip_size_bytes(self) -> int:
        """Return the exact number of compressed bytes observed by OpsLens."""
        return len(self.raw_gzip_bytes)
