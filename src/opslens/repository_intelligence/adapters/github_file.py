"""Project GitHub Contents API payloads into immutable inert file evidence."""

from __future__ import annotations

import base64
import binascii
import re

from opslens.repository_intelligence.domain import (
    MAX_REPOSITORY_FILE_BYTES,
    UV_LOCK_PATH,
    ImmutableRepositoryFileEvidence,
    ImmutableRepositorySnapshot,
    InvalidGitHubSourceEvidenceError,
    compute_content_sha256,
)

_BASE64_WHITESPACE_PATTERN = re.compile(r"[\r\n]", re.ASCII)


def project_github_uv_lock_evidence(
    *,
    snapshot: ImmutableRepositorySnapshot,
    payload: dict[str, object],
) -> ImmutableRepositoryFileEvidence:
    """Validate one GitHub Contents response and bind inert bytes to the snapshot."""
    source_type = _required_str(payload, "type")
    source_path = _required_str(payload, "path")
    source_name = _required_str(payload, "name")
    encoding = _required_str(payload, "encoding")
    source_size = _required_int(payload, "size")
    blob_sha = _required_str(payload, "sha")
    encoded_content = _required_str(payload, "content")

    if source_type != "file":
        raise InvalidGitHubSourceEvidenceError(
            "GitHub uv.lock evidence must describe a regular repository file."
        )

    if source_path != UV_LOCK_PATH or source_name != UV_LOCK_PATH:
        raise InvalidGitHubSourceEvidenceError(
            "GitHub uv.lock evidence path/name does not match the allowlisted file."
        )

    if encoding != "base64":
        raise InvalidGitHubSourceEvidenceError(
            "GitHub uv.lock evidence must use Base64 content encoding."
        )

    compact_content = _BASE64_WHITESPACE_PATTERN.sub("", encoded_content)
    if not compact_content:
        raise InvalidGitHubSourceEvidenceError(
            "GitHub uv.lock evidence must contain non-empty Base64 content."
        )

    try:
        content_bytes = base64.b64decode(compact_content, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InvalidGitHubSourceEvidenceError(
            "GitHub uv.lock content is not valid strict Base64 evidence."
        ) from exc

    if not content_bytes:
        raise InvalidGitHubSourceEvidenceError(
            "GitHub uv.lock must contain non-empty inert content."
        )

    if len(content_bytes) > MAX_REPOSITORY_FILE_BYTES:
        raise InvalidGitHubSourceEvidenceError(
            "GitHub uv.lock decoded content exceeds the 1 MiB evidence bound."
        )

    if source_size != len(content_bytes):
        raise InvalidGitHubSourceEvidenceError(
            "GitHub uv.lock source size does not match decoded content bytes."
        )

    return ImmutableRepositoryFileEvidence(
        snapshot=snapshot,
        path=UV_LOCK_PATH,
        blob_sha=blob_sha,
        size_bytes=source_size,
        content_sha256=compute_content_sha256(content_bytes),
        content_bytes=content_bytes,
    )


def _required_str(payload: dict[str, object], field: str) -> str:
    """Return one required non-empty source string without rewriting it."""
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise InvalidGitHubSourceEvidenceError(
            f"GitHub source field {field!r} must contain a non-empty string."
        )
    return value


def _required_int(payload: dict[str, object], field: str) -> int:
    """Return one required non-negative JSON integer while rejecting booleans."""
    value = payload.get(field)
    if type(value) is not int or value < 0:
        raise InvalidGitHubSourceEvidenceError(
            f"GitHub source field {field!r} must contain a non-negative integer."
        )
    return value
