"""Deterministic offline controlled-benign demonstration for OpsLens V1."""

import base64
import gzip
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import cast

from opslens.correlation.adapters.ghsa import (
    GhsaPyPIVulnerabilityEvidence,
    GhsaSourceIdentifierEvidence,
)
from opslens.demo.material_vulnerability import DemoContractError
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.epss.domain.parser import EpssSnapshotParser
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.public_analysis.application import (
    RepresentativeRepositoryAnalysis,
    RepresentativeRepositoryThreatEvidence,
    build_public_repository_evidence,
    build_representative_repository_analysis,
)
from opslens.public_analysis.application.threat_evidence_authority import (
    PublicThreatEvidenceScope,
    build_public_threat_evidence_scope,
)
from opslens.public_analysis.domain import (
    PublicRepositoryEvidenceExecution,
    PublicRepositoryTarget,
    create_public_analysis_request,
)
from opslens.repository_intelligence.domain import compute_git_blob_sha1
from opslens.risk_policy.application import prioritize_repository_analysis
from opslens.risk_policy.domain import RiskPrioritizationResult
from opslens.transformation.nvd.domain.models import NvdCveCoreRecord
from opslens.transformation.nvd.domain.transformer import NvdCveCoreTransformer

type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None

CONTROLLED_BENIGN_RESULT_CONTRACT_VERSION = "opslens-demo-controlled-benign-result:v1"
CONTROLLED_BENIGN_SCENARIO_ID = "controlled-benign"
CONTROLLED_BENIGN_FIXTURE_VERSION = "controlled-benign-fixture:v1"

_REPOSITORY_OWNER = "opslens-demo"
_REPOSITORY_NAME = "controlled-benign-fixture"
_REPOSITORY_ID = 19_110_002
_COMMIT_SHA = "3" * 40
_TREE_SHA = "4" * 40
_CVE_ID = "CVE-2026-12345"


def _canonical_json(value: object) -> bytes:
    """Serialize deterministic JSON for benign demo identity and reviewer output."""
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _decode_object(payload: bytes, *, label: str) -> dict[str, JsonValue]:
    """Decode one retained canonical JSON projection and require an object root."""
    value = cast(JsonValue, json.loads(payload.decode("utf-8")))
    if not isinstance(value, dict):
        raise DemoContractError(f"{label} must decode to one JSON object")
    return value


def _uv_lock_content() -> bytes:
    """Return inert lock evidence at the first patched Requests release."""
    return (
        b"version = 1\n"
        b"revision = 3\n"
        b'requires-python = ">=3.13"\n'
        b"[[package]]\n"
        b'name = "Requests"\n'
        b'version = "2.32.0"\n'
        b'source = { registry = "https://pypi.org/simple" }\n'
    )


@dataclass(frozen=True, slots=True)
class OfflineControlledBenignRepositorySource:
    """Serve exact inert benign repository evidence without provider access."""

    def get_repository(self, owner: str, name: str) -> dict[str, object]:
        """Return source-confirmed public metadata for the synthetic fixture."""
        if (owner, name) != (_REPOSITORY_OWNER, _REPOSITORY_NAME):
            raise DemoContractError("controlled-benign repository coordinates drifted")
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
        """Return the exact immutable synthetic commit/tree coordinates."""
        if (owner, name, ref) != (_REPOSITORY_OWNER, _REPOSITORY_NAME, "main"):
            raise DemoContractError("controlled-benign commit coordinates drifted")
        return {"sha": _COMMIT_SHA, "commit": {"tree": {"sha": _TREE_SHA}}}

    def get_uv_lock(
        self,
        owner: str,
        name: str,
        commit_sha: str,
    ) -> dict[str, object]:
        """Return exact-commit inert dependency evidence without executing code."""
        if (owner, name, commit_sha) != (
            _REPOSITORY_OWNER,
            _REPOSITORY_NAME,
            _COMMIT_SHA,
        ):
            raise DemoContractError("controlled-benign lockfile coordinates drifted")
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


def _ghsa_evidence() -> GhsaPyPIVulnerabilityEvidence:
    """Return complete scoped advisory evidence that does not affect 2.32.0."""
    return GhsaPyPIVulnerabilityEvidence(
        observed_advisory_version_id="ghsa-controlled-benign-v1",
        source_advisory_sha256="5" * 64,
        ghsa_id="GHSA-demo-1911",
        github_cve_id=_CVE_ID,
        github_identifiers=(
            GhsaSourceIdentifierEvidence(identifier_type="CVE", value=_CVE_ID),
        ),
        vulnerability_entry_id="ghsa-benign-entry-0",
        source_index=0,
        source_entry_sha256="6" * 64,
        ecosystem_original="pip",
        package_name_original="requests",
        vulnerable_range_original=">= 2, < 2.32",
        first_patched_version_original="2.32.0",
    )


