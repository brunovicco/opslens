"""Tests for exact current and historical EPSS enrichment of repository findings."""

from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import replace
from datetime import UTC, date, datetime

import pytest

import opslens.repository_intelligence.domain.epss_enrichment as epss_domain
from opslens.correlation.adapters.ghsa import (
    GhsaPyPIVulnerabilityEvidence,
    GhsaSourceIdentifierEvidence,
)
from opslens.ingestion.epss.domain.history import HistoricalEpssSnapshotParser
from opslens.ingestion.epss.domain.parser import EpssSnapshotParser
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.repository_intelligence.application import (
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
    InvalidRepositoryEpssEnrichmentError,
    RepositoryEpssEnrichedFinding,
    RepositoryEpssEnrichmentLimitError,
    RepositoryEpssSnapshotKind,
    RepositoryEpssState,
    RepositoryKevEnrichmentEvidence,
    RepositoryKevState,
    RepositoryPyPINormalizationInventory,
    RepositoryVulnerabilityScanEvidence,
    compute_content_sha256,
    compute_git_blob_sha1,
)
from opslens.repository_intelligence.parsers.uv_lock import parse_uv_lock_evidence

_REPOSITORY_ID = 1_333_092_779
_COMMIT_SHA = "68194737c1fc8ff25441128ee610e8f565811745"
_TREE_SHA = "a" * 40
_CVE_ID = "CVE-2026-12345"


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


def _scan(
    source: GhsaPyPIVulnerabilityEvidence,
    *,
    version: str = "2.31.0",
) -> RepositoryVulnerabilityScanEvidence:
    """Build Gate 4.7 repository evidence through the real correlation path."""
    return build_repository_pypi_vulnerability_scan(_inventory(version), [source])


