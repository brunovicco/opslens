"""Tests for canonical, content-addressed Phase 3 correlation evidence records."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime
from typing import cast

import pytest

from opslens.correlation.adapters.cve_alias import reconcile_github_cve_with_nvd
from opslens.correlation.adapters.ghsa import (
    GhsaPyPICorrelationDecision,
    GhsaPyPIVulnerabilityEvidence,
    GhsaSourceIdentifierEvidence,
    evaluate_ghsa_pypi_vulnerability,
)
from opslens.correlation.domain.aliases import CveAliasLinkState
from opslens.correlation.domain.errors import InvalidCorrelationEvidenceRecordError
from opslens.correlation.domain.evidence import (
    Phase3CorrelationEvidenceRecordV1,
    build_phase3_correlation_evidence_record,
)
from opslens.correlation.domain.pypi_ranges import CorrelationResult
from opslens.transformation.nvd.domain.models import (
    NvdCveCoreRecord,
    NvdVulnerabilityStatus,
    ObservedCveVersion,
)

_GHSA_ID = "GHSA-2345-6789-cfgh"
_CVE_ID = "CVE-2026-12345"
_GHSA_VERSION_ID = f"{_GHSA_ID}@sha256:{'a' * 64}"
_GHSA_ENTRY_ID = f"{_GHSA_VERSION_ID}/vulnerability:0@sha256:{'b' * 64}"
_TIMESTAMP = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)


def _source(*, cve_id: str | None = _CVE_ID) -> GhsaPyPIVulnerabilityEvidence:
    """Build one exact GHSA PyPI source occurrence for evidence-record tests."""
    identifiers = [
        GhsaSourceIdentifierEvidence(identifier_type="GHSA", value=_GHSA_ID),
    ]
    if cve_id is not None:
        identifiers.append(GhsaSourceIdentifierEvidence(identifier_type="CVE", value=cve_id))

    return GhsaPyPIVulnerabilityEvidence(
        observed_advisory_version_id=_GHSA_VERSION_ID,
        source_advisory_sha256="a" * 64,
        ghsa_id=_GHSA_ID,
        github_cve_id=cve_id,
        github_identifiers=tuple(identifiers),
        vulnerability_entry_id=_GHSA_ENTRY_ID,
        source_index=0,
        source_entry_sha256="b" * 64,
        ecosystem_original="pip",
        package_name_original="Demo_Package",
        vulnerable_range_original=">= 1.0, < 2.0",
        first_patched_version_original="2.0",
    )


def _nvd(
    *,
    status: NvdVulnerabilityStatus = NvdVulnerabilityStatus.ANALYZED,
) -> NvdCveCoreRecord:
    """Build one exact NVD CVE observation for alias evidence."""
    observed = ObservedCveVersion.from_source(
        {
            "id": _CVE_ID,
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


def _decision(
    source: GhsaPyPIVulnerabilityEvidence,
    *,
    package: str = "demo-package",
    version: str = "1.5",
    purl: str | None = "pkg:pypi/demo-package@1.5",
) -> GhsaPyPICorrelationDecision:
    """Evaluate one installed package using the Phase 3 GHSA bridge."""
    return evaluate_ghsa_pypi_vulnerability(
        source,
        installed_ecosystem="pypi",
        installed_package=package,
        installed_version=version,
        installed_purl=purl,
    )


def _record(
    *,
    source: GhsaPyPIVulnerabilityEvidence | None = None,
    status: NvdVulnerabilityStatus = NvdVulnerabilityStatus.ANALYZED,
    package: str = "demo-package",
    version: str = "1.5",
    purl: str | None = "pkg:pypi/demo-package@1.5",
) -> Phase3CorrelationEvidenceRecordV1:
    """Build one full Phase 3 record through applicability and alias reconciliation."""
    ghsa = source or _source()
    decision = _decision(ghsa, package=package, version=version, purl=purl)
    alias = reconcile_github_cve_with_nvd(ghsa, nvd=_nvd(status=status))
    return build_phase3_correlation_evidence_record(decision=decision, alias=alias)


def _payload(record: Phase3CorrelationEvidenceRecordV1) -> dict[str, object]:
    """Decode one tested canonical evidence record."""
    parsed = cast(object, json.loads(record.canonical_json.decode("utf-8")))
    assert isinstance(parsed, dict)
    return cast(dict[str, object], parsed)


def test_affected_record_contains_complete_phase3_output_and_source_coordinates() -> None:
    """Emit affected status, range, fix, identifiers, aliases, and exact provenance."""
    record = _record()
    payload = _payload(record)

    assert record.result is CorrelationResult.AFFECTED
    assert record.correlation_record_id == f"correlation:v1@sha256:{record.evidence_sha256}"
    assert payload["schema_version"] == "1"
    assert payload["engine"] == "opslens.phase3.pypi.v1"

    installed = cast(dict[str, object], payload["installed"])
    assert installed["package_name_canonical"] == "demo-package"
    assert installed["version_canonical"] == "1.5"
    assert installed["purl_canonical"] == "pkg:pypi/demo-package@1.5"

    decision = cast(dict[str, object], payload["decision"])
    assert decision["affected_status"] == "affected"
    assert decision["vulnerable_range_original"] == ">= 1.0, < 2.0"
    assert decision["first_patched_version_original"] == "2.0"
    assert decision["first_patched_version_canonical"] == "2.0"
    clauses = cast(list[object], decision["parsed_clauses"])
    assert len(clauses) == 2

    source_evidence = cast(dict[str, object], payload["source_evidence"])
    ghsa = cast(dict[str, object], source_evidence["ghsa"])
    nvd_alias = cast(dict[str, object], source_evidence["nvd_alias"])
    assert ghsa["ghsa_id"] == _GHSA_ID
    assert ghsa["observed_advisory_version_id"] == _GHSA_VERSION_ID
    assert ghsa["vulnerability_entry_id"] == _GHSA_ENTRY_ID
    assert nvd_alias["link_state"] == CveAliasLinkState.NVD_OBSERVED.value
    assert nvd_alias["cve_id"] == _CVE_ID


def test_same_evidence_produces_identical_canonical_bytes_and_content_id() -> None:
    """Make repeat correlation of identical immutable evidence byte-for-byte stable."""
    first = _record()
    second = _record()

    assert first.canonical_json == second.canonical_json
    assert first.evidence_sha256 == second.evidence_sha256
    assert first.correlation_record_id == second.correlation_record_id


def test_changed_installed_version_changes_content_identity_and_decision() -> None:
    """Bind record identity to installed package evidence and resulting applicability."""
    affected = _record(version="1.5", purl="pkg:pypi/demo-package@1.5")
    fixed = _record(version="2.0", purl="pkg:pypi/demo-package@2.0")

    assert affected.result is CorrelationResult.AFFECTED
    assert fixed.result is CorrelationResult.NOT_AFFECTED
    assert affected.evidence_sha256 != fixed.evidence_sha256


def test_package_non_match_is_reproducible_without_range_clause_evaluation() -> None:
    """Emit deterministic non-match evidence when package identity differs."""
    record = _record(
        package="other-package",
        version="1.5",
        purl="pkg:pypi/other-package@1.5",
    )
    payload = _payload(record)
    decision = cast(dict[str, object], payload["decision"])

    assert record.result is CorrelationResult.NOT_AFFECTED
    assert decision["reason_code"] == "package_identity_mismatch"
    assert decision["package_identity_matched"] is False
    assert decision["parsed_clauses"] == []
    assert decision["first_patched_version_original"] == "2.0"
    assert decision["first_patched_version_canonical"] is None


def test_unsupported_installed_identity_is_still_content_addressed_evidence() -> None:
    """Emit a reproducible unsupported result instead of dropping invalid purl evidence."""
    source = _source()
    decision = _decision(
        source,
        purl="pkg:pypi/different-package@1.5",
    )
    alias = reconcile_github_cve_with_nvd(source, nvd=_nvd())
    record = build_phase3_correlation_evidence_record(decision=decision, alias=alias)
    payload = _payload(record)
    decision_payload = cast(dict[str, object], payload["decision"])

    assert record.result is CorrelationResult.UNSUPPORTED
    assert decision_payload["reason_code"] == "invalid_purl"
    assert decision_payload["package_identity_matched"] is None


def test_nvd_rejected_state_is_preserved_in_final_record() -> None:
    """Carry rejected NVD evidence through the final record without rewriting its meaning."""
    record = _record(status=NvdVulnerabilityStatus.REJECTED)
    payload = _payload(record)
    source_evidence = cast(dict[str, object], payload["source_evidence"])
    nvd_alias = cast(dict[str, object], source_evidence["nvd_alias"])

    assert nvd_alias["link_state"] == CveAliasLinkState.NVD_REJECTED.value
    assert nvd_alias["vulnerability_status"] == NvdVulnerabilityStatus.REJECTED.value


def test_alias_from_different_ghsa_occurrence_cannot_be_assembled() -> None:
    """Fail closed when applicability and alias evidence refer to different source records."""
    source = _source()
    decision = _decision(source)
    alias = reconcile_github_cve_with_nvd(source, nvd=_nvd())
    wrong_alias = replace(alias, ghsa_vulnerability_entry_id="different-entry")

    with pytest.raises(InvalidCorrelationEvidenceRecordError) as exc_info:
        build_phase3_correlation_evidence_record(decision=decision, alias=wrong_alias)

    assert exc_info.value.reason_code == "invalid_correlation_evidence_record"


def test_alias_with_different_github_cve_assertion_cannot_be_assembled() -> None:
    """Require the final record to preserve one consistent GitHub CVE assertion."""
    source = _source()
    decision = _decision(source)
    alias = reconcile_github_cve_with_nvd(source, nvd=_nvd())
    wrong_alias = replace(alias, github_cve_id="CVE-2026-99999")

    with pytest.raises(InvalidCorrelationEvidenceRecordError):
        build_phase3_correlation_evidence_record(decision=decision, alias=wrong_alias)


def test_tampered_hash_is_rejected_by_record_invariants() -> None:
    """Detect evidence bytes that no longer match their content address."""
    record = _record()

    with pytest.raises(InvalidCorrelationEvidenceRecordError):
        Phase3CorrelationEvidenceRecordV1(
            canonical_json=record.canonical_json,
            evidence_sha256="0" * 64,
            result=record.result,
        )


def test_noncanonical_json_is_rejected_even_with_matching_hash() -> None:
    """Reject semantically valid but differently encoded JSON as canonical evidence."""
    record = _record()
    payload = _payload(record)
    pretty_json = json.dumps(payload, indent=2, sort_keys=False).encode("utf-8")
    pretty_hash = hashlib.sha256(pretty_json).hexdigest()

    with pytest.raises(InvalidCorrelationEvidenceRecordError):
        Phase3CorrelationEvidenceRecordV1(
            canonical_json=pretty_json,
            evidence_sha256=pretty_hash,
            result=record.result,
        )


def test_matched_package_cannot_claim_missing_applicability_evidence() -> None:
    """Reject internally inconsistent decision objects before canonical serialization."""
    source = _source()
    decision = _decision(source)
    alias = reconcile_github_cve_with_nvd(source, nvd=_nvd())
    invalid_decision = replace(decision, applicability=None)

    with pytest.raises(InvalidCorrelationEvidenceRecordError):
        build_phase3_correlation_evidence_record(decision=invalid_decision, alias=alias)
