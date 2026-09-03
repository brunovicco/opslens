"""Tests for exact CVE/NVD/CVSS enrichment of affected repository findings."""

from __future__ import annotations

from dataclasses import replace

import pytest

import opslens.repository_intelligence.application.nvd_enrichment as enrichment_module
from opslens.correlation.adapters.ghsa import (
    GhsaPyPIVulnerabilityEvidence,
    GhsaSourceIdentifierEvidence,
)
from opslens.correlation.domain.aliases import CveAliasLinkState
from opslens.repository_intelligence.application import (
    build_repository_pypi_vulnerability_scan,
    enrich_repository_findings_with_nvd,
    normalize_uv_lock_pypi_dependencies,
)
from opslens.repository_intelligence.domain import (
    GitHubRepositoryIdentity,
    ImmutableRepositoryFileEvidence,
    ImmutableRepositorySnapshot,
    InvalidRepositoryNvdEnrichmentError,
    RepositoryNvdCvssEvidence,
    RepositoryNvdEnrichedFinding,
    RepositoryNvdEnrichmentLimitError,
    compute_content_sha256,
    compute_git_blob_sha1,
)
from opslens.repository_intelligence.parsers.uv_lock import parse_uv_lock_evidence
from opslens.transformation.nvd.domain.models import NvdCvssMetrics
from opslens.transformation.nvd.domain.transformer import NvdCveCoreTransformer

_REPOSITORY_ID = 1_333_092_779
_COMMIT_SHA = "439dd29d6298b656374c8a8e053a05b56dff20ec"
_TREE_SHA = "a" * 40
_CVE_ID = "CVE-2026-12345"


def _snapshot() -> ImmutableRepositorySnapshot:
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
    """Bind inert lock bytes to exact repository file evidence."""
    return ImmutableRepositoryFileEvidence(
        snapshot=_snapshot(),
        path="uv.lock",
        blob_sha=compute_git_blob_sha1(content),
        size_bytes=len(content),
        content_sha256=compute_content_sha256(content),
        content_bytes=content,
    )


def _inventory(version: str = "2.31.0"):  # type: ignore[no-untyped-def]
    """Parse and normalize one inert PyPI lock record through the real pipeline."""
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


def _ghsa(
    *,
    cve_id: str | None = _CVE_ID,
    index: int = 0,
    vulnerable_range: str = ">= 2, < 2.32",
    entry_sha: str = "1" * 64,
) -> GhsaPyPIVulnerabilityEvidence:
    """Build exact projected GHSA evidence used by both scan and enrichment."""
    identifiers = (
        (GhsaSourceIdentifierEvidence(identifier_type="CVE", value=cve_id),)
        if cve_id is not None
        else ()
    )
    return GhsaPyPIVulnerabilityEvidence(
        observed_advisory_version_id=f"ghsa-observed-{index}",
        source_advisory_sha256="0" * 64,
        ghsa_id=f"GHSA-test-{index}",
        github_cve_id=cve_id,
        github_identifiers=identifiers,
        vulnerability_entry_id=f"ghsa-entry-{index}",
        source_index=index,
        source_entry_sha256=entry_sha,
        ecosystem_original="pip",
        package_name_original="requests",
        vulnerable_range_original=vulnerable_range,
        first_patched_version_original="2.32",
    )


def _scan(source: GhsaPyPIVulnerabilityEvidence | None = None):  # type: ignore[no-untyped-def]
    """Build one affected repository scan through Gate 4.7."""
    source = source or _ghsa()
    return build_repository_pypi_vulnerability_scan(_inventory(), [source])


