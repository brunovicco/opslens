"""Tests for deterministic repository-analysis composition used by Gate 19.2."""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from opslens.correlation.adapters.ghsa import (
    GhsaPyPIVulnerabilityEvidence,
    GhsaSourceIdentifierEvidence,
)
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.epss.domain.parser import EpssSnapshotParser
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.public_analysis.application import (
    RepresentativeRepositoryThreatEvidence,
    build_public_repository_evidence,
    build_representative_repository_analysis,
)
from opslens.public_analysis.domain import (
    PublicRepositoryTarget,
    create_public_analysis_request,
)
from opslens.repository_intelligence.domain import compute_git_blob_sha1
from opslens.risk_policy.application import prioritize_repository_analysis
from opslens.risk_policy.domain import RiskPriorityTier
from opslens.transformation.nvd.domain.models import NvdCveCoreRecord
from opslens.transformation.nvd.domain.transformer import NvdCveCoreTransformer

_REPOSITORY_ID = 1_333_092_779
_COMMIT_SHA = "164b936e1c27b14b6fdf3a9484f7ae0772c076a3"
_TREE_SHA = "a" * 40
_CVE_ID = "CVE-2026-12345"


def _uv_lock_content() -> bytes:
    """Return one inert uv.lock with an affected Requests version."""
    return (
        b"version = 1\n"
        b"revision = 3\n"
        b'requires-python = \">=3.13\"\n'
        b"[[package]]\n"
        b'name = "Requests"\n'
        b'version = "2.31.0"\n'
        b'source = { registry = "https://pypi.org/simple" }\n'
    )


@dataclass(slots=True)
class FakeRepositorySource:
    """Return exact public repository metadata and inert lock evidence."""

    def get_repository(self, owner: str, name: str) -> dict[str, object]:
        """Return source-confirmed public repository metadata."""
        return {
            "id": _REPOSITORY_ID,
            "name": name,
            "full_name": f"{owner}/{name}",
            "private": False,
            "visibility": "public",
            "default_branch": "main",
            "owner": {"login": owner},
        }

    def get_commit(self, owner: str, name: str, ref: str) -> dict[str, object]:
        """Return one exact immutable commit/tree observation."""
        assert (owner, name, ref) == ("brunovicco", "opslens", "main")
        return {"sha": _COMMIT_SHA, "commit": {"tree": {"sha": _TREE_SHA}}}

    def get_uv_lock(
        self,
        owner: str,
        name: str,
        commit_sha: str,
    ) -> dict[str, object]:
        """Return the exact-commit inert uv.lock evidence payload."""
        assert (owner, name, commit_sha) == ("brunovicco", "opslens", _COMMIT_SHA)
        content = _uv_lock_content()
        return {
            "type": "file",
            "path": "uv.lock",
            "name": "uv.lock",
            "encoding": "base64",
            "size": len(content),
            "sha": compute_git_blob_sha1(content),
            "content": base64.encodebytes(content).decode("ascii"),
        }


def _ghsa() -> GhsaPyPIVulnerabilityEvidence:
    """Build one exact GHSA occurrence affecting the inert dependency."""
    return GhsaPyPIVulnerabilityEvidence(
        observed_advisory_version_id="ghsa-observed-v1",
        source_advisory_sha256="0" * 64,
        ghsa_id="GHSA-test-1234",
        github_cve_id=_CVE_ID,
        github_identifiers=(
            GhsaSourceIdentifierEvidence(identifier_type="CVE", value=_CVE_ID),
        ),
        vulnerability_entry_id="ghsa-entry-0",
        source_index=0,
        source_entry_sha256="1" * 64,
        ecosystem_original="pip",
        package_name_original="requests",
        vulnerable_range_original=">= 2, < 2.32",
        first_patched_version_original="2.32.0",
    )


def _nvd_record() -> NvdCveCoreRecord:
    """Build exact NVD/CVSS evidence through the retained transformer."""
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
                }
            ]
        },
    }
    return NvdCveCoreTransformer().transform(source)


def _kev_snapshot() -> KevCatalogSnapshot:
    """Build one complete immutable CISA KEV snapshot containing the CVE."""
    record: dict[str, object] = {
        "cveID": _CVE_ID,
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


def _epss_snapshot() -> EpssSnapshot:
    """Build one complete exact FIRST EPSS snapshot containing the CVE."""
    text = (
        "#model_version:v2026.06.15,score_date:2026-09-03T12:00:00Z\n"
        "cve,epss,percentile\n"
        f"{_CVE_ID},0.42,0.88\n"
    )
    return EpssSnapshotParser().parse(gzip.compress(text.encode(), mtime=0))


def test_composes_retained_repository_truth_without_reinterpreting_risk() -> None:
    """Build the Phase 4 chain from admitted public evidence, then reuse Risk Policy v1."""
    request = create_public_analysis_request(
        PublicRepositoryTarget(owner="brunovicco", name="opslens", requested_ref="main")
    )
    execution = build_public_repository_evidence(request, FakeRepositorySource())
    ghsa = _ghsa()
    composed = build_representative_repository_analysis(
        execution=execution,
        threat_evidence=RepresentativeRepositoryThreatEvidence(
            ghsa_vulnerabilities=(ghsa,),
            nvd_records=(_nvd_record(),),
            kev_snapshot=_kev_snapshot(),
            epss_snapshot=_epss_snapshot(),
        ),
    )

    assert composed.source_execution == execution
    assert composed.vulnerability_scan.normalization_inventory == execution.normalization_inventory
    assert len(composed.analysis.findings) == 1
    assert composed.analysis.source == composed.epss_enrichment

    prioritization = prioritize_repository_analysis(composed.analysis)
    assert len(prioritization.ranked_findings) == 1
    assert prioritization.ranked_findings[0].evaluation.priority_tier is RiskPriorityTier.P0
