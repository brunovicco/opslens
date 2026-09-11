"""Tests for the Gate 19.2 preloaded threat-evidence measurement boundary."""

from __future__ import annotations

import base64
from typing import cast

import pytest

from opslens.public_analysis.application import (
    admit_public_analysis_request,
    build_public_repository_evidence,
)
from opslens.public_analysis.application.representative_preloaded_threat_evidence import (
    PreloadedRepresentativeThreatEvidenceLoader,
    RepresentativePreloadedThreatEvidenceError,
)
from opslens.public_analysis.application.representative_repository_analysis import (
    RepresentativeRepositoryThreatEvidence,
)
from opslens.public_analysis.domain import PublicRepositoryEvidenceExecution
from opslens.repository_intelligence.domain import compute_git_blob_sha1

_REPOSITORY_URL = "https://github.com/openedx/mockprock"
_COMMIT_SHA = "18c954d8604df4740c829ba17fa2f3640b92b900"
_TREE_SHA = "1" * 40


class FakeRepositorySource:
    """Provide inert repository evidence without network or provider I/O."""

    def get_repository(self, owner: str, name: str) -> dict[str, object]:
        """Return public repository metadata for the frozen anchor."""
        assert (owner, name) == ("openedx", "mockprock")
        return {
            "id": 123456,
            "name": "mockprock",
            "full_name": "openedx/mockprock",
            "private": False,
            "visibility": "public",
            "default_branch": "main",
            "owner": {"login": "openedx"},
        }

    def get_commit(self, owner: str, name: str, ref: str) -> dict[str, object]:
        """Return the exact frozen commit/tree identity."""
        assert (owner, name, ref) == ("openedx", "mockprock", _COMMIT_SHA)
        return {"sha": _COMMIT_SHA, "commit": {"tree": {"sha": _TREE_SHA}}}

    def get_uv_lock(
        self,
        owner: str,
        name: str,
        commit_sha: str,
    ) -> dict[str, object]:
        """Return inert lock bytes containing the frozen WebOb dependency."""
        assert (owner, name, commit_sha) == ("openedx", "mockprock", _COMMIT_SHA)
        raw = (
            b"version = 1\n"
            b"revision = 3\n"
            b'requires-python = \">=3.11\"\n'
            b"[[package]]\n"
            b'name = "webob"\n'
            b'version = "1.8.10"\n'
            b'source = { registry = "https://pypi.org/simple" }\n'
        )
        return {
            "type": "file",
            "path": "uv.lock",
            "name": "uv.lock",
            "encoding": "base64",
            "size": len(raw),
            "sha": compute_git_blob_sha1(raw),
            "content": base64.encodebytes(raw).decode("ascii"),
        }


def _execution(
    *,
    repository_url: str = _REPOSITORY_URL,
    commit_sha: str = _COMMIT_SHA,
) -> PublicRepositoryEvidenceExecution:
    """Build one real typed public evidence execution from inert fixtures."""
    raw = (
        f'{{"repository_url":"{repository_url}",'
        f'"requested_ref":"{commit_sha}"}}'
    ).encode()
    request = admit_public_analysis_request(raw).request

    class Source(FakeRepositorySource):
        def get_commit(self, owner: str, name: str, ref: str) -> dict[str, object]:
            assert (owner, name, ref) == (
                request.target.owner,
                request.target.name,
                commit_sha,
            )
            return {"sha": commit_sha, "commit": {"tree": {"sha": _TREE_SHA}}}

        def get_uv_lock(
            self,
            owner: str,
            name: str,
            resolved_commit_sha: str,
        ) -> dict[str, object]:
            assert resolved_commit_sha == commit_sha
            return super().get_uv_lock(owner, name, _COMMIT_SHA)

    return build_public_repository_evidence(request, Source())


def _pre_admitted_evidence() -> RepresentativeRepositoryThreatEvidence:
    """Return an opaque already-admitted evidence instance for loader isolation."""
    return object.__new__(RepresentativeRepositoryThreatEvidence)


def test_preloaded_loader_releases_exact_anchor_with_zero_usage() -> None:
    """Preloaded service state adds no request-time provider accounting."""
    evidence = _pre_admitted_evidence()
    loader = PreloadedRepresentativeThreatEvidenceLoader(
        evidence=evidence,
        expected_repository_url=_REPOSITORY_URL,
        expected_commit_sha=_COMMIT_SHA,
    )

    result = loader(_execution())

    assert result.evidence is evidence
    assert result.usage.github_http_request_count == 0
    assert result.usage.athena_query_count == 0
    assert result.usage.athena_bytes_scanned == 0
    assert result.usage.bedrock_retrieve_count == 0
    assert result.usage.bedrock_model_call_count == 0


def test_preloaded_loader_rejects_repository_drift() -> None:
    """Repository identity drift fails before preloaded evidence is released."""
    loader = PreloadedRepresentativeThreatEvidenceLoader(
        evidence=_pre_admitted_evidence(),
        expected_repository_url=_REPOSITORY_URL,
        expected_commit_sha=_COMMIT_SHA,
    )
    execution = _execution(repository_url="https://github.com/openedx/other-repo")

    with pytest.raises(RepresentativePreloadedThreatEvidenceError, match="URL"):
        loader(execution)


def test_preloaded_loader_rejects_commit_drift() -> None:
    """A different immutable commit cannot consume authority frozen for this experiment."""
    loader = PreloadedRepresentativeThreatEvidenceLoader(
        evidence=_pre_admitted_evidence(),
        expected_repository_url=_REPOSITORY_URL,
        expected_commit_sha=_COMMIT_SHA,
    )

    with pytest.raises(RepresentativePreloadedThreatEvidenceError, match="commit SHA"):
        loader(_execution(commit_sha="2" * 40))


def test_preloaded_loader_rejects_invalid_composition_inputs() -> None:
    """Invalid preload types and mutable commit coordinates fail at composition time."""
    invalid = cast(RepresentativeRepositoryThreatEvidence, object())
    with pytest.raises(TypeError, match="evidence"):
        PreloadedRepresentativeThreatEvidenceLoader(
            evidence=invalid,
            expected_repository_url=_REPOSITORY_URL,
            expected_commit_sha=_COMMIT_SHA,
        )

    with pytest.raises(RepresentativePreloadedThreatEvidenceError, match="40-hex"):
        PreloadedRepresentativeThreatEvidenceLoader(
            evidence=_pre_admitted_evidence(),
            expected_repository_url=_REPOSITORY_URL,
            expected_commit_sha="main",
        )
