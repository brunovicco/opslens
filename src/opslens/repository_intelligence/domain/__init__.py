"""Domain types for immutable repository intelligence evidence."""

from opslens.repository_intelligence.domain.errors import (
    InvalidGitHubSourceEvidenceError,
    InvalidRepositoryFileEvidenceError,
    InvalidRepositoryIdentityError,
    InvalidRepositorySnapshotError,
    InvalidUvLockError,
    RepositoryIntelligenceContractError,
    UnsupportedRepositoryFileError,
    UnsupportedRepositoryVisibilityError,
    UnsupportedUvLockSchemaError,
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
from opslens.repository_intelligence.domain.pypi_normalization import (
    NormalizedRepositoryPyPIDependencyEvidence,
    RepositoryPyPINormalizationInventory,
    UnsupportedRepositoryPyPINormalizationEvidence,
)
from opslens.repository_intelligence.domain.uv_lock import (
    MAX_UV_LOCK_PACKAGE_RECORDS,
    PYPI_SIMPLE_REGISTRY_URL,
    SUPPORTED_UV_LOCK_REVISIONS,
    SUPPORTED_UV_LOCK_SCHEMA_VERSION,
    ParsedUvLockEvidence,
    UvLockedPyPIPackageEvidence,
    UvUnsupportedLockedPackageEvidence,
    UvUnsupportedPackageReason,
)

__all__ = [
    "MAX_REPOSITORY_FILE_BYTES",
    "MAX_UV_LOCK_PACKAGE_RECORDS",
    "PYPI_SIMPLE_REGISTRY_URL",
    "SUPPORTED_UV_LOCK_REVISIONS",
    "SUPPORTED_UV_LOCK_SCHEMA_VERSION",
    "UV_LOCK_PATH",
    "GitHubRepositoryIdentity",
    "ImmutableRepositoryFileEvidence",
    "ImmutableRepositorySnapshot",
    "InvalidGitHubSourceEvidenceError",
    "InvalidRepositoryFileEvidenceError",
    "InvalidRepositoryIdentityError",
    "InvalidRepositorySnapshotError",
    "InvalidUvLockError",
    "NormalizedRepositoryPyPIDependencyEvidence",
    "ParsedUvLockEvidence",
    "RepositoryIntelligenceContractError",
    "RepositoryProvider",
    "RepositoryPyPINormalizationInventory",
    "UnsupportedRepositoryFileError",
    "UnsupportedRepositoryPyPINormalizationEvidence",
    "UnsupportedRepositoryVisibilityError",
    "UnsupportedUvLockSchemaError",
    "UvLockedPyPIPackageEvidence",
    "UvUnsupportedLockedPackageEvidence",
    "UvUnsupportedPackageReason",
    "compute_content_sha256",
    "compute_git_blob_sha1",
    "validate_github_repository_coordinates",
    "validate_github_repository_ref",
    "validate_repository_evidence_path",
]
