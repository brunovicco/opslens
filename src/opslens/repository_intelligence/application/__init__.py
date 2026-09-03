"""Application services for bounded repository intelligence acquisition."""

from opslens.repository_intelligence.application.analysis_result import (
    build_repository_analysis_result,
)
from opslens.repository_intelligence.application.epss_enrichment import (
    enrich_repository_findings_with_epss,
)
from opslens.repository_intelligence.application.file_acquisition import (
    GitHubUvLockSource,
    acquire_uv_lock_evidence,
)
from opslens.repository_intelligence.application.kev_enrichment import (
    enrich_repository_findings_with_kev,
)
from opslens.repository_intelligence.application.nvd_enrichment import (
    enrich_repository_findings_with_nvd,
)
from opslens.repository_intelligence.application.pypi_normalization import (
    normalize_uv_lock_pypi_dependencies,
)
from opslens.repository_intelligence.application.snapshot_resolution import (
    GitHubRepositorySnapshotSource,
    GitHubSnapshotResolutionEvidence,
    resolve_github_repository_snapshot,
)
from opslens.repository_intelligence.application.vulnerability_findings import (
    build_repository_pypi_vulnerability_scan,
)

__all__ = [
    "GitHubRepositorySnapshotSource",
    "GitHubSnapshotResolutionEvidence",
    "GitHubUvLockSource",
    "acquire_uv_lock_evidence",
    "build_repository_analysis_result",
    "build_repository_pypi_vulnerability_scan",
    "enrich_repository_findings_with_epss",
    "enrich_repository_findings_with_kev",
    "enrich_repository_findings_with_nvd",
    "normalize_uv_lock_pypi_dependencies",
    "resolve_github_repository_snapshot",
]