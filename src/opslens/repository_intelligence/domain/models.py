"""Typed public GitHub repository and immutable snapshot identity models."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from opslens.repository_intelligence.domain.errors import (
    InvalidRepositoryIdentityError,
    InvalidRepositorySnapshotError,
    UnsupportedRepositoryVisibilityError,
)

_OWNER_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$", re.ASCII)
_REPOSITORY_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,100}$", re.ASCII)
_FULL_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$", re.ASCII)
_CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x1f\x7f]", re.ASCII)


class RepositoryProvider(StrEnum):
    """Repository providers supported by the frozen Phase 4 v1 contract."""

    GITHUB = "github"


@dataclass(frozen=True, slots=True)
class GitHubRepositoryIdentity:
    """Stable source identity for one public GitHub repository.

    The numeric repository id is authoritative. Owner/name/full_name are retained
    as human-readable source provenance and must agree exactly with each other.
    """

    repository_id: int
    owner: str
    name: str
    full_name: str
    is_private: bool

    def __post_init__(self) -> None:
        """Validate the narrow public-GitHub identity contract."""
        if type(self.repository_id) is not int or self.repository_id <= 0:
            raise InvalidRepositoryIdentityError(
                "GitHub repository id must be a positive integer and cannot be boolean."
            )

        if _OWNER_PATTERN.fullmatch(self.owner) is None:
            raise InvalidRepositoryIdentityError(
                "GitHub repository owner is outside the Phase 4 v1 identity "
                f"contract: {self.owner!r}."
            )

        if _REPOSITORY_NAME_PATTERN.fullmatch(self.name) is None:
            raise InvalidRepositoryIdentityError(
                "GitHub repository name is outside the Phase 4 v1 identity "
                f"contract: {self.name!r}."
            )

        expected_full_name = f"{self.owner}/{self.name}"
        if self.full_name != expected_full_name:
            raise InvalidRepositoryIdentityError(
                "GitHub full_name must exactly match the supplied owner/name identity."
            )

        if type(self.is_private) is not bool:
            raise InvalidRepositoryIdentityError(
                "GitHub repository privacy evidence must be boolean."
            )

        if self.is_private:
            raise UnsupportedRepositoryVisibilityError(
                "Private GitHub repositories are outside the Phase 4 v1 contract."
            )

    @property
    def provider(self) -> RepositoryProvider:
        """Return the explicit repository provider for this source identity."""
        return RepositoryProvider.GITHUB

    @property
    def repository_key(self) -> str:
        """Return the stable provider-qualified repository identity."""
        return f"{self.provider.value}:{self.repository_id}"


@dataclass(frozen=True, slots=True)
class ImmutableRepositorySnapshot:
    """One exact public GitHub repository snapshot resolved to a full commit SHA."""

    repository: GitHubRepositoryIdentity
    requested_ref: str
    commit_sha: str
    tree_sha: str

    def __post_init__(self) -> None:
        """Validate immutable commit authority and ref provenance."""
        if (
            not self.requested_ref
            or self.requested_ref != self.requested_ref.strip()
            or _CONTROL_CHARACTER_PATTERN.search(self.requested_ref) is not None
        ):
            raise InvalidRepositorySnapshotError(
                "Requested GitHub ref must be a non-empty clean provenance token."
            )

        if len(self.requested_ref) > 1024:
            raise InvalidRepositorySnapshotError(
                "Requested GitHub ref exceeds the Phase 4 v1 evidence bound."
            )

        if _FULL_GIT_SHA_PATTERN.fullmatch(self.commit_sha) is None:
            raise InvalidRepositorySnapshotError(
                "GitHub snapshot commit SHA must be exactly 40 lowercase hexadecimal characters."
            )

        if _FULL_GIT_SHA_PATTERN.fullmatch(self.tree_sha) is None:
            raise InvalidRepositorySnapshotError(
                "GitHub snapshot tree SHA must be exactly 40 lowercase hexadecimal characters."
            )

    @property
    def snapshot_id(self) -> str:
        """Return the stable immutable snapshot identity independent of moving refs."""
        return f"{self.repository.repository_key}@{self.commit_sha}"
