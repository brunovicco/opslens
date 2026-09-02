"""Reconcile GitHub CVE assertions against exact NVD evidence without merging sources."""

from __future__ import annotations

from opslens.correlation.adapters.ghsa import GhsaPyPIVulnerabilityEvidence
from opslens.correlation.domain.aliases import (
    CveAliasLinkState,
    CveAliasReconciliationEvidence,
)
from opslens.correlation.domain.errors import InvalidCveAliasReconciliationError
from opslens.transformation.nvd.domain.models import (
    NvdCveCoreRecord,
    NvdVulnerabilityStatus,
)


def reconcile_github_cve_with_nvd(
    ghsa: GhsaPyPIVulnerabilityEvidence,
    *,
    nvd: NvdCveCoreRecord | None,
) -> CveAliasReconciliationEvidence:
    """Build one source-preserving CVE alias edge from supplied GHSA and NVD evidence.

    The function does not perform discovery. `nvd=None` means only that no NVD evidence was
    supplied to this reconciliation call; it must not be interpreted as NVD absence.
    """
    github_cve_id = ghsa.github_cve_id

    if github_cve_id is None:
        if nvd is not None:
            raise InvalidCveAliasReconciliationError(
                "NVD evidence cannot be linked when GitHub did not assert a CVE identifier."
            )
        return _build_evidence(
            ghsa=ghsa,
            nvd=None,
            state=CveAliasLinkState.NO_GITHUB_CVE,
            reason_code="github_cve_not_asserted",
        )

    if nvd is None:
        return _build_evidence(
            ghsa=ghsa,
            nvd=None,
            state=CveAliasLinkState.GITHUB_ASSERTED_ONLY,
            reason_code="nvd_evidence_not_supplied",
        )

    nvd_cve_id = nvd.observed_version.cve_id
    if nvd_cve_id != github_cve_id:
        raise InvalidCveAliasReconciliationError(
            "Supplied NVD CVE identity does not match the GitHub CVE assertion."
        )

    if nvd.vuln_status is NvdVulnerabilityStatus.REJECTED:
        return _build_evidence(
            ghsa=ghsa,
            nvd=nvd,
            state=CveAliasLinkState.NVD_REJECTED,
            reason_code="matching_cve_observed_rejected_by_nvd",
        )

    return _build_evidence(
        ghsa=ghsa,
        nvd=nvd,
        state=CveAliasLinkState.NVD_OBSERVED,
        reason_code="matching_cve_observed_by_nvd",
    )


def _build_evidence(
    *,
    ghsa: GhsaPyPIVulnerabilityEvidence,
    nvd: NvdCveCoreRecord | None,
    state: CveAliasLinkState,
    reason_code: str,
) -> CveAliasReconciliationEvidence:
    """Construct one immutable alias edge while preserving both source coordinates."""
    observed_nvd = nvd.observed_version if nvd is not None else None

    return CveAliasReconciliationEvidence(
        ghsa_id=ghsa.ghsa_id,
        ghsa_observed_advisory_version_id=ghsa.observed_advisory_version_id,
        ghsa_source_advisory_sha256=ghsa.source_advisory_sha256,
        ghsa_vulnerability_entry_id=ghsa.vulnerability_entry_id,
        github_cve_id=ghsa.github_cve_id,
        nvd_cve_id=observed_nvd.cve_id if observed_nvd is not None else None,
        nvd_observed_cve_version_id=(
            observed_nvd.observed_cve_version_id if observed_nvd is not None else None
        ),
        nvd_source_cve_sha256=(
            observed_nvd.source_cve_sha256 if observed_nvd is not None else None
        ),
        nvd_source_identifier=nvd.source_identifier if nvd is not None else None,
        nvd_vulnerability_status=nvd.vuln_status.value if nvd is not None else None,
        state=state,
        reason_code=reason_code,
    )
