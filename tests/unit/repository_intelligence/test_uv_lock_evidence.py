"""Tests for immutable inert `uv.lock` evidence at an exact repository snapshot."""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from dataclasses import dataclass, field

import pytest

from opslens.repository_intelligence.adapters.github_file import (
    project_github_uv_lock_evidence,
)
from opslens.repository_intelligence.adapters.github_http import (
    GitHubHttpsConnection,
    GitHubInvalidResponseError,
    GitHubResponseTooLargeError,
    GitHubRestClientConfig,
    GitHubRestSnapshotSource,
)
from opslens.repository_intelligence.application import acquire_uv_lock_evidence
from opslens.repository_intelligence.domain import (
    MAX_REPOSITORY_FILE_BYTES,
    UV_LOCK_PATH,
    GitHubRepositoryIdentity,
    ImmutableRepositoryFileEvidence,
    ImmutableRepositorySnapshot,
    InvalidGitHubSourceEvidenceError,
    InvalidRepositoryFileEvidenceError,
    UnsupportedRepositoryFileError,
    compute_content_sha256,
    compute_git_blob_sha1,
    validate_repository_evidence_path,
)

_REPOSITORY_ID = 1_333_092_779
_COMMIT_SHA = "e9fd556a7809e4fb67b1d2fc12d845fe2b88b0d5"
_TREE_SHA = "e6022fbbc1a9b14e6f958156d535cc6a639ce4c3"


def _snapshot() -> ImmutableRepositorySnapshot:
    """Build the immutable OpsLens snapshot observed after Gate 4.3."""
    repository = GitHubRepositoryIdentity(
        repository_id=_REPOSITORY_ID,
        owner="brunovicco",
        name="opslens",
        full_name="brunovicco/opslens",
        is_private=False,
    )
    return ImmutableRepositorySnapshot(
        repository=repository,
        requested_ref="main",
        commit_sha=_COMMIT_SHA,
        tree_sha=_TREE_SHA,
    )


def _uv_content() -> bytes:
    """Return a small inert lockfile fixture; it is never executed."""
    return b'version = 1\n\n[[package]]\nname = "packaging"\nversion = "26.3"\n'


def _contents_payload(
    *,
    content: bytes | None = None,
    source_type: str = "file",
    path: str = UV_LOCK_PATH,
    name: str = UV_LOCK_PATH,
    encoding: str = "base64",
    size: int | None = None,
    blob_sha: str | None = None,
    encoded_content: str | None = None,
) -> dict[str, object]:
    """Build the minimal GitHub Contents payload required by the Gate 4.4 adapter."""
    raw_content = _uv_content() if content is None else content
    return {
        "type": source_type,
        "path": path,
        "name": name,
        "encoding": encoding,
        "size": len(raw_content) if size is None else size,
        "sha": compute_git_blob_sha1(raw_content) if blob_sha is None else blob_sha,
        "content": (
            base64.encodebytes(raw_content).decode("ascii")
            if encoded_content is None
            else encoded_content
        ),
    }


def test_git_blob_sha_matches_known_git_vector() -> None:
    """Verify Git object hashing independently from payload construction helpers."""
    assert compute_git_blob_sha1(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


def test_uv_lock_projection_emits_verified_immutable_evidence() -> None:
    """Bind valid GitHub Contents bytes to the exact immutable snapshot."""
    content = _uv_content()
    snapshot = _snapshot()

    evidence = project_github_uv_lock_evidence(
        snapshot=snapshot,
        payload=_contents_payload(content=content),
    )

    assert evidence.snapshot is snapshot
    assert evidence.path == UV_LOCK_PATH
    assert evidence.size_bytes == len(content)
    assert evidence.blob_sha == compute_git_blob_sha1(content)
    assert evidence.content_sha256 == compute_content_sha256(content)
    assert evidence.content_bytes == content
    assert evidence.evidence_id.startswith(f"github:{_REPOSITORY_ID}@{_COMMIT_SHA}:")


def test_uv_lock_projection_accepts_github_base64_line_breaks() -> None:
    """Accept GitHub-style Base64 wrapping without broad whitespace normalization."""
    content = b"x" * 120
    payload = _contents_payload(content=content)
    encoded = payload["content"]
    assert isinstance(encoded, str)
    assert "\n" in encoded

    evidence = project_github_uv_lock_evidence(
        snapshot=_snapshot(),
        payload=payload,
    )

    assert evidence.content_bytes == content


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("type", "dir"),
        ("path", "nested/uv.lock"),
        ("name", "other.lock"),
        ("encoding", "none"),
    ],
)
def test_source_identity_fields_fail_closed(field: str, value: str) -> None:
    """Reject source metadata that does not describe the one allowlisted file."""
    payload = _contents_payload()
    payload[field] = value

    with pytest.raises(InvalidGitHubSourceEvidenceError):
        project_github_uv_lock_evidence(snapshot=_snapshot(), payload=payload)


