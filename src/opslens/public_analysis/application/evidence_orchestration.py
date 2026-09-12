"""Compose admitted public requests into immutable repository dependency evidence."""

from typing import Protocol

from opslens.public_analysis.domain import (
    PublicAnalysisRequest,
    PublicAnalysisValidationError,
    PublicRepositoryEvidenceExecution,
)
from opslens.repository_intelligence.application import (
    GitHubRepositorySnapshotSource,
    GitHubUvLockSource,
    acquire_uv_lock_evidence,
    normalize_uv_lock_pypi_dependencies,
    resolve_github_repository_snapshot,
)
from opslens.repository_intelligence.parsers.uv_lock import parse_uv_lock_evidence


class PublicRepositoryEvidenceSource(
    GitHubRepositorySnapshotSource,
    GitHubUvLockSource,
    Protocol,
):
    """Read-only source operations allowed by the Gate 9.2 orchestration boundary."""


def build_public_repository_evidence(
    request: PublicAnalysisRequest,
    source: PublicRepositoryEvidenceSource,
) -> PublicRepositoryEvidenceExecution:
    """Resolve and inspect one admitted repository without executing repository code."""
    if type(request) is not PublicAnalysisRequest:
        raise PublicAnalysisValidationError(
            "public repository evidence orchestration requires an admitted request"
        )

    target = request.target
    resolution = resolve_github_repository_snapshot(
        source,
        owner=target.owner,
        name=target.name,
        requested_ref=target.requested_ref,
    )
    file_evidence = acquire_uv_lock_evidence(
        source,
        snapshot=resolution.snapshot,
    )
    parsed_lock = parse_uv_lock_evidence(file_evidence)
    normalization_inventory = normalize_uv_lock_pypi_dependencies(parsed_lock)

    return PublicRepositoryEvidenceExecution(
        request=request,
        snapshot_resolution=resolution,
        file_evidence=file_evidence,
        parsed_lock=parsed_lock,
        normalization_inventory=normalization_inventory,
    )


__all__ = [
    "PublicRepositoryEvidenceSource",
    "build_public_repository_evidence",
]
