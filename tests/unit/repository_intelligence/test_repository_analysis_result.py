"""Tests for the final deterministic Phase 4 repository-analysis projection."""

from __future__ import annotations

import gzip
import hashlib
import json
from datetime import UTC, datetime

from opslens.correlation.adapters.ghsa import (
    GhsaPyPIVulnerabilityEvidence,
    GhsaSourceIdentifierEvidence,
)
from opslens.ingestion.epss.domain.parser import EpssSnapshotParser
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.repository_intelligence.application import (
    build_repository_analysis_result,
    build_repository_pypi_vulnerability_scan,
    enrich_repository_findings_with_epss,
    enrich_repository_findings_with_kev,
    enrich_repository_findings_with_nvd,
    normalize_uv_lock_pypi_dependencies,
)
from opslens.repository_intelligence.domain import (
    GitHubRepositoryIdentity,
    ImmutableRepositoryFileEvidence,
    ImmutableRepositorySnapshot,
    RepositoryEpssState,
    RepositoryKevState,
    compute_content_sha256,
    compute_git_blob_sha1,
)
from opslens.repository_intelligence.parsers.uv_lock import parse_uv_lock_evidence
from opslens.transformation.nvd.domain.transformer import NvdCveCoreTransformer

_REPOSITORY_ID = 1_333_092_779
_COMMIT_SHA = "bfe823598591d348556284439498df5b84d57cc1"
_TREE_SHA = "a" * 40
_CVE_ID = "CVE-2026-12345"


def _repository_snapshot() -> ImmutableRepositorySnapshot:
    """Build one exact public GitHub repository snapshot."""
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


def _inventory(version: str = "2.31.0"):
    """Parse and normalize exact inert PyPI dependency evidence."""
    content = (
        "version = 1\n"
        "revision = 3\n"
        'requires-python = ">=3.13"\n'
        "[[package]]\n"
        'name = "Requests"\n'
        f'version = "{version}"\n'
        'source = { registry = "https://pypi.org/simple" }\n'
    ).encode()
    file_evidence = ImmutableRepositoryFileEvidence(
        snapshot=_repository_snapshot(),
        path="uv.lock",
        blob_sha=compute_git_blob_sha1(content),
        size_bytes=len(content),
        content_sha256=compute_content_sha256(content),
        content_bytes=content,
    )
    return normalize_uv_lock_pypi_dependencies(parse_uv_lock_evidence(file_evidence))


def _ghsa(cve_id: str | None = _CVE_ID) -> GhsaPyPIVulnerabilityEvidence:
    """Build one exact affected GHSA occurrence with a known fixed version."""
    identifiers = (
        (GhsaSourceIdentifierEvidence(identifier_type="CVE", value=cve_id),)
        if cve_id is not None
        else ()
    )
    return GhsaPyPIVulnerabilityEvidence(
        observed_advisory_version_id="ghsa-observed-v1",
        source_advisory_sha256="0" * 64,
        ghsa_id="GHSA-test-1234",
        github_cve_id=cve_id,
        github_identifiers=identifiers,
        vulnerability_entry_id="ghsa-entry-0",
        source_index=0,
        source_entry_sha256="1" * 64,
        ecosystem_original="pip",
        package_name_original="requests",
        vulnerable_range_original=">= 2, < 2.32",
        first_patched_version_original="2.32.0",
    )


def _nvd_record():  # type: ignore[no-untyped-def]
    """Build exact NVD evidence with two CVSS observations through the Phase 2 transformer."""
    source: dict[str, object] = {
        "id": _CVE_ID,
        "sourceIdentifier": "security@example.com",
        "published": "2026-09-01T12:00:00.000",
        "lastModified": "2026-09-03T12:00:00.000",
        "vulnStatus": "Analyzed",
        "metrics": {
            "cvssMetricV31": [
                {
                    "source": "nvd@nist.gov",
                    "type": "Primary",
                    "cvssData": {
                        "version": "3.1",
                        "vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                        "baseScore": 9.8,
                        "baseSeverity": "CRITICAL",
                    },
                    "exploitabilityScore": 3.9,
                    "impactScore": 5.9,
                },
                {
                    "source": "security@example.com",
                    "type": "Secondary",
                    "cvssData": {
                        "version": "3.1",
                        "vectorString": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H",
                        "baseScore": 8.8,
                        "baseSeverity": "HIGH",
                    },
                    "exploitabilityScore": 2.8,
                    "impactScore": 5.9,
                },
            ]
        },
    }
    return NvdCveCoreTransformer().transform(source)