def _nvd_record() -> NvdCveCoreRecord:
    """Build deterministic NVD evidence for the same non-applicable advisory."""
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
    """Build one complete immutable KEV snapshot containing the advisory CVE."""
    record: dict[str, object] = {
        "cveID": _CVE_ID,
        "vendorProject": "OpsLens Demo Vendor",
        "product": "OpsLens Demo Product",
        "vulnerabilityName": "Synthetic Known Exploited Vulnerability",
        "dateAdded": "2026-09-01",
        "shortDescription": "Synthetic exploitation evidence for the controlled fixture.",
        "requiredAction": "Upgrade to the fixed release.",
        "dueDate": "2026-09-22",
        "knownRansomwareCampaignUse": "Unknown",
        "notes": "https://example.com/opslens-demo/advisory",
        "cwes": ["CWE-79"],
    }
    document: dict[str, object] = {
        "title": "CISA Known Exploited Vulnerabilities Catalog",
        "catalogVersion": "2026.09.03-controlled-demo",
        "dateReleased": "2026-09-03T12:00:00Z",
        "count": 1,
        "vulnerabilities": [record],
    }
    payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
    return KevCatalogSnapshot(
        raw_bytes=payload,
        catalog_version="2026.09.03-controlled-demo",
        date_released=datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
        retrieved_at=datetime(2026, 9, 3, 12, 30, tzinfo=UTC),
        sha256=hashlib.sha256(payload).hexdigest(),
        record_count=1,
    )


def _epss_snapshot() -> EpssSnapshot:
    """Build one complete exact EPSS snapshot containing the advisory CVE."""
    text = (
        "#model_version:v2026.06.15,score_date:2026-09-03T12:00:00Z\n"
        "cve,epss,percentile\n"
        f"{_CVE_ID},0.42,0.88\n"
    )
    return EpssSnapshotParser().parse(gzip.compress(text.encode("utf-8"), mtime=0))


def _threat_evidence() -> RepresentativeRepositoryThreatEvidence:
    """Compose complete typed source evidence for deterministic non-applicability."""
    return RepresentativeRepositoryThreatEvidence(
        ghsa_vulnerabilities=(_ghsa_evidence(),),
        nvd_records=(_nvd_record(),),
        kev_snapshot=_kev_snapshot(),
        epss_snapshot=_epss_snapshot(),
    )


