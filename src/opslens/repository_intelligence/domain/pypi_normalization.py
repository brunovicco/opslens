"""Repository dependency evidence normalized by the Phase 3 PyPI identity authority."""

from __future__ import annotations

from dataclasses import dataclass

from opslens.correlation.domain.pypi import (
    CanonicalPyPIPackage,
    CanonicalPyPIVersion,
    build_pypi_purl,
)
from opslens.repository_intelligence.domain.errors import InvalidUvLockError
from opslens.repository_intelligence.domain.uv_lock import (
    ParsedUvLockEvidence,
    UvLockedPyPIPackageEvidence,
)


@dataclass(frozen=True, slots=True)
class NormalizedRepositoryPyPIDependencyEvidence:
    """One lock record with canonical identity established by the Phase 3 authority."""

    source_record: UvLockedPyPIPackageEvidence
    package: CanonicalPyPIPackage
    version: CanonicalPyPIVersion
    purl: str
    snapshot_id: str
    file_evidence_id: str

    def __post_init__(self) -> None:
        """Ensure canonical evidence still links exactly to the original lock record."""
        if self.package.original != self.source_record.name_original:
            raise InvalidUvLockError(
                "Normalized PyPI package evidence must preserve the source lockfile name."
            )
        if self.version.original != self.source_record.version_original:
            raise InvalidUvLockError(
                "Normalized PyPI version evidence must preserve the source lockfile version."
            )
        if self.purl != build_pypi_purl(package=self.package, version=self.version):
            raise InvalidUvLockError(
                "Normalized repository dependency purl must match Phase 3 canonical identity."
            )
        _validate_evidence_id(self.snapshot_id, field="snapshot_id")
        _validate_evidence_id(self.file_evidence_id, field="file_evidence_id")

    @property
    def record_index(self) -> int:
        """Return the original zero-based `uv.lock` record index."""
        return self.source_record.record_index

    @property
    def resolution_markers(self) -> tuple[str, ...]:
        """Return marker provenance without evaluating runtime applicability."""
        return self.source_record.resolution_markers


@dataclass(frozen=True, slots=True)
class UnsupportedRepositoryPyPINormalizationEvidence:
    """One canonical-PyPI source record rejected by the Phase 3 identity authority."""

    source_record: UvLockedPyPIPackageEvidence
    reason_code: str

    def __post_init__(self) -> None:
        """Require an explicit stable reason for fail-closed record handling."""
        if not self.reason_code or self.reason_code != self.reason_code.strip():
            raise InvalidUvLockError(
                "Unsupported PyPI normalization evidence requires a clean reason code."
            )

    @property
    def record_index(self) -> int:
        """Return the original zero-based `uv.lock` record index."""
        return self.source_record.record_index


@dataclass(frozen=True, slots=True)
class RepositoryPyPINormalizationInventory:
    """Complete Phase 3 normalization accounting for every PyPI-source lock record."""

    parsed_lock: ParsedUvLockEvidence
    normalized_dependencies: tuple[NormalizedRepositoryPyPIDependencyEvidence, ...]
    unsupported_normalization: tuple[UnsupportedRepositoryPyPINormalizationEvidence, ...]

    def __post_init__(self) -> None:
        """Require complete exactly-once accounting of all canonical-PyPI source records."""
        expected_by_index = {
            record.record_index: record for record in self.parsed_lock.pypi_packages
        }
        if len(expected_by_index) != len(self.parsed_lock.pypi_packages):
            raise InvalidUvLockError(
                "Parsed PyPI lock records must have unique source indexes before normalization."
            )

        observed: dict[int, UvLockedPyPIPackageEvidence] = {}
        for dependency in self.normalized_dependencies:
            _record_once(observed, dependency.source_record)
            if dependency.snapshot_id != self.parsed_lock.file_evidence.snapshot.snapshot_id:
                raise InvalidUvLockError(
                    "Normalized dependency snapshot id does not match parsed lock evidence."
                )
            if dependency.file_evidence_id != self.parsed_lock.file_evidence.evidence_id:
                raise InvalidUvLockError(
                    "Normalized dependency file evidence id does not match parsed lock evidence."
                )

        for unsupported in self.unsupported_normalization:
            _record_once(observed, unsupported.source_record)

        if observed != expected_by_index:
            raise InvalidUvLockError(
                "Every PyPI-source lock record must be accounted for exactly once after normalization."
            )

    @property
    def pypi_source_record_count(self) -> int:
        """Return the complete canonical-PyPI source record count."""
        return len(self.parsed_lock.pypi_packages)


def _record_once(
    observed: dict[int, UvLockedPyPIPackageEvidence],
    record: UvLockedPyPIPackageEvidence,
) -> None:
    """Insert one record by source index while rejecting duplicate bridge accounting."""
    if record.record_index in observed:
        raise InvalidUvLockError(
            f"PyPI lock record {record.record_index} appears more than once in normalization output."
        )
    observed[record.record_index] = record


def _validate_evidence_id(value: str, *, field: str) -> None:
    """Require non-empty exact provenance identifiers without normalization."""
    if not value or value != value.strip():
        raise InvalidUvLockError(f"Normalized dependency {field} must be a clean string.")
