"""Tests for Gate 19.2 cross-source threat-evidence admission."""

import gzip
import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import cast

import pytest

from opslens.correlation.adapters.ghsa import (
    GhsaPyPIVulnerabilityEvidence,
    GhsaSourceIdentifierEvidence,
)
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.epss.domain.parser import EpssSnapshotParser
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.public_analysis.application.representative_threat_evidence_admission import (
    RepresentativeThreatEvidenceAdmissionError,
    RepresentativeThreatEvidenceAuthority,
    admit_representative_threat_evidence,
)
from opslens.repository_intelligence.domain.epss_enrichment import (
    RepositoryEpssSnapshotEvidence,
)
from opslens.transformation.nvd.domain.models import NvdCveCoreRecord
from opslens.transformation.nvd.domain.transformer import NvdCveCoreTransformer

_CVE_ID = "CVE-2026-54770"
_OBSERVED_GHSA = "GHSA-6hx8-3wjj-gr8g@sha256:" + "a" * 64
_GHSA_SHA = "a" * 64
_ENTRY_SHA = "b" * 64
_ENTRY_ID = "GHSA-6hx8-3wjj-gr8g:vulnerability:0"


def _ghsa() -> GhsaPyPIVulnerabilityEvidence:
    """Build one exact typed PyPI GHSA occurrence."""
    return GhsaPyPIVulnerabilityEvidence(
        observed_advisory_version_id=_OBSERVED_GHSA,
        source_advisory_sha256=_GHSA_SHA,
        ghsa_id="GHSA-6hx8-3wjj-gr8g",
        github_cve_id=_CVE_ID,
        github_identifiers=(
            GhsaSourceIdentifierEvidence(identifier_type="CVE", value=_CVE_ID),
        ),
        vulnerability_entry_id=_ENTRY_ID,
        source_index=0,
        source_entry_sha256=_ENTRY_SHA,
        ecosystem_original="pip",
        package_name_original="webob",
        vulnerable_range_original="< 1.8.11",
        first_patched_version_original="1.8.11",
    )


def _nvd() -> NvdCveCoreRecord:
    """Build exact NVD identity through the retained transformer."""
    source: dict[str, object] = {
        "id": _CVE_ID,
        "sourceIdentifier": "security@example.com",
        "published": "2026-09-01T12:00:00.000",
        "lastModified": "2026-09-03T12:00:00.000",
        "vulnStatus": "Analyzed",
    }
    return NvdCveCoreTransformer().transform(source)


def _kev_snapshot() -> KevCatalogSnapshot:
    """Build one complete KEV snapshot proving selected-CVE absence."""
    other_cve: dict[str, object] = {
        "cveID": "CVE-2026-99999",
        "vendorProject": "Example Vendor",
        "product": "Example Product",
        "vulnerabilityName": "Example vulnerability",
        "dateAdded": "2026-09-01",
        "shortDescription": "Example description.",
        "requiredAction": "Apply mitigations.",
        "dueDate": "2026-09-22",
        "knownRansomwareCampaignUse": "Unknown",
        "notes": "https://example.com/advisory",
        "cwes": ["CWE-79"],
    }
    document: dict[str, object] = {
        "title": "CISA Known Exploited Vulnerabilities Catalog",
        "catalogVersion": "2026.09.10",
        "dateReleased": "2026-09-10T12:00:00Z",
        "count": 1,
        "vulnerabilities": [other_cve],
    }
    payload = json.dumps(document, separators=(",", ":")).encode()
    return KevCatalogSnapshot(
        raw_bytes=payload,
        catalog_version="2026.09.10",
        date_released=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        retrieved_at=datetime(2026, 9, 10, 12, 30, tzinfo=UTC),
        sha256=hashlib.sha256(payload).hexdigest(),
        record_count=1,
    )


def _epss_snapshot() -> EpssSnapshot:
    """Build one complete EPSS snapshot containing the selected CVE."""
    text = (
        "#model_version:v2026.09.01,score_date:2026-09-10T12:00:00Z\n"
        "cve,epss,percentile\n"
        f"{_CVE_ID},0.00339,0.26988\n"
    )
    return EpssSnapshotParser().parse(gzip.compress(text.encode(), mtime=0))


def _authority() -> RepresentativeThreatEvidenceAuthority:
    """Build exact typed authority independently of the analytical bundle."""
    return RepresentativeThreatEvidenceAuthority(
        ghsa_vulnerabilities=(_ghsa(),),
        nvd_records=(_nvd(),),
        kev_snapshot=_kev_snapshot(),
        epss_snapshot=_epss_snapshot(),
    )


