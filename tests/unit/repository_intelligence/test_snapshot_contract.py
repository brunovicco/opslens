"""Tests for the Phase 4 public GitHub immutable snapshot contract."""

from __future__ import annotations

from dataclasses import replace

import pytest

from opslens.repository_intelligence.domain import (
    GitHubRepositoryIdentity,
    ImmutableRepositorySnapshot,
    InvalidRepositoryIdentityError,
    InvalidRepositorySnapshotError,
    RepositoryProvider,
    UnsupportedRepositoryVisibilityError,
)

_REPOSITORY_ID = 1_333_092_779
_COMMIT_SHA = "a" * 40
_TREE_SHA = "b" * 40


def _repository(**overrides: object) -> GitHubRepositoryIdentity:
    """Build one valid public GitHub repository identity."""
    values: dict[str, object] = {
        "repository_id": _REPOSITORY_ID,
        "owner": "brunovicco",
        "name": "opslens",
        "full_name": "brunovicco/opslens",
        "is_private": False,
    }
    values.update(overrides)
    return GitHubRepositoryIdentity(
        repository_id=values["repository_id"],  # type: ignore[arg-type]
        owner=values["owner"],  # type: ignore[arg-type]
        name=values["name"],  # type: ignore[arg-type]
        full_name=values["full_name"],  # type: ignore[arg-type]
        is_private=values["is_private"],  # type: ignore[arg-type]
    )


def _snapshot(
    *,
    repository: GitHubRepositoryIdentity | None = None,
    requested_ref: str = "main",
    commit_sha: str = _COMMIT_SHA,
    tree_sha: str = _TREE_SHA,
) -> ImmutableRepositorySnapshot:
    """Build one valid immutable repository snapshot."""
    return ImmutableRepositorySnapshot(
        repository=repository or _repository(),
        requested_ref=requested_ref,
        commit_sha=commit_sha,
        tree_sha=tree_sha,
    )


def test_public_github_repository_identity_is_typed_and_stable() -> None:
    """Use numeric GitHub identity as the stable source key."""
    repository = _repository()

    assert repository.provider is RepositoryProvider.GITHUB
    assert repository.repository_key == f"github:{_REPOSITORY_ID}"
    assert repository.full_name == "brunovicco/opslens"


def test_private_repository_fails_closed() -> None:
    """Keep Phase 4 v1 public-only instead of silently accepting private inputs."""
    with pytest.raises(UnsupportedRepositoryVisibilityError) as exc_info:
        _repository(is_private=True)

    assert exc_info.value.reason_code == "unsupported_repository_visibility"


def test_boolean_repository_id_is_not_accepted_as_integer() -> None:
    """Reject Python bool values even though bool subclasses int."""
    with pytest.raises(InvalidRepositoryIdentityError):
        _repository(repository_id=True)


def test_non_positive_repository_id_is_rejected() -> None:
    """Require a positive GitHub repository source identity."""
    with pytest.raises(InvalidRepositoryIdentityError):
        _repository(repository_id=0)


def test_full_name_must_match_owner_and_name_exactly() -> None:
    """Prevent source provenance fields from describing different repositories."""
    with pytest.raises(InvalidRepositoryIdentityError) as exc_info:
        _repository(full_name="other/opslens")

    assert exc_info.value.reason_code == "invalid_repository_identity"


def test_snapshot_id_uses_repository_id_and_exact_commit_sha() -> None:
    """Make immutable snapshot identity independent of human-readable repository naming."""
    snapshot = _snapshot()

    assert snapshot.snapshot_id == f"github:{_REPOSITORY_ID}@{_COMMIT_SHA}"


def test_different_requested_refs_resolving_to_same_commit_share_snapshot_id() -> None:
    """Treat branch/tag names as provenance rather than immutable snapshot authority."""
    branch_snapshot = _snapshot(requested_ref="main")
    tag_snapshot = _snapshot(requested_ref="refs/tags/v1.0.0")

    assert branch_snapshot.requested_ref != tag_snapshot.requested_ref
    assert branch_snapshot.snapshot_id == tag_snapshot.snapshot_id


def test_changed_commit_changes_snapshot_identity() -> None:
    """Bind reuse/cache identity to immutable Git history rather than moving refs."""
    first = _snapshot()
    second = replace(first, commit_sha="c" * 40)

    assert first.snapshot_id != second.snapshot_id


@pytest.mark.parametrize(
    "commit_sha",
    [
        "a" * 39,
        "A" * 40,
        "g" * 40,
        "main",
    ],
)
def test_commit_sha_must_be_full_lowercase_40_hex(commit_sha: str) -> None:
    """Reject abbreviated or non-canonical commit identifiers as snapshot authority."""
    with pytest.raises(InvalidRepositorySnapshotError) as exc_info:
        _snapshot(commit_sha=commit_sha)

    assert exc_info.value.reason_code == "invalid_repository_snapshot"


def test_tree_sha_is_exact_additional_evidence() -> None:
    """Require exact tree evidence when establishing a GitHub commit snapshot."""
    with pytest.raises(InvalidRepositorySnapshotError):
        _snapshot(tree_sha="b" * 39)


@pytest.mark.parametrize(
    "requested_ref",
    [
        "",
        " main",
        "main ",
        "main\nother",
    ],
)
def test_requested_ref_must_be_clean_provenance(requested_ref: str) -> None:
    """Reject dirty ref provenance rather than carrying ambiguous control data."""
    with pytest.raises(InvalidRepositorySnapshotError):
        _snapshot(requested_ref=requested_ref)
