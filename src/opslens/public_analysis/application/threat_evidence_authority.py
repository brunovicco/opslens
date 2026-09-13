"""Provider-neutral request-time threat-evidence authority for public analysis.

Gate 19.8 froze the deterministic contract between admitted repository dependency
evidence and the structured threat sources required by Phase 3/4 correlation. This
module intentionally performs no provider I/O and grants no runtime enablement.

Gate 20.0 admits a **partial scope**. The v1 contract refused any lock carrying an
unsupported normalization, which is correct fail-closed behaviour for one curated
repository and the dominant outcome for arbitrary public ones: this repository's own
lock has one non-PyPI package out of 55, so v1 would reject the repository it ships
from. Any project with a git dependency, a local path or a private index hits the
same wall, and an endpoint that answers "rejected" to most real inputs demonstrates
refusal rather than analysis.

So an unidentified record is now carried rather than fatal — as a first-class part
of the scope, inside the scope's own identity, never as a dropped row:

```text
partial scope != complete scope
scoped verdict != repository verdict
```

Two invariants keep that from becoming a lie. A scope must carry at least one
identified dependency, so an entirely unidentifiable lock still fails closed rather
than correlating nothing and reporting nothing. And every source record is
accounted for exactly once across the two halves, so coverage cannot be overstated
by an index appearing in both.
"""

import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import Protocol

from opslens.correlation.adapters.ghsa import GhsaPyPIVulnerabilityEvidence
from opslens.correlation.domain.errors import CorrelationContractError
from opslens.correlation.domain.pypi import (
    canonicalize_pypi_ecosystem,
    canonicalize_pypi_package,
    canonicalize_pypi_purl,
    canonicalize_pypi_version,
)
from opslens.ingestion.epss.domain.history import HistoricalEpssSnapshot
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.public_analysis.domain import (
    PublicAnalysisValidationError,
    PublicRepositoryEvidenceExecution,
)
from opslens.shared.evidence import canonical_json
from opslens.transformation.nvd.domain.models import NvdCveCoreRecord

# v2 carries unidentified records inside the scope identity. A v1 digest must never
# silently match a v2 scope derived from the same lock, so the version moves.
PUBLIC_THREAT_EVIDENCE_SCOPE_CONTRACT_VERSION = "public-threat-evidence-scope:v2"
PUBLIC_THREAT_EVIDENCE_REQUEST_CONTRACT_VERSION = "public-threat-evidence-request:v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.ASCII)


type SupportedEpssSnapshot = EpssSnapshot | HistoricalEpssSnapshot


class PublicThreatSnapshotPolicy(StrEnum):
    """Deterministic request-time selection vocabulary for complete source authority."""

    LATEST_COMPLETE = "latest_complete"


@dataclass(frozen=True, slots=True)
class PublicThreatDependencyScope:
    """One canonical package-version query scope with source-record provenance."""

    package_name: str
    version: str
    purl: str
    source_record_indexes: tuple[int, ...]

    def __post_init__(self) -> None:
        """Require exact Phase 3 PyPI identity and stable source-record accounting."""
        try:
            package = canonicalize_pypi_package(self.package_name)
            version = canonicalize_pypi_version(self.version)
            purl = canonicalize_pypi_purl(
                self.purl,
                expected_package=package,
                expected_version=version,
            )
        except CorrelationContractError as exc:
            raise PublicAnalysisValidationError(
                "public threat dependency scope must use canonical Phase 3 PyPI identity"
            ) from exc

        if package.canonical != self.package_name:
            raise PublicAnalysisValidationError(
                "public threat dependency package_name must already be canonical"
            )
        if version.canonical != self.version:
            raise PublicAnalysisValidationError(
                "public threat dependency version must already be canonical"
            )
        if purl.canonical != self.purl:
            raise PublicAnalysisValidationError(
                "public threat dependency purl must already be canonical"
            )
        if type(self.source_record_indexes) is not tuple or not self.source_record_indexes:
            raise PublicAnalysisValidationError(
                "public threat dependency must preserve at least one source record index"
            )
        if any(type(index) is not int or index < 0 for index in self.source_record_indexes):
            raise PublicAnalysisValidationError(
                "public threat dependency source indexes must be non-negative integers"
            )
        if self.source_record_indexes != tuple(sorted(set(self.source_record_indexes))):
            raise PublicAnalysisValidationError(
                "public threat dependency source indexes must be sorted and unique"
            )


