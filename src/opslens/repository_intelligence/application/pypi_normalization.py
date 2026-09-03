"""Normalize canonical-PyPI lock records through the existing Phase 3 authority."""

from __future__ import annotations

from opslens.correlation.domain.errors import CorrelationContractError
from opslens.correlation.domain.pypi import (
    build_pypi_purl,
    canonicalize_pypi_package,
    canonicalize_pypi_version,
)
from opslens.repository_intelligence.domain import (
    NormalizedRepositoryPyPIDependencyEvidence,
    ParsedUvLockEvidence,
    RepositoryPyPINormalizationInventory,
    UnsupportedRepositoryPyPINormalizationEvidence,
)


def normalize_uv_lock_pypi_dependencies(
    parsed_lock: ParsedUvLockEvidence,
) -> RepositoryPyPINormalizationInventory:
    """Apply Phase 3 identity semantics to every canonical-PyPI source lock record."""
    normalized: list[NormalizedRepositoryPyPIDependencyEvidence] = []
    unsupported: list[UnsupportedRepositoryPyPINormalizationEvidence] = []

    snapshot_id = parsed_lock.file_evidence.snapshot.snapshot_id
    file_evidence_id = parsed_lock.file_evidence.evidence_id

    for source_record in parsed_lock.pypi_packages:
        try:
            package = canonicalize_pypi_package(source_record.name_original)
            version = canonicalize_pypi_version(source_record.version_original)
            purl = build_pypi_purl(package=package, version=version)
        except CorrelationContractError as exc:
            unsupported.append(
                UnsupportedRepositoryPyPINormalizationEvidence(
                    source_record=source_record,
                    reason_code=exc.reason_code,
                )
            )
            continue

        normalized.append(
            NormalizedRepositoryPyPIDependencyEvidence(
                source_record=source_record,
                package=package,
                version=version,
                purl=purl,
                snapshot_id=snapshot_id,
                file_evidence_id=file_evidence_id,
            )
        )

    return RepositoryPyPINormalizationInventory(
        parsed_lock=parsed_lock,
        normalized_dependencies=tuple(normalized),
        unsupported_normalization=tuple(unsupported),
    )
