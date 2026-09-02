"""Domain types for immutable repository intelligence evidence."""

from opslens.repository_intelligence.domain.errors import (
    InvalidGitHubSourceEvidenceError,
    InvalidRepositoryFileEvidenceError,
    InvalidRepositoryIdentityError,
    InvalidRepositorySnapshotError,
    RepositoryIntelligenceContractError,
    UnsupportedRepositoryFileError,
    UnsupportedRepositoryVisibilityError,
)
from opslens.repository_intelligence.domain.file_evidence import (
    MAX_REPOSITORY_FILE_BYTES,
    UV_LOCK_PATH,
    ImmutableRepositoryFileEvidence,
    compute_content_sha256,
    compute_git_blob_sha1,
    validate_repository_evidence_path,
)
from opslens.repository_intelligence.domain.models import (
    GitHubRepositoryIdentity,
    ImmutableRepositorySnapshot,
    RepositoryProvider,
    validate_github_repository_coordinates,
    validate_github_repository_ref,
)

__all__ = [
    "MAX_REPOSITORY_FILE_BYTES",
    "UV_LOCK_PATH",
    "GitHubRepositoryIdentity",
    "ImmutableRepositoryFileEvidence",
    "ImmutableRepositorySnapshot",
    "InvalidGitHubSourceEvidenceError",
    "InvalidRepositoryFileEvidenceError",
    "InvalidRepositoryIdentityError",
    "InvalidRepositorySnapshotError",
    "RepositoryIntelligenceContractError",
    "RepositoryProvider",
    "UnsupportedRepositoryFileError",
    "UnsupportedRepositoryVisibilityError",
    "compute_content_sha256",
    "compute_git_blob_sha1",
    "validate_github_repository_coordinates",
    "validate_github_repository_ref",
    "validate_repository_evidence_path",
]
