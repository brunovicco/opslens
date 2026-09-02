"""Acquire one allowlisted inert repository file at an exact immutable snapshot."""

from __future__ import annotations

from typing import Protocol

from opslens.repository_intelligence.adapters.github_file import (
    project_github_uv_lock_evidence,
)
from opslens.repository_intelligence.domain import (
    ImmutableRepositoryFileEvidence,
    ImmutableRepositorySnapshot,
)


class GitHubUvLockSource(Protocol):
    """Read-only source operation required for the first repository file gate."""

    def get_uv_lock(
        self,
        owner: str,
        name: str,
        commit_sha: str,
    ) -> dict[str, object]:
        """Return the GitHub Contents payload for `uv.lock` at an exact commit SHA."""
        ...


def acquire_uv_lock_evidence(
    source: GitHubUvLockSource,
    *,
    snapshot: ImmutableRepositorySnapshot,
) -> ImmutableRepositoryFileEvidence:
    """Acquire and verify inert `uv.lock` bytes using snapshot commit authority only."""
    payload = source.get_uv_lock(
        snapshot.repository.owner,
        snapshot.repository.name,
        snapshot.commit_sha,
    )
    return project_github_uv_lock_evidence(
        snapshot=snapshot,
        payload=payload,
    )