@dataclass(frozen=True, slots=True)
class PublicThreatUnidentifiedDependency:
    """One lock record the Phase 3 identity authority could not turn into PyPI identity.

    Carried inside the scope so a verdict can never be read without its coverage. The
    original strings are preserved exactly as the lock spelled them; no canonical
    identity is invented for a record that has none.

    Attributes:
        name_original: Package name exactly as the lock recorded it.
        version_original: Version exactly as the lock recorded it.
        reason_code: Stable reason the identity authority rejected the record.
        source_record_indexes: Every `uv.lock` record index this entry accounts for.
    """

    name_original: str
    version_original: str
    reason_code: str
    source_record_indexes: tuple[int, ...]

    def __post_init__(self) -> None:
        """Require clean originals, a stable reason, and exact source accounting.

        Raises:
            PublicAnalysisValidationError: If any field is blank, padded, or the
                source record indexes are not sorted, unique and non-negative.
        """
        for label, value in (
            ("name_original", self.name_original),
            ("version_original", self.version_original),
            ("reason_code", self.reason_code),
        ):
            if not value or value != value.strip():
                raise PublicAnalysisValidationError(
                    f"unidentified dependency {label} must be a clean non-empty string"
                )
        if type(self.source_record_indexes) is not tuple or not self.source_record_indexes:
            raise PublicAnalysisValidationError(
                "unidentified dependency must preserve at least one source record index"
            )
        if any(type(index) is not int or index < 0 for index in self.source_record_indexes):
            raise PublicAnalysisValidationError(
                "unidentified dependency source indexes must be non-negative integers"
            )
        if self.source_record_indexes != tuple(sorted(set(self.source_record_indexes))):
            raise PublicAnalysisValidationError(
                "unidentified dependency source indexes must be sorted and unique"
            )


