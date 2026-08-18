"""Deterministic source identity for NVD yearly-feed bootstrap artifacts."""

from dataclasses import dataclass
from datetime import UTC

from opslens.ingestion.nvd.domain.models import NvdFeedMeta


@dataclass(frozen=True, slots=True)
class NvdBootstrapSourceIdentity:
    """Identify one immutable NVD yearly-feed source revision.

    The identity combines:

    - the requested yearly feed;
    - the NVD META last-modified instant normalized to UTC;
    - the NVD SHA-256 of the uncompressed JSON artifact.

    Attributes:
        feed_year: Four-digit NVD yearly-feed identifier.
        meta: Validated NVD META evidence for the source revision.
    """

    feed_year: int
    meta: NvdFeedMeta

    def __post_init__(self) -> None:
        """Validate invariants required by a bootstrap source identity."""
        if type(self.feed_year) is not int:
            raise ValueError("NVD feed year must be an integer.")

        if self.feed_year < 1000 or self.feed_year > 9999:
            raise ValueError("NVD feed year must contain exactly four digits.")

    @property
    def feed_revision(self) -> str:
        """Return a deterministic filesystem-safe NVD feed revision."""
        source_timestamp = self.meta.last_modified_at.astimezone(UTC)

        timespec = "microseconds" if source_timestamp.microsecond else "seconds"

        normalized_timestamp = (
            source_timestamp.isoformat(timespec=timespec)
            .replace("+00:00", "Z")
            .replace("-", "")
            .replace(":", "")
        )

        return f"{normalized_timestamp}-{self.meta.source_sha256}"