def test_malformed_base64_fails_closed() -> None:
    """Reject malformed encoded content before it becomes repository evidence."""
    payload = _contents_payload(encoded_content="%%%not-base64%%")

    with pytest.raises(InvalidGitHubSourceEvidenceError):
        project_github_uv_lock_evidence(snapshot=_snapshot(), payload=payload)


def test_source_size_must_match_decoded_content() -> None:
    """Do not trust the source size independently of observed inert bytes."""
    payload = _contents_payload(size=999)

    with pytest.raises(InvalidGitHubSourceEvidenceError):
        project_github_uv_lock_evidence(snapshot=_snapshot(), payload=payload)


def test_decoded_content_over_one_mib_fails_closed() -> None:
    """Keep the first repository file evidence contract within its raw byte budget."""
    content = b"x" * (MAX_REPOSITORY_FILE_BYTES + 1)
    payload = _contents_payload(content=content)

    with pytest.raises(InvalidGitHubSourceEvidenceError):
        project_github_uv_lock_evidence(snapshot=_snapshot(), payload=payload)


def test_blob_sha_mismatch_fails_independent_domain_validation() -> None:
    """Detect source blob identity that does not match the decoded inert bytes."""
    payload = _contents_payload(blob_sha="a" * 40)

    with pytest.raises(InvalidRepositoryFileEvidenceError):
        project_github_uv_lock_evidence(snapshot=_snapshot(), payload=payload)


def test_file_model_recomputes_sha256_instead_of_trusting_caller() -> None:
    """Keep the domain model authoritative over content digest integrity."""
    content = _uv_content()

    with pytest.raises(InvalidRepositoryFileEvidenceError):
        ImmutableRepositoryFileEvidence(
            snapshot=_snapshot(),
            path=UV_LOCK_PATH,
            blob_sha=compute_git_blob_sha1(content),
            size_bytes=len(content),
            content_sha256="b" * 64,
            content_bytes=content,
        )


def test_non_allowlisted_repository_path_is_unsupported() -> None:
    """Do not broaden the first repository content gate to caller-selected paths."""
    with pytest.raises(UnsupportedRepositoryFileError):
        validate_repository_evidence_path("pyproject.toml")


@dataclass(slots=True)
class RecordingUvLockSource:
    """Record the exact repository coordinates used by the application service."""

    payload: dict[str, object]
    calls: list[tuple[str, str, str]] = field(
        default_factory=lambda: list[tuple[str, str, str]]()
    )

    def get_uv_lock(
        self,
        owner: str,
        name: str,
        commit_sha: str,
    ) -> dict[str, object]:
        """Return deterministic Contents evidence and record the immutable lookup."""
        self.calls.append((owner, name, commit_sha))
        return self.payload


def test_application_uses_snapshot_commit_sha_not_requested_ref() -> None:
    """Make the immutable commit, never the moving ref, authoritative for file reads."""
    source = RecordingUvLockSource(payload=_contents_payload())
    snapshot = _snapshot()

    evidence = acquire_uv_lock_evidence(source, snapshot=snapshot)

    assert source.calls == [("brunovicco", "opslens", _COMMIT_SHA)]
    assert evidence.snapshot.commit_sha == _COMMIT_SHA
    assert evidence.snapshot.requested_ref == "main"