@dataclass(frozen=True, slots=True)
class PublicThreatEvidenceScope:
    """Content-bound structured-threat scope derived from admitted repository evidence."""

    source_execution_id: str
    source_evidence_sha256: str
    dependencies: tuple[PublicThreatDependencyScope, ...]
    unidentified: tuple[PublicThreatUnidentifiedDependency, ...] = ()

    def __post_init__(self) -> None:
        """Reject malformed identity or non-canonical dependency ordering."""
        if (
            not self.source_execution_id
            or self.source_execution_id != self.source_execution_id.strip()
        ):
            raise PublicAnalysisValidationError(
                "public threat scope requires one normalized source execution id"
            )
        if _SHA256_RE.fullmatch(self.source_evidence_sha256) is None:
            raise PublicAnalysisValidationError(
                "public threat scope requires one lowercase source evidence SHA-256"
            )
        if type(self.dependencies) is not tuple or any(
            type(item) is not PublicThreatDependencyScope for item in self.dependencies
        ):
            raise PublicAnalysisValidationError(
                "public threat scope dependencies must be a typed tuple"
            )
        ordered = tuple(
            sorted(
                self.dependencies,
                key=lambda item: (item.package_name, item.version, item.purl),
            )
        )
        if self.dependencies != ordered:
            raise PublicAnalysisValidationError(
                "public threat scope dependencies must use canonical deterministic ordering"
            )
        if len({item.purl for item in self.dependencies}) != len(self.dependencies):
            raise PublicAnalysisValidationError(
                "public threat scope cannot contain duplicate canonical purls"
            )
        self._validate_partial_coverage()

    def _validate_partial_coverage(self) -> None:
        """Keep a partially identified scope from becoming an overstated one.

        Raises:
            PublicAnalysisValidationError: If the unidentified half is malformed or
                unordered, if no dependency was identified at all, or if one source
                record is claimed by both halves.
        """
        if type(self.unidentified) is not tuple or any(
            type(item) is not PublicThreatUnidentifiedDependency for item in self.unidentified
        ):
            raise PublicAnalysisValidationError(
                "public threat scope unidentified records must be a typed tuple"
            )
        ordered = tuple(
            sorted(
                self.unidentified,
                key=lambda item: (item.name_original, item.version_original, item.reason_code),
            )
        )
        if self.unidentified != ordered:
            raise PublicAnalysisValidationError(
                "public threat scope unidentified records must use canonical ordering"
            )
        keys = {
            (item.name_original, item.version_original, item.reason_code)
            for item in self.unidentified
        }
        if len(keys) != len(self.unidentified):
            raise PublicAnalysisValidationError(
                "public threat scope cannot contain duplicate unidentified records"
            )

        # A scope that identified nothing must not correlate nothing and report
        # nothing. Partial coverage is admissible; zero coverage is not.
        if not self.dependencies:
            raise PublicAnalysisValidationError(
                "public threat scope requires at least one identified dependency; "
                "a lock whose records cannot be identified at all fails closed"
            )

        identified_indexes = {
            index for item in self.dependencies for index in item.source_record_indexes
        }
        unidentified_indexes = {
            index for item in self.unidentified for index in item.source_record_indexes
        }
        overlap = identified_indexes & unidentified_indexes
        if overlap:
            raise PublicAnalysisValidationError(
                "a source record cannot be both identified and unidentified: "
                f"{sorted(overlap)}"
            )

    @property
    def identified_dependency_count(self) -> int:
        """Return how many canonical package-version scopes were identified."""
        return len(self.dependencies)

    @property
    def unidentified_record_count(self) -> int:
        """Return how many source records carry no canonical PyPI identity."""
        return sum(len(item.source_record_indexes) for item in self.unidentified)

    @property
    def coverage_complete(self) -> bool:
        """Report whether every PyPI-source record in the lock was identified."""
        return not self.unidentified

    @property
    def query_package_names(self) -> tuple[str, ...]:
        """Return unique package names for bounded source lookup.

        The exact dependency scope remains separately preserved.
        """
        return tuple(sorted({item.package_name for item in self.dependencies}))

    @property
    def canonical_json(self) -> bytes:
        """Serialize the bounded identity, including what could not be identified.

        Coverage lives inside the scope identity rather than beside it. Two locks that
        differ only in which records were identifiable are different scopes, and a
        retained v1 digest cannot match a v2 scope derived from the same lock.
        """
        return canonical_json({
                "contract_version": PUBLIC_THREAT_EVIDENCE_SCOPE_CONTRACT_VERSION,
                "source_execution_id": self.source_execution_id,
                "source_evidence_sha256": self.source_evidence_sha256,
                "coverage": {
                    "complete": self.coverage_complete,
                    "identified_dependency_count": self.identified_dependency_count,
                    "unidentified_record_count": self.unidentified_record_count,
                },
                "dependencies": [
                    {
                        "package_name": item.package_name,
                        "version": item.version,
                        "purl": item.purl,
                        "source_record_indexes": list(item.source_record_indexes),
                    }
                    for item in self.dependencies
                ],
                "unidentified": [
                    {
                        "name_original": item.name_original,
                        "version_original": item.version_original,
                        "reason_code": item.reason_code,
                        "source_record_indexes": list(item.source_record_indexes),
                    }
                    for item in self.unidentified
                ],
            })

    @property
    def scope_sha256(self) -> str:
        """Return the content address of the exact dependency query scope."""
        return sha256(self.canonical_json).hexdigest()

    @property
    def scope_id(self) -> str:
        """Return a stable identifier for the exact request-time threat scope."""
        return (
            f"{PUBLIC_THREAT_EVIDENCE_SCOPE_CONTRACT_VERSION}@sha256:"
            f"{self.scope_sha256}"
        )


