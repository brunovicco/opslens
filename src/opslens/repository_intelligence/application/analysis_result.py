"""Build the final deterministic Phase 4 repository-analysis projection."""

from opslens.repository_intelligence.domain.analysis_result import (
    RepositoryAnalysisResult,
)
from opslens.repository_intelligence.domain.epss_enrichment import (
    RepositoryEpssEnrichmentEvidence,
)


def build_repository_analysis_result(
    source: RepositoryEpssEnrichmentEvidence,
) -> RepositoryAnalysisResult:
    """Project validated repository evidence without introducing new risk authority."""
    return RepositoryAnalysisResult(source=source)