@dataclass(slots=True)
class FakeHttpsResponse:
    """Provide the minimal HTTPS response used by the bounded transport."""

    body: bytes
    status: int = 200
    headers: dict[str, str] = field(
        default_factory=lambda: {"Content-Type": "application/json"}
    )
    read_calls: list[int | None] = field(default_factory=lambda: list[int | None]())

    def getheader(self, name: str, default: str | None = None) -> str | None:
        """Return one case-insensitive response header."""
        target = name.lower()
        for key, value in self.headers.items():
            if key.lower() == target:
                return value
        return default

    def read(self, amt: int | None = None) -> bytes:
        """Return at most the caller-requested number of bytes."""
        self.read_calls.append(amt)
        return self.body if amt is None else self.body[:amt]


@dataclass(slots=True)
class FakeHttpsConnection:
    """Record one bounded GitHub request."""

    response: FakeHttpsResponse
    calls: list[tuple[str, str, dict[str, str]]] = field(
        default_factory=lambda: list[tuple[str, str, dict[str, str]]]()
    )
    closed: bool = False

    def request(self, method: str, url: str, *, headers: Mapping[str, str]) -> None:
        """Record the outbound fixed-host request."""
        self.calls.append((method, url, dict(headers)))

    def getresponse(self) -> FakeHttpsResponse:
        """Return the configured response."""
        return self.response

    def close(self) -> None:
        """Record deterministic connection cleanup."""
        self.closed = True


@dataclass(slots=True)
class SingleConnectionFactory:
    """Create exactly one fake HTTPS connection for the file read."""

    response: FakeHttpsResponse
    calls: list[tuple[str, float]] = field(
        default_factory=lambda: list[tuple[str, float]]()
    )
    connection: FakeHttpsConnection | None = None

    def __call__(self, host: str, timeout_seconds: float) -> GitHubHttpsConnection:
        """Create and record one connection to the fixed GitHub host."""
        self.calls.append((host, timeout_seconds))
        self.connection = FakeHttpsConnection(response=self.response)
        return self.connection


def _json_response(payload: dict[str, object]) -> FakeHttpsResponse:
    """Encode one deterministic GitHub JSON response."""
    return FakeHttpsResponse(
        body=json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )


def test_transport_reads_only_uv_lock_at_exact_commit_sha() -> None:
    """Keep path and immutable ref fixed by code instead of caller-controlled input."""
    response = _json_response(_contents_payload())
    factory = SingleConnectionFactory(response=response)
    source = GitHubRestSnapshotSource(connection_factory=factory)

    payload = source.get_uv_lock("brunovicco", "opslens", _COMMIT_SHA)

    assert payload["path"] == UV_LOCK_PATH
    assert factory.calls == [("api.github.com", 10.0)]
    connection = factory.connection
    assert connection is not None
    assert connection.closed is True
    method, path, headers = connection.calls[0]
    assert method == "GET"
    assert path == f"/repos/brunovicco/opslens/contents/uv.lock?ref={_COMMIT_SHA}"
    assert headers["Accept"] == "application/vnd.github+json"


def test_transport_rejects_non_full_commit_before_connection() -> None:
    """Never let a moving or abbreviated ref enter immutable file acquisition."""
    response = _json_response(_contents_payload())
    factory = SingleConnectionFactory(response=response)
    source = GitHubRestSnapshotSource(connection_factory=factory)

    with pytest.raises(GitHubInvalidResponseError):
        source.get_uv_lock("brunovicco", "opslens", "main")

    assert factory.calls == []


def test_transport_applies_separate_file_json_budget() -> None:
    """Bound Base64/JSON framing independently from the decoded content budget."""
    response = _json_response(_contents_payload())
    response.headers["Content-Length"] = str(len(response.body))
    config = GitHubRestClientConfig(max_file_json_response_bytes=10)
    factory = SingleConnectionFactory(response=response)
    source = GitHubRestSnapshotSource(config=config, connection_factory=factory)

    with pytest.raises(GitHubResponseTooLargeError):
        source.get_uv_lock("brunovicco", "opslens", _COMMIT_SHA)

    assert response.read_calls == []
