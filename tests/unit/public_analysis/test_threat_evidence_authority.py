"""Offline tests for the Gate 19.8 request-time threat-evidence authority contract."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from opslens.correlation.adapters.ghsa import GhsaPyPIVulnerabilityEvidence
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.public_analysis.application import (
    admit_public_analysis_request,
    build_public_repository_evidence,
)
from opslens.public_analysis.application.threat_evidence_authority import (
    PublicRepositoryThreatEvidence,
    PublicThreatDependencyScope,
    PublicThreatEvidenceRequest,
    PublicThreatEvidenceScope,
    build_public_threat_evidence_scope,
    load_public_repository_threat_evidence,
)
from opslens.public_analysis.domain import PublicAnalysisValidationError
from opslens.repository_intelligence.domain import compute_git_blob_sha1
from opslens.transformation.nvd.domain.models import (
    NvdCveCoreRecord,
    NvdVulnerabilityStatus,
    ObservedCveVersion,
)

_REPOSITORY_ID = 1_333_092_779
_COMMIT_SHA = "3f75a4fc2bd22589df0a5ffe98a8442fda81c8d3"
_TREE_SHA = "01ac6fe03f1db867ef29c6652311ee43b1f63afb"


def _request():
    return admit_public_analysis_request(
        b'{"repository_url":"https://github.com/brunovicco/opslens","requested_ref":null}'
    ).request


def _lock_content(*, version: str = "2.31.0") -> bytes:
    return (
        b"version = 1\n"
        b"revision = 3\n"
        b'requires-python = ">=3.13"\n'
        b"[[package]]\n"
        b'name = "Requests"\n'
        + f'version = "{version}"\n'.encode()
        + b'source = { registry = "https://pypi.org/simple" }\n'
    )


def _uv_payload(content: bytes) -> dict[str, object]:
    return {
        "type": "file",
        "path": "uv.lock",
        "name": "uv.lock",
        "encoding": "base64",
        "size": len(content),
        "sha": compute_git_blob_sha1(content),
        "content": base64.encodebytes(content).decode("ascii"),
    }


@dataclass(slots=True)
class _Source:
    content: bytes = field(default_factory=_lock_content)

    def get_repository(self, owner: str, name: str) -> dict[str, object]:
        assert (owner, name) == ("brunovicco", "opslens")
        return {
            "id": _REPOSITORY_ID,
            "name": "opslens",
            "full_name": "brunovicco/opslens",
            "private": False,
            "visibility": "public",
            "default_branch": "main",
            "owner": {"login": "brunovicco"},
        }

    def get_commit(self, owner: str, name: str, ref: str) -> dict[str, object]:
        assert (owner, name, ref) == ("brunovicco", "opslens", "main")
        return {"sha": _COMMIT_SHA, "commit": {"tree": {"sha": _TREE_SHA}}}

    def get_uv_lock(
        self,
        owner: str,
        name: str,
        commit_sha: str,
    ) -> dict[str, object]:
        assert (owner, name, commit_sha) == ("brunovicco", "opslens", _COMMIT_SHA)
        return _uv_payload(self.content)


def _execution(*, version: str = "2.31.0"):
    return build_public_repository_evidence(
        _request(),
        _Source(content=_lock_content(version=version)),
    )


def _ghsa(
    *,
    package_name: str = "Requests",
    cve_id: str | None = None,
) -> GhsaPyPIVulnerabilityEvidence:
    source_sha = "a" * 64
    return GhsaPyPIVulnerabilityEvidence(
        observed_advisory_version_id=f"GHSA-aaaa-bbbb-cccc@sha256:{source_sha}",
        source_advisory_sha256=source_sha,
        ghsa_id="GHSA-aaaa-bbbb-cccc",
        github_cve_id=cve_id,
        github_identifiers=(),
        vulnerability_entry_id="ghsa-entry:v1:test",
        source_index=0,
        source_entry_sha256="b" * 64,
        ecosystem_original="pip",
        package_name_original=package_name,
        vulnerable_range_original="<2.32.0",
        first_patched_version_original="2.32.0",
    )


def _nvd(cve_id: str) -> NvdCveCoreRecord:
    observed = ObservedCveVersion.from_source({"id": cve_id})
    return NvdCveCoreRecord(
        observed_version=observed,
        source_identifier="security@example.test",
        published_at=datetime(2026, 9, 1, tzinfo=UTC),
        last_modified_at=datetime(2026, 9, 2, tzinfo=UTC),
        vuln_status=NvdVulnerabilityStatus.ANALYZED,
    )


def _kev() -> KevCatalogSnapshot:
    return KevCatalogSnapshot(
        raw_bytes=b"{}",
        catalog_version="2026.09.12",
        date_released=datetime(2026, 9, 12, tzinfo=UTC),
        retrieved_at=datetime(2026, 9, 12, 12, tzinfo=UTC),
        sha256="c" * 64,
        record_count=1,
    )


def _epss() -> EpssSnapshot:
    return EpssSnapshot(
        raw_bytes=b"epss",
        model_version="v2026.06.15",
        score_timestamp=datetime(2026, 9, 12, tzinfo=UTC),
        sha256="d" * 64,
        row_count=1,
    )


def test_scope_is_bound_to_exact_repository_evidence_and_canonical_pypi_identity() -> None:
    execution = _execution()

    scope = build_public_threat_evidence_scope(execution)

    assert scope.source_execution_id == execution.execution_id
    assert scope.source_evidence_sha256 == execution.evidence_sha256
    assert scope.query_package_names == ("requests",)
    assert len(scope.dependencies) == 1
    dependency = scope.dependencies[0]
    assert dependency.package_name == "requests"
    assert dependency.version == "2.31.0"
    assert dependency.purl == "pkg:pypi/requests@2.31.0"
    assert dependency.source_record_indexes == (0,)
    assert scope.scope_id.startswith("public-threat-evidence-scope:v1@sha256:")


def test_query_package_names_collapse_package_lookup_without_losing_version_scope() -> None:
    scope = PublicThreatEvidenceScope(
        source_execution_id="public-repository-evidence:v1@sha256:" + ("e" * 64),
        source_evidence_sha256="e" * 64,
        dependencies=(
            PublicThreatDependencyScope(
                package_name="requests",
                version="2.31.0",
                purl="pkg:pypi/requests@2.31.0",
                source_record_indexes=(0,),
            ),
            PublicThreatDependencyScope(
                package_name="requests",
                version="2.32.0",
                purl="pkg:pypi/requests@2.32.0",
                source_record_indexes=(4, 8),
            ),
        ),
    )

    assert scope.query_package_names == ("requests",)
    assert tuple(item.purl for item in scope.dependencies) == (
        "pkg:pypi/requests@2.31.0",
        "pkg:pypi/requests@2.32.0",
    )
    assert scope.dependencies[1].source_record_indexes == (4, 8)


def test_scope_fails_closed_when_phase3_cannot_normalize_a_pypi_record() -> None:
    execution = _execution(version="definitely-not-pep440")

    with pytest.raises(
        PublicAnalysisValidationError,
        match="refuses incomplete PyPI normalization evidence",
    ):
        build_public_threat_evidence_scope(execution)


def test_typed_evidence_preserves_exact_snapshot_and_source_local_provenance() -> None:
    request = PublicThreatEvidenceRequest(scope=build_public_threat_evidence_scope(_execution()))
    ghsa = _ghsa(cve_id="CVE-2026-12345")
    nvd = _nvd("CVE-2026-12345")

    evidence = PublicRepositoryThreatEvidence(
        request=request,
        ghsa_vulnerabilities=(ghsa,),
        nvd_records=(nvd,),
        kev_snapshot=_kev(),
        epss_snapshot=_epss(),
    )

    assert evidence.provenance.ghsa_observed_advisory_version_ids == (
        ghsa.observed_advisory_version_id,
    )
    assert evidence.provenance.nvd_observed_cve_version_ids == (
        nvd.observed_version.observed_cve_version_id,
    )
    assert evidence.provenance.kev_snapshot_date == "2026-09-12"
    assert evidence.provenance.kev_sha256 == "c" * 64
    assert evidence.provenance.epss_snapshot_date == "2026-09-12"
    assert evidence.provenance.epss_sha256 == "d" * 64


def test_ghsa_evidence_outside_admitted_dependency_scope_is_rejected() -> None:
    request = PublicThreatEvidenceRequest(scope=build_public_threat_evidence_scope(_execution()))

    with pytest.raises(
        PublicAnalysisValidationError,
        match="outside the admitted dependency scope",
    ):
        PublicRepositoryThreatEvidence(
            request=request,
            ghsa_vulnerabilities=(_ghsa(package_name="flask"),),
            nvd_records=(),
            kev_snapshot=_kev(),
            epss_snapshot=_epss(),
        )


def test_nvd_evidence_unrelated_to_scoped_ghsa_evidence_is_rejected() -> None:
    request = PublicThreatEvidenceRequest(scope=build_public_threat_evidence_scope(_execution()))

    with pytest.raises(
        PublicAnalysisValidationError,
        match="unrelated to admitted scoped GHSA evidence",
    ):
        PublicRepositoryThreatEvidence(
            request=request,
            ghsa_vulnerabilities=(_ghsa(cve_id="CVE-2026-12345"),),
            nvd_records=(_nvd("CVE-2026-99999"),),
            kev_snapshot=_kev(),
            epss_snapshot=_epss(),
        )


@dataclass(slots=True)
class _Authority:
    evidence: PublicRepositoryThreatEvidence
    requests: list[PublicThreatEvidenceRequest] = field(default_factory=list)

    def load(self, request: PublicThreatEvidenceRequest) -> PublicRepositoryThreatEvidence:
        self.requests.append(request)
        return self.evidence


def test_authority_load_is_bound_to_the_exact_request() -> None:
    execution = _execution()
    request = PublicThreatEvidenceRequest(scope=build_public_threat_evidence_scope(execution))
    evidence = PublicRepositoryThreatEvidence(
        request=request,
        ghsa_vulnerabilities=(_ghsa(),),
        nvd_records=(),
        kev_snapshot=_kev(),
        epss_snapshot=_epss(),
    )
    authority = _Authority(evidence=evidence)

    loaded = load_public_repository_threat_evidence(execution, authority)

    assert loaded == evidence
    assert authority.requests == [request]
