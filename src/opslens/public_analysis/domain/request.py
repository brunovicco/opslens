"""Deterministic public repository-analysis request identity."""

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from opslens.public_analysis.domain.errors import PublicAnalysisValidationError
from opslens.repository_intelligence.domain.models import (
    validate_github_repository_coordinates,
    validate_github_repository_ref,
)

PUBLIC_ANALYSIS_REQUEST_CONTRACT_VERSION = "public-analysis-request:v1"

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)


def _canonical_json(value: object) -> bytes:
    """Serialize one deterministic public-request identity payload."""
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _request_identity_payload(target: "PublicRepositoryTarget") -> dict[str, object]:
    """Return the normalized semantics that own public request identity."""
    return {
        "contract_version": PUBLIC_ANALYSIS_REQUEST_CONTRACT_VERSION,
        "provider": "github",
        "repository_name": target.name,
        "repository_owner": target.owner,
        "requested_ref": target.requested_ref,
    }


@dataclass(frozen=True, slots=True)
class PublicRepositoryTarget:
    """Validated public-input coordinates for later immutable GitHub resolution."""

    owner: str
    name: str
    requested_ref: str | None = None

    def __post_init__(self) -> None:
        """Reuse the Phase 4 GitHub coordinate/ref authority contract."""
        if type(self.owner) is not str or type(self.name) is not str:
            raise PublicAnalysisValidationError(
                "repository owner and name must be strings"
            )
        try:
            owner, name = validate_github_repository_coordinates(self.owner, self.name)
        except ValueError as exc:
            raise PublicAnalysisValidationError(
                "repository coordinates violate the GitHub identity contract"
            ) from exc
        object.__setattr__(self, "owner", owner)
        object.__setattr__(self, "name", name)

        requested_ref = self.requested_ref
        if requested_ref is not None:
            if type(requested_ref) is not str:
                raise PublicAnalysisValidationError(
                    "requested_ref must be a string or null"
                )
            try:
                requested_ref = validate_github_repository_ref(requested_ref)
            except ValueError as exc:
                raise PublicAnalysisValidationError(
                    "requested_ref violates the GitHub ref contract"
                ) from exc
            object.__setattr__(self, "requested_ref", requested_ref)

    @property
    def canonical_repository_url(self) -> str:
        """Return the canonical human-readable GitHub web URL."""
        return f"https://github.com/{self.owner}/{self.name}"


@dataclass(frozen=True, slots=True)
class PublicAnalysisRequest:
    """Content-addressed admitted request for the fixed public analysis operation."""

    target: PublicRepositoryTarget
    request_sha256: str
    request_id: str

    def __post_init__(self) -> None:
        """Reject forged identities or values outside the v1 public contract."""
        if type(self.target) is not PublicRepositoryTarget:
            raise PublicAnalysisValidationError(
                "target must be one admitted PublicRepositoryTarget"
            )
        expected_sha256 = sha256(
            _canonical_json(_request_identity_payload(self.target))
        ).hexdigest()
        if (
            type(self.request_sha256) is not str
            or _SHA256_PATTERN.fullmatch(self.request_sha256) is None
            or self.request_sha256 != expected_sha256
        ):
            raise PublicAnalysisValidationError(
                "request_sha256 must match the normalized public request semantics"
            )
        expected_request_id = (
            f"{PUBLIC_ANALYSIS_REQUEST_CONTRACT_VERSION}:{expected_sha256}"
        )
        if self.request_id != expected_request_id:
            raise PublicAnalysisValidationError(
                "request_id must match the content-addressed public request identity"
            )


def create_public_analysis_request(
    target: PublicRepositoryTarget,
) -> PublicAnalysisRequest:
    """Create one deterministic request from already-validated GitHub coordinates."""
    if type(target) is not PublicRepositoryTarget:
        raise PublicAnalysisValidationError(
            "target must be one admitted PublicRepositoryTarget"
        )
    digest = sha256(_canonical_json(_request_identity_payload(target))).hexdigest()
    return PublicAnalysisRequest(
        target=target,
        request_sha256=digest,
        request_id=f"{PUBLIC_ANALYSIS_REQUEST_CONTRACT_VERSION}:{digest}",
    )


__all__ = [
    "PUBLIC_ANALYSIS_REQUEST_CONTRACT_VERSION",
    "PublicAnalysisRequest",
    "PublicRepositoryTarget",
    "create_public_analysis_request",
]
