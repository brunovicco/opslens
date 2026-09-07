"""Tests for deterministic Phase 9 public repository evidence orchestration."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field, replace

import pytest

from opslens.public_analysis.application import (
    admit_public_analysis_request,
    build_public_repository_evidence,
)
from opslens.public_analysis.domain import (
    PUBLIC_REPOSITORY_EVIDENCE_CONTRACT_VERSION,
    PublicAnalysisValidationError,
    PublicRepositoryEvidenceExecution,
)
from opslens.repository_intelligence.domain import (
    InvalidUvLockError,
    UnsupportedRepositoryVisibilityError,
    compute_git_blob_sha1,
)

_REPOSITORY_ID = 1_333_092_779
_COMMIT_SHA = "3f75a4fc2bd22589df0a5ffe98a8442fda81c8d3"
_TREE_SHA = "01ac6fe03f1db867ef29c6652311ee43b1f63afb"


def _request(
    *,
    repository_url: str = "https://github.com/brunovicco/opslens",
    requested_ref: str | None = None,
):
    """Admit one Gate 9.1 request through the real public-input boundary."""
    ref_json = "null" if requested_ref is None else f'"{requested_ref}"'
    raw = (
        f'{{"repository_url":"{repository_url}","requested_ref":{ref_json}}}'
    ).encode()
    return admit_public_analysis_request(raw).request


def _repository_payload(
    *,
    owner: str = "brunovicco",
    name: str = "opslens",
    full_name: str = "brunovicco/opslens",
    private: bool = False,
    visibility: str = "public",
    default_branch: str = "trunk",
) -> dict[str, object]:
    """Build the bounded GitHub repository metadata fixture used by Phase 4."""
    return {
        "id": _REPOSITORY_ID,
        "name": name,
        "full_name": full_name,
        "private": private,
        "visibility": visibility,
        "default_branch": default_branch,
        "owner": {"login": owner},
    }


def _commit_payload() -> dict[str, object]:
    """Return exact commit/tree source evidence."""
    return {
        "sha": _COMMIT_SHA,
        "commit": {"tree": {"sha": _TREE_SHA}},
    }


def _uv_lock_content() -> bytes:
    """Return inert lock bytes with one PyPI and one unsupported local package."""
    return (
        b"version = 1\n"
        b"revision = 3\n"
        b'requires-python = ">=3.13"\n'
        b"[[package]]\n"
        b'name = "Requests"\n'
        b'version = "2.31.0"\n'
        b'source = { registry = "https://pypi.org/simple" }\n'
        b"[[package]]\n"
        b'name = "local-demo"\n'
        b'version = "0.1.0"\n'
        b'source = { path = "." }\n'
    )


def _uv_lock_payload(content: bytes | None = None) -> dict[str, object]:
    """Build the exact GitHub Contents shape already admitted by Phase 4."""
    raw = _uv_lock_content() if content is None else content
    return {
        "type": "file",
        "path": "uv.lock",
        "name": "uv.lock",
        "encoding": "base64",
        "size": len(raw),
        "sha": compute_git_blob_sha1(raw),
        "content": base64.encodebytes(raw).decode("ascii"),
    }


@dataclass(slots=True)
class FakePublicRepositorySource:
    """Record every allowed source call without making network requests."""

    repository_payload: dict[str, object] = field(default_factory=_repository_payload)
    commit_payload: dict[str, object] = field(default_factory=_commit_payload)
    uv_lock_payload: dict[str, object] = field(default_factory=_uv_lock_payload)
    repository_calls: list[tuple[str, str]] = field(default_factory=list)
    commit_calls: list[tuple[str, str, str]] = field(default_factory=list)
    uv_lock_calls: list[tuple[str, str, str]] = field(default_factory=list)

    def get_repository(self, owner: str, name: str) -> dict[str, object]:
        """Return repository metadata and record only validated coordinates."""
        self.repository_calls.append((owner, name))
        return self.repository_payload

    def get_commit(self, owner: str, name: str, ref: str) -> dict[str, object]:
        """Return immutable commit evidence and record the resolved ref lookup."""
        self.commit_calls.append((owner, name, ref))
        return self.commit_payload

    def get_uv_lock(
        self,
        owner: str,
        name: str,
        commit_sha: str,
    ) -> dict[str, object]:
        """Return inert file evidence and record exact-commit acquisition authority."""
        self.uv_lock_calls.append((owner, name, commit_sha))
        return self.uv_lock_payload


def test_null_ref_uses_source_default_then_exact_commit_for_file_acquisition() -> None:
    """Default-branch source evidence, not an invented `main`, owns moving-ref resolution."""
    source = FakePublicRepositorySource()
    request = _request()

    result = build_public_repository_evidence(request, source)

    assert result.snapshot_resolution.used_default_branch is True
    assert result.snapshot_resolution.snapshot.requested_ref == "trunk"
    assert result.snapshot_id == f"github:{_REPOSITORY_ID}@{_COMMIT_SHA}"
    assert source.repository_calls == [("brunovicco", "opslens")]
    assert source.commit_calls == [("brunovicco", "opslens", "trunk")]
    assert source.uv_lock_calls == [("brunovicco", "opslens", _COMMIT_SHA)]
    assert result.parsed_lock.package_count == 2
    assert len(result.parsed_lock.pypi_packages) == 1
    assert len(result.parsed_lock.unsupported_packages) == 1
    assert len(result.normalization_inventory.normalized_dependencies) == 1
    dependency = result.normalization_inventory.normalized_dependencies[0]
    assert dependency.package.canonical == "requests"
    assert dependency.version.canonical == "2.31.0"
    assert dependency.purl == "pkg:pypi/requests@2.31.0"
    assert result.execution_id.startswith(
        f"{PUBLIC_REPOSITORY_EVIDENCE_CONTRACT_VERSION}@sha256:"
    )


def test_explicit_ref_is_preserved_but_file_read_uses_only_resolved_commit() -> None:
    """A moving explicit ref is provenance only after exact snapshot resolution."""
    source = FakePublicRepositorySource()
    request = _request(requested_ref="refs/tags/v1.2.3")

    result = build_public_repository_evidence(request, source)

    assert result.snapshot_resolution.used_default_branch is False
    assert result.snapshot_resolution.snapshot.requested_ref == "refs/tags/v1.2.3"
    assert source.commit_calls == [
        ("brunovicco", "opslens", "refs/tags/v1.2.3")
    ]
    assert source.uv_lock_calls == [("brunovicco", "opslens", _COMMIT_SHA)]


def test_source_confirmed_rename_becomes_canonical_after_initial_lookup() -> None:
    """Preserve Phase 4 authority when GitHub confirms canonical renamed coordinates."""
    source = FakePublicRepositorySource(
        repository_payload=_repository_payload(
            owner="CanonicalOwner",
            name="CanonicalRepo",
            full_name="CanonicalOwner/CanonicalRepo",
        )
    )
    request = _request(repository_url="https://github.com/old-owner/old-repo")

    result = build_public_repository_evidence(request, source)

    assert source.repository_calls == [("old-owner", "old-repo")]
    assert source.commit_calls == [("CanonicalOwner", "CanonicalRepo", "trunk")]
    assert source.uv_lock_calls == [
        ("CanonicalOwner", "CanonicalRepo", _COMMIT_SHA)
    ]
    assert result.snapshot_resolution.requested_owner == "old-owner"
    assert result.snapshot_resolution.requested_name == "old-repo"
    assert result.snapshot_resolution.snapshot.repository.full_name == (
        "CanonicalOwner/CanonicalRepo"
    )


def test_equivalent_source_evidence_produces_same_content_addressed_execution() -> None:
    """Execution identity depends on admitted semantics and exact evidence, not object identity."""
    first = build_public_repository_evidence(_request(), FakePublicRepositorySource())
    second = build_public_repository_evidence(_request(), FakePublicRepositorySource())

    assert first.evidence_sha256 == second.evidence_sha256
    assert first.execution_id == second.execution_id
    assert b"repository_url" not in first.canonical_json
    assert b"https://github.com/brunovicco/opslens" not in first.canonical_json


def test_private_repository_fails_before_commit_or_file_acquisition() -> None:
    """Publicness remains source-evidence authority rather than a Gate 9.1 assumption."""
    source = FakePublicRepositorySource(
        repository_payload=_repository_payload(
            private=True,
            visibility="private",
        )
    )

    with pytest.raises(UnsupportedRepositoryVisibilityError):
        build_public_repository_evidence(_request(), source)

    assert source.repository_calls == [("brunovicco", "opslens")]
    assert source.commit_calls == []
    assert source.uv_lock_calls == []


def test_malformed_uv_lock_fails_after_bounded_exact_commit_acquisition() -> None:
    """Invalid inert dependency evidence cannot become a public evidence execution."""
    source = FakePublicRepositorySource(
        uv_lock_payload=_uv_lock_payload(b"version = [\n")
    )

    with pytest.raises(InvalidUvLockError):
        build_public_repository_evidence(_request(), source)

    assert source.repository_calls == [("brunovicco", "opslens")]
    assert source.commit_calls == [("brunovicco", "opslens", "trunk")]
    assert source.uv_lock_calls == [("brunovicco", "opslens", _COMMIT_SHA)]


def test_execution_rejects_request_resolution_coordinate_drift() -> None:
    """A valid evidence chain cannot be rebound to a different admitted request."""
    result = build_public_repository_evidence(_request(), FakePublicRepositorySource())
    different_request = _request(
        repository_url="https://github.com/other-owner/other-repo"
    )

    with pytest.raises(PublicAnalysisValidationError):
        PublicRepositoryEvidenceExecution(
            request=different_request,
            snapshot_resolution=result.snapshot_resolution,
            file_evidence=result.file_evidence,
            parsed_lock=result.parsed_lock,
            normalization_inventory=result.normalization_inventory,
        )


def test_execution_rejects_cross_snapshot_file_evidence() -> None:
    """Dependency evidence from another commit cannot be composed into the execution."""
    result = build_public_repository_evidence(_request(), FakePublicRepositorySource())
    other_snapshot = replace(
        result.snapshot_resolution.snapshot,
        commit_sha="b" * 40,
    )
    other_file = replace(result.file_evidence, snapshot=other_snapshot)

    with pytest.raises(PublicAnalysisValidationError):
        PublicRepositoryEvidenceExecution(
            request=result.request,
            snapshot_resolution=result.snapshot_resolution,
            file_evidence=other_file,
            parsed_lock=result.parsed_lock,
            normalization_inventory=result.normalization_inventory,
        )