def _nvd_source(
    *,
    cve_id: str = _CVE_ID,
    status: str = "Analyzed",
    base_score: float = 9.8,
    include_second_metric: bool = False,
    unsupported_family: bool = False,
    last_modified: str = "2026-09-02T12:00:00.000",
) -> dict[str, object]:
    """Build one complete NVD source object with deterministic CVSS fixtures."""
    metrics: dict[str, object] = {}
    if status != "Rejected":
        v31_metrics: list[object] = [
            {
                "source": "nvd@nist.gov",
                "type": "Primary",
                "cvssData": {
                    "version": "3.1",
                    "vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                    "baseScore": base_score,
                    "baseSeverity": "CRITICAL",
                },
                "exploitabilityScore": 3.9,
                "impactScore": 5.9,
            }
        ]
        if include_second_metric:
            v31_metrics.append(
                {
                    "source": "security@example.com",
                    "type": "Secondary",
                    "cvssData": {
                        "version": "3.1",
                        "vectorString": (
                            "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H"
                        ),
                        "baseScore": 8.8,
                        "baseSeverity": "HIGH",
                    },
                    "exploitabilityScore": 2.8,
                    "impactScore": 5.9,
                }
            )
        metrics["cvssMetricV31"] = v31_metrics
    if unsupported_family:
        metrics["cvssMetricV50"] = []

    source: dict[str, object] = {
        "id": cve_id,
        "sourceIdentifier": "security@example.com",
        "published": "2026-09-01T12:00:00.000",
        "lastModified": last_modified,
        "vulnStatus": status,
    }
    if metrics:
        source["metrics"] = metrics
    return source


def _nvd(**kwargs: object):  # type: ignore[no-untyped-def]
    """Normalize a complete NVD source object through the existing Phase 2 authority."""
    return NvdCveCoreTransformer().transform(_nvd_source(**kwargs))


def test_matching_cve_attaches_exact_nvd_and_cvss_without_changing_finding() -> None:
    """Enrich affected repository risk while leaving Gate 4.7 identity untouched."""
    source = _ghsa()
    scan = _scan(source)
    base_finding_id = scan.findings[0].finding_id
    nvd = _nvd()

    evidence = enrich_repository_findings_with_nvd(scan, [source], [nvd])

    assert evidence.supplied_ghsa_rehydration_count == 1
    assert evidence.supplied_nvd_record_count == 1
    assert evidence.nvd_linked_count == 1
    assert evidence.cvss_metric_count == 1
    enriched = evidence.enriched_findings[0]
    assert enriched.finding.finding_id == base_finding_id
    assert enriched.alias.state is CveAliasLinkState.NVD_OBSERVED
    assert enriched.alias.github_cve_id == _CVE_ID
    assert enriched.nvd_cvss is not None
    assert enriched.nvd_cvss.nvd == nvd
    metric = enriched.nvd_cvss.cvss.metrics[0]
    assert metric.version == "3.1"
    assert metric.base_score == 9.8
    assert metric.base_severity == "CRITICAL"
    assert b'"base_score":9.8' in enriched.canonical_json
    assert enriched.enrichment_id.startswith("repository-finding-enrichment:v1@sha256:")


def test_no_github_cve_preserves_explicit_alias_state_without_nvd_lookup() -> None:
    """Do not infer a CVE or attach unrelated NVD evidence when GitHub asserted none."""
    source = _ghsa(cve_id=None)
    scan = _scan(source)

    evidence = enrich_repository_findings_with_nvd(scan, [source], [_nvd()])

    enriched = evidence.enriched_findings[0]
    assert enriched.alias.state is CveAliasLinkState.NO_GITHUB_CVE
    assert enriched.alias.reason_code == "github_cve_not_asserted"
    assert enriched.nvd_cvss is None
    assert evidence.nvd_linked_count == 0
    assert evidence.cvss_metric_count == 0


def test_github_cve_without_supplied_nvd_stays_github_asserted_only() -> None:
    """Treat missing call input as unsupplied evidence, never as NVD absence."""
    source = _ghsa()
    scan = _scan(source)

    evidence = enrich_repository_findings_with_nvd(scan, [source], [])

    enriched = evidence.enriched_findings[0]
    assert enriched.alias.state is CveAliasLinkState.GITHUB_ASSERTED_ONLY
    assert enriched.alias.reason_code == "nvd_evidence_not_supplied"
    assert enriched.nvd_cvss is None


