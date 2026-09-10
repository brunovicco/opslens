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
from opslens.hybrid_retrieval.domain import EvidenceNeed, StructuredEvidenceAuthority
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.epss.domain.parser import EpssSnapshotParser
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.knowledge_retrieval.application.bedrock_retrieval import (
    BedrockRetrieveInvocationEvidence,
    BedrockRetrieveResult,
)
from opslens.knowledge_retrieval.domain import (
    KnowledgeSourceType,
    RetrievalBackend,
    RetrievalEvidence,
    RetrievalRequest,
    RetrievedChunk,
)
from opslens.public_analysis.application import (
    MAX_REPRESENTATIVE_STRUCTURED_FINDINGS,
    REPRESENTATIVE_REMEDIATION_TOP_K,
    RepresentativeRepositoryAnalysis,
    RepresentativeRepositoryThreatEvidence,
    admit_public_semantic_plan,
    build_public_repository_evidence,
    build_public_semantic_planning_request,
    build_representative_hybrid_evidence,
    build_representative_repository_analysis,
    build_representative_structured_evidence,
    retrieve_representative_semantic_evidence,
)
from opslens.public_analysis.domain import (
    PUBLIC_ANALYSIS_V1_REQUIRED_EVIDENCE_NEEDS,
    ProviderResourceUsage,
    PublicRepositoryTarget,
    PublicSemanticPlanProposal,
    create_public_analysis_request,
)
from opslens.repository_intelligence.domain import compute_git_blob_sha1
from opslens.risk_policy.application import prioritize_repository_analysis
from opslens.risk_policy.domain import RiskPrioritizationResult, RiskPriorityTier
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


def _representative_analysis() -> RepresentativeRepositoryAnalysis:
    """Compose one exact repository finding through retained deterministic authority."""
    request = create_public_analysis_request(
        PublicRepositoryTarget(owner="brunovicco", name="opslens", requested_ref="main")
    )
    execution = build_public_repository_evidence(request, FakeRepositorySource())
    ghsa = _ghsa()
    return build_representative_repository_analysis(
        execution=execution,
        threat_evidence=RepresentativeRepositoryThreatEvidence(
            ghsa_vulnerabilities=(ghsa,),
            nvd_records=(_nvd_record(),),
            kev_snapshot=_kev_snapshot(),
            epss_snapshot=_epss_snapshot(),
        ),
    )


def _prioritization(composed: RepresentativeRepositoryAnalysis) -> RiskPrioritizationResult:
    """Apply the retained deterministic Risk Policy v1 to the exact analysis."""
    return prioritize_repository_analysis(composed.analysis)


def _bedrock_retriever(request: RetrievalRequest) -> BedrockRetrieveResult:
    """Return checked Bedrock-shaped retrieval evidence without provider execution."""
    text = "Upgrade to version 2.32.0 or later and follow the vendor advisory."
    chunk = RetrievedChunk.from_text(
        chunk_id="chunk-remediation-1",
        document_id="doc-remediation-1",
        source_id="source-remediation-1",
        source_type=KnowledgeSourceType.VENDOR_ADVISORY,
        canonical_uri="https://example.com/security/advisory",
        document_content_sha256="c" * 64,
        text=text,
        rank=1,
        relevance_score=0.94,
        title="Example security advisory",
    )
    evidence = RetrievalEvidence(
        retrieval_id="bedrock-retrieve:request-1",
        request=request,
        chunks=(chunk,),
        backend=RetrievalBackend.BEDROCK_KNOWLEDGE_BASE,
        backend_reference="kb-test",
    )
    invocation = BedrockRetrieveInvocationEvidence(
        knowledge_base_id="kb-test",
        provider_request_id="request-1",
        retry_attempts=2,
        client_elapsed_ms=12,
        returned_result_count=1,
    )
    return BedrockRetrieveResult(evidence=evidence, invocation=invocation)


def test_composes_retained_repository_truth_without_reinterpreting_risk() -> None:
    """Build Phase 4/5 truth and project it directly into bounded structured evidence."""
    composed = _representative_analysis()
    execution = composed.source_execution

    assert composed.vulnerability_scan.normalization_inventory == execution.normalization_inventory
    assert len(composed.analysis.findings) == 1
    assert composed.analysis.source == composed.epss_enrichment

    prioritization = _prioritization(composed)
    assert len(prioritization.ranked_findings) == 1
    assert prioritization.ranked_findings[0].evaluation.priority_tier is RiskPriorityTier.P0

    structured = build_representative_structured_evidence(
        analysis=composed.analysis,
        prioritization=prioritization,
    )
    assert MAX_REPRESENTATIVE_STRUCTURED_FINDINGS == 8
    assert tuple(row.evidence_need for row in structured) == (
        EvidenceNeed.VULNERABILITY_FACTS,
        EvidenceNeed.RISK_PRIORITY,
    )
    assert tuple(row.authority for row in structured) == (
        StructuredEvidenceAuthority.REPOSITORY_ANALYSIS,
        StructuredEvidenceAuthority.RISK_POLICY,
    )
    vulnerability_fields = {field.name: field.value for field in structured[0].fields}
    risk_fields = {field.name: field.value for field in structured[1].fields}
    assert vulnerability_fields == {
        "cve_id": _CVE_ID,
        "dependency_purl": "pkg:pypi/requests@2.31.0",
        "ghsa_id": "GHSA-test-1234",
        "installed_version": "2.31.0",
    }
    assert risk_fields == {
        "priority_score": 90,
        "priority_tier": "P0",
        "rank": 1,
        "review_required": False,
    }


def test_composes_checked_semantic_evidence_under_exact_public_hybrid_route() -> None:
    """Use one Bedrock-shaped retrieve result to satisfy only remediation evidence."""
    composed = _representative_analysis()
    prioritization = _prioritization(composed)
    execution = composed.source_execution
    planning_request = build_public_semantic_planning_request(execution)
    proposal = PublicSemanticPlanProposal(
        planning_request_sha256=planning_request.request_sha256,
        evidence_needs=PUBLIC_ANALYSIS_V1_REQUIRED_EVIDENCE_NEEDS,
    )
    handoff = admit_public_semantic_plan(
        proposal,
        planning_request=planning_request,
        source_execution=execution,
    )

    semantic = retrieve_representative_semantic_evidence(
        analysis=composed.analysis,
        prioritization=prioritization,
        retriever=_bedrock_retriever,
    )
    assert semantic.request.top_k == REPRESENTATIVE_REMEDIATION_TOP_K == 5
    assert _CVE_ID in semantic.request.query
    assert "pkg:pypi/requests@2.31.0" in semantic.request.query
    assert "2.32.0" in semantic.request.query
    assert semantic.usage == ProviderResourceUsage(
        bedrock_retrieve_count=1,
        retry_count=2,
    )

    envelope = build_representative_hybrid_evidence(
        handoff=handoff,
        repository_analysis=composed,
        prioritization=prioritization,
        semantic_evidence=semantic,
    )
    assert envelope.authority_decision == handoff.route_decision
    assert envelope.satisfied_evidence_needs == handoff.route_decision.evidence_needs
    assert len(envelope.structured_evidence) == 2
    assert len(envelope.semantic_evidence) == 1
