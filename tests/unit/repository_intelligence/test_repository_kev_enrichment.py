"""Tests for complete-snapshot CISA KEV enrichment of repository findings."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime

import pytest

import opslens.repository_intelligence.domain.kev_enrichment as kev_domain
from opslens.correlation.adapters.ghsa import (
    GhsaPyPIVulnerabilityEvidence,
    GhsaSourceIdentifierEvidence,
)
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.repository_intelligence.application import (
    build_repository_pypi_vulnerability_scan,
    enrich_repository_findings_with_kev,
    enrich_repository_findings_with_nvd,
    normalize_uv_lock_pypi_dependencies,
)
from opslens.repository_intelligence.domain import (
    GitHubRepositoryIdentity,
    ImmutableRepositoryFileEvidence,
    ImmutableRepositorySnapshot,
    InvalidRepositoryKevEnrichmentError,
    RepositoryKevEnrichedFinding,
    RepositoryKevEnrichmentLimitError,
    RepositoryKevState,
    RepositoryNvdEnrichmentEvidence,
    RepositoryPyPINormalizationInventory,
    RepositoryVulnerabilityScanEvidence,
    compute_content_sha256,
    compute_git_blob_sha1,
)
from opslens.repository_intelligence.parsers.uv_lock import parse_uv_lock_evidence

_REPOSITORY_ID = 1_333_092_779
_COMMIT_SHA = "3bbe875951728094753ef872cfe6b8113d55f147"
_TREE_SHA = "a" * 40
_CVE_ID = "CVE-2026-12345"
_KEV_CATALOG_VERSION = "2026.09.03"
_KEV_DATE_RELEASED = datetime(2026, 9, 3, 12, 0, tzinfo=UTC)
_KEV_RETRIEVED_AT = datetime(2026, 9, 3, 12, 30, tzinfo=UTC)


def _repository_snapshot() -> ImmutableRepositorySnapshot:
    """Build one exact immutable repository snapshot fixture."""
    return ImmutableRepositorySnapshot(
        repository=GitHubRepositoryIdentity(
            repository_id=_REPOSITORY_ID,
            owner="brunovicco",
            name="opslens",
            full_name="brunovicco/opslens",
            is_private=False,
        ),
        requested_ref="main",
        commit_sha=_COMMIT_SHA,
        tree_sha=_TREE_SHA,
    )


def _file_evidence(content: bytes) -> ImmutableRepositoryFileEvidence:
    """Bind inert lock bytes to exact immutable repository evidence."""
    return ImmutableRepositoryFileEvidence(
        snapshot=_repository_snapshot(),
        path="uv.lock",
        blob_sha=compute_git_blob_sha1(content),
        size_bytes=len(content),
        content_sha256=compute_content_sha256(content),
        content_bytes=content,
    )


def _inventory(version: str = "2.31.0") -> RepositoryPyPINormalizationInventory:
    """Build normalized PyPI dependency evidence through the real lock parser."""
    content = (
        "version = 1\n"
        "revision = 3\n"
        'requires-python = ">=3.13"\n'
        "[[package]]\n"
        'name = "requests"\n'
        f'version = "{version}"\n'
        'source = { registry = "https://pypi.org/simple" }\n'
    ).encode()
    parsed = parse_uv_lock_evidence(_file_evidence(content))
    return normalize_uv_lock_pypi_dependencies(parsed)


def _ghsa(cve_id: str | None = _CVE_ID) -> GhsaPyPIVulnerabilityEvidence:
    """Build one affected exact GHSA PyPI occurrence."""
    identifiers = (
        (GhsaSourceIdentifierEvidence(identifier_type="CVE", value=cve_id),)
        if cve_id is not None
        else ()
    )
    return GhsaPyPIVulnerabilityEvidence(
        observed_advisory_version_id="ghsa-observed-0",
        source_advisory_sha256="0" * 64,
        ghsa_id="GHSA-test-0",
        github_cve_id=cve_id,
        github_identifiers=identifiers,
        vulnerability_entry_id="ghsa-entry-0",
        source_index=0,
        source_entry_sha256="1" * 64,
        ecosystem_original="pip",
        package_name_original="requests",
        vulnerable_range_original=">= 2, < 2.32",
        first_patched_version_original="2.32",
    )


def _scan(source: GhsaPyPIVulnerabilityEvidence) -> RepositoryVulnerabilityScanEvidence:
    """Build Gate 4.7 affected repository evidence."""
    return build_repository_pypi_vulnerability_scan(_inventory(), [source])


def _previous(cve_id: str | None = _CVE_ID) -> RepositoryNvdEnrichmentEvidence:
    """Build Gate 4.8 evidence without requiring NVD for KEV membership tests."""
    source = _ghsa(cve_id)
    return enrich_repository_findings_with_nvd(_scan(source), [source], [])


def _kev_record(cve_id: str = _CVE_ID, *, notes: str = "Source note") -> dict[str, object]:
    """Build one valid CISA KEV vulnerability record."""
    return {
        "cveID": cve_id,
        "vendorProject": "Example Vendor",
        "product": "Example Product",
        "vulnerabilityName": "Example Vulnerability",
        "dateAdded": "2026-09-01",
        "shortDescription": "A vulnerability affecting the example product.",
        "requiredAction": "Apply mitigations according to vendor guidance.",
        "dueDate": "2026-09-22",
        "knownRansomwareCampaignUse": "Known",
        "notes": notes,
        "cwes": ["CWE-79"],
    }


def _kev_snapshot(
    *,
    records: tuple[dict[str, object], ...] | None = None,
    declared_count: int | None = None,
    notes: str = "Source note",
) -> KevCatalogSnapshot:
    """Build one immutable validated-style complete KEV Bronze snapshot."""
    resolved_records = records if records is not None else (_kev_record(notes=notes),)
    document: dict[str, object] = {
        "title": "CISA Known Exploited Vulnerabilities Catalog",
        "catalogVersion": _KEV_CATALOG_VERSION,
        "dateReleased": "2026-09-03T12:00:00Z",
        "count": len(resolved_records),
        "vulnerabilities": list(resolved_records),
    }
    payload = json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return KevCatalogSnapshot(
        raw_bytes=payload,
        catalog_version=_KEV_CATALOG_VERSION,
        date_released=_KEV_DATE_RELEASED,
        retrieved_at=_KEV_RETRIEVED_AT,
        sha256=hashlib.sha256(payload).hexdigest(),
        record_count=(declared_count if declared_count is not None else len(resolved_records)),
    )


def test_complete_snapshot_present_state_preserves_full_kev_evidence() -> None:
    """Emit positive KEV evidence only from the fully transformed supplied snapshot."""
    previous = _previous()
    previous_id = previous.enriched_findings[0].enrichment_id
    snapshot = _kev_snapshot()

    evidence = enrich_repository_findings_with_kev(previous, snapshot)

    assert evidence.present_count == 1
    assert evidence.absent_count == 0
    assert evidence.cve_unavailable_count == 0
    enriched = evidence.enriched_findings[0]
    assert enriched.previous.enrichment_id == previous_id
    assert enriched.state is RepositoryKevState.PRESENT
    assert enriched.evaluated_cve_id == _CVE_ID
    assert enriched.kev_record is not None
    assert enriched.kev_record.cve == _CVE_ID
    assert enriched.kev_record.known_ransomware_campaign_use.value == "Known"
    assert enriched.kev_record.source_sha256 == snapshot.sha256
    assert b'"kev_state":"present"' in enriched.canonical_json
    assert snapshot.sha256.encode() in enriched.canonical_json


def test_complete_snapshot_can_prove_cve_absence() -> None:
    """Emit absent only after a different complete KEV catalog has been validated."""
    previous = _previous()
    snapshot = _kev_snapshot(records=(_kev_record("CVE-2026-99999"),))

    evidence = enrich_repository_findings_with_kev(previous, snapshot)

    enriched = evidence.enriched_findings[0]
    assert enriched.state is RepositoryKevState.ABSENT
    assert enriched.evaluated_cve_id == _CVE_ID
    assert enriched.kev_record is None
    assert evidence.present_count == 0
    assert evidence.absent_count == 1


def test_missing_github_cve_is_unavailable_not_absent() -> None:
    """Never convert missing CVE identity into negative KEV membership evidence."""
    previous = _previous(cve_id=None)
    snapshot = _kev_snapshot()

    evidence = enrich_repository_findings_with_kev(previous, snapshot)

    enriched = evidence.enriched_findings[0]
    assert enriched.state is RepositoryKevState.CVE_UNAVAILABLE
    assert enriched.evaluated_cve_id is None
    assert enriched.kev_record is None
    assert evidence.absent_count == 0
    assert evidence.cve_unavailable_count == 1


def test_kev_membership_does_not_require_nvd_evidence() -> None:
    """Use the GitHub CVE assertion directly even when Gate 4.8 had no NVD record."""
    previous = _previous()
    assert previous.enriched_findings[0].nvd_cvss is None

    evidence = enrich_repository_findings_with_kev(previous, _kev_snapshot())

    assert evidence.enriched_findings[0].state is RepositoryKevState.PRESENT


def test_tampered_snapshot_sha_fails_before_membership_evaluation() -> None:
    """Reject KEV metadata whose digest no longer authenticates the supplied source bytes."""
    previous = _previous()
    snapshot = replace(_kev_snapshot(), sha256="0" * 64)

    with pytest.raises(InvalidRepositoryKevEnrichmentError):
        enrich_repository_findings_with_kev(previous, snapshot)


def test_inconsistent_complete_snapshot_count_fails_closed() -> None:
    """Reject a snapshot whose metadata does not describe the complete source document."""
    previous = _previous()
    snapshot = _kev_snapshot(declared_count=2)

    with pytest.raises(InvalidRepositoryKevEnrichmentError):
        enrich_repository_findings_with_kev(previous, snapshot)


def test_record_bound_fails_before_catalog_use(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bound complete-snapshot transformation without truncating KEV evidence."""
    previous = _previous()
    snapshot = _kev_snapshot()
    monkeypatch.setattr(kev_domain, "MAX_KEV_ENRICHMENT_RECORDS", 0)

    with pytest.raises(RepositoryKevEnrichmentLimitError):
        enrich_repository_findings_with_kev(previous, snapshot)


