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
