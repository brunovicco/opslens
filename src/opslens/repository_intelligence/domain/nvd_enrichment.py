"""Exact NVD and CVSS enrichment evidence for affected repository findings."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import cast

from opslens.correlation.domain.aliases import (
    CveAliasLinkState,
    CveAliasReconciliationEvidence,
)
from opslens.repository_intelligence.domain.errors import (
    InvalidRepositoryNvdEnrichmentError,
    RepositoryNvdEnrichmentLimitError,
)
from opslens.repository_intelligence.domain.vulnerability_findings import (
    MAX_GHSA_VULNERABILITY_OCCURRENCES,
    RepositoryPyPIVulnerabilityFinding,
    RepositoryVulnerabilityScanEvidence,
)
from opslens.transformation.nvd.domain.cvss_transformer import (
    NvdCvssMetricsTransformer,
)
from opslens.transformation.nvd.domain.models import (
    NvdCveCoreRecord,
    NvdCvssMetric,
    NvdCvssMetrics,
)

MAX_NVD_ENRICHMENT_RECORDS = 50_000
_ENRICHMENT_SCHEMA_VERSION = "1"
_ENRICHMENT_ENGINE = "opslens.phase4.repository-nvd-cvss.v1"


@dataclass(frozen=True, slots=True)
class RepositoryNvdCvssEvidence:
    """Bind normalized CVSS evidence to one exact immutable NVD CVE observation."""

    nvd: NvdCveCoreRecord
    cvss: NvdCvssMetrics

    def __post_init__(self) -> None:
        """Reject detached CVSS evidence by deriving the expected metrics again."""
        expected = _derive_cvss_from_exact_nvd_source(self.nvd)
        if self.cvss != expected:
            raise InvalidRepositoryNvdEnrichmentError(
                "Repository NVD CVSS evidence is detached from the exact NVD source version."
            )


@dataclass(frozen=True, slots=True)
class RepositoryNvdEnrichedFinding:
    """Attach source-preserving CVE/NVD/CVSS evidence to one affected finding."""

    finding: RepositoryPyPIVulnerabilityFinding
    alias: CveAliasReconciliationEvidence
    nvd_cvss: RepositoryNvdCvssEvidence | None

    def __post_init__(self) -> None:
        """Validate exact GHSA binding and NVD presence semantics."""
        assessment = self.finding.assessment
        expected_ghsa_fields = (
            (self.alias.ghsa_id, assessment.ghsa_id, "GHSA id"),
            (
                self.alias.ghsa_observed_advisory_version_id,
                assessment.observed_advisory_version_id,
                "GHSA observed advisory version",
            ),
            (
                self.alias.ghsa_source_advisory_sha256,
                assessment.source_advisory_sha256,
                "GHSA advisory source hash",
            ),
            (
                self.alias.ghsa_vulnerability_entry_id,
                assessment.vulnerability_entry_id,
                "GHSA vulnerability entry",
            ),
        )
        for observed, expected, field_name in expected_ghsa_fields:
            if observed != expected:
                raise InvalidRepositoryNvdEnrichmentError(
                    f"Repository NVD enrichment disagrees on {field_name}."
                )

        has_nvd_state = self.alias.state in {
            CveAliasLinkState.NVD_OBSERVED,
            CveAliasLinkState.NVD_REJECTED,
        }
        if has_nvd_state != (self.nvd_cvss is not None):
            raise InvalidRepositoryNvdEnrichmentError(
                "NVD-linked alias states require exact NVD/CVSS evidence and only those states may carry it."
            )

        if self.nvd_cvss is not None:
            self._validate_nvd_binding(self.nvd_cvss.nvd)
        else:
            self._validate_absent_nvd_binding()

    def _validate_nvd_binding(self, nvd: NvdCveCoreRecord) -> None:
        """Require alias coordinates to match the exact supplied NVD observation."""
        observed = nvd.observed_version
        expected_pairs = (
            (self.alias.github_cve_id, observed.cve_id, "GitHub CVE assertion"),
            (self.alias.nvd_cve_id, observed.cve_id, "NVD CVE id"),
            (
                self.alias.nvd_observed_cve_version_id,
                observed.observed_cve_version_id,
                "NVD observed CVE version",
            ),
            (
                self.alias.nvd_source_cve_sha256,
                observed.source_cve_sha256,
                "NVD source hash",
            ),
            (
                self.alias.nvd_source_identifier,
                nvd.source_identifier,
                "NVD source identifier",
            ),
            (
                self.alias.nvd_vulnerability_status,
                nvd.vuln_status.value,
                "NVD vulnerability status",
            ),
        )
        for alias_value, nvd_value, field_name in expected_pairs:
            if alias_value != nvd_value:
                raise InvalidRepositoryNvdEnrichmentError(
                    f"Repository NVD enrichment disagrees on {field_name}."
                )

    def _validate_absent_nvd_binding(self) -> None:
        """Ensure non-NVD alias states do not smuggle NVD coordinates."""
        nvd_values = (
            self.alias.nvd_cve_id,
            self.alias.nvd_observed_cve_version_id,
            self.alias.nvd_source_cve_sha256,
            self.alias.nvd_source_identifier,
            self.alias.nvd_vulnerability_status,
        )
        if any(value is not None for value in nvd_values):
            raise InvalidRepositoryNvdEnrichmentError(
                "Alias states without NVD evidence cannot contain NVD coordinates."
            )
        if self.alias.state is CveAliasLinkState.NO_GITHUB_CVE:
            if self.alias.github_cve_id is not None:
                raise InvalidRepositoryNvdEnrichmentError(
                    "A no-GitHub-CVE alias state cannot contain a GitHub CVE assertion."
                )
        elif self.alias.state is CveAliasLinkState.GITHUB_ASSERTED_ONLY:
            if self.alias.github_cve_id is None:
                raise InvalidRepositoryNvdEnrichmentError(
                    "A GitHub-asserted-only alias state requires a GitHub CVE assertion."
                )
        else:
            raise InvalidRepositoryNvdEnrichmentError(
                "Unsupported alias state without NVD evidence in repository enrichment."
            )

    @property
    def canonical_json(self) -> bytes:
        """Return stable canonical JSON for this immutable enrichment record."""
        alias_payload: dict[str, object] = {
            "state": self.alias.state.value,
            "reason_code": self.alias.reason_code,
            "ghsa_id": self.alias.ghsa_id,
            "ghsa_observed_advisory_version_id": (
                self.alias.ghsa_observed_advisory_version_id
            ),
            "ghsa_source_advisory_sha256": self.alias.ghsa_source_advisory_sha256,
            "ghsa_vulnerability_entry_id": self.alias.ghsa_vulnerability_entry_id,
            "github_cve_id": self.alias.github_cve_id,
            "nvd_cve_id": self.alias.nvd_cve_id,
            "nvd_observed_cve_version_id": self.alias.nvd_observed_cve_version_id,
            "nvd_source_cve_sha256": self.alias.nvd_source_cve_sha256,
            "nvd_source_identifier": self.alias.nvd_source_identifier,
            "nvd_vulnerability_status": self.alias.nvd_vulnerability_status,
        }
        payload: dict[str, object] = {
            "schema_version": _ENRICHMENT_SCHEMA_VERSION,
            "engine": _ENRICHMENT_ENGINE,
            "base_finding": {
                "finding_id": self.finding.finding_id,
                "evidence_sha256": self.finding.evidence_sha256,
            },
            "cve_alias": alias_payload,
            "nvd": self._nvd_payload(),
        }
        return _canonical_json(payload)

    def _nvd_payload(self) -> dict[str, object] | None:
        """Serialize exact NVD source coordinates and every normalized CVSS observation."""
        if self.nvd_cvss is None:
            return None

        nvd = self.nvd_cvss.nvd
        observed = nvd.observed_version
        metrics: list[object] = [
            _cvss_metric_payload(metric)
            for metric in self.nvd_cvss.cvss.metrics
        ]
        return {
            "cve_id": observed.cve_id,
            "observed_cve_version_id": observed.observed_cve_version_id,
            "source_cve_sha256": observed.source_cve_sha256,
            "source_identifier": nvd.source_identifier,
            "vulnerability_status": nvd.vuln_status.value,
            "published_at": nvd.published_at.isoformat(),
            "last_modified_at": nvd.last_modified_at.isoformat(),
            "cvss_metrics": metrics,
            "unsupported_cvss_families": list(
                self.nvd_cvss.cvss.unsupported_cvss_families
            ),
        }

    @property
    def evidence_sha256(self) -> str:
        """Return the SHA-256 of canonical repository NVD enrichment evidence."""
        return hashlib.sha256(self.canonical_json).hexdigest()

    @property
    def enrichment_id(self) -> str:
        """Return the content-addressed identity without changing the base finding id."""
        return f"repository-finding-enrichment:v1@sha256:{self.evidence_sha256}"


@dataclass(frozen=True, slots=True)
class RepositoryNvdEnrichmentEvidence:
    """Bounded complete NVD/CVSS enrichment accounting for affected scan findings."""

    scan: RepositoryVulnerabilityScanEvidence
    supplied_ghsa_rehydration_count: int
    supplied_nvd_record_count: int
    enriched_findings: tuple[RepositoryNvdEnrichedFinding, ...]

    def __post_init__(self) -> None:
        """Require bounded input accounting and exactly one enrichment per finding."""
        _validate_count(
            self.supplied_ghsa_rehydration_count,
            field="supplied_ghsa_rehydration_count",
        )
        _validate_count(
            self.supplied_nvd_record_count,
            field="supplied_nvd_record_count",
        )
        if self.supplied_ghsa_rehydration_count > MAX_GHSA_VULNERABILITY_OCCURRENCES:
            raise RepositoryNvdEnrichmentLimitError(
                "Repository NVD enrichment exceeds the GHSA rehydration bound."
            )
        if self.supplied_nvd_record_count > MAX_NVD_ENRICHMENT_RECORDS:
            raise RepositoryNvdEnrichmentLimitError(
                "Repository NVD enrichment exceeds the NVD observation bound."
            )

        observed_findings = tuple(
            enriched.finding for enriched in self.enriched_findings
        )
        if observed_findings != self.scan.findings:
            raise InvalidRepositoryNvdEnrichmentError(
                "Repository NVD enrichment must preserve every affected finding exactly once and in order."
            )

        enrichment_ids = [
            enriched.enrichment_id for enriched in self.enriched_findings
        ]
        if len(set(enrichment_ids)) != len(enrichment_ids):
            raise InvalidRepositoryNvdEnrichmentError(
                "Repository NVD enrichment records must have unique content-addressed identities."
            )

    @property
    def nvd_linked_count(self) -> int:
        """Return findings linked to an exact supplied NVD observation."""
        return sum(enriched.nvd_cvss is not None for enriched in self.enriched_findings)

    @property
    def cvss_metric_count(self) -> int:
        """Return all preserved NVD CVSS metric observations without selecting one."""
        return sum(
            len(enriched.nvd_cvss.cvss.metrics)
            if enriched.nvd_cvss is not None
            else 0
            for enriched in self.enriched_findings
        )


def derive_repository_nvd_cvss_evidence(
    nvd: NvdCveCoreRecord,
) -> RepositoryNvdCvssEvidence:
    """Derive CVSS only from the exact canonical NVD source bound to the core record."""
    return RepositoryNvdCvssEvidence(
        nvd=nvd,
        cvss=_derive_cvss_from_exact_nvd_source(nvd),
    )


def _derive_cvss_from_exact_nvd_source(nvd: NvdCveCoreRecord) -> NvdCvssMetrics:
    """Re-run the existing Phase 2 CVSS transformer on exact canonical NVD content."""
    try:
        parsed = cast(object, json.loads(nvd.observed_version.canonical_json.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidRepositoryNvdEnrichmentError(
            "Exact NVD source content is not valid UTF-8 JSON."
        ) from exc

    if not isinstance(parsed, dict):
        raise InvalidRepositoryNvdEnrichmentError(
            "Exact NVD source content must contain a JSON object."
        )

    source_cve = cast(dict[str, object], parsed)
    try:
        return NvdCvssMetricsTransformer().transform(source_cve)
    except ValueError as exc:
        raise InvalidRepositoryNvdEnrichmentError(
            "Exact NVD source content cannot produce deterministic CVSS evidence."
        ) from exc


def _cvss_metric_payload(metric: NvdCvssMetric) -> dict[str, object]:
    """Preserve every normalized CVSS field without applying a ranking policy."""
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


def _canonical_json(payload: dict[str, object]) -> bytes:
    """Encode repository enrichment evidence with deterministic Canonical JSON v1."""
    try:
        text = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise InvalidRepositoryNvdEnrichmentError(
            "Repository NVD enrichment contains a non-canonicalizable value."
        ) from exc
    return text.encode("utf-8")


def _validate_count(value: int, *, field: str) -> None:
    """Reject booleans and negative evidence counts."""
    if type(value) is not int or value < 0:
        raise InvalidRepositoryNvdEnrichmentError(
            f"Repository NVD enrichment field {field!r} must be non-negative."
        )