def test_source_byte_bound_fails_before_catalog_use(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bound KEV source bytes independently of the catalog record count."""
    previous = _previous()
    snapshot = _kev_snapshot()
    monkeypatch.setattr(kev_domain, "MAX_KEV_ENRICHMENT_BYTES", 1)

    with pytest.raises(RepositoryKevEnrichmentLimitError):
        enrich_repository_findings_with_kev(previous, snapshot)


def test_domain_rejects_state_that_disagrees_with_complete_snapshot() -> None:
    """Prevent callers from relabeling a positive KEV match as negative evidence."""
    previous = _previous()
    evidence = enrich_repository_findings_with_kev(previous, _kev_snapshot())
    enriched = evidence.enriched_findings[0]

    with pytest.raises(InvalidRepositoryKevEnrichmentError):
        RepositoryKevEnrichedFinding(
            previous=enriched.previous,
            kev_snapshot=enriched.kev_snapshot,
            state=RepositoryKevState.ABSENT,
            kev_record=None,
        )


def test_enrichment_id_is_deterministic_and_commits_to_exact_kev_snapshot() -> None:
    """Change KEV enrichment identity when complete source content changes."""
    previous = _previous()
    first_snapshot = _kev_snapshot(notes="first")
    changed_snapshot = _kev_snapshot(notes="changed")

    first = enrich_repository_findings_with_kev(previous, first_snapshot)
    repeated = enrich_repository_findings_with_kev(previous, first_snapshot)
    changed = enrich_repository_findings_with_kev(previous, changed_snapshot)

    first_finding = first.enriched_findings[0]
    repeated_finding = repeated.enriched_findings[0]
    changed_finding = changed.enriched_findings[0]
    assert first_finding.enrichment_id == repeated_finding.enrichment_id
    assert first_finding.enrichment_id != changed_finding.enrichment_id
    assert first_finding.previous.enrichment_id == changed_finding.previous.enrichment_id


def test_no_affected_findings_remains_empty_without_invented_kev_risk() -> None:
    """Do not create KEV-enriched findings when Gate 4.7 emitted no affected finding."""
    source = _ghsa()
    scan = build_repository_pypi_vulnerability_scan(_inventory("2.32.0"), [source])
    previous = enrich_repository_findings_with_nvd(scan, [source], [])
    assert previous.enriched_findings == ()

    evidence = enrich_repository_findings_with_kev(previous, _kev_snapshot())

    assert evidence.enriched_findings == ()
    assert evidence.present_count == 0
    assert evidence.absent_count == 0
    assert evidence.cve_unavailable_count == 0
