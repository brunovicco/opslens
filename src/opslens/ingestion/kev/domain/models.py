"""Domain models representing an observed CISA KEV catalog snapshot."""

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class KevCatalogSnapshot:
    """Represent a validated immutable observation of the CISA KEV catalog.

    Attributes:
        raw_bytes: Original JSON bytes received from CISA.
        catalog_version: Catalog version declared by CISA.
        date_released: Source release timestamp declared by CISA.
        retrieved_at: Timestamp when OpsLens observed the source artifact.
        sha256: SHA-256 digest calculated from the original JSON bytes.
        record_count: Number of vulnerability records declared by the catalog.
    """

    raw_bytes: bytes
    catalog_version: str
    date_released: datetime
    retrieved_at: datetime
    sha256: str
    record_count: int

    def __post_init__(self) -> None:
        """Validate invariants that every KEV Bronze snapshot must satisfy."""
        if not self.raw_bytes:
            raise ValueError("KEV catalog payload cannot be empty.")

        if not self.catalog_version:
            raise ValueError("KEV catalog version cannot be empty.")

        if self.date_released.tzinfo is None:
            raise ValueError("KEV dateReleased must be timezone-aware.")

        if self.retrieved_at.tzinfo is None:
            raise ValueError("KEV retrieved_at must be timezone-aware.")

        if len(self.sha256) != 64:
            raise ValueError("KEV SHA-256 digest must contain 64 hexadecimal characters.")

        if self.record_count <= 0:
            raise ValueError("KEV catalog must contain at least one vulnerability.")

    @property
    def snapshot_date(self) -> str:
        """Return the UTC date on which OpsLens observed this catalog."""
        return self.retrieved_at.astimezone(UTC).date().isoformat()

    @property
    def payload_size_bytes(self) -> int:
        """Return the original source artifact size in bytes."""
        return len(self.raw_bytes)