def test_rejected_nvd_is_preserved_as_rejected_with_exact_source_evidence() -> None:
    """Keep NVD rejection explicit instead of treating the CVE as ordinary observed data."""
    source = _ghsa()
    scan = _scan(source)
    nvd = _nvd(status="Rejected")

    evidence = enrich_repository_findings_with_nvd(scan, [source], [nvd])

    enriched = evidence.enriched_findings[0]
    assert enriched.alias.state is CveAliasLinkState.NVD_REJECTED
    assert enriched.nvd_cvss is not None
    assert enriched.nvd_cvss.nvd.vuln_status.value == "Rejected"
    assert enriched.nvd_cvss.cvss.metrics == ()
    assert evidence.nvd_linked_count == 1
    assert evidence.cvss_metric_count == 0


def test_all_nvd_cvss_metrics_are_preserved_without_preferred_score_selection() -> None:
    """Keep multiple NVD observations as evidence rather than collapsing them to one score."""
    source = _ghsa()
    scan = _scan(source)
    nvd = _nvd(include_second_metric=True)

    evidence = enrich_repository_findings_with_nvd(scan, [source], [nvd])

    enriched = evidence.enriched_findings[0]
    assert enriched.nvd_cvss is not None
    metrics = enriched.nvd_cvss.cvss.metrics
    assert len(metrics) == 2
    assert [metric.metric_type.value for metric in metrics] == ["Primary", "Secondary"]
    assert [metric.base_score for metric in metrics] == [9.8, 8.8]
    assert evidence.cvss_metric_count == 2


def test_future_nvd_cvss_family_is_preserved_as_unsupported_evidence() -> None:
    """Expose future CVSS families without fabricating typed metric values."""
    source = _ghsa()
    scan = _scan(source)
    nvd = _nvd(unsupported_family=True)

    evidence = enrich_repository_findings_with_nvd(scan, [source], [nvd])

    nvd_cvss = evidence.enriched_findings[0].nvd_cvss
    assert nvd_cvss is not None
    assert nvd_cvss.cvss.unsupported_cvss_families == ("cvssMetricV50",)
    assert b'"unsupported_cvss_families":["cvssMetricV50"]' in (
        evidence.enriched_findings[0].canonical_json
    )


def test_duplicate_nvd_observations_for_same_cve_fail_without_latest_selection() -> None:
    """Reject ambiguous NVD versions rather than selecting one by timestamp or order."""
    source = _ghsa()
    scan = _scan(source)
    first = _nvd(last_modified="2026-09-02T12:00:00.000")
    second = _nvd(last_modified="2026-09-03T12:00:00.000")

    with pytest.raises(InvalidRepositoryNvdEnrichmentError):
        enrich_repository_findings_with_nvd(scan, [source], [first, second])


def test_missing_exact_ghsa_rehydration_source_fails_closed() -> None:
    """Require the exact GHSA occurrence before recovering its CVE assertion."""
    source = _ghsa()
    scan = _scan(source)

    with pytest.raises(InvalidRepositoryNvdEnrichmentError):
        enrich_repository_findings_with_nvd(scan, [], [_nvd()])


def test_changed_ghsa_source_hash_cannot_rebind_to_existing_finding() -> None:
    """Prevent identifier evidence from a different GHSA content occurrence being attached."""
    source = _ghsa(entry_sha="1" * 64)
    scan = _scan(source)
    changed = replace(source, source_entry_sha256="2" * 64)

    with pytest.raises(InvalidRepositoryNvdEnrichmentError):
        enrich_repository_findings_with_nvd(scan, [changed], [_nvd()])


def test_duplicate_ghsa_rehydration_occurrence_fails_closed() -> None:
    """Reject ambiguous repeated source-local occurrence identities."""
    source = _ghsa()
    scan = _scan(source)

    with pytest.raises(InvalidRepositoryNvdEnrichmentError):
        enrich_repository_findings_with_nvd(scan, [source, source], [_nvd()])


