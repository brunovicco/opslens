"""Source-preserving evidence models for deterministic CVE alias reconciliation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CveAliasLinkState(StrEnum):
    """States for a GitHub CVE assertion evaluated against supplied NVD evidence."""

    NO_GITHUB_CVE = "no_github_cve"
    GITHUB_ASSERTED_UNVERIFIED = "github_asserted_unverified"
    NVD_OBSERVED = "nvd_observed"
    NVD_REJECTED = "nvd_rejected"


@dataclass(frozen=True, slots=True)
class CveAliasReconciliationEvidence:
    """Preserve independent GHSA and NVD evidence connected by one CVE identifier."""

    ghsa_id: str
    ghsa_observed_advisory_version_id: str
    ghsa_source_advisory_sha256: str
    ghsa_vulnerability_entry_id: str
    github_cve_id: str | None
    nvd_cve_id: str | None
    nvd_observed_cve_version_id: str | None
    nvd_source_cve_sha256: str | None
    nvd_source_identifier: str | None
    nvd_vulnerability_status: str | None
    state: CveAliasLinkState
    reason_code: str