def _kev_snapshot() -> KevCatalogSnapshot:
    """Build a complete KEV snapshot that intentionally does not contain the test CVE."""
    record: dict[str, object] = {
        "cveID": "CVE-2026-99999",
        "vendorProject": "Example Vendor",
        "product": "Example Product",
        "vulnerabilityName": "Example Vulnerability",
        "dateAdded": "2026-09-01",
        "shortDescription": "A vulnerability affecting an unrelated product.",
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


def _previous(
    cve_id: str | None = _CVE_ID,
    *,
    version: str = "2.31.0",
) -> RepositoryKevEnrichmentEvidence:
    """Build the complete Gate 4.9 evidence chain without NVD observations."""
    source = _ghsa(cve_id)
    nvd = enrich_repository_findings_with_nvd(
        _scan(source, version=version),
        [source],
        [],
    )
    return enrich_repository_findings_with_kev(nvd, _kev_snapshot())


def _current_epss_snapshot(
    *,
    cve_id: str = _CVE_ID,
    epss: float = 0.42,
    percentile: float = 0.88,
):  # type: ignore[no-untyped-def]
    """Build one complete modern EPSS gzip snapshot through the Phase 2 parser."""
    text = (
        "#model_version:v2026.06.15,score_date:2026-09-03T12:00:00Z\n"
        "cve,epss,percentile\n"
        f"{cve_id},{epss},{percentile}\n"
    )
    return EpssSnapshotParser().parse(gzip.compress(text.encode(), mtime=0))


def _historical_v1_snapshot(
    *,
    snapshot_date: date = date(2021, 4, 14),
    cve_id: str = _CVE_ID,
    epss: float = 0.12,
):  # type: ignore[no-untyped-def]
    """Build metadata-free two-column EPSS v1 evidence through the history parser."""
    text = f"cve,epss\n{cve_id},{epss}\n"
    payload = gzip.compress(text.encode(), mtime=0)
    return HistoricalEpssSnapshotParser().parse(
        payload,
        snapshot_date=snapshot_date,
    )


def test_current_snapshot_attaches_exact_score_without_changing_prior_evidence() -> None:
    """Attach modern EPSS evidence even when KEV and NVD did not observe the CVE."""
    previous = _previous()
    assert previous.enriched_findings[0].state is RepositoryKevState.ABSENT
    assert previous.enriched_findings[0].previous.nvd_cvss is None
    previous_id = previous.enriched_findings[0].enrichment_id

    evidence = enrich_repository_findings_with_epss(
        previous,
        _current_epss_snapshot(),
    )

    assert evidence.score_present_count == 1
    assert evidence.score_absent_count == 0
    enriched = evidence.enriched_findings[0]
    assert enriched.previous.enrichment_id == previous_id
    assert enriched.state is RepositoryEpssState.SCORE_PRESENT
    assert enriched.evaluated_cve_id == _CVE_ID
    assert enriched.epss_snapshot.kind is RepositoryEpssSnapshotKind.CURRENT
    assert enriched.epss_record is not None
    assert enriched.epss_record.epss == 0.42
    assert enriched.epss_record.percentile == 0.88
    assert enriched.epss_record.model_version == "v2026.06.15"
    assert b'"epss_state":"score_present"' in enriched.canonical_json
    assert enriched.enrichment_id.startswith("repository-epss-enrichment:v1@sha256:")


def test_complete_current_snapshot_can_prove_score_absence() -> None:
    """Emit score_absent only after a different complete EPSS snapshot is validated."""
    previous = _previous()
    snapshot = _current_epss_snapshot(cve_id="CVE-2026-99999")

    evidence = enrich_repository_findings_with_epss(previous, snapshot)

    enriched = evidence.enriched_findings[0]
    assert enriched.state is RepositoryEpssState.SCORE_ABSENT
    assert enriched.epss_record is None
    assert evidence.score_present_count == 0
    assert evidence.score_absent_count == 1


def test_missing_github_cve_is_unavailable_not_score_absent() -> None:
    """Never convert missing CVE identity into negative EPSS score evidence."""
    previous = _previous(cve_id=None)

    evidence = enrich_repository_findings_with_epss(
        previous,
        _current_epss_snapshot(),
    )

    enriched = evidence.enriched_findings[0]
    assert enriched.state is RepositoryEpssState.CVE_UNAVAILABLE
    assert enriched.evaluated_cve_id is None
    assert enriched.epss_record is None
    assert evidence.score_absent_count == 0
    assert evidence.cve_unavailable_count == 1


def test_historical_v1_preserves_missing_metadata_and_percentile() -> None:
    """Keep legacy EPSS v1 source absences explicit rather than fabricating modern fields."""
    previous = _previous()
    snapshot = _historical_v1_snapshot()

    evidence = enrich_repository_findings_with_epss(previous, snapshot)

    enriched = evidence.enriched_findings[0]
    assert enriched.state is RepositoryEpssState.SCORE_PRESENT
    assert enriched.epss_snapshot.kind is RepositoryEpssSnapshotKind.HISTORICAL
    assert enriched.epss_snapshot.snapshot_date == date(2021, 4, 14)
    assert enriched.epss_snapshot.model_version is None
    assert enriched.epss_snapshot.score_timestamp is None
    assert enriched.epss_record is not None
    assert enriched.epss_record.epss == 0.12
    assert enriched.epss_record.percentile is None
    assert enriched.epss_record.model_version is None
    assert enriched.epss_record.score_timestamp is None
    assert b'"model_era":"v1"' in enriched.canonical_json
    assert b'"source_metadata_present":false' in enriched.canonical_json


def test_historical_v1_archive_date_is_part_of_enrichment_identity() -> None:
    """Commit to external archive date when legacy source bytes contain no score_date."""
    previous = _previous()
    first = enrich_repository_findings_with_epss(
        previous,
        _historical_v1_snapshot(snapshot_date=date(2021, 4, 14)),
    )
    next_day = enrich_repository_findings_with_epss(
        previous,
        _historical_v1_snapshot(snapshot_date=date(2021, 4, 15)),
    )

    first_finding = first.enriched_findings[0]
    next_finding = next_day.enriched_findings[0]
    assert first.epss_snapshot.snapshot.raw_bytes == next_day.epss_snapshot.snapshot.raw_bytes
    assert first_finding.enrichment_id != next_finding.enrichment_id
    assert first_finding.epss_record is not None
    assert next_finding.epss_record is not None
    assert first_finding.epss_record.score_timestamp is None
    assert next_finding.epss_record.score_timestamp is None


def test_tampered_snapshot_sha_fails_before_score_lookup() -> None:
    """Reject EPSS metadata whose digest no longer authenticates exact source bytes."""
    previous = _previous()
    snapshot = replace(_current_epss_snapshot(), sha256="0" * 64)

    with pytest.raises(InvalidRepositoryEpssEnrichmentError):
        enrich_repository_findings_with_epss(previous, snapshot)


def test_changed_snapshot_metadata_fails_reparse_identity_check() -> None:
    """Reject typed metadata that disagrees with metadata inside immutable EPSS bytes."""
    previous = _previous()
    snapshot = replace(_current_epss_snapshot(), model_version="v2099.01.01")

    with pytest.raises(InvalidRepositoryEpssEnrichmentError):
        enrich_repository_findings_with_epss(previous, snapshot)


def test_record_bound_fails_before_complete_snapshot_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bound EPSS transformation without truncating source evidence."""
    previous = _previous()
    snapshot = _current_epss_snapshot()
    monkeypatch.setattr(epss_domain, "MAX_EPSS_ENRICHMENT_RECORDS", 0)

    with pytest.raises(RepositoryEpssEnrichmentLimitError):
        enrich_repository_findings_with_epss(previous, snapshot)


def test_source_byte_bound_fails_before_complete_snapshot_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bound compressed EPSS bytes independently from row count."""
    previous = _previous()
    snapshot = _current_epss_snapshot()
    monkeypatch.setattr(epss_domain, "MAX_EPSS_ENRICHMENT_BYTES", 1)

    with pytest.raises(RepositoryEpssEnrichmentLimitError):
        enrich_repository_findings_with_epss(previous, snapshot)


def test_domain_rejects_state_that_disagrees_with_complete_snapshot() -> None:
    """Prevent callers from relabeling a positive EPSS observation as score absence."""
    evidence = enrich_repository_findings_with_epss(
        _previous(),
        _current_epss_snapshot(),
    )
    enriched = evidence.enriched_findings[0]

    with pytest.raises(InvalidRepositoryEpssEnrichmentError):
        RepositoryEpssEnrichedFinding(
            previous=enriched.previous,
            epss_snapshot=enriched.epss_snapshot,
            state=RepositoryEpssState.SCORE_ABSENT,
            epss_record=None,
        )


def test_enrichment_id_is_deterministic_and_commits_to_score_observation() -> None:
    """Change enrichment identity when the selected EPSS score evidence changes."""
    previous = _previous()
    first_snapshot = _current_epss_snapshot(epss=0.42)
    changed_snapshot = _current_epss_snapshot(epss=0.43)

    first = enrich_repository_findings_with_epss(previous, first_snapshot)
    repeated = enrich_repository_findings_with_epss(previous, first_snapshot)
    changed = enrich_repository_findings_with_epss(previous, changed_snapshot)

    first_finding = first.enriched_findings[0]
    repeated_finding = repeated.enriched_findings[0]
    changed_finding = changed.enriched_findings[0]
    assert first_finding.enrichment_id == repeated_finding.enrichment_id
    assert first_finding.enrichment_id != changed_finding.enrichment_id
    assert first_finding.previous.enrichment_id == changed_finding.previous.enrichment_id


def test_no_affected_findings_remains_empty_without_invented_epss_risk() -> None:
    """Do not create EPSS evidence when the deterministic applicability gate found nothing."""
    previous = _previous(version="2.32.0")
    assert previous.enriched_findings == ()

    evidence = enrich_repository_findings_with_epss(
        previous,
        _current_epss_snapshot(),
    )

    assert evidence.enriched_findings == ()
    assert evidence.score_present_count == 0
    assert evidence.score_absent_count == 0
    assert evidence.cve_unavailable_count == 0
