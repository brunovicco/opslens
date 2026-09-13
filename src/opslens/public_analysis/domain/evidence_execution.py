"""Deterministic binding from a public request to immutable repository evidence."""

import json
from dataclasses import dataclass
from hashlib import sha256

from opslens.public_analysis.domain.errors import PublicAnalysisValidationError
from opslens.public_analysis.domain.request import PublicAnalysisRequest
from opslens.repository_intelligence.application.snapshot_resolution import (
    GitHubSnapshotResolutionEvidence,
)
from opslens.repository_intelligence.domain import (
    ImmutableRepositoryFileEvidence,
    ParsedUvLockEvidence,
    RepositoryPyPINormalizationInventory,
)

PUBLIC_REPOSITORY_EVIDENCE_CONTRACT_VERSION = "public-repository-evidence:v1"


def _canonical_json(value: object) -> bytes:
    """Serialize one deterministic public repository evidence identity payload."""
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class PublicRepositoryEvidenceExecution:
    """Verified dependency evidence for one admitted public repository request."""

    request: PublicAnalysisRequest
    snapshot_resolution: GitHubSnapshotResolutionEvidence
    file_evidence: ImmutableRepositoryFileEvidence
    parsed_lock: ParsedUvLockEvidence
    normalization_inventory: RepositoryPyPINormalizationInventory

    def __post_init__(self) -> None:
        """Reject authority drift between request, snapshot, file, and parsed evidence."""
        if type(self.request) is not PublicAnalysisRequest:
            raise PublicAnalysisValidationError(
                "public evidence execution requires one admitted PublicAnalysisRequest"
            )
        if type(self.snapshot_resolution) is not GitHubSnapshotResolutionEvidence:
            raise PublicAnalysisValidationError(
                "public evidence execution requires typed snapshot-resolution evidence"
            )
        if type(self.file_evidence) is not ImmutableRepositoryFileEvidence:
            raise PublicAnalysisValidationError(
                "public evidence execution requires immutable repository file evidence"
            )
        if type(self.parsed_lock) is not ParsedUvLockEvidence:
            raise PublicAnalysisValidationError(
                "public evidence execution requires typed parsed uv.lock evidence"
            )
        if type(self.normalization_inventory) is not RepositoryPyPINormalizationInventory:
            raise PublicAnalysisValidationError(
                "public evidence execution requires typed normalization inventory"
            )

        target = self.request.target
        resolution = self.snapshot_resolution
        snapshot = resolution.snapshot

        if (
            resolution.requested_owner != target.owner
            or resolution.requested_name != target.name
        ):
            raise PublicAnalysisValidationError(
                "snapshot resolution must originate from the admitted public coordinates"
            )

        requested_ref = target.requested_ref
        if requested_ref is None:
            if resolution.used_default_branch is not True:
                raise PublicAnalysisValidationError(
                    "null public requested_ref must resolve through source default-branch evidence"
                )
        elif (
            resolution.used_default_branch is not False
            or snapshot.requested_ref != requested_ref
        ):
            raise PublicAnalysisValidationError(
                "explicit public requested_ref must be preserved by snapshot resolution"
            )

        if self.file_evidence.snapshot != snapshot:
            raise PublicAnalysisValidationError(
                "repository file evidence must use the exact resolved immutable snapshot"
            )
        if self.parsed_lock.file_evidence != self.file_evidence:
            raise PublicAnalysisValidationError(
                "parsed uv.lock evidence must use the exact acquired file evidence"
            )
        if self.normalization_inventory.parsed_lock != self.parsed_lock:
            raise PublicAnalysisValidationError(
                "normalization inventory must use the exact parsed uv.lock evidence"
            )

    @property
    def snapshot_id(self) -> str:
        """Return the exact immutable repository snapshot identity."""
        return self.snapshot_resolution.snapshot.snapshot_id

    @property
    def file_evidence_id(self) -> str:
        """Return the exact immutable uv.lock evidence identity."""
        return self.file_evidence.evidence_id

    @property
    def canonical_json(self) -> bytes:
        """Project the complete bounded identity needed for downstream public analysis."""
        snapshot = self.snapshot_resolution.snapshot
        repository = snapshot.repository
        parsed = self.parsed_lock
        inventory = self.normalization_inventory

        normalized_dependencies: list[object] = [
            {
                "record_index": dependency.record_index,
                "name": dependency.package.canonical,
                "version": dependency.version.canonical,
                "purl": dependency.purl,
                "resolution_markers": list(dependency.resolution_markers),
            }
            for dependency in inventory.normalized_dependencies
        ]
        unsupported_normalization: list[object] = [
            {
                "record_index": unsupported.record_index,
                "reason_code": unsupported.reason_code,
            }
            for unsupported in inventory.unsupported_normalization
        ]
        unsupported_packages: list[object] = [
            {
                "record_index": package.record_index,
                "name_original": package.name_original,
                "version_original": package.version_original,
                "source_kind": package.source_kind,
                "reason_code": package.reason_code.value,
                "resolution_markers": list(package.resolution_markers),
            }
            for package in parsed.unsupported_packages
        ]

        payload: dict[str, object] = {
            "contract_version": PUBLIC_REPOSITORY_EVIDENCE_CONTRACT_VERSION,
            "request": {
                "request_id": self.request.request_id,
                "request_sha256": self.request.request_sha256,
                "requested_owner": self.snapshot_resolution.requested_owner,
                "requested_name": self.snapshot_resolution.requested_name,
            },
            "repository": {
                "provider": repository.provider.value,
                "repository_id": repository.repository_id,
                "owner": repository.owner,
                "name": repository.name,
                "full_name": repository.full_name,
                "used_default_branch": self.snapshot_resolution.used_default_branch,
                "resolved_ref": snapshot.requested_ref,
                "commit_sha": snapshot.commit_sha,
                "tree_sha": snapshot.tree_sha,
                "snapshot_id": snapshot.snapshot_id,
            },
            "dependency_file": {
                "path": self.file_evidence.path,
                "file_evidence_id": self.file_evidence.evidence_id,
                "blob_sha": self.file_evidence.blob_sha,
                "content_sha256": self.file_evidence.content_sha256,
                "size_bytes": self.file_evidence.size_bytes,
            },
            "parsed_lock": {
                "schema_version": parsed.schema_version,
                "revision": parsed.revision,
                "requires_python": parsed.requires_python,
                "resolution_markers": list(parsed.resolution_markers),
                "package_count": parsed.package_count,
                "pypi_source_record_count": len(parsed.pypi_packages),
                "unsupported_package_count": len(parsed.unsupported_packages),
                "unsupported_packages": unsupported_packages,
            },
            "normalization": {
                "normalized_dependency_count": len(inventory.normalized_dependencies),
                "unsupported_normalization_count": len(
                    inventory.unsupported_normalization
                ),
                "normalized_dependencies": normalized_dependencies,
                "unsupported_normalization": unsupported_normalization,
            },
        }
        return _canonical_json(payload)

    @property
    def evidence_sha256(self) -> str:
        """Return SHA-256 of the complete public repository evidence projection."""
        return sha256(self.canonical_json).hexdigest()

    @property
    def execution_id(self) -> str:
        """Return stable content-addressed identity for the evidence execution."""
        return (
            f"{PUBLIC_REPOSITORY_EVIDENCE_CONTRACT_VERSION}@sha256:"
            f"{self.evidence_sha256}"
        )


__all__ = [
    "PUBLIC_REPOSITORY_EVIDENCE_CONTRACT_VERSION",
    "PublicRepositoryEvidenceExecution",
]