@dataclass(frozen=True, slots=True)
class PublicThreatEvidenceRequest:
    """Bounded authority request; the provider must return exact selected source evidence."""

    scope: PublicThreatEvidenceScope
    snapshot_policy: PublicThreatSnapshotPolicy = PublicThreatSnapshotPolicy.LATEST_COMPLETE

    def __post_init__(self) -> None:
        """Require explicit typed scope and the frozen selection-policy vocabulary."""
        if type(self.scope) is not PublicThreatEvidenceScope:
            raise PublicAnalysisValidationError(
                "public threat evidence request requires a typed dependency scope"
            )
        if type(self.snapshot_policy) is not PublicThreatSnapshotPolicy:
            raise PublicAnalysisValidationError(
                "public threat evidence request requires a supported snapshot policy"
            )

    @property
    def canonical_json(self) -> bytes:
        """Bind the authority request to exact dependency scope and selection semantics."""
        return canonical_json({
                "contract_version": PUBLIC_THREAT_EVIDENCE_REQUEST_CONTRACT_VERSION,
                "scope_id": self.scope.scope_id,
                "snapshot_policy": self.snapshot_policy.value,
            })

    @property
    def request_id(self) -> str:
        """Return one content-addressed request identity."""
        return (
            f"{PUBLIC_THREAT_EVIDENCE_REQUEST_CONTRACT_VERSION}@sha256:"
            f"{sha256(self.canonical_json).hexdigest()}"
        )


@dataclass(frozen=True, slots=True)
class PublicThreatEvidenceProvenance:
    """Exact source-local identities selected by one authority execution."""

    ghsa_observed_advisory_version_ids: tuple[str, ...]
    nvd_observed_cve_version_ids: tuple[str, ...]
    kev_snapshot_date: str
    kev_sha256: str
    epss_snapshot_date: str
    epss_sha256: str

    def __post_init__(self) -> None:
        """Require canonical ordering and exact immutable snapshot identities."""
        for label, values in (
            ("GHSA", self.ghsa_observed_advisory_version_ids),
            ("NVD", self.nvd_observed_cve_version_ids),
        ):
            if type(values) is not tuple or any(
                not value or value != value.strip() for value in values
            ):
                raise PublicAnalysisValidationError(
                    f"{label} provenance identities must be normalized strings"
                )
            if values != tuple(sorted(set(values))):
                raise PublicAnalysisValidationError(
                    f"{label} provenance identities must be sorted and unique"
                )
        for label, value in (
            ("KEV", self.kev_sha256),
            ("EPSS", self.epss_sha256),
        ):
            if _SHA256_RE.fullmatch(value) is None:
                raise PublicAnalysisValidationError(
                    f"{label} provenance requires a lowercase SHA-256"
                )
        for label, value in (
            ("KEV", self.kev_snapshot_date),
            ("EPSS", self.epss_snapshot_date),
        ):
            if not value or value != value.strip():
                raise PublicAnalysisValidationError(
                    f"{label} provenance requires an exact snapshot date"
                )


