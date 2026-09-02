"""Tests for deterministic source-preserving CVE/GHSA alias reconciliation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from opslens.correlation.adapters.cve_alias import reconcile_github_cve_with_nvd
from opslens.correlation.adapters.ghsa import GhsaPyPIVulnerabilityEvidence
from opslens.correlation.domain.aliases import CveAliasLinkState
from opslens.correlation.domain.errors import InvalidCveAliasReconciliationError
from opslens.transformation.nvd.domain.models import (
    NvdCveCoreRecord,
    NvdVulnerabilityStatus,
    ObservedCveVersion,
)

_GHSA_ID = "GHSA-2345-6789-cfgh"
_CVE_ID = "CVE-2026-12345"
_OTHER_CVE_ID = "CVE-2026-54321"
_OBSERVED_GHSA_VERSION_ID = f"{_GHSA_ID}@sha256:{'a' * 64}"
_GHSA_ENTRY_ID = f"{_OBSERVED_GHSA_VERSION_ID}/vulnerability:0@sha256:{'b' * 64}"
_TIMESTAMP = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)


def _ghsa(*, cve_id: str | None = _CVE_ID) -> GhsaPyPIVulnerabilityEvidence:
    """Build exact GHSA correlation-source coordinates for alias tests."""
    return GhsaPyPIVulnerabilityEvidence(
        observed_advisory_version_id=_OBSERVED_GHSA_VERSION_ID,
        source_advisory_sha256="a" * 64,
        ghsa_id=_GHSA_ID,
        github_cve_id=cve_id,
        github_identifiers=(),
        vulnerability_entry_id=_GHSA_ENTRY_ID,
        source_index=0,
        source_entry_sha256="b" * 64,
        ecosystem_original="pip",
        package_name_original="demo-package",
        vulnerable_range_original=">= 1.0, < 2.0",
        first_patched_version_original="2.0",
    )


def _nvd(
    *,
    cve_id: str = _CVE_ID,
    status: NvdVulnerabilityStatus = NvdVulnerabilityStatus.ANALYZED,
) -> NvdCveCoreRecord:
    """Build one exact NVD CVE observation and normalized core record."""
    observed = ObservedCveVersion.from_source(
        {
            "id": cve_id,
            "sourceIdentifier": "nvd@nist.gov",
            "vulnStatus": status.value,
        }
    )
    return NvdCveCoreRecord(
        observed_version=observed,
        source_identifier="nvd@nist.gov",
        published_at=_TIMESTAMP,
        last_modified_at=_TIMESTAMP,
        vuln_status=status,
    )


def test_no_github_cve_is_preserved_without_synthesizing_alias() -> None:
    """Represent missing GitHub CVE evidence explicitly instead of inventing an alias."""
    evidence = reconcile_github_cve_with_nvd(_ghsa(cve_id=None), nvd=None)

    assert evidence.state is CveAliasLinkState.NO_GITHUB_CVE
    assert evidence.reason_code == "github_cve_not_asserted"
    assert evidence.github_cve_id is None
    assert evidence.nvd_cve_id is None
    assert evidence.nvd_observed_cve_version_id is None


def test_github_assertion_without_supplied_nvd_evidence_remains_source_local() -> None:
    """Do not treat absence of supplied NVD evidence as proof that NVD lacks the CVE."""
    evidence = reconcile_github_cve_with_nvd(_ghsa(), nvd=None)

    assert evidence.state is CveAliasLinkState.GITHUB_ASSERTED_ONLY
    assert evidence.reason_code == "nvd_evidence_not_supplied"
    assert evidence.github_cve_id == _CVE_ID
    assert evidence.nvd_cve_id is None
    assert evidence.ghsa_observed_advisory_version_id == _OBSERVED_GHSA_VERSION_ID
    assert evidence.ghsa_vulnerability_entry_id == _GHSA_ENTRY_ID


def test_matching_active_nvd_record_creates_source_preserving_alias_edge() -> None:
    """Link equal CVE identifiers while retaining exact independent source versions."""
    nvd = _nvd()
    evidence = reconcile_github_cve_with_nvd(_ghsa(), nvd=nvd)

    assert evidence.state is CveAliasLinkState.NVD_OBSERVED
    assert evidence.reason_code == "matching_cve_observed_by_nvd"
    assert evidence.github_cve_id == _CVE_ID
    assert evidence.nvd_cve_id == _CVE_ID
    assert evidence.nvd_observed_cve_version_id == nvd.observed_version.observed_cve_version_id
    assert evidence.nvd_source_cve_sha256 == nvd.observed_version.source_cve_sha256
    assert evidence.nvd_source_identifier == "nvd@nist.gov"
    assert evidence.nvd_vulnerability_status == NvdVulnerabilityStatus.ANALYZED.value
    assert evidence.ghsa_source_advisory_sha256 == "a" * 64


def test_matching_rejected_nvd_record_is_not_collapsed_into_active_confirmation() -> None:
    """Preserve NVD rejection as a distinct reconciliation state."""
    nvd = _nvd(status=NvdVulnerabilityStatus.REJECTED)
    evidence = reconcile_github_cve_with_nvd(_ghsa(), nvd=nvd)

    assert evidence.state is CveAliasLinkState.NVD_REJECTED
    assert evidence.reason_code == "matching_cve_observed_rejected_by_nvd"
    assert evidence.nvd_vulnerability_status == NvdVulnerabilityStatus.REJECTED.value
    assert evidence.github_cve_id == evidence.nvd_cve_id == _CVE_ID


def test_different_nvd_cve_cannot_be_linked_to_github_assertion() -> None:
    """Fail closed rather than presenting two different CVE identifiers as aliases."""
    with pytest.raises(InvalidCveAliasReconciliationError) as exc_info:
        reconcile_github_cve_with_nvd(_ghsa(), nvd=_nvd(cve_id=_OTHER_CVE_ID))

    assert exc_info.value.reason_code == "invalid_cve_alias_reconciliation"


def test_nvd_evidence_cannot_be_attached_when_github_asserted_no_cve() -> None:
    """Reject unrelated NVD evidence when the GHSA source contains no CVE assertion."""
    with pytest.raises(InvalidCveAliasReconciliationError) as exc_info:
        reconcile_github_cve_with_nvd(_ghsa(cve_id=None), nvd=_nvd())

    assert exc_info.value.reason_code == "invalid_cve_alias_reconciliation"


@pytest.mark.parametrize(
    "status",
    [
        NvdVulnerabilityStatus.UNDERGOING_ANALYSIS,
        NvdVulnerabilityStatus.MODIFIED,
        NvdVulnerabilityStatus.AWAITING_ANALYSIS,
        NvdVulnerabilityStatus.RECEIVED,
        NvdVulnerabilityStatus.ANALYZED,
        NvdVulnerabilityStatus.DEFERRED,
    ],
)
def test_non_rejected_nvd_statuses_mean_observed_not_semantically_approved(
    status: NvdVulnerabilityStatus,
) -> None:
    """Use observed semantics for every non-rejected NVD lifecycle state."""
    evidence = reconcile_github_cve_with_nvd(_ghsa(), nvd=_nvd(status=status))

    assert evidence.state is CveAliasLinkState.NVD_OBSERVED
    assert evidence.nvd_vulnerability_status == status.value
