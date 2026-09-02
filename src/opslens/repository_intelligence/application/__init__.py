"""Application services for bounded repository intelligence acquisition."""

from opslens.repository_intelligence.application.file_acquisition import (
    GitHubUvLockSource,
    acquire_uv_lock_evidence,
)
from opslens.repository_intelligence.application.pypi_normalization import (
    normalize_uv_lock_pypi_dependencies,
)
from opslens.repository_intelligence.application.snapshot_resolution import (
    GitHubRepositorySnapshotSource,
    GitHubSnapshotResolutionEvidence,
    resolve_github_repository_snapshot,
)

__all__ = [
    "GitHubRepositorySnapshotSource",
    "GitHubSnapshotResolutionEvidence",
    "GitHubUvLockSource",
    "acquire_uv_lock_evidence",
    "normalize_uv_lock_pypi_dependencies",
    "resolve_github_repository_snapshot",
]
