"""Domain models for normalized EPSS Silver records."""

import math
import re
from dataclasses import dataclass
from datetime import date, datetime

_CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_FIRST_EPSS_SOURCE = "first-epss"


@dataclass(frozen=True, slots=True)
class SilverEpssRecord:
    """Represent one normalized EPSS record in the Silver layer.

    Attributes:
        cve: Canonical CVE identifier.
        epss: EPSS probability score in the inclusive range from 0.0 to 1.0.
        percentile: EPSS percentile in the inclusive range from 0.0 to 1.0.
        model_version: EPSS model version declared by FIRST.
        score_timestamp: Timezone-aware timestamp declared by the source snapshot.
        source: Canonical source identifier.
        source_sha256: SHA-256 digest of the immutable Bronze source artifact.
        snapshot_date: Source snapshot date derived from the score timestamp.
    """

    cve: str
    epss: float
    percentile: float
    model_version: str
    score_timestamp: datetime
    source: str
    source_sha256: str
    snapshot_date: date

    def __post_init__(self) -> None:
        """Validate invariants required by every EPSS Silver record."""
        if _CVE_PATTERN.fullmatch(self.cve) is None:
            raise ValueError("CVE identifier must use the canonical CVE format.")

        if not math.isfinite(self.epss) or not 0.0 <= self.epss <= 1.0:
            raise ValueError("EPSS score must be a finite value between 0.0 and 1.0.")

        if not math.isfinite(self.percentile) or not 0.0 <= self.percentile <= 1.0:
            raise ValueError("EPSS percentile must be a finite value between 0.0 and 1.0.")

        if not self.model_version.strip():
            raise ValueError("EPSS model version cannot be empty.")

        if self.score_timestamp.tzinfo is None:
            raise ValueError("EPSS score timestamp must be timezone-aware.")

        if self.source != _FIRST_EPSS_SOURCE:
            raise ValueError(f"EPSS Silver source must be {_FIRST_EPSS_SOURCE!r}.")

        if _SHA256_PATTERN.fullmatch(self.source_sha256) is None:
            raise ValueError(
                "EPSS source SHA-256 digest must contain 64 lowercase hexadecimal characters."
            )

        if self.snapshot_date != self.score_timestamp.date():
            raise ValueError(
                "EPSS snapshot date must match the date declared by the score timestamp."
            )