@dataclass(frozen=True, slots=True)
class PublicRepositoryThreatEvidence:
    """Typed structured source authority admitted for exactly one public threat request."""

    request: PublicThreatEvidenceRequest
    ghsa_vulnerabilities: tuple[GhsaPyPIVulnerabilityEvidence, ...]
    nvd_records: tuple[NvdCveCoreRecord, ...]
    kev_snapshot: KevCatalogSnapshot
    epss_snapshot: SupportedEpssSnapshot

    def __post_init__(self) -> None:
        """Reject evidence outside scope, unrelated NVD material, or duplicate identities."""
        if type(self.request) is not PublicThreatEvidenceRequest:
            raise PublicAnalysisValidationError(
                "public threat evidence must bind to one typed authority request"
            )
        if type(self.ghsa_vulnerabilities) is not tuple or any(
            type(item) is not GhsaPyPIVulnerabilityEvidence
            for item in self.ghsa_vulnerabilities
        ):
            raise PublicAnalysisValidationError(
                "public GHSA threat evidence must be a typed tuple"
            )
        if type(self.nvd_records) is not tuple or any(
            type(item) is not NvdCveCoreRecord for item in self.nvd_records
        ):
            raise PublicAnalysisValidationError(
                "public NVD threat evidence must be a typed tuple"
            )
        if type(self.kev_snapshot) is not KevCatalogSnapshot:
            raise PublicAnalysisValidationError(
                "public KEV threat evidence must be one complete typed snapshot"
            )
        if type(self.epss_snapshot) not in {EpssSnapshot, HistoricalEpssSnapshot}:
            raise PublicAnalysisValidationError(
                "public EPSS threat evidence must be one complete supported snapshot"
            )

        allowed_packages = set(self.request.scope.query_package_names)
        ghsa_keys: set[tuple[str, int]] = set()
        allowed_cves: set[str] = set()
        for item in self.ghsa_vulnerabilities:
            try:
                canonicalize_pypi_ecosystem(item.ecosystem_original)
                package = canonicalize_pypi_package(item.package_name_original)
            except CorrelationContractError as exc:
                raise PublicAnalysisValidationError(
                    "public GHSA evidence contains unsupported package identity"
                ) from exc
            if package.canonical not in allowed_packages:
                raise PublicAnalysisValidationError(
                    "public GHSA evidence is outside the admitted dependency scope"
                )
            if _SHA256_RE.fullmatch(item.source_advisory_sha256) is None or (
                _SHA256_RE.fullmatch(item.source_entry_sha256) is None
            ):
                raise PublicAnalysisValidationError(
                    "public GHSA evidence requires exact lowercase source hashes"
                )
            if item.observed_advisory_version_id != (
                f"{item.ghsa_id}@sha256:{item.source_advisory_sha256}"
            ):
                raise PublicAnalysisValidationError(
                    "public GHSA observed version identity contradicts source hash"
                )
            key = (item.observed_advisory_version_id, item.source_index)
            if key in ghsa_keys:
                raise PublicAnalysisValidationError(
                    "public GHSA evidence cannot contain duplicate source occurrences"
                )
            ghsa_keys.add(key)
            if item.github_cve_id is not None:
                allowed_cves.add(item.github_cve_id)

        observed_nvd_ids: set[str] = set()
        observed_nvd_cves: set[str] = set()
        for item in self.nvd_records:
            observed = item.observed_version
            if observed.observed_cve_version_id in observed_nvd_ids:
                raise PublicAnalysisValidationError(
                    "public NVD evidence cannot contain duplicate observed versions"
                )
            if observed.cve_id in observed_nvd_cves:
                raise PublicAnalysisValidationError(
                    "public NVD evidence must select at most one observed version per CVE"
                )
            if observed.cve_id not in allowed_cves:
                raise PublicAnalysisValidationError(
                    "public NVD evidence is unrelated to admitted scoped GHSA evidence"
                )
            observed_nvd_ids.add(observed.observed_cve_version_id)
            observed_nvd_cves.add(observed.cve_id)

    @property
    def provenance(self) -> PublicThreatEvidenceProvenance:
        """Project exact selected source-local identities without provider-specific invention."""
        epss_date = self.epss_snapshot.snapshot_date
        if not isinstance(epss_date, str):
            epss_date = epss_date.isoformat()
        return PublicThreatEvidenceProvenance(
            ghsa_observed_advisory_version_ids=tuple(
                sorted(
                    {
                        item.observed_advisory_version_id
                        for item in self.ghsa_vulnerabilities
                    }
                )
            ),
            nvd_observed_cve_version_ids=tuple(
                sorted(
                    {item.observed_version.observed_cve_version_id for item in self.nvd_records}
                )
            ),
            kev_snapshot_date=self.kev_snapshot.snapshot_date,
            kev_sha256=self.kev_snapshot.sha256,
            epss_snapshot_date=epss_date,
            epss_sha256=self.epss_snapshot.sha256,
        )


class PublicThreatEvidenceAuthority(Protocol):
    """Port for exact structured threat authority; physical access is a later decision."""

    def load(self, request: PublicThreatEvidenceRequest) -> PublicRepositoryThreatEvidence:
        """Return evidence bound to the exact request or fail without inventing absence."""
        ...