def _kev_snapshot(*, include_cve: bool = True) -> KevCatalogSnapshot:
    """Build one complete immutable CISA KEV catalog snapshot."""
    cve_id = _CVE_ID if include_cve else "CVE-2026-99999"
    record: dict[str, object] = {
        "cveID": cve_id,
        "vendorProject": "Example Vendor",
        "product": "Example Product",
        "vulnerabilityName": "Example Known Exploited Vulnerability",
        "dateAdded": "2026-09-01",
        "shortDescription": "A vulnerability with observed exploitation evidence.",
        "requiredAction": "Apply vendor mitigations.",
        "dueDate": "2026-09-22",
        "knownRansomwareCampaignUse": "Unknown",
        "notes": "https://example.com/advisory",
        "cwes": ["CWE-79"],
    }
    document: dict[str, object] = {
        "title": "CISA Known Exploited Vulnerabilities Catalog",
        "catalogVersion": "2026.09.03",
        "dateReleased": "2026-09-03T12:00:00Z",
        "count": 1,
        "vulnerabilities": [record],
    }
    payload = json.dumps(document, separators=(",", ":")).encode()
    return KevCatalogSnapshot(
        raw_bytes=payload,
        catalog_version="2026.09.03",
        date_released=datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
        retrieved_at=datetime(2026, 9, 3, 12, 30, tzinfo=UTC),
        sha256=hashlib.sha256(payload).hexdigest(),
        record_count=1,
    )


def _epss_snapshot(
    *,
    cve_id: str = _CVE_ID,
    epss: float = 0.42,
    percentile: float = 0.88,
):  # type: ignore[no-untyped-def]
    """Build one complete current FIRST EPSS snapshot."""
    text = (
        "#model_version:v2026.06.15,score_date:2026-09-03T12:00:00Z\n"
        "cve,epss,percentile\n"
        f"{cve_id},{epss},{percentile}\n"
    )
    return EpssSnapshotParser().parse(gzip.compress(text.encode(), mtime=0))


def _analysis(
    *,
    version: str = "2.31.0",
    cve_id: str | None = _CVE_ID,
    include_nvd: bool = True,
    include_kev: bool = True,
    epss_cve: str = _CVE_ID,
    epss_score: float = 0.42,
):  # type: ignore[no-untyped-def]
    """Run the complete deterministic Phase 4 evidence chain into the final result."""
    source = _ghsa(cve_id)
    scan = build_repository_pypi_vulnerability_scan(_inventory(version), [source])
    nvd_records = [_nvd_record()] if include_nvd and cve_id is not None else []
    nvd = enrich_repository_findings_with_nvd(scan, [source], nvd_records)
    kev = enrich_repository_findings_with_kev(
        nvd,
        _kev_snapshot(include_cve=include_kev),
    )
    epss = enrich_repository_findings_with_epss(
        kev,
        _epss_snapshot(cve_id=epss_cve, epss=epss_score),
    )
    return build_repository_analysis_result(epss)


def test_final_result_exposes_every_phase4_roadmap_finding_field() -> None:
    """Project dependency, vulnerability, fix, CVSS, KEV, EPSS, and evidence together."""
    result = _analysis()

    assert result.snapshot_id == f"github:{_REPOSITORY_ID}@{_COMMIT_SHA}"
    assert result.file_evidence_id.startswith(f"{result.snapshot_id}:uv.lock@")
    assert result.finding_count == 1

    finding = result.findings[0]
    assert finding.dependency_name == "requests"
    assert finding.dependency_name_original == "Requests"
    assert finding.installed_version == "2.31.0"
    assert finding.installed_version_original == "2.31.0"
    assert finding.purl == "pkg:pypi/requests@2.31.0"
    assert finding.ghsa_id == "GHSA-test-1234"
    assert finding.cve_id == _CVE_ID
    assert finding.vulnerable_range == ">= 2, < 2.32"
    assert [clause.matched for clause in finding.matched_clauses] == [True, True]
    assert finding.fixed_version == "2.32.0"
    assert finding.fixed_version_original == "2.32.0"

    assert [metric.base_score for metric in finding.cvss_metrics] == [9.8, 8.8]
    assert finding.kev_state is RepositoryKevState.PRESENT
    assert finding.kev_record is not None
    assert finding.kev_record.cve == _CVE_ID
    assert finding.epss_state is RepositoryEpssState.SCORE_PRESENT
    assert finding.epss_record is not None
    assert finding.epss_record.epss == 0.42
    assert finding.epss_record.percentile == 0.88
    assert finding.epss_record.snapshot_date.isoformat() == "2026-09-03"

    payload = json.loads(finding.canonical_json)
    assert payload["vulnerability"]["matched_range"] == ">= 2, < 2.32"
    assert payload["vulnerability"]["fixed_version"] == "2.32.0"
    assert len(payload["cvss"]["metrics"]) == 2
    assert payload["kev"]["state"] == "present"
    assert payload["epss"]["state"] == "score_present"
    assert payload["evidence_chain"]["finding_id"].startswith(
        "repository-finding:v1@sha256:"
    )
    assert payload["evidence_chain"]["nvd_enrichment_id"].startswith(
        "repository-finding-enrichment:v1@sha256:"
    )
    assert payload["evidence_chain"]["kev_enrichment_id"].startswith(
        "repository-kev-enrichment:v1@sha256:"
    )
    assert payload["evidence_chain"]["epss_enrichment_id"].startswith(
        "repository-epss-enrichment:v1@sha256:"
    )


