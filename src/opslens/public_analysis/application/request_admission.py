"""Strict offline admission for the future public repository-analysis surface."""

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import cast
from urllib.parse import urlsplit

from opslens.public_analysis.domain.errors import PublicAnalysisValidationError
from opslens.public_analysis.domain.request import (
    PublicAnalysisRequest,
    PublicRepositoryTarget,
    create_public_analysis_request,
)

MAX_PUBLIC_ANALYSIS_REQUEST_BYTES = 2_048
MAX_PUBLIC_REPOSITORY_URL_CHARS = 256

_ALLOWED_KEYS = frozenset({"repository_url", "requested_ref"})
_REQUIRED_KEYS = frozenset({"repository_url"})
_REPOSITORY_PATH_PATTERN = re.compile(r"^/([^/]+)/([^/]+)/?$", re.ASCII)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x1f\x7f]", re.ASCII)


class PublicAnalysisRequestAdmissionError(ValueError):
    """Raised when untrusted public JSON cannot enter the domain contract."""


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate JSON object keys before normal object projection."""
    projected: dict[str, object] = {}
    for key, value in pairs:
        if key in projected:
            raise PublicAnalysisRequestAdmissionError(
                "public request JSON cannot contain duplicate object keys"
            )
        projected[key] = value
    return projected


def _decode_request_object(raw_body: bytes) -> dict[str, object]:
    """Decode one small UTF-8 JSON object with exact field admission."""
    if type(raw_body) is not bytes:
        raise PublicAnalysisRequestAdmissionError("public request body must be bytes")
    if not raw_body:
        raise PublicAnalysisRequestAdmissionError("public request body cannot be empty")
    if len(raw_body) > MAX_PUBLIC_ANALYSIS_REQUEST_BYTES:
        raise PublicAnalysisRequestAdmissionError(
            "public request body exceeds the hard byte limit"
        )
    try:
        text = raw_body.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise PublicAnalysisRequestAdmissionError(
            "public request body must be valid UTF-8"
        ) from exc
    try:
        decoded: object = json.loads(text, object_pairs_hook=_unique_json_object)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise PublicAnalysisRequestAdmissionError(
            "public request body must contain valid bounded JSON"
        ) from exc
    if not isinstance(decoded, dict):
        raise PublicAnalysisRequestAdmissionError(
            "public request JSON must contain one object"
        )
    mapping = cast(dict[object, object], decoded)
    if any(not isinstance(key, str) for key in mapping):
        raise PublicAnalysisRequestAdmissionError(
            "public request object keys must be strings"
        )
    typed = cast(dict[str, object], mapping)
    keys = frozenset(typed)
    if not _REQUIRED_KEYS.issubset(keys):
        raise PublicAnalysisRequestAdmissionError(
            "public request is missing a required field"
        )
    if not keys.issubset(_ALLOWED_KEYS):
        raise PublicAnalysisRequestAdmissionError(
            "public request contains unknown fields"
        )
    return typed


def _parse_repository_url(value: object) -> tuple[str, str]:
    """Project one GitHub web URL into coordinates; never retain it as a fetch target."""
    if not isinstance(value, str):
        raise PublicAnalysisRequestAdmissionError("repository_url must be a string")
    if not value or value != value.strip():
        raise PublicAnalysisRequestAdmissionError(
            "repository_url must be one normalized non-empty string"
        )
    if len(value) > MAX_PUBLIC_REPOSITORY_URL_CHARS:
        raise PublicAnalysisRequestAdmissionError(
            "repository_url exceeds the hard character limit"
        )
    if _CONTROL_CHARACTER_PATTERN.search(value) is not None:
        raise PublicAnalysisRequestAdmissionError(
            "repository_url cannot contain control characters"
        )
    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise PublicAnalysisRequestAdmissionError(
            "repository_url is not a valid bounded web URL"
        ) from exc
    if parsed.scheme.lower() != "https":
        raise PublicAnalysisRequestAdmissionError("repository_url must use HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise PublicAnalysisRequestAdmissionError(
            "repository_url cannot contain user information"
        )
    try:
        port = parsed.port
    except ValueError as exc:
        raise PublicAnalysisRequestAdmissionError(
            "repository_url contains an invalid port"
        ) from exc
    if port is not None:
        raise PublicAnalysisRequestAdmissionError(
            "repository_url cannot contain an explicit port"
        )
    if parsed.hostname is None or parsed.hostname.lower() != "github.com":
        raise PublicAnalysisRequestAdmissionError(
            "repository_url host is outside the public GitHub contract"
        )
    if parsed.query or parsed.fragment:
        raise PublicAnalysisRequestAdmissionError(
            "repository_url cannot contain query or fragment components"
        )
    if "%" in parsed.path:
        raise PublicAnalysisRequestAdmissionError(
            "repository_url cannot contain percent-encoded path data"
        )
    path_match = _REPOSITORY_PATH_PATTERN.fullmatch(parsed.path)
    if path_match is None:
        raise PublicAnalysisRequestAdmissionError(
            "repository_url must identify exactly one owner/repository path"
        )
    owner, name = path_match.groups()
    try:
        target = PublicRepositoryTarget(owner=owner, name=name)
    except PublicAnalysisValidationError as exc:
        raise PublicAnalysisRequestAdmissionError(
            "repository_url coordinates violate the GitHub identity contract"
        ) from exc
    return target.owner, target.name


def _parse_requested_ref(value: object) -> str | None:
    """Preserve null for later default-branch resolution and reject non-string values."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise PublicAnalysisRequestAdmissionError(
            "requested_ref must be a string or null"
        )
    return value


