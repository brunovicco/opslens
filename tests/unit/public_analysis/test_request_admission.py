"""Unit tests for the Phase 9 public repository request boundary."""

from __future__ import annotations

import json

import pytest

from opslens.public_analysis.application import (
    MAX_PUBLIC_ANALYSIS_REQUEST_BYTES,
    PublicAnalysisRequestAdmissionError,
    admit_public_analysis_request,
)
from opslens.public_analysis.domain import (
    PUBLIC_ANALYSIS_REQUEST_CONTRACT_VERSION,
    PublicAnalysisRequest,
    PublicAnalysisValidationError,
)


def _json_body(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":")).encode("utf-8")


def test_admits_canonical_github_repository_with_default_branch_resolution() -> None:
    """Null/absent ref means later default-branch resolution, never invented `main`."""
    admitted = admit_public_analysis_request(
        _json_body({"repository_url": "https://github.com/brunovicco/opslens"})
    )

    request = admitted.request
    assert request.target.owner == "brunovicco"
    assert request.target.name == "opslens"
    assert request.target.requested_ref is None
    assert request.target.canonical_repository_url == (
        "https://github.com/brunovicco/opslens"
    )
    assert request.request_sha256 == (
        "c504720cdc942909ce3a2b40461b59f63cc71dea651549a392f15776788074e5"
    )
    assert request.request_id == (
        f"{PUBLIC_ANALYSIS_REQUEST_CONTRACT_VERSION}:"
        "c504720cdc942909ce3a2b40461b59f63cc71dea651549a392f15776788074e5"
    )
    assert admitted.raw_body_bytes > 0
    assert len(admitted.raw_body_sha256) == 64


def test_admits_explicit_ref_and_optional_trailing_slash() -> None:
    """A clean explicit GitHub ref survives admission for later immutable resolution."""
    admitted = admit_public_analysis_request(
        _json_body(
            {
                "repository_url": "https://GitHub.com/brunovicco/opslens/",
                "requested_ref": "release/v1",
            }
        )
    )

    assert admitted.request.target.owner == "brunovicco"
    assert admitted.request.target.name == "opslens"
    assert admitted.request.target.requested_ref == "release/v1"


def test_semantically_identical_bodies_share_normalized_request_identity() -> None:
    """JSON whitespace/key order are raw provenance, not normalized request semantics."""
    first = admit_public_analysis_request(
        b'{"repository_url":"https://github.com/brunovicco/opslens","requested_ref":null}'
    )
    second = admit_public_analysis_request(
        b'{ "requested_ref": null, "repository_url": "https://GitHub.com/brunovicco/opslens/" }'
    )

    assert first.request.request_id == second.request.request_id
    assert first.request.request_sha256 == second.request.request_sha256
    assert first.raw_body_sha256 != second.raw_body_sha256


@pytest.mark.parametrize(
    "repository_url",
    [
        "http://github.com/brunovicco/opslens",
        "https://gitlab.com/brunovicco/opslens",
        "https://api.github.com/repos/brunovicco/opslens",
        "https://github.com.evil.example/brunovicco/opslens",
        "https://evil.example/?next=https://github.com/brunovicco/opslens",
        "https://github.com@evil.example/brunovicco/opslens",
        "https://user:secret@github.com/brunovicco/opslens",
        "https://github.com:443/brunovicco/opslens",
        "https://github.com/brunovicco/opslens?tab=readme",
        "https://github.com/brunovicco/opslens#readme",
        "https://github.com/brunovicco/opslens/tree/main",
        "https://github.com/brunovicco%2Fopslens/repository",
        "https://github.com/brunovicco/%6fpslens",
        "https://github.com/brunovicco/opslens%2Ftree%2Fmain",
        "https://github.com//brunovicco/opslens",
        "https://git\nhub.com/brunovicco/opslens",
        "https://github.com\\@evil.example/brunovicco/opslens",
        "https://[github.com/brunovicco/opslens",
        " https://github.com/brunovicco/opslens",
    ],
)
def test_rejects_urls_outside_exact_public_github_repository_boundary(
    repository_url: str,
) -> None:
    """Public URL admission must collapse SSRF/path ambiguity before acquisition."""
    with pytest.raises(PublicAnalysisRequestAdmissionError):
        admit_public_analysis_request(_json_body({"repository_url": repository_url}))


def test_rejects_duplicate_json_keys_before_projection() -> None:
    """Duplicate fields cannot exploit parser last-value-wins behavior."""
    with pytest.raises(
        PublicAnalysisRequestAdmissionError,
        match="duplicate object keys",
    ):
        admit_public_analysis_request(
            b'{"repository_url":"https://github.com/a/b",'
            b'"repository_url":"https://github.com/c/d"}'
        )


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"repository_url": 7},
        {"repository_url": "https://github.com/a/b", "requested_ref": False},
        {"repository_url": "https://github.com/a/b", "requested_ref": " bad"},
        {"repository_url": "https://github.com/a/b", "provider": "github"},
        ["https://github.com/a/b"],
    ],
)
def test_rejects_wrong_shape_types_unknown_fields_and_invalid_ref(payload: object) -> None:
    """The public v1 body is intentionally smaller than internal domain contracts."""
    with pytest.raises(PublicAnalysisRequestAdmissionError):
        admit_public_analysis_request(_json_body(payload))


def test_rejects_empty_invalid_utf8_invalid_json_and_oversized_body() -> None:
    """Transport-independent admission owns a hard body budget before JSON semantics."""
    invalid_bodies = (
        b"",
        b"\xff",
        b"{",
        b" " * (MAX_PUBLIC_ANALYSIS_REQUEST_BYTES + 1),
    )

    for raw_body in invalid_bodies:
        with pytest.raises(PublicAnalysisRequestAdmissionError):
            admit_public_analysis_request(raw_body)


def test_request_identity_changes_when_explicit_ref_changes() -> None:
    """Moving-ref provenance participates in pre-resolution public request identity."""
    main = admit_public_analysis_request(
        _json_body(
            {
                "repository_url": "https://github.com/brunovicco/opslens",
                "requested_ref": "main",
            }
        )
    )
    release = admit_public_analysis_request(
        _json_body(
            {
                "repository_url": "https://github.com/brunovicco/opslens",
                "requested_ref": "release/v1",
            }
        )
    )

    assert main.request.request_sha256 != release.request.request_sha256


def test_content_addressed_request_rejects_forged_identity() -> None:
    """Callers cannot replace a normalized request digest after admission."""
    admitted = admit_public_analysis_request(
        _json_body({"repository_url": "https://github.com/brunovicco/opslens"})
    )

    with pytest.raises(PublicAnalysisValidationError):
        PublicAnalysisRequest(
            target=admitted.request.target,
            request_sha256="0" * 64,
            request_id=f"{PUBLIC_ANALYSIS_REQUEST_CONTRACT_VERSION}:{'0' * 64}",
        )


def test_error_messages_do_not_echo_untrusted_repository_url() -> None:
    """Admission failures remain bounded/content-free enough for future telemetry."""
    untrusted = "https://evil.example/private-token-like-value"

    with pytest.raises(PublicAnalysisRequestAdmissionError) as exc_info:
        admit_public_analysis_request(_json_body({"repository_url": untrusted}))

    assert untrusted not in str(exc_info.value)
    assert "private-token-like-value" not in str(exc_info.value)