def test_final_projection_contains_no_phase5_risk_policy_fields() -> None:
    """Keep score weighting and priority outside the Phase 4 result contract."""
    payload = json.loads(_analysis().canonical_json)
    serialized = json.dumps(payload, sort_keys=True)

    assert "risk_score" not in serialized
    assert "priority" not in serialized
    assert "severity_rank" not in serialized
    assert "runtime_exposure" not in serialized


def test_result_identity_is_deterministic_for_the_same_complete_evidence_chain() -> None:
    """Provide a safe future cache coordinate for identical immutable evidence."""
    first = _analysis()
    repeated = _analysis()

    assert first.canonical_json == repeated.canonical_json
    assert first.evidence_sha256 == repeated.evidence_sha256
    assert first.analysis_id == repeated.analysis_id
    assert first.analysis_id.startswith("repository-analysis:v1@sha256:")
    assert first.findings[0].analysis_finding_id == repeated.findings[0].analysis_finding_id


def test_temporal_epss_change_changes_final_id_without_changing_base_evidence() -> None:
    """Prevent repository-commit-only caching when temporal threat evidence changes."""
    first = _analysis(epss_score=0.42)
    changed = _analysis(epss_score=0.43)

    first_finding = first.findings[0]
    changed_finding = changed.findings[0]
    assert first.snapshot_id == changed.snapshot_id
    assert first.file_evidence_id == changed.file_evidence_id
    assert first_finding.base_finding.finding_id == changed_finding.base_finding.finding_id
    assert (
        first_finding.nvd_enrichment.enrichment_id
        == changed_finding.nvd_enrichment.enrichment_id
    )
    assert (
        first_finding.kev_enrichment.enrichment_id
        == changed_finding.kev_enrichment.enrichment_id
    )
    assert first_finding.evidence.enrichment_id != changed_finding.evidence.enrichment_id
    assert first.analysis_id != changed.analysis_id


def test_zero_finding_result_still_preserves_repository_and_lock_provenance() -> None:
    """Represent a reproducible clean analysis without inventing vulnerability findings."""
    result = _analysis(version="2.32.0")

    assert result.finding_count == 0
    assert result.findings == ()
    assert result.snapshot_id == f"github:{_REPOSITORY_ID}@{_COMMIT_SHA}"
    assert result.file_evidence_id.startswith(f"{result.snapshot_id}:uv.lock@")
    payload = json.loads(result.canonical_json)
    assert payload["accounting"]["affected_finding_count"] == 0
    assert payload["accounting"]["final_finding_count"] == 0
    assert payload["findings"] == []
    assert result.analysis_id.startswith("repository-analysis:v1@sha256:")


def test_missing_cve_remains_explicit_across_final_projection() -> None:
    """Do not fabricate CVE, CVSS, KEV absence, or EPSS absence when GHSA has no CVE."""
    result = _analysis(cve_id=None, include_nvd=False)
    finding = result.findings[0]

    assert finding.cve_id is None
    assert finding.cvss_metrics == ()
    assert finding.kev_state is RepositoryKevState.CVE_UNAVAILABLE
    assert finding.kev_record is None
    assert finding.epss_state is RepositoryEpssState.CVE_UNAVAILABLE
    assert finding.epss_record is None

    payload = json.loads(finding.canonical_json)
    assert payload["vulnerability"]["cve_id"] is None
    assert payload["cvss"]["metrics"] == []
    assert payload["kev"]["state"] == "cve_unavailable"
    assert payload["epss"]["state"] == "cve_unavailable"
