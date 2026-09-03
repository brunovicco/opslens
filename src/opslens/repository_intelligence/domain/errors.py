"""Fail-closed errors for immutable repository snapshot evidence."""


class RepositoryIntelligenceContractError(ValueError):
    """Base error for repository evidence outside the frozen Phase 4 contract."""

    reason_code = "invalid_repository_evidence"


class InvalidRepositoryIdentityError(RepositoryIntelligenceContractError):
    """Raised when repository identity fields are malformed or inconsistent."""

    reason_code = "invalid_repository_identity"


class UnsupportedRepositoryVisibilityError(RepositoryIntelligenceContractError):
    """Raised when a repository visibility is outside the public-only v1 contract."""

    reason_code = "unsupported_repository_visibility"


class InvalidRepositorySnapshotError(RepositoryIntelligenceContractError):
    """Raised when an immutable repository snapshot cannot be established exactly."""

    reason_code = "invalid_repository_snapshot"


class InvalidGitHubSourceEvidenceError(RepositoryIntelligenceContractError):
    """Raised when GitHub REST evidence is malformed or missing required fields."""

    reason_code = "invalid_github_source_evidence"


class InvalidRepositoryFileEvidenceError(RepositoryIntelligenceContractError):
    """Raised when immutable repository file evidence fails integrity validation."""

    reason_code = "invalid_repository_file_evidence"


class UnsupportedRepositoryFileError(RepositoryIntelligenceContractError):
    """Raised when a repository path is outside the Phase 4 v1 evidence allowlist."""

    reason_code = "unsupported_repository_file"


class InvalidUvLockError(RepositoryIntelligenceContractError):
    """Raised when verified `uv.lock` bytes violate the supported parser contract."""

    reason_code = "invalid_uv_lock"


class UnsupportedUvLockSchemaError(InvalidUvLockError):
    """Raised when a valid lockfile declares unsupported schema semantics."""

    reason_code = "unsupported_uv_lock_schema"


class InvalidRepositoryVulnerabilityScanError(RepositoryIntelligenceContractError):
    """Raised when repository/GHSA evidence cannot form one deterministic scan."""

    reason_code = "invalid_repository_vulnerability_scan"


class RepositoryVulnerabilityScanLimitError(InvalidRepositoryVulnerabilityScanError):
    """Raised when a deterministic repository vulnerability scan exceeds a hard bound."""

    reason_code = "repository_vulnerability_scan_limit_exceeded"
