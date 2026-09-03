"""Integration tests from validated Phase 4 evidence into Risk Policy v1."""

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
    compute_content_sha256,
    compute_git_blob_sha1,
)
from opslens.repository_intelligence.parsers.uv_lock import parse_uv_lock_evidence
from opslens.risk_policy.application import (
    build_risk_finding_input,
    prioritize_repository_analysis,
)
from opslens.risk_policy.domain import (
    RiskEvidenceCompleteness,
    RiskEpssState,
    RiskKevState,
    RiskPriorityTier,
)
from opslens.transformation.nvd.domain.transformer import NvdCveCoreTransformer

_REPOSITORY_ID = 1_333_092_779
_COMMIT_SHA = "164b936e1c27b14b6fdf3a9484f7ae0772c076a3"
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


def _inventory():  # type: ignore[no-untyped-def]
    """Build normalized inert PyPI dependency evidence."""
    content = (
        "version = 1\n"
        "revision = 3\n"
        'requires-python = ">=3.13"\n'
        "[[package]]\n"
        'name = "Requests"\n'
        'version = "2.31.0"\n'
        'source = { registry = "https://pypi.org/simple" }\n'
    ).encode()
    evidence = ImmutableRepositoryFileEvidence(
        snapshot=_repository_snapshot(),
        path="uv.lock",
        blob_sha=compute_git_blob_sha1(content),
        size_bytes=len(content),
        content_sha256=compute_content_sha256(content),
        content_bytes=content,
    )
    return normalize_uv_lock_pypi_dependencies(parse_uv_lock_evidence(evidence))


def _ghsa(
    *,
    cve_id: str | None = _CVE_ID,
    fixed_version: str | None = "2.32.0",
) -> GhsaPyPIVulnerabilityEvidence:
    """Build one exact affected GHSA PyPI occurrence."""
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
        first_patched_version_original=fixed_version,
    )


def _nvd_record(cvss_score: float = 9.8):  # type: ignore[no-untyped-def]
    """Build exact NVD evidence through the existing transformer."""
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
                        "baseScore": cvss_score,
                        "baseSeverity": "CRITICAL" if cvss_score >= 9.0 else "HIGH",
                    },
                    "exploitabilityScore": 3.9,
                    "impactScore": 5.9,
                }
            ]
        },
    }
    return NvdCveCoreTransformer().transform(source)


def _kev_snapshot(*, include_cve: bool = True) -> KevCatalogSnapshot:
    """Build one complete immutable KEV catalog snapshot."""
    cve_id = _CVE_ID if include_cve else "CVE-2026-99999"
    record: dict[str, object] = {
        "cveID": cve_id,
        "vendorProject": "Example Vendor",
        "product": "Example Product",
        "vulnerabilityName": "Example Known Exploited Vulnerability",
        "dateAdded": "2026-09-01",
        "shortDescription": "Observed exploitation evidence.",
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


def _epss_snapshot(*, cve_id: str = _CVE_ID, score: float = 0.42):  # type: ignore[no-untyped-def]
    """Build one complete current FIRST EPSS snapshot."""
    text = (
        "#model_version:v2026.06.15,score_date:2026-09-03T12:00:00Z\n"
        "cve,epss,percentile\n"
        f"{cve_id},{score},0.88\n"
    )
    return EpssSnapshotParser().parse(gzip.compress(text.encode(), mtime=0))


def _analysis(
    *,
    cve_id: str | None = _CVE_ID,
    fixed_version: str | None = "2.32.0",
    include_nvd: bool = True,
    include_kev: bool = True,
    epss_cve: str = _CVE_ID,
    epss_score: float = 0.42,
):  # type: ignore[no-untyped-def]
    """Run the complete Phase 4 chain into one final repository analysis."""
    source = _ghsa(cve_id=cve_id, fixed_version=fixed_version)
    scan = build_repository_pypi_vulnerability_scan(_inventory(), [source])
    nvd_records = [_nvd_record()] if include_nvd and cve_id is not None else []
    nvd = enrich_repository_findings_with_nvd(scan, [source], nvd_records)
    kev = enrich_repository_findings_with_kev(
        nvd,
        _kev_snapshot(include_cve=include_kev),
    )
    epss = enrich_repository_findings_with_epss(
        kev,
        _epss_snapshot(cve_id=epss_cve, score=epss_score),
    )
    return build_repository_analysis_result(epss)


def test_bridge_extracts_only_authorized_phase4_policy_facts() -> None:
    """The Phase 5 bridge reuses exact Phase 4 facts without reinterpretation."""
    analysis = _analysis()
    finding = analysis.findings[0]
    source = build_risk_finding_input(finding)

    assert source.analysis_finding_id == finding.analysis_finding_id
    assert source.source_evidence_sha256 == finding.evidence_sha256
    assert source.kev_state is RiskKevState.PRESENT
    assert source.epss_state is RiskEpssState.SCORE_PRESENT
    assert source.epss_score == 0.42
    assert source.cvss_base_scores == (9.8,)
    assert source.unsupported_cvss_families == ()
    assert source.fixed_version_available is True


def test_repository_analysis_is_prioritized_with_versioned_factor_evidence() -> None:
    """One Phase 4 finding becomes one content-addressed Phase 5 priority evaluation."""
    analysis = _analysis()
    result = prioritize_repository_analysis(analysis)
    ranked = result.ranked_findings[0]
    evaluation = ranked.evaluation

    assert result.source_analysis_id == analysis.analysis_id
    assert result.source_analysis_sha256 == analysis.evidence_sha256
    assert len(result.evaluations) == 1
    assert ranked.rank == 1
    assert evaluation.priority_score == 90
    assert evaluation.priority_tier is RiskPriorityTier.P0
    assert evaluation.evidence_completeness is RiskEvidenceCompleteness.COMPLETE
    assert evaluation.review_required is False
    assert [factor.points for factor in evaluation.factors] == [40, 20, 20, 10]


def test_complete_negative_kev_and_low_epss_reduce_priority_deterministically() -> None:
    """Changing source-backed factors changes score without changing applicability truth."""
    analysis = _analysis(include_kev=False, epss_score=0.09)
    evaluation = prioritize_repository_analysis(analysis).evaluations[0]

    assert evaluation.priority_score == 30
    assert evaluation.priority_tier is RiskPriorityTier.P2
    assert evaluation.evidence_completeness is RiskEvidenceCompleteness.COMPLETE
    assert [factor.points for factor in evaluation.factors] == [0, 0, 20, 10]


def test_missing_cve_and_nvd_evidence_requires_review_instead_of_low_risk_claim() -> None:
    """Source gaps remain explicit and are never converted into negative threat evidence."""
    analysis = _analysis(cve_id=None, include_nvd=False)
    evaluation = prioritize_repository_analysis(analysis).evaluations[0]

    assert evaluation.priority_score == 10
    assert evaluation.priority_tier is RiskPriorityTier.P3
    assert evaluation.evidence_completeness is RiskEvidenceCompleteness.PARTIAL
    assert evaluation.review_required is True
    assert evaluation.factors[0].reason_code == "kev_cve_unavailable"
    assert evaluation.factors[1].reason_code == "epss_cve_unavailable"
    assert evaluation.factors[2].reason_code == "cvss_unavailable"


def test_priority_result_is_reproducible_for_identical_phase4_analysis() -> None:
    """Same immutable analysis and policy reproduce the same prioritization identity."""
    analysis = _analysis()
    first = prioritize_repository_analysis(analysis)
    second = prioritize_repository_analysis(analysis)

    assert first.canonical_json == second.canonical_json
    assert first.prioritization_id == second.prioritization_id
