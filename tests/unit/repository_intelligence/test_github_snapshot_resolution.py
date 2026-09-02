"""Tests for projecting and resolving immutable GitHub repository snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from opslens.repository_intelligence.adapters.github import (
    project_github_commit_snapshot,
    project_github_repository_metadata,
)
from opslens.repository_intelligence.application import resolve_github_repository_snapshot
from opslens.repository_intelligence.domain import (
    InvalidGitHubSourceEvidenceError,
    InvalidRepositoryIdentityError,
    InvalidRepositorySnapshotError,
    UnsupportedRepositoryVisibilityError,
)

_REPOSITORY_ID = 1_333_092_779
_COMMIT_SHA = "3f75a4fc2bd22589df0a5ffe98a8442fda81c8d3"
_TREE_SHA = "01ac6fe03f1db867ef29c6652311ee43b1f63afb"


def _repository_payload(
    *,
    owner: str = "brunovicco",
    name: str = "opslens",
    full_name: str = "brunovicco/opslens",
    repository_id: int = _REPOSITORY_ID,
    private: bool = False,
    visibility: str = "public",
    default_branch: str = "main",
) -> dict[str, object]:
    """Build the minimal GitHub repository payload required by the adapter."""
    return {
        "id": repository_id,
        "name": name,
        "full_name": full_name,
        "private": private,
        "visibility": visibility,
        "default_branch": default_branch,
        "owner": {"login": owner},
    }


def _commit_payload(
    *,
    commit_sha: str = _COMMIT_SHA,
    tree_sha: str = _TREE_SHA,
) -> dict[str, object]:
    """Build the minimal GitHub commit payload required by the adapter."""
    return {
        "sha": commit_sha,
        "commit": {
            "tree": {
                "sha": tree_sha,
            }
        },
    }


@dataclass(slots=True)
class FakeGitHubSnapshotSource:
    """Record read calls while returning deterministic GitHub REST fixtures."""

    repository_payload: dict[str, object]
    commit_payload: dict[str, object]
    repository_calls: list[tuple[str, str]] = field(default_factory=list)
    commit_calls: list[tuple[str, str, str]] = field(default_factory=list)

    def get_repository(self, owner: str, name: str) -> dict[str, object]:
        """Return the configured repository payload and record the lookup."""
        self.repository_calls.append((owner, name))
        return self.repository_payload

    def get_commit(self, owner: str, name: str, ref: str) -> dict[str, object]:
        """Return the configured commit payload and record the lookup."""
        self.commit_calls.append((owner, name, ref))
        return self.commit_payload


def test_repository_metadata_projects_real_github_shape() -> None:
    """Project the minimal shape observed from GitHub into typed public metadata."""
    metadata = project_github_repository_metadata(_repository_payload())

    assert metadata.repository.repository_id == _REPOSITORY_ID
    assert metadata.repository.full_name == "brunovicco/opslens"
    assert metadata.repository.repository_key == f"github:{_REPOSITORY_ID}"
    assert metadata.visibility == "public"
    assert metadata.default_branch == "main"


def test_commit_payload_projects_exact_snapshot_identity() -> None:
    """Bind the resolved ref to exact commit and tree evidence from GitHub."""
    metadata = project_github_repository_metadata(_repository_payload())
    snapshot = project_github_commit_snapshot(
        metadata=metadata,
        requested_ref="main",
        payload=_commit_payload(),
    )

    assert snapshot.commit_sha == _COMMIT_SHA
    assert snapshot.tree_sha == _TREE_SHA
    assert snapshot.snapshot_id == f"github:{_REPOSITORY_ID}@{_COMMIT_SHA}"


def test_non_public_visibility_fails_closed() -> None:
    """Require explicit public visibility instead of inferring it from private=false."""
    with pytest.raises(UnsupportedRepositoryVisibilityError):
        project_github_repository_metadata(
            _repository_payload(visibility="internal")
        )


def test_private_flag_cannot_disagree_with_public_only_contract() -> None:
    """Reject metadata that claims public visibility while the private flag is true."""
    with pytest.raises(UnsupportedRepositoryVisibilityError):
        project_github_repository_metadata(_repository_payload(private=True))


def test_missing_owner_object_is_invalid_source_evidence() -> None:
    """Distinguish malformed REST evidence from a valid but unsupported repository."""
    payload = _repository_payload()
    del payload["owner"]

    with pytest.raises(InvalidGitHubSourceEvidenceError) as exc_info:
        project_github_repository_metadata(payload)

    assert exc_info.value.reason_code == "invalid_github_source_evidence"


def test_source_boolean_repository_id_is_rejected_before_domain_projection() -> None:
    """Keep JSON booleans from becoming numeric source identities."""
    payload = _repository_payload()
    payload["id"] = True

    with pytest.raises(InvalidGitHubSourceEvidenceError):
        project_github_repository_metadata(payload)


def test_source_full_name_mismatch_remains_domain_identity_failure() -> None:
    """Reject source fields that individually parse but describe different identities."""
    with pytest.raises(InvalidRepositoryIdentityError):
        project_github_repository_metadata(
            _repository_payload(full_name="other/opslens")
        )


def test_missing_commit_tree_is_invalid_source_evidence() -> None:
    """Require exact Git tree evidence in the commit response."""
    metadata = project_github_repository_metadata(_repository_payload())
    payload: dict[str, object] = {
        "sha": _COMMIT_SHA,
        "commit": {},
    }

    with pytest.raises(InvalidGitHubSourceEvidenceError):
        project_github_commit_snapshot(
            metadata=metadata,
            requested_ref="main",
            payload=payload,
        )


def test_malformed_commit_sha_remains_snapshot_contract_failure() -> None:
    """Do not convert malformed Git commit identity into a source-not-found result."""
    metadata = project_github_repository_metadata(_repository_payload())

    with pytest.raises(InvalidRepositorySnapshotError):
        project_github_commit_snapshot(
            metadata=metadata,
            requested_ref="main",
            payload=_commit_payload(commit_sha="abc123"),
        )


def test_resolver_uses_default_branch_when_ref_is_omitted() -> None:
    """Resolve the source-declared default branch then freeze the exact commit identity."""
    source = FakeGitHubSnapshotSource(
        repository_payload=_repository_payload(),
        commit_payload=_commit_payload(),
    )

    evidence = resolve_github_repository_snapshot(
        source,
        owner="brunovicco",
        name="opslens",
    )

    assert evidence.used_default_branch is True
    assert evidence.snapshot.requested_ref == "main"
    assert evidence.snapshot.snapshot_id == f"github:{_REPOSITORY_ID}@{_COMMIT_SHA}"
    assert source.repository_calls == [("brunovicco", "opslens")]
    assert source.commit_calls == [("brunovicco", "opslens", "main")]


def test_resolver_preserves_explicit_ref_provenance() -> None:
    """Use an explicit validated ref without allowing it to become snapshot authority."""
    source = FakeGitHubSnapshotSource(
        repository_payload=_repository_payload(),
        commit_payload=_commit_payload(),
    )

    evidence = resolve_github_repository_snapshot(
        source,
        owner="brunovicco",
        name="opslens",
        requested_ref="refs/tags/v1.0.0",
    )

    assert evidence.used_default_branch is False
    assert evidence.snapshot.requested_ref == "refs/tags/v1.0.0"
    assert evidence.snapshot.snapshot_id == f"github:{_REPOSITORY_ID}@{_COMMIT_SHA}"
    assert source.commit_calls == [("brunovicco", "opslens", "refs/tags/v1.0.0")]


def test_resolver_uses_canonical_metadata_coordinates_for_commit_lookup() -> None:
    """Use source-confirmed repository coordinates after the initial repository lookup."""
    source = FakeGitHubSnapshotSource(
        repository_payload=_repository_payload(
            owner="CanonicalOwner",
            name="CanonicalRepo",
            full_name="CanonicalOwner/CanonicalRepo",
        ),
        commit_payload=_commit_payload(),
    )

    evidence = resolve_github_repository_snapshot(
        source,
        owner="old-owner",
        name="old-repo",
    )

    assert evidence.requested_owner == "old-owner"
    assert evidence.requested_name == "old-repo"
    assert source.repository_calls == [("old-owner", "old-repo")]
    assert source.commit_calls == [("CanonicalOwner", "CanonicalRepo", "main")]


def test_invalid_request_coordinates_fail_before_any_source_call() -> None:
    """Keep malformed repository coordinates away from the future transport boundary."""
    source = FakeGitHubSnapshotSource(
        repository_payload=_repository_payload(),
        commit_payload=_commit_payload(),
    )

    with pytest.raises(InvalidRepositoryIdentityError):
        resolve_github_repository_snapshot(
            source,
            owner="../bad-owner",
            name="opslens",
        )

    assert source.repository_calls == []
    assert source.commit_calls == []


def test_invalid_explicit_ref_fails_before_commit_source_call() -> None:
    """Never send a dirty ref token into the future commit acquisition operation."""
    source = FakeGitHubSnapshotSource(
        repository_payload=_repository_payload(),
        commit_payload=_commit_payload(),
    )

    with pytest.raises(InvalidRepositorySnapshotError):
        resolve_github_repository_snapshot(
            source,
            owner="brunovicco",
            name="opslens",
            requested_ref="main\nother",
        )

    assert source.repository_calls == [("brunovicco", "opslens")]
    assert source.commit_calls == []


def test_dirty_default_branch_fails_before_commit_source_call() -> None:
    """Reject malformed source-provided refs before a second GitHub operation occurs."""
    source = FakeGitHubSnapshotSource(
        repository_payload=_repository_payload(default_branch="main\nother"),
        commit_payload=_commit_payload(),
    )

    with pytest.raises(InvalidGitHubSourceEvidenceError):
        resolve_github_repository_snapshot(
            source,
            owner="brunovicco",
            name="opslens",
        )

    assert source.repository_calls == [("brunovicco", "opslens")]
    assert source.commit_calls == []
