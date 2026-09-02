"""Resolve immutable GitHub snapshots through a narrow read-only source contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from opslens.repository_intelligence.adapters.github import (
    GitHubRepositoryMetadataEvidence,
    project_github_commit_snapshot,
    project_github_repository_metadata,
)
from opslens.repository_intelligence.domain import (
    ImmutableRepositorySnapshot,
    validate_github_repository_coordinates,
    validate_github_repository_ref,
)


class GitHubRepositorySnapshotSource(Protocol):
    """Read-only source operations required to resolve one GitHub snapshot."""

    def get_repository(self, owner: str, name: str) -> dict[str, object]:
        """Return one GitHub repository metadata payload."""
        ...

    def get_commit(self, owner: str, name: str, ref: str) -> dict[str, object]:
        """Return one GitHub commit payload for a validated ref."""
        ...


@dataclass(frozen=True, slots=True)
class GitHubSnapshotResolutionEvidence:
    """Preserve request coordinates and the exact immutable resolution result."""

    requested_owner: str
    requested_name: str
    used_default_branch: bool
    metadata: GitHubRepositoryMetadataEvidence
    snapshot: ImmutableRepositorySnapshot


def resolve_github_repository_snapshot(
    source: GitHubRepositorySnapshotSource,
    *,
    owner: str,
    name: str,
    requested_ref: str | None = None,
) -> GitHubSnapshotResolutionEvidence:
    """Resolve one public GitHub repository request to an exact immutable commit snapshot."""
    requested_owner, requested_name = validate_github_repository_coordinates(owner, name)

    repository_payload = source.get_repository(requested_owner, requested_name)
    metadata = project_github_repository_metadata(repository_payload)

    used_default_branch = requested_ref is None
    effective_ref = metadata.default_branch if used_default_branch else requested_ref
    assert effective_ref is not None
    effective_ref = validate_github_repository_ref(effective_ref)

    commit_payload = source.get_commit(
        metadata.repository.owner,
        metadata.repository.name,
        effective_ref,
    )
    snapshot = project_github_commit_snapshot(
        metadata=metadata,
        requested_ref=effective_ref,
        payload=commit_payload,
    )

    return GitHubSnapshotResolutionEvidence(
        requested_owner=requested_owner,
        requested_name=requested_name,
        used_default_branch=used_default_branch,
        metadata=metadata,
        snapshot=snapshot,
    )
