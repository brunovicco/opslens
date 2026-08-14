"""Domain models representing an EPSS source snapshot."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class EpssSnapshot:
    """Represent a validated immutable EPSS source snapshot.

    Attributes:
        raw_bytes: Original gzip bytes received from the source.
        model_version: EPSS model version declared by FIRST.
        score_timestamp: Source timestamp declared in the EPSS metadata.
        sha256: SHA-256 digest calculated from the original gzip bytes.
        row_count: Number of EPSS data rows, excluding metadata and header.
    """

    raw_bytes: bytes
    model_version: str
    score_timestamp: datetime
    sha256: str
    row_count: int

    def __post_init__(self) -> None:
        """Validate invariants that every EPSS snapshot must satisfy."""
        if not self.raw_bytes:
            raise ValueError("EPSS snapshot payload cannot be empty.")

        if not self.model_version:
            raise ValueError("EPSS model version cannot be empty.")

        if self.score_timestamp.tzinfo is None:
            raise ValueError("EPSS score timestamp must be timezone-aware.")

        if len(self.sha256) != 64:
            raise ValueError("EPSS SHA-256 digest must contain 64 hexadecimal characters.")

        if self.row_count <= 0:
            raise ValueError("EPSS snapshot must contain at least one data row.")

    @property
    def snapshot_date(self) -> str:
        """Return the canonical source snapshot date in ISO-8601 format."""
        return self.score_timestamp.date().isoformat()

    @property
    def payload_size_bytes(self) -> int:
        """Return the compressed source artifact size in bytes."""
        return len(self.raw_bytes)
