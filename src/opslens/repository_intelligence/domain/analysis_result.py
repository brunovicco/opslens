"""Final consumer-facing projection over the validated Phase 4 evidence chain."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import cast

from opslens.correlation.domain.pypi_ranges import PyPIClauseEvidence
from opslens.ingestion.epss.domain.history import HistoricalEpssSnapshot
from opslens.repository_intelligence.domain.epss_enrichment import (
    RepositoryEpssEnrichedFinding,
    RepositoryEpssEnrichmentEvidence,
    RepositoryEpssSnapshotEvidence,
    RepositoryEpssState,
)
from opslens.repository_intelligence.domain.errors import (
    InvalidRepositoryAnalysisResultError,
)
from opslens.repository_intelligence.domain.file_evidence import (
    ImmutableRepositoryFileEvidence,
)
from opslens.repository_intelligence.domain.kev_enrichment import (
    RepositoryKevEnrichedFinding,
    RepositoryKevState,
)
from opslens.repository_intelligence.domain.models import ImmutableRepositorySnapshot
from opslens.repository_intelligence.domain.nvd_enrichment import (
    RepositoryNvdEnrichedFinding,
)
from opslens.repository_intelligence.domain.vulnerability_findings import (
    RepositoryPyPIVulnerabilityFinding,
)
from opslens.transformation.epss.domain.models import SilverEpssRecord
from opslens.transformation.kev.domain.models import SilverKevRecord
from opslens.transformation.nvd.domain.models import NvdCvssMetric

_ANALYSIS_SCHEMA_VERSION = "1"
_ANALYSIS_ENGINE = "opslens.phase4.repository-analysis.v1"


@dataclass(frozen=True, slots=True)
class RepositoryAnalysisFinding:
    """Read-only Phase 4 projection for one deterministically affected dependency."""

    evidence: RepositoryEpssEnrichedFinding

    @property
    def kev_enrichment(self) -> RepositoryKevEnrichedFinding:
        """Return the exact KEV-enriched finding immediately below EPSS."""
        return self.evidence.previous

    @property
    def nvd_enrichment(self) -> RepositoryNvdEnrichedFinding:
        """Return the exact NVD/CVSS enrichment below KEV."""
        return self.kev_enrichment.previous

    @property
    def base_finding(self) -> RepositoryPyPIVulnerabilityFinding:
        """Return deterministic Gate 4.7 applicability evidence."""
        return self.nvd_enrichment.finding

    @property
    def dependency_name(self) -> str:
        """Return canonical affected dependency name."""
        return self.base_finding.assessment.dependency_name_canonical

    @property
    def dependency_name_original(self) -> str:
        """Return dependency name exactly as observed in the lockfile."""
        return self.base_finding.assessment.dependency_name_original

    @property
    def installed_version(self) -> str:
        """Return canonical installed dependency version."""
        return self.base_finding.assessment.dependency_version_canonical

    @property
    def installed_version_original(self) -> str:
        """Return installed version exactly as observed in the lockfile."""
        return self.base_finding.assessment.dependency_version_original

    @property
    def purl(self) -> str:
        """Return canonical package URL established by Phase 3 semantics."""
        return self.base_finding.assessment.dependency_purl

    @property
    def ghsa_id(self) -> str:
        """Return the exact GitHub Security Advisory identifier."""
        return self.base_finding.assessment.ghsa_id

    @property
    def cve_id(self) -> str | None:
        """Return GitHub-asserted CVE identity when the advisory supplied one."""
        return self.nvd_enrichment.alias.github_cve_id

    @property
    def vulnerable_range(self) -> str:
        """Return the exact GHSA vulnerable range used for applicability."""
        return self.base_finding.assessment.vulnerable_range_original

    @property
    def matched_clauses(self) -> tuple[PyPIClauseEvidence, ...]:
        """Return parsed clauses with deterministic match evidence."""
        return self.base_finding.assessment.parsed_clauses

    @property
    def fixed_version(self) -> str | None:
        """Return canonical first patched version when source evidence provides one."""
        return self.base_finding.assessment.first_patched_version_canonical

    @property
    def fixed_version_original(self) -> str | None:
        """Return first patched version exactly as published by GHSA when present."""
        return self.base_finding.assessment.first_patched_version_original

    @property
    def cvss_metrics(self) -> tuple[NvdCvssMetric, ...]:
        """Return every normalized NVD CVSS observation without selecting a winner."""
        nvd_cvss = self.nvd_enrichment.nvd_cvss
        return nvd_cvss.cvss.metrics if nvd_cvss is not None else ()

    @property
    def kev_state(self) -> RepositoryKevState:
        """Return complete-snapshot CISA KEV membership state."""
        return self.kev_enrichment.state

    @property
    def kev_record(self) -> SilverKevRecord | None:
        """Return exact positive KEV row evidence when present."""
        return self.kev_enrichment.kev_record

    @property
    def epss_state(self) -> RepositoryEpssState:
        """Return score presence state for the explicitly selected EPSS snapshot."""
        return self.evidence.state

    @property
    def epss_record(self) -> SilverEpssRecord | None:
        """Return exact EPSS score observation when present."""
        return self.evidence.epss_record

    @property
    def canonical_json(self) -> bytes:
        """Return deterministic final finding JSON exposing the Phase 4 exit fields."""
        assessment = self.base_finding.assessment
        nvd = self.nvd_enrichment
        kev = self.kev_enrichment
        epss_snapshot = self.evidence.epss_snapshot
        clauses: list[object] = [
            {
                "operator": clause.operator,
                "bound_original": clause.bound_original,
                "bound_canonical": clause.bound_canonical,
                "matched": clause.matched,
            }
            for clause in self.matched_clauses
        ]
        metrics: list[object] = [_cvss_payload(metric) for metric in self.cvss_metrics]
        nvd_payload: dict[str, object] | None = None
        unsupported_cvss: list[str] = []
        if nvd.nvd_cvss is not None:
            observed = nvd.nvd_cvss.nvd.observed_version
            nvd_payload = {
                "cve_id": observed.cve_id,
                "observed_cve_version_id": observed.observed_cve_version_id,
                "source_cve_sha256": observed.source_cve_sha256,
                "source_identifier": nvd.nvd_cvss.nvd.source_identifier,
                "vulnerability_status": nvd.nvd_cvss.nvd.vuln_status.value,
            }
            unsupported_cvss = list(nvd.nvd_cvss.cvss.unsupported_cvss_families)

        payload: dict[str, object] = {
            "schema_version": _ANALYSIS_SCHEMA_VERSION,
            "engine": _ANALYSIS_ENGINE,
            "repository": {
                "snapshot_id": assessment.snapshot_id,
                "file_evidence_id": assessment.file_evidence_id,
            },
            "dependency": {
                "record_index": assessment.dependency_record_index,
                "name": self.dependency_name,
                "name_original": self.dependency_name_original,
                "installed_version": self.installed_version,
                "installed_version_original": self.installed_version_original,
                "purl": self.purl,
                "resolution_markers": list(assessment.resolution_markers),
            },
            "vulnerability": {
                "ghsa_id": self.ghsa_id,
                "cve_id": self.cve_id,
                "matched_range": self.vulnerable_range,
                "matched_clauses": clauses,
                "fixed_version": self.fixed_version,
                "fixed_version_original": self.fixed_version_original,
                "affected_status": assessment.result.value,
                "reason_code": assessment.reason_code,
            },
            "cvss": {
                "alias_state": nvd.alias.state.value,
                "nvd": nvd_payload,
                "metrics": metrics,
                "unsupported_families": unsupported_cvss,
            },
            "kev": {
                "state": self.kev_state.value,
                "snapshot": _kev_snapshot_payload(kev),
                "record": _kev_record_payload(self.kev_record),
            },
            "epss": {
                "state": self.epss_state.value,
                "snapshot": _epss_snapshot_payload(epss_snapshot),
                "record": _epss_record_payload(self.epss_record),
            },
            "evidence_chain": {
                "finding_id": self.base_finding.finding_id,
                "finding_sha256": self.base_finding.evidence_sha256,
                "nvd_enrichment_id": nvd.enrichment_id,
                "nvd_enrichment_sha256": nvd.evidence_sha256,
                "kev_enrichment_id": kev.enrichment_id,
                "kev_enrichment_sha256": kev.evidence_sha256,
                "epss_enrichment_id": self.evidence.enrichment_id,
                "epss_enrichment_sha256": self.evidence.evidence_sha256,
            },
        }
        return _canonical_json(payload)

    @property
    def evidence_sha256(self) -> str:
        """Return SHA-256 of the final finding projection."""
        return hashlib.sha256(self.canonical_json).hexdigest()

    @property
    def analysis_finding_id(self) -> str:
        """Return stable content-addressed identity for this final finding projection."""
        return f"repository-analysis-finding:v1@sha256:{self.evidence_sha256}"


@dataclass(frozen=True, slots=True)
class RepositoryAnalysisResult:
    """Final reproducible Phase 4 analysis for one immutable repository evidence chain."""

    source: RepositoryEpssEnrichmentEvidence
    findings: tuple[RepositoryAnalysisFinding, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Derive final findings exactly once from the validated EPSS evidence chain."""
        findings = tuple(
            RepositoryAnalysisFinding(evidence=evidence)
            for evidence in self.source.enriched_findings
        )
        finding_ids = [finding.analysis_finding_id for finding in findings]
        if len(set(finding_ids)) != len(finding_ids):
            raise InvalidRepositoryAnalysisResultError(
                "Final repository analysis findings must have unique identities."
            )
        object.__setattr__(self, "findings", findings)

    @property
    def file_evidence(self) -> ImmutableRepositoryFileEvidence:
        """Return exact inert dependency file evidence even when there are no findings."""
        return (
            self.source.previous.previous.scan.normalization_inventory
            .parsed_lock.file_evidence
        )

    @property
    def repository_snapshot(self) -> ImmutableRepositorySnapshot:
        """Return the immutable public GitHub snapshot analyzed by Phase 4."""
        return self.file_evidence.snapshot

    @property
    def snapshot_id(self) -> str:
        """Return immutable repository snapshot identity."""
        return self.repository_snapshot.snapshot_id

    @property
    def file_evidence_id(self) -> str:
        """Return immutable lockfile evidence identity."""
        return self.file_evidence.evidence_id

    @property
    def finding_count(self) -> int:
        """Return deterministic affected-finding count."""
        return len(self.findings)

    @property
    def canonical_json(self) -> bytes:
        """Return deterministic aggregate analysis JSON suitable for future cache keys."""
        snapshot = self.repository_snapshot
        repository = snapshot.repository
        scan = self.source.previous.previous.scan
        finding_payloads = [
            _decode_canonical_object(finding.canonical_json)
            for finding in self.findings
        ]
        payload: dict[str, object] = {
            "schema_version": _ANALYSIS_SCHEMA_VERSION,
            "engine": _ANALYSIS_ENGINE,
            "repository": {
                "provider": repository.provider.value,
                "repository_id": repository.repository_id,
                "full_name": repository.full_name,
                "requested_ref": snapshot.requested_ref,
                "commit_sha": snapshot.commit_sha,
                "tree_sha": snapshot.tree_sha,
                "snapshot_id": snapshot.snapshot_id,
            },
            "dependency_evidence": {
                "path": self.file_evidence.path,
                "file_evidence_id": self.file_evidence.evidence_id,
                "blob_sha": self.file_evidence.blob_sha,
                "content_sha256": self.file_evidence.content_sha256,
                "size_bytes": self.file_evidence.size_bytes,
            },
            "accounting": {
                "pypi_source_record_count": (
                    scan.normalization_inventory.pypi_source_record_count
                ),
                "supplied_ghsa_occurrence_count": scan.supplied_ghsa_occurrence_count,
                "candidate_evaluation_count": scan.candidate_evaluation_count,
                "unsupported_assessment_count": scan.unsupported_assessment_count,
                "unsupported_ghsa_join_count": len(scan.unsupported_ghsa_join),
                "affected_finding_count": scan.affected_count,
                "final_finding_count": self.finding_count,
            },
            "selected_threat_intelligence": {
                "kev_snapshot_sha256": self.source.previous.kev_snapshot.snapshot_sha256,
                "epss_snapshot": _epss_snapshot_payload(self.source.epss_snapshot),
            },
            "findings": finding_payloads,
            "analysis_finding_ids": [
                finding.analysis_finding_id for finding in self.findings
            ],
        }
        return _canonical_json(payload)

    @property
    def evidence_sha256(self) -> str:
        """Return SHA-256 of the complete final repository analysis projection."""
        return hashlib.sha256(self.canonical_json).hexdigest()

    @property
    def analysis_id(self) -> str:
        """Return deterministic reusable identity for the complete selected evidence chain."""
        return f"repository-analysis:v1@sha256:{self.evidence_sha256}"