@dataclass(frozen=True, slots=True)
class PublicAnalysisRequestAdmission:
    """Content-free provenance for one raw public body and its admitted domain request."""

    request: PublicAnalysisRequest
    raw_body_sha256: str
    raw_body_bytes: int

    def __post_init__(self) -> None:
        """Reject forged admission provenance."""
        if type(self.request) is not PublicAnalysisRequest:
            raise PublicAnalysisRequestAdmissionError(
                "request must be one admitted PublicAnalysisRequest"
            )
        if (
            type(self.raw_body_sha256) is not str
            or _SHA256_PATTERN.fullmatch(self.raw_body_sha256) is None
        ):
            raise PublicAnalysisRequestAdmissionError(
                "raw_body_sha256 must be one lowercase SHA-256 digest"
            )
        if (
            type(self.raw_body_bytes) is not int
            or self.raw_body_bytes <= 0
            or self.raw_body_bytes > MAX_PUBLIC_ANALYSIS_REQUEST_BYTES
        ):
            raise PublicAnalysisRequestAdmissionError(
                "raw_body_bytes violates the public request byte bound"
            )


def admit_public_analysis_request(raw_body: bytes) -> PublicAnalysisRequestAdmission:
    """Admit one untrusted JSON body without performing network/provider operations."""
    mapping = _decode_request_object(raw_body)
    owner, name = _parse_repository_url(mapping["repository_url"])
    requested_ref = _parse_requested_ref(mapping.get("requested_ref"))
    try:
        target = PublicRepositoryTarget(
            owner=owner,
            name=name,
            requested_ref=requested_ref,
        )
    except PublicAnalysisValidationError as exc:
        raise PublicAnalysisRequestAdmissionError(
            "requested_ref violates the GitHub ref contract"
        ) from exc
    request = create_public_analysis_request(target)
    return PublicAnalysisRequestAdmission(
        request=request,
        raw_body_sha256=sha256(raw_body).hexdigest(),
        raw_body_bytes=len(raw_body),
    )


__all__ = [
    "MAX_PUBLIC_ANALYSIS_REQUEST_BYTES",
    "MAX_PUBLIC_REPOSITORY_URL_CHARS",
    "PublicAnalysisRequestAdmission",
    "PublicAnalysisRequestAdmissionError",
    "admit_public_analysis_request",
]
