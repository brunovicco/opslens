"""Domain models for normalized CISA KEV Silver records."""

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum

_CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,}$")
_CWE_PATTERN = re.compile(r"^CWE-\d+$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_CISA_KEV_SOURCE = "cisa-kev"


class KevRansomwareUse(StrEnum):
    """Represent CISA's known ransomware campaign classification."""

    KNOWN = "Known"
    UNKNOWN = "Unknown"


@dataclass(frozen=True, slots=True)
class SilverKevRecord:
    """Represent one normalized CISA KEV vulnerability in the Silver layer.

    Attributes:
        cve: Canonical CVE identifier.
        vendor_project: Vendor or project identified by CISA.
        product: Affected product identified by CISA.
        vulnerability_name: Human-readable vulnerability name.
        date_added: Date on which CISA added the vulnerability to KEV.
        short_description: CISA vulnerability description.
        required_action: Remediation action required by CISA.
        due_date: CISA remediation due date.
        known_ransomware_campaign_use: CISA ransomware-use classification.
        notes: Source notes supplied by CISA.
        cwes: Zero or more canonical CWE identifiers.
        catalog_version: CISA catalog version containing this record.
        catalog_date_released: Timezone-aware catalog release timestamp.
        source: Canonical OpsLens source identifier.
        source_sha256: SHA-256 digest of the immutable Bronze artifact.
        retrieved_at: Timezone-aware timestamp when OpsLens observed the source.
        snapshot_date: UTC date on which OpsLens observed the Bronze snapshot.
    """

    cve: str
    vendor_project: str
    product: str
    vulnerability_name: str
    date_added: date
    short_description: str
    required_action: str
    due_date: date
    known_ransomware_campaign_use: KevRansomwareUse
    notes: str
    cwes: tuple[str, ...]
    catalog_version: str
    catalog_date_released: datetime
    source: str
    source_sha256: str
    retrieved_at: datetime
    snapshot_date: date

    def __post_init__(self) -> None:
        """Validate invariants required by every KEV Silver record."""
        if _CVE_PATTERN.fullmatch(self.cve) is None:
            raise ValueError("CVE identifier must use the canonical CVE format.")

        self._require_non_empty_text(self.vendor_project, "vendor_project")
        self._require_non_empty_text(self.product, "product")
        self._require_non_empty_text(
            self.vulnerability_name,
            "vulnerability_name",
        )
        self._require_non_empty_text(
            self.short_description,
            "short_description",
        )
        self._require_non_empty_text(
            self.required_action,
            "required_action",
        )
        self._require_non_empty_text(self.notes, "notes")
        self._require_non_empty_text(self.catalog_version, "catalog_version")

        for cwe in self.cwes:
            if _CWE_PATTERN.fullmatch(cwe) is None:
                raise ValueError(f"CWE identifier {cwe!r} must use the canonical CWE format.")

        if self.catalog_date_released.tzinfo is None:
            raise ValueError("KEV catalog release timestamp must be timezone-aware.")

        if self.source != _CISA_KEV_SOURCE:
            raise ValueError(f"KEV Silver source must be {_CISA_KEV_SOURCE!r}.")

        if _SHA256_PATTERN.fullmatch(self.source_sha256) is None:
            raise ValueError(
                "KEV source SHA-256 digest must contain 64 lowercase hexadecimal characters."
            )

        if self.retrieved_at.tzinfo is None:
            raise ValueError("KEV retrieval timestamp must be timezone-aware.")

        expected_snapshot_date = self.retrieved_at.astimezone(UTC).date()

        if self.snapshot_date != expected_snapshot_date:
            raise ValueError("KEV snapshot date must match the UTC retrieval date.")

    @staticmethod
    def _require_non_empty_text(value: str, field_name: str) -> None:
        """Require one normalized non-empty text value."""
        if not value or value != value.strip():
            raise ValueError(
                f"KEV Silver {field_name} must be non-empty and free of outer whitespace."
            )