def _bundle() -> dict[str, object]:
    """Build one CrossSourceCveEvidenceV1-shaped analytical proof."""
    nvd = _nvd()
    epss_evidence = RepositoryEpssSnapshotEvidence(_epss_snapshot())
    epss_record = epss_evidence.record_for_cve(_CVE_ID)
    assert epss_record is not None

    return {
        "schema_version": 1,
        "bundle_type": "CrossSourceCveEvidenceV1",
        "read_only": True,
        "cve_id": _CVE_ID,
        "nvd": {
            "exists": True,
            "observation_count": 1,
            "observations": [
                {
                    "cve_id": _CVE_ID,
                    "observed_cve_version_id": (
                        nvd.observed_version.observed_cve_version_id
                    ),
                    "published_at": nvd.published_at.isoformat(),
                    "last_modified_at": nvd.last_modified_at.isoformat(),
                    "vuln_status": nvd.vuln_status.value,
                }
            ],
        },
        "kev": {
            "snapshot_date": "2026-09-10",
            "is_kev": False,
            "entry": None,
            "absence_semantics": "not present in the selected KEV snapshot",
        },
        "epss": {
            "snapshot_date": "2026-09-10",
            "evidence_present": True,
            "score": {
                "cve": _CVE_ID,
                "epss": epss_record.epss,
                "percentile": epss_record.percentile,
                "model_version": epss_record.model_version,
                "score_timestamp": (
                    epss_record.score_timestamp.isoformat()
                    if epss_record.score_timestamp is not None
                    else None
                ),
                "source": epss_record.source,
                "source_sha256": epss_record.source_sha256,
            },
        },
        "ghsa": {
            "advisory_version_count": 1,
            "vulnerability_entry_count": 1,
            "advisory_versions": [
                {
                    "ghsa_id": "GHSA-6hx8-3wjj-gr8g",
                    "observed_advisory_version_id": _OBSERVED_GHSA,
                    "source_advisory_sha256": _GHSA_SHA,
                    "cve_id": _CVE_ID,
                    "package_evidence": [
                        {
                            "source_index": 0,
                            "vulnerability_entry_id": _ENTRY_ID,
                            "source_entry_sha256": _ENTRY_SHA,
                            "ecosystem": "pip",
                            "package_name": "webob",
                            "vulnerable_version_range": "< 1.8.11",
                            "first_patched_version": "1.8.11",
                            "range_evaluation_performed": False,
                        }
                    ],
                }
            ],
        },
    }


def test_admit_representative_threat_evidence_preserves_typed_authority() -> None:
    """Return the exact supplied typed objects only after all checks agree."""
    authority = _authority()
    admitted = admit_representative_threat_evidence(_bundle(), authority=authority)

    assert admitted.ghsa_vulnerabilities == authority.ghsa_vulnerabilities
    assert admitted.nvd_records == authority.nvd_records
    assert admitted.kev_snapshot == authority.kev_snapshot
    assert admitted.epss_snapshot == authority.epss_snapshot


def test_admission_rejects_kev_absence_when_complete_snapshot_contains_cve() -> None:
    """Do not turn one analytical KEV absence into empty-snapshot authority."""
    bundle = _bundle()
    document = cast(dict[str, object], json.loads(_kev_snapshot().raw_bytes))
    vulnerabilities = cast(
        list[dict[str, object]],
        document["vulnerabilities"],
    )
    vulnerabilities[0]["cveID"] = _CVE_ID
    payload = json.dumps(document, separators=(",", ":")).encode()
    authority = _authority()
    contradictory = RepresentativeThreatEvidenceAuthority(
        ghsa_vulnerabilities=authority.ghsa_vulnerabilities,
        nvd_records=authority.nvd_records,
        kev_snapshot=KevCatalogSnapshot(
            raw_bytes=payload,
            catalog_version="2026.09.10",
            date_released=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
            retrieved_at=datetime(2026, 9, 10, 12, 30, tzinfo=UTC),
            sha256=hashlib.sha256(payload).hexdigest(),
            record_count=1,
        ),
        epss_snapshot=authority.epss_snapshot,
    )

    with pytest.raises(
        RepresentativeThreatEvidenceAdmissionError,
        match="KEV membership contradicts",
    ):
        admit_representative_threat_evidence(bundle, authority=contradictory)