def _cvss_payload(metric: NvdCvssMetric) -> dict[str, object]:
    """Project one preserved CVSS observation without applying preference policy."""
    return {
        "family": metric.family.value,
        "version": metric.version,
        "source": metric.source,
        "metric_type": metric.metric_type.value,
        "vector_string": metric.vector_string,
        "base_score": metric.base_score,
        "base_severity": metric.base_severity,
        "exploitability_score": metric.exploitability_score,
        "impact_score": metric.impact_score,
        "metric_json": metric.metric_json,
    }


def _kev_snapshot_payload(evidence: RepositoryKevEnrichedFinding) -> dict[str, object]:
    """Project exact complete KEV snapshot coordinates."""
    snapshot = evidence.kev_snapshot.snapshot
    return {
        "catalog_version": snapshot.catalog_version,
        "date_released": snapshot.date_released.isoformat(),
        "retrieved_at": snapshot.retrieved_at.isoformat(),
        "snapshot_date": snapshot.snapshot_date,
        "source_sha256": snapshot.sha256,
        "record_count": snapshot.record_count,
        "payload_size_bytes": snapshot.payload_size_bytes,
    }


def _kev_record_payload(record: SilverKevRecord | None) -> dict[str, object] | None:
    """Project exact positive KEV row evidence when present."""
    if record is None:
        return None
    return {
        "cve": record.cve,
        "vendor_project": record.vendor_project,
        "product": record.product,
        "vulnerability_name": record.vulnerability_name,
        "date_added": record.date_added.isoformat(),
        "required_action": record.required_action,
        "due_date": record.due_date.isoformat(),
        "known_ransomware_campaign_use": record.known_ransomware_campaign_use.value,
        "source_sha256": record.source_sha256,
        "snapshot_date": record.snapshot_date.isoformat(),
    }