@dataclass(frozen=True, slots=True)
class ControlledBenignDemoResult:
    """Content-addressed no-finding result from complete controlled fixture evidence."""

    source_execution: PublicRepositoryEvidenceExecution
    threat_scope: PublicThreatEvidenceScope
    repository_analysis: RepresentativeRepositoryAnalysis
    prioritization: RiskPrioritizationResult

    def __post_init__(self) -> None:
        """Require complete scope and a deterministic zero-finding outcome."""
        if self.repository_analysis.source_execution != self.source_execution:
            raise DemoContractError("controlled-benign analysis drifted from repository evidence")
        if self.threat_scope.source_execution_id != self.source_execution.execution_id:
            raise DemoContractError(
                "controlled-benign threat scope drifted from repository evidence"
            )
        analysis = self.repository_analysis.analysis
        if self.prioritization.source_analysis_id != analysis.analysis_id:
            raise DemoContractError("controlled-benign risk result drifted from analysis identity")
        if self.prioritization.source_analysis_sha256 != analysis.evidence_sha256:
            raise DemoContractError("controlled-benign risk result drifted from analysis evidence")
        if analysis.finding_count != 0 or self.prioritization.ranked_findings:
            raise DemoContractError("controlled-benign scenario must produce zero findings")
        if self.source_execution.normalization_inventory.unsupported_normalization:
            raise DemoContractError(
                "controlled-benign evidence cannot contain unsupported normalization"
            )
        if not self.threat_scope.dependencies:
            raise DemoContractError(
                "controlled-benign threat scope must contain one admitted dependency"
            )

    @property
    def canonical_payload(self) -> dict[str, JsonValue]:
        """Return stable JSON proving complete evidence without a live safety claim."""
        analysis = self.repository_analysis.analysis
        return {
            "contract_version": CONTROLLED_BENIGN_RESULT_CONTRACT_VERSION,
            "scenario": {
                "id": CONTROLLED_BENIGN_SCENARIO_ID,
                "fixture_version": CONTROLLED_BENIGN_FIXTURE_VERSION,
                "source_kind": "offline_synthetic_fixture",
            },
            "authority": {
                "mode": "OFFLINE_DETERMINISTIC",
                "aws_credentials_required": False,
                "network_access": False,
                "live_provider_execution": False,
                "model_execution": False,
                "third_party_repository_code_execution": False,
            },
            "outcome": {
                "state": "NO_MATERIAL_FINDING",
                "finding_count": 0,
                "scoped_evidence_complete": True,
                "unsupported_normalization_count": 0,
                "benign_claim_scope": "controlled_fixture_only",
                "live_repository_safety_claim": False,
            },
            "summary": {
                "repository": analysis.repository_snapshot.repository.full_name,
                "commit_sha": analysis.repository_snapshot.commit_sha,
                "dependency": "requests",
                "installed_version": "2.32.0",
                "applicable_vulnerability_count": 0,
                "risk_evaluation_count": 0,
            },
            "identities": {
                "repository_execution_id": self.source_execution.execution_id,
                "repository_execution_sha256": self.source_execution.evidence_sha256,
                "threat_scope_id": self.threat_scope.scope_id,
                "threat_scope_sha256": self.threat_scope.scope_sha256,
                "repository_analysis_id": analysis.analysis_id,
                "repository_analysis_sha256": analysis.evidence_sha256,
                "risk_policy_id": self.prioritization.policy.policy_id,
                "risk_prioritization_sha256": sha256(
                    self.prioritization.canonical_json
                ).hexdigest(),
            },
            "repository_evidence": _decode_object(
                self.source_execution.canonical_json,
                label="repository_evidence",
            ),
            "repository_analysis": _decode_object(
                analysis.canonical_json,
                label="repository_analysis",
            ),
            "risk_prioritization": _decode_object(
                self.prioritization.canonical_json,
                label="risk_prioritization",
            ),
        }

    @property
    def canonical_json(self) -> bytes:
        """Return stable canonical JSON for machine comparison."""
        return _canonical_json(self.canonical_payload)

    @property
    def evidence_sha256(self) -> str:
        """Return SHA-256 of the complete controlled-benign projection."""
        return sha256(self.canonical_json).hexdigest()

    @property
    def result_id(self) -> str:
        """Return the content-addressed controlled-benign result identity."""
        return (
            f"{CONTROLLED_BENIGN_RESULT_CONTRACT_VERSION}@sha256:"
            f"{self.evidence_sha256}"
        )

    def to_text(self) -> str:
        """Render a concise reviewer summary that cannot imply live repository safety."""
        analysis = self.repository_analysis.analysis
        return "\n".join(
            (
                "OpsLens V1 deterministic offline demo",
                f"scenario: {CONTROLLED_BENIGN_SCENARIO_ID}",
                f"repository fixture: {analysis.repository_snapshot.repository.full_name}",
                "dependency: requests==2.32.0",
                "outcome: NO_MATERIAL_FINDING",
                "evidence: complete scoped fixture; unsupported normalization=0",
                "scope: controlled fixture only; no live repository safety claim",
                f"threat scope: {self.threat_scope.scope_id}",
                f"repository analysis: {analysis.analysis_id}",
                f"risk policy: {self.prioritization.policy.policy_id}",
                f"demo result: {self.result_id}",
                "authority: deterministic facts only; no model/provider execution",
                "safety: READ, NEVER EXECUTE third-party repository code",
                "",
            )
        )


def build_controlled_benign_demo() -> ControlledBenignDemoResult:
    """Execute complete offline evidence that deterministically yields no finding."""
    request = create_public_analysis_request(
        PublicRepositoryTarget(
            owner=_REPOSITORY_OWNER,
            name=_REPOSITORY_NAME,
            requested_ref="main",
        )
    )
    execution = build_public_repository_evidence(
        request,
        OfflineControlledBenignRepositorySource(),
    )
    threat_scope = build_public_threat_evidence_scope(execution)
    repository_analysis = build_representative_repository_analysis(
        execution=execution,
        threat_evidence=_threat_evidence(),
    )
    prioritization = prioritize_repository_analysis(repository_analysis.analysis)
    return ControlledBenignDemoResult(
        source_execution=execution,
        threat_scope=threat_scope,
        repository_analysis=repository_analysis,
        prioritization=prioritization,
    )


__all__ = [
    "CONTROLLED_BENIGN_FIXTURE_VERSION",
    "CONTROLLED_BENIGN_RESULT_CONTRACT_VERSION",
    "CONTROLLED_BENIGN_SCENARIO_ID",
    "ControlledBenignDemoResult",
    "OfflineControlledBenignRepositorySource",
    "build_controlled_benign_demo",
]