def test_admission_rejects_epss_score_drift() -> None:
    """Reject analytical EPSS values that disagree with the complete snapshot."""
    bundle = deepcopy(_bundle())
    epss = cast(dict[str, object], bundle["epss"])
    score = cast(dict[str, object], epss["score"])
    score["epss"] = 0.9

    with pytest.raises(
        RepresentativeThreatEvidenceAdmissionError,
        match="EPSS score mismatch",
    ):
        admit_representative_threat_evidence(bundle, authority=_authority())


def test_admission_rejects_nvd_observed_identity_drift() -> None:
    """Reject NVD projections not bound to the supplied exact observed version."""
    bundle = deepcopy(_bundle())
    nvd = cast(dict[str, object], bundle["nvd"])
    observations = cast(list[dict[str, object]], nvd["observations"])
    observations[0]["observed_cve_version_id"] = _CVE_ID + "@sha256:" + "f" * 64

    with pytest.raises(
        RepresentativeThreatEvidenceAdmissionError,
        match="typed NVD record is not present",
    ):
        admit_representative_threat_evidence(bundle, authority=_authority())


def test_admission_rejects_non_pip_ghsa_package_evidence() -> None:
    """Keep the representative repository bridge bounded to the PyPI ecosystem."""
    bundle = deepcopy(_bundle())
    ghsa = cast(dict[str, object], bundle["ghsa"])
    versions = cast(list[dict[str, object]], ghsa["advisory_versions"])
    packages = cast(list[dict[str, object]], versions[0]["package_evidence"])
    packages[0]["ecosystem"] = "npm"

    with pytest.raises(
        RepresentativeThreatEvidenceAdmissionError,
        match="must use the pip ecosystem",
    ):
        admit_representative_threat_evidence(bundle, authority=_authority())


def test_admission_rejects_pre_evaluated_ghsa_range() -> None:
    """Leave installed-version applicability exclusively to retained correlation."""
    bundle = deepcopy(_bundle())
    ghsa = cast(dict[str, object], bundle["ghsa"])
    versions = cast(list[dict[str, object]], ghsa["advisory_versions"])
    packages = cast(list[dict[str, object]], versions[0]["package_evidence"])
    packages[0]["range_evaluation_performed"] = True

    with pytest.raises(
        RepresentativeThreatEvidenceAdmissionError,
        match="must not pre-evaluate vulnerable ranges",
    ):
        admit_representative_threat_evidence(bundle, authority=_authority())

def test_admission_accepts_offsetless_nvd_timestamps_as_utc() -> None:
    """Treat offset-less analytical NVD timestamps as retained UTC authority."""
    bundle = deepcopy(_bundle())
    nvd = cast(dict[str, object], bundle["nvd"])
    observations = cast(list[dict[str, object]], nvd["observations"])

    observations[0]["published_at"] = "2026-09-01T12:00:00"
    observations[0]["last_modified_at"] = "2026-09-03T12:00:00"

    authority = _authority()
    admitted = admit_representative_threat_evidence(
        bundle,
        authority=authority,
    )

    assert admitted.nvd_records == authority.nvd_records


def test_admission_normalizes_offset_nvd_timestamps_to_utc() -> None:
    """Compare aware analytical NVD timestamps by their normalized UTC instant."""
    bundle = deepcopy(_bundle())
    nvd = cast(dict[str, object], bundle["nvd"])
    observations = cast(list[dict[str, object]], nvd["observations"])

    observations[0]["published_at"] = "2026-09-01T09:00:00-03:00"
    observations[0]["last_modified_at"] = "2026-09-03T09:00:00-03:00"

    authority = _authority()
    admitted = admit_representative_threat_evidence(
        bundle,
        authority=authority,
    )

    assert admitted.nvd_records == authority.nvd_records


def test_admission_rejects_malformed_nvd_timestamp() -> None:
    """Keep malformed analytical NVD timestamps fail-closed."""
    bundle = deepcopy(_bundle())
    nvd = cast(dict[str, object], bundle["nvd"])
    observations = cast(list[dict[str, object]], nvd["observations"])
    observations[0]["published_at"] = "not-an-iso-timestamp"

    with pytest.raises(
        RepresentativeThreatEvidenceAdmissionError,
        match="must contain an ISO-8601 timestamp",
    ):
        admit_representative_threat_evidence(
            bundle,
            authority=_authority(),
        )
