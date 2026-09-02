"""Domain types for immutable repository intelligence evidence."""

from opslens.repository_intelligence.domain.errors import (
    InvalidGitHubSourceEvidenceError,
    InvalidRepositoryIdentityError,
    InvalidRepositorySnapshotError,
    RepositoryIntelligenceContractError,
    UnsupportedRepositoryVisibilityError,
)
from opslens.repository_intelligence.domain.models import (
    GitHubRepositoryIdentity,
    ImmutableRepositorySnapshot,
    RepositoryProvider,
    validate_github_repository_coordinates,
    validate_github_repository_ref,
)

__all__ = [
    "GitHubRepositoryIdentity",
    "ImmutableRepositorySnapshot",
    "InvalidGitHubSourceEvidenceError",
    "InvalidRepositoryIdentityError",
    "InvalidRepositorySnapshotError",
    "RepositoryIntelligenceContractError",
    "RepositoryProvider",
    "UnsupportedRepositoryVisibilityError",
    "validate_github_repository_coordinates",
    "validate_github_repository_ref",
]
