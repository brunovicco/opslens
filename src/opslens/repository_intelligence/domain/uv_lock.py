"""Typed deterministic inventory evidence extracted from verified `uv.lock` bytes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from opslens.repository_intelligence.domain.errors import InvalidUvLockError
from opslens.repository_intelligence.domain.file_evidence import (
    UV_LOCK_PATH,
    ImmutableRepositoryFileEvidence,
)

PYPI_SIMPLE_REGISTRY_URL = "https://pypi.org/simple"
MAX_UV_LOCK_PACKAGE_RECORDS = 5_000
SUPPORTED_UV_LOCK_SCHEMA_VERSION = 1
SUPPORTED_UV_LOCK_REVISIONS = frozenset({1, 2, 3})


class UvUnsupportedPackageReason(StrEnum):
    """Stable reasons why one structurally valid locked package is not PyPI evidence."""

    UNSUPPORTED_REGISTRY = "unsupported_registry"
    UNSUPPORTED_NON_REGISTRY_SOURCE = "unsupported_non_registry_source"
    UNSUPPORTED_SOURCE_KIND = "unsupported_source_kind"


@dataclass(frozen=True, slots=True)
class UvLockedPyPIPackageEvidence:
    """One exact package/version record whose source is canonical PyPI."""

    record_index: int
    name_original: str
    version_original: str
    registry_url: str
    resolution_markers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Protect the typed PyPI lock-record invariants independently of the parser."""
        _validate_record_index(self.record_index)
        _validate_clean_text(self.name_original, field="package name")
        _validate_clean_text(self.version_original, field="package version")
        if self.registry_url != PYPI_SIMPLE_REGISTRY_URL:
            raise InvalidUvLockError(
                "PyPI locked-package evidence must use the canonical PyPI simple registry."
            )
        _validate_markers(self.resolution_markers)


@dataclass(frozen=True, slots=True)
class UvUnsupportedLockedPackageEvidence:
    """One valid lock record retained explicitly because its source is not supported."""

    record_index: int
    name_original: str
    version_original: str
    source_kind: str
    reason_code: UvUnsupportedPackageReason
    resolution_markers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Protect unsupported-record provenance without normalizing its identity."""
        _validate_record_index(self.record_index)
        _validate_clean_text(self.name_original, field="package name")
        _validate_clean_text(self.version_original, field="package version")
        _validate_clean_text(self.source_kind, field="package source kind")
        _validate_markers(self.resolution_markers)


@dataclass(frozen=True, slots=True)
class ParsedUvLockEvidence:
    """Bounded typed package inventory derived from one immutable `uv.lock` file."""

    file_evidence: ImmutableRepositoryFileEvidence
    schema_version: int
    revision: int | None
    requires_python: str | None
    resolution_markers: tuple[str, ...]
    pypi_packages: tuple[UvLockedPyPIPackageEvidence, ...]
    unsupported_packages: tuple[UvUnsupportedLockedPackageEvidence, ...]

    def __post_init__(self) -> None:
        """Ensure parsed inventory remains bound to the frozen parser contract."""
        if self.file_evidence.path != UV_LOCK_PATH:
            raise InvalidUvLockError("Parsed uv.lock evidence must originate from `uv.lock`.")
        if self.schema_version != SUPPORTED_UV_LOCK_SCHEMA_VERSION:
            raise InvalidUvLockError("Parsed uv.lock evidence carries an unsupported schema version.")
        if self.revision is not None and self.revision not in SUPPORTED_UV_LOCK_REVISIONS:
            raise InvalidUvLockError("Parsed uv.lock evidence carries an unsupported revision.")
        if self.requires_python is not None:
            _validate_clean_text(self.requires_python, field="requires-python")
        _validate_markers(self.resolution_markers)

        total_records = len(self.pypi_packages) + len(self.unsupported_packages)
        if not 1 <= total_records <= MAX_UV_LOCK_PACKAGE_RECORDS:
            raise InvalidUvLockError(
                "Parsed uv.lock inventory must contain between 1 and 5000 package records."
            )

        observed_indexes = [
            package.record_index
            for package in (*self.pypi_packages, *self.unsupported_packages)
        ]
        if len(set(observed_indexes)) != total_records:
            raise InvalidUvLockError("Parsed uv.lock package record indexes must be unique.")
        if set(observed_indexes) != set(range(total_records)):
            raise InvalidUvLockError(
                "Parsed uv.lock package record indexes must preserve the complete source array."
            )

    @property
    def package_count(self) -> int:
        """Return the complete package-record count without hiding unsupported records."""
        return len(self.pypi_packages) + len(self.unsupported_packages)


def _validate_record_index(value: int) -> None:
    """Reject boolean and negative record indexes."""
    if type(value) is not int or value < 0:
        raise InvalidUvLockError("uv.lock package record index must be a non-negative integer.")


def _validate_clean_text(value: str, *, field: str) -> None:
    """Require non-empty source text while preserving exact original spelling."""
    if not value or value != value.strip():
        raise InvalidUvLockError(f"uv.lock {field} must be a non-empty clean string.")


def _validate_markers(markers: tuple[str, ...]) -> None:
    """Validate marker provenance without evaluating marker semantics."""
    for marker in markers:
        _validate_clean_text(marker, field="resolution marker")