def test_unrelated_nvd_cve_does_not_link_to_github_assertion() -> None:
    """Join NVD only by the exact GitHub CVE assertion."""
    source = _ghsa()
    scan = _scan(source)
    unrelated = _nvd(cve_id="CVE-2026-99999")

    evidence = enrich_repository_findings_with_nvd(scan, [source], [unrelated])

    enriched = evidence.enriched_findings[0]
    assert enriched.alias.state is CveAliasLinkState.GITHUB_ASSERTED_ONLY
    assert enriched.nvd_cvss is None


def test_detached_cvss_evidence_is_rejected_by_domain_model() -> None:
    """Prevent CVSS normalized from another source from being paired with this NVD version."""
    nvd = _nvd()

    with pytest.raises(InvalidRepositoryNvdEnrichmentError):
        RepositoryNvdCvssEvidence(
            nvd=nvd,
            cvss=NvdCvssMetrics(metrics=(), unsupported_cvss_families=()),
        )


def test_enriched_model_rejects_alias_from_different_ghsa_occurrence() -> None:
    """Keep the enrichment alias bound to the exact Gate 4.7 affected occurrence."""
    source = _ghsa()
    scan = _scan(source)
    evidence = enrich_repository_findings_with_nvd(scan, [source], [_nvd()])
    enriched = evidence.enriched_findings[0]
    changed_alias = replace(enriched.alias, ghsa_id="GHSA-other")

    with pytest.raises(InvalidRepositoryNvdEnrichmentError):
        RepositoryNvdEnrichedFinding(
            finding=enriched.finding,
            alias=changed_alias,
            nvd_cvss=enriched.nvd_cvss,
        )


def test_enrichment_id_is_deterministic_and_commits_to_exact_nvd_version() -> None:
    """Change enrichment identity when immutable NVD source content changes."""
    source = _ghsa()
    scan = _scan(source)
    first_nvd = _nvd(last_modified="2026-09-02T12:00:00.000")
    changed_nvd = _nvd(last_modified="2026-09-03T12:00:00.000")

    first = enrich_repository_findings_with_nvd(scan, [source], [first_nvd])
    repeated = enrich_repository_findings_with_nvd(scan, [source], [first_nvd])
    changed = enrich_repository_findings_with_nvd(scan, [source], [changed_nvd])

    assert first.enriched_findings[0].enrichment_id == (
        repeated.enriched_findings[0].enrichment_id
    )
    assert first.enriched_findings[0].enrichment_id != (
        changed.enriched_findings[0].enrichment_id
    )
    assert first.enriched_findings[0].finding.finding_id == (
        changed.enriched_findings[0].finding.finding_id
    )


def test_no_affected_findings_produces_empty_enrichment_without_invented_risk() -> None:
    """Never create enriched risk evidence for a Gate 4.7 not-affected assessment."""
    source = _ghsa()
    scan = build_repository_pypi_vulnerability_scan(_inventory("2.32.0"), [source])
    assert scan.findings == ()

    evidence = enrich_repository_findings_with_nvd(scan, [source], [_nvd()])

    assert evidence.enriched_findings == ()
    assert evidence.nvd_linked_count == 0
    assert evidence.cvss_metric_count == 0


def test_nvd_input_bound_fails_without_truncation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail closed when supplied NVD observations exceed the application hard bound."""
    monkeypatch.setattr(enrichment_module, "MAX_NVD_ENRICHMENT_RECORDS", 1)
    source = _ghsa()
    scan = _scan(source)

    with pytest.raises(RepositoryNvdEnrichmentLimitError):
        enrich_repository_findings_with_nvd(
            scan,
            [source],
            [_nvd(), _nvd(cve_id="CVE-2026-99999")],
        )


def test_ghsa_rehydration_bound_fails_without_truncation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail closed when GHSA rehydration evidence exceeds the existing source bound."""
    monkeypatch.setattr(enrichment_module, "MAX_GHSA_VULNERABILITY_OCCURRENCES", 1)
    source = _ghsa()
    scan = _scan(source)
    unrelated = _ghsa(index=1, cve_id="CVE-2026-99999")

    with pytest.raises(RepositoryNvdEnrichmentLimitError):
        enrich_repository_findings_with_nvd(scan, [source, unrelated], [_nvd()])