def build_public_threat_evidence_scope(
    execution: PublicRepositoryEvidenceExecution,
) -> PublicThreatEvidenceScope:
    """Derive the admissible package scope, carrying whatever could not be identified.

    Args:
        execution: Admitted deterministic repository evidence.

    Returns:
        One scope whose identity includes its own coverage.

    Raises:
        PublicAnalysisValidationError: If the execution is not admitted evidence, if a
            canonical purl maps to contradictory identity, or if no record in the lock
            could be identified at all.
    """
    if type(execution) is not PublicRepositoryEvidenceExecution:
        raise PublicAnalysisValidationError(
            "public threat scope requires admitted public repository evidence"
        )
    inventory = execution.normalization_inventory

    grouped: dict[str, tuple[str, str, list[int]]] = {}
    for item in inventory.normalized_dependencies:
        existing = grouped.get(item.purl)
        if existing is None:
            grouped[item.purl] = (
                item.package.canonical,
                item.version.canonical,
                [item.record_index],
            )
            continue
        package_name, version, indexes = existing
        if package_name != item.package.canonical or version != item.version.canonical:
            raise PublicAnalysisValidationError(
                "canonical purl maps to contradictory repository dependency identity"
            )
        indexes.append(item.record_index)

    dependencies = tuple(
        sorted(
            (
                PublicThreatDependencyScope(
                    package_name=package_name,
                    version=version,
                    purl=purl,
                    source_record_indexes=tuple(sorted(indexes)),
                )
                for purl, (package_name, version, indexes) in grouped.items()
            ),
            key=lambda item: (item.package_name, item.version, item.purl),
        )
    )
    # The inventory already guarantees exactly-once accounting of every PyPI-source
    # record, so grouping the unsupported half here cannot invent or lose coverage.
    unidentified_groups: dict[tuple[str, str, str], list[int]] = {}
    for item in inventory.unsupported_normalization:
        key = (
            item.source_record.name_original,
            item.source_record.version_original,
            item.reason_code,
        )
        unidentified_groups.setdefault(key, []).append(item.record_index)

    unidentified = tuple(
        sorted(
            (
                PublicThreatUnidentifiedDependency(
                    name_original=name_original,
                    version_original=version_original,
                    reason_code=reason_code,
                    source_record_indexes=tuple(sorted(indexes)),
                )
                for (name_original, version_original, reason_code), indexes
                in unidentified_groups.items()
            ),
            key=lambda item: (item.name_original, item.version_original, item.reason_code),
        )
    )

    return PublicThreatEvidenceScope(
        source_execution_id=execution.execution_id,
        source_evidence_sha256=execution.evidence_sha256,
        dependencies=dependencies,
        unidentified=unidentified,
    )


def load_public_repository_threat_evidence(
    execution: PublicRepositoryEvidenceExecution,
    authority: PublicThreatEvidenceAuthority,
    *,
    snapshot_policy: PublicThreatSnapshotPolicy = PublicThreatSnapshotPolicy.LATEST_COMPLETE,
) -> PublicRepositoryThreatEvidence:
    """Load one exact authority result and enforce request binding before correlation."""
    scope = build_public_threat_evidence_scope(execution)
    request = PublicThreatEvidenceRequest(
        scope=scope,
        snapshot_policy=snapshot_policy,
    )
    evidence = authority.load(request)
    if type(evidence) is not PublicRepositoryThreatEvidence:
        raise PublicAnalysisValidationError(
            "public threat authority must return typed PublicRepositoryThreatEvidence"
        )
    if evidence.request != request:
        raise PublicAnalysisValidationError(
            "public threat authority returned evidence for a different request"
        )
    return evidence


__all__ = [
    "PUBLIC_THREAT_EVIDENCE_REQUEST_CONTRACT_VERSION",
    "PUBLIC_THREAT_EVIDENCE_SCOPE_CONTRACT_VERSION",
    "PublicRepositoryThreatEvidence",
    "PublicThreatDependencyScope",
    "PublicThreatEvidenceAuthority",
    "PublicThreatEvidenceProvenance",
    "PublicThreatEvidenceRequest",
    "PublicThreatEvidenceScope",
    "PublicThreatSnapshotPolicy",
    "PublicThreatUnidentifiedDependency",
    "build_public_threat_evidence_scope",
    "load_public_repository_threat_evidence",
]
