"""Project GitHub REST metadata and commit payloads into Phase 4 domain evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import cast

from opslens.repository_intelligence.domain import (
    GitHubRepositoryIdentity,
    ImmutableRepositorySnapshot,
    InvalidGitHubSourceEvidenceError,
)

_CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x1f\x7f]", re.ASCII)


@dataclass(frozen=True, slots=True)
class GitHubRepositoryMetadataEvidence:
    """Validated repository metadata required before resolving one immutable snapshot."""

    repository: GitHubRepositoryIdentity
    default_branch: str


def project_github_repository_metadata(
    payload: dict[str, object],
) -> GitHubRepositoryMetadataEvidence:
    """Project one GitHub `GET /repos/{owner}/{repo}` response into typed evidence."""
    repository_id = _required_int(payload, "id")
    name = _required_str(payload, "name")
    full_name = _required_str(payload, "full_name")
    is_private = _required_bool(payload, "private")
    default_branch = _required_clean_ref(payload, "default_branch")

    owner_payload = _required_object(payload, "owner")
    owner = _required_str(owner_payload, "login")

    repository = GitHubRepositoryIdentity(
        repository_id=repository_id,
        owner=owner,
        name=name,
        full_name=full_name,
        is_private=is_private,
    )
    return GitHubRepositoryMetadataEvidence(
        repository=repository,
        default_branch=default_branch,
    )


def project_github_commit_snapshot(
    *,
    metadata: GitHubRepositoryMetadataEvidence,
    requested_ref: str,
    payload: dict[str, object],
) -> ImmutableRepositorySnapshot:
    """Project one GitHub commit response into an immutable repository snapshot."""
    commit_sha = _required_str(payload, "sha")
    commit_payload = _required_object(payload, "commit")
    tree_payload = _required_object(commit_payload, "tree")
    tree_sha = _required_str(tree_payload, "sha")

    return ImmutableRepositorySnapshot(
        repository=metadata.repository,
        requested_ref=requested_ref,
        commit_sha=commit_sha,
        tree_sha=tree_sha,
    )


def _required_object(payload: dict[str, object], field: str) -> dict[str, object]:
    """Return one required JSON object with a stable source-evidence error on mismatch."""
    value = payload.get(field)
    if not isinstance(value, dict):
        raise InvalidGitHubSourceEvidenceError(
            f"GitHub source field {field!r} must contain an object."
        )
    return cast(dict[str, object], value)


def _required_str(payload: dict[str, object], field: str) -> str:
    """Return one required non-empty string without source-value rewriting."""
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise InvalidGitHubSourceEvidenceError(
            f"GitHub source field {field!r} must contain a non-empty string."
        )
    return value


def _required_int(payload: dict[str, object], field: str) -> int:
    """Return one required integer while rejecting JSON booleans as identities."""
    value = payload.get(field)
    if type(value) is not int:
        raise InvalidGitHubSourceEvidenceError(
            f"GitHub source field {field!r} must contain an integer."
        )
    return value


def _required_bool(payload: dict[str, object], field: str) -> bool:
    """Return one required JSON boolean."""
    value = payload.get(field)
    if type(value) is not bool:
        raise InvalidGitHubSourceEvidenceError(
            f"GitHub source field {field!r} must contain a boolean."
        )
    return value


def _required_clean_ref(payload: dict[str, object], field: str) -> str:
    """Validate one source-provided ref before it can be used for commit resolution."""
    value = _required_str(payload, field)
    if (
        value != value.strip()
        or _CONTROL_CHARACTER_PATTERN.search(value) is not None
        or len(value) > 1024
    ):
        raise InvalidGitHubSourceEvidenceError(
            f"GitHub source field {field!r} is not a clean bounded ref token."
        )
    return value
