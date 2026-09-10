"""Compose retained deterministic repository-analysis stages for Gate 19.2."""

from __future__ import annotations

from dataclasses import dataclass

from opslens.correlation.adapters.ghsa import GhsaPyPIVulnerabilityEvidence
from opslens.ingestion.epss.domain.history import HistoricalEpssSnapshot
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.public_analysis.domain import (
    PublicAnalysisValidationError,
    PublicRepositoryEvidenceExecution,
)
from opslens.repository_intelligence.application import (
    build_repository_analysis_result,
    build_repository_pypi_vulnerability_scan,
    enrich_repository_findings_with_epss,
    enrich_repository_findings_with_kev,
    enrich_repository_findings_with_nvd,
)
from opslens.repository_intelligence.domain import RepositoryAnalysisResult
from opslens.repository_intelligence.domain.epss_enrichment import (
    RepositoryEpssEnrichmentEvidence,
)
from opslens.repository_intelligence.domain.kev_enrichment import (
    RepositoryKevEnrichmentEvidence,
)
from opslens.repository_intelligence.domain.nvd_enrichment import (
    RepositoryNvdEnrichmentEvidence,
)
from opslens.repository_intelligence.domain.vulnerability_findings import (
    RepositoryVulnerabilityScanEvidence,
)
from opslens.transformation.nvd.domain.models import NvdCveCoreRecord


@dataclass(frozen=True, slots=True)
class RepresentativeRepositoryThreatEvidence:
    """Exact source evidence required to reproduce one deterministic repository analysis."""

    ghsa_vulnerabilities: tuple[GhsaPyPIVulnerabilityEvidence, ...]
    nvd_records: tuple[NvdCveCoreRecord, ...]
    kev_snapshot: KevCatalogSnapshot
    epss_snapshot: EpssSnapshot | HistoricalEpssSnapshot

    def __post_init__(self) -> None:
        """Reject untyped collections or snapshots before deterministic composition."""
        if type(self.ghsa_vulnerabilities) is not tuple or any(
            type(item) is not GhsaPyPIVulnerabilityEvidence
            for item in self.ghsa_vulnerabilities
        ):
            raise PublicAnalysisValidationError(
                "representative GHSA evidence must be a typed tuple"
            )
        if type(self.nvd_records) is not tuple or any(
            type(item) is not NvdCveCoreRecord for item in self.nvd_records
        ):
            raise PublicAnalysisValidationError(
                "representative NVD evidence must be a typed tuple"
            )
        if type(self.kev_snapshot) is not KevCatalogSnapshot:
            raise PublicAnalysisValidationError(
                "representative KEV evidence must be one complete typed snapshot"
            )
        if type(self.epss_snapshot) not in {EpssSnapshot, HistoricalEpssSnapshot}:
            raise PublicAnalysisValidationError(
                "representative EPSS evidence must be one exact typed snapshot"
            )


@dataclass(frozen=True, slots=True)
class RepresentativeRepositoryAnalysis:
    """Complete deterministic repository finding/enrichment projection for one public request."""

    source_execution: PublicRepositoryEvidenceExecution
    vulnerability_scan: RepositoryVulnerabilityScanEvidence
    nvd_enrichment: RepositoryNvdEnrichmentEvidence
    kev_enrichment: RepositoryKevEnrichmentEvidence
    epss_enrichment: RepositoryEpssEnrichmentEvidence
    analysis: RepositoryAnalysisResult

    def __post_init__(self) -> None:
        """Require the final analysis to remain bound to the supplied public evidence chain."""
        if type(self.source_execution) is not PublicRepositoryEvidenceExecution:
            raise PublicAnalysisValidationError(
                "representative analysis requires verified public repository evidence"
            )
        if self.vulnerability_scan.normalization_inventory != (
            self.source_execution.normalization_inventory
        ):
            raise PublicAnalysisValidationError(
                "representative vulnerability scan drifted from public repository evidence"
            )
        if self.nvd_enrichment.scan != self.vulnerability_scan:
            raise PublicAnalysisValidationError(
                "representative NVD enrichment drifted from vulnerability scan"
            )
        if self.kev_enrichment.previous != self.nvd_enrichment:
            raise PublicAnalysisValidationError(
                "representative KEV enrichment drifted from NVD evidence"
            )
        if self.epss_enrichment.previous != self.kev_enrichment:
            raise PublicAnalysisValidationError(
                "representative EPSS enrichment drifted from KEV evidence"
            )
        if self.analysis.source != self.epss_enrichment:
            raise PublicAnalysisValidationError(
                "representative analysis result drifted from EPSS evidence"
            )


def build_representative_repository_analysis(
    *,
    execution: PublicRepositoryEvidenceExecution,
    threat_evidence: RepresentativeRepositoryThreatEvidence,
) -> RepresentativeRepositoryAnalysis:
    """Reuse Phase 3/4 truth to build one deterministic analysis without new authority."""
    if type(execution) is not PublicRepositoryEvidenceExecution:
        raise PublicAnalysisValidationError(
            "representative repository analysis requires admitted public evidence"
        )
    if type(threat_evidence) is not RepresentativeRepositoryThreatEvidence:
        raise PublicAnalysisValidationError(
            "representative repository analysis requires typed threat evidence"
        )

    vulnerability_scan = build_repository_pypi_vulnerability_scan(
        execution.normalization_inventory,
        threat_evidence.ghsa_vulnerabilities,
    )
    nvd_enrichment = enrich_repository_findings_with_nvd(
        vulnerability_scan,
        threat_evidence.ghsa_vulnerabilities,
        threat_evidence.nvd_records,
    )
    kev_enrichment = enrich_repository_findings_with_kev(
        nvd_enrichment,
        threat_evidence.kev_snapshot,
    )
    epss_enrichment = enrich_repository_findings_with_epss(
        kev_enrichment,
        threat_evidence.epss_snapshot,
    )
    analysis = build_repository_analysis_result(epss_enrichment)

    return RepresentativeRepositoryAnalysis(
        source_execution=execution,
        vulnerability_scan=vulnerability_scan,
        nvd_enrichment=nvd_enrichment,
        kev_enrichment=kev_enrichment,
        epss_enrichment=epss_enrichment,
        analysis=analysis,
    )