def _epss_snapshot_payload(
    evidence: RepositoryEpssSnapshotEvidence,
) -> dict[str, object]:
    """Project exact selected EPSS snapshot coordinates from validated evidence."""
    snapshot = evidence.snapshot
    payload: dict[str, object] = {
        "kind": evidence.kind.value,
        "snapshot_date": evidence.snapshot_date.isoformat(),
        "model_version": evidence.model_version,
        "score_timestamp": (
            evidence.score_timestamp.isoformat()
            if evidence.score_timestamp is not None
            else None
        ),
        "source_sha256": snapshot.sha256,
        "row_count": snapshot.row_count,
        "payload_size_bytes": len(snapshot.raw_bytes),
    }
    if isinstance(snapshot, HistoricalEpssSnapshot):
        payload.update(
            {
                "model_era": snapshot.model_era.value,
                "source_shape": snapshot.source_shape.value,
                "source_metadata_present": snapshot.source_metadata_present,
                "percentile_available": snapshot.percentile_available,
            }
        )
    else:
        payload.update(
            {
                "model_era": None,
                "source_shape": "modern_metadata",
                "source_metadata_present": True,
                "percentile_available": True,
            }
        )
    return payload


def _epss_record_payload(record: SilverEpssRecord | None) -> dict[str, object] | None:
    """Project exact EPSS score evidence without threshold or ranking semantics."""
    if record is None:
        return None
    return {
        "cve": record.cve,
        "epss": record.epss,
        "percentile": record.percentile,
        "model_version": record.model_version,
        "score_timestamp": (
            record.score_timestamp.isoformat()
            if record.score_timestamp is not None
            else None
        ),
        "source": record.source,
        "source_sha256": record.source_sha256,
        "snapshot_date": record.snapshot_date.isoformat(),
    }


def _decode_canonical_object(value: bytes) -> dict[str, object]:
    """Decode an internally generated canonical JSON object for aggregate embedding."""
    try:
        parsed = cast(object, json.loads(value.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidRepositoryAnalysisResultError(
            "Final repository analysis contains invalid nested canonical JSON."
        ) from exc
    if not isinstance(parsed, dict):
        raise InvalidRepositoryAnalysisResultError(
            "Final repository analysis nested canonical JSON must be an object."
        )
    return cast(dict[str, object], parsed)


def _canonical_json(payload: dict[str, object]) -> bytes:
    """Encode the final repository analysis with deterministic Canonical JSON v1."""
    try:
        text = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise InvalidRepositoryAnalysisResultError(
            "Final repository analysis contains a non-canonicalizable value."
        ) from exc
    return text.encode("utf-8")
