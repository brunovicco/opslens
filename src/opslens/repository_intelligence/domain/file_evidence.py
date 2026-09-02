"""Immutable inert repository file evidence bound to one exact snapshot."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from opslens.repository_intelligence.domain.errors import (
    InvalidRepositoryFileEvidenceError,
    UnsupportedRepositoryFileError,
)
from opslens.repository_intelligence.domain.models import ImmutableRepositorySnapshot

UV_LOCK_PATH = "uv.lock"
MAX_REPOSITORY_FILE_BYTES = 1_048_576
_FULL_GIT_SHA1_PATTERN = re.compile(r"^[0-9a-f]{40}$", re.ASCII)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)


def validate_repository_evidence_path(path: str) -> str:
    """Allow only the first frozen dependency-evidence path for Phase 4 v1."""
    if path != UV_LOCK_PATH:
        raise UnsupportedRepositoryFileError(
            f"Repository evidence path is outside the Phase 4 v1 allowlist: {path!r}."
        )
    return path


def compute_git_blob_sha1(content: bytes) -> str:
    """Compute the traditional Git SHA-1 object id for inert blob bytes."""
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content, usedforsecurity=False).hexdigest()


def compute_content_sha256(content: bytes) -> str:
    """Compute the OpsLens SHA-256 digest for inert repository content."""
    return hashlib.sha256(content).hexdigest()


@dataclass(frozen=True, slots=True)
class ImmutableRepositoryFileEvidence:
    """Verified inert bytes for one allowlisted file at one immutable snapshot."""

    snapshot: ImmutableRepositorySnapshot
    path: str
    blob_sha: str
    size_bytes: int
    content_sha256: str
    content_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        """Independently verify file identity, bounds, and content integrity."""
        validate_repository_evidence_path(self.path)

        if _FULL_GIT_SHA1_PATTERN.fullmatch(self.blob_sha) is None:
            raise InvalidRepositoryFileEvidenceError(
                "Repository file Git blob SHA must be exactly 40 lowercase hexadecimal characters."
            )

        if type(self.size_bytes) is not int or not 0 < self.size_bytes <= MAX_REPOSITORY_FILE_BYTES:
            raise InvalidRepositoryFileEvidenceError(
                "Repository file size must be a positive integer no larger than 1 MiB."
            )

        if type(self.content_bytes) is not bytes:
            raise InvalidRepositoryFileEvidenceError(
                "Repository file content evidence must be immutable bytes."
            )

        if len(self.content_bytes) != self.size_bytes:
            raise InvalidRepositoryFileEvidenceError(
                "Repository file size evidence does not match the observed content bytes."
            )

        if _SHA256_PATTERN.fullmatch(self.content_sha256) is None:
            raise InvalidRepositoryFileEvidenceError(
                "Repository file SHA-256 must be exactly 64 lowercase hexadecimal characters."
            )

        expected_sha256 = compute_content_sha256(self.content_bytes)
        if self.content_sha256 != expected_sha256:
            raise InvalidRepositoryFileEvidenceError(
                "Repository file SHA-256 does not match the observed content bytes."
            )

        expected_blob_sha = compute_git_blob_sha1(self.content_bytes)
        if self.blob_sha != expected_blob_sha:
            raise InvalidRepositoryFileEvidenceError(
                "Repository file Git blob SHA does not match the observed content bytes."
            )

    @property
    def evidence_id(self) -> str:
        """Return deterministic file evidence identity under the immutable snapshot."""
        return f"{self.snapshot.snapshot_id}:{self.path}@{self.blob_sha}"
