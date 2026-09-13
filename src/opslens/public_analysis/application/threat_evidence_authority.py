"""Provider-neutral request-time threat-evidence authority for public analysis.

Gate 19.8 freezes the deterministic contract between admitted repository dependency
evidence and the structured threat sources required by Phase 3/4 correlation. This
module intentionally performs no provider I/O and grants no runtime enablement.
"""

import json
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
from opslens.transformation.nvd.domain.models import NvdCveCoreRecord

PUBLIC_THREAT_EVIDENCE_SCOPE_CONTRACT_VERSION = "public-threat-evidence-scope:v1"
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
class PublicThreatEvidenceScope:
    """Content-bound structured-threat scope derived from admitted repository evidence."""

    source_execution_id: str
    source_evidence_sha256: str
    dependencies: tuple[PublicThreatDependencyScope, ...]

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

    @property
    def query_package_names(self) -> tuple[str, ...]:
        """Return unique package names for bounded source lookup.

        The exact dependency scope remains separately preserved.
        """
        return tuple(sorted({item.package_name for item in self.dependencies}))

    @property
    def canonical_json(self) -> bytes:
        """Serialize only the bounded identity required for structured threat retrieval."""
        value = {
            "contract_version": PUBLIC_THREAT_EVIDENCE_SCOPE_CONTRACT_VERSION,
            "source_execution_id": self.source_execution_id,
            "source_evidence_sha256": self.source_evidence_sha256,
            "dependencies": [
                {
                    "package_name": item.package_name,
                    "version": item.version,
                    "purl": item.purl,
                    "source_record_indexes": list(item.source_record_indexes),
                }
                for item in self.dependencies
            ],
        }
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

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
        return json.dumps(
            {
                "contract_version": PUBLIC_THREAT_EVIDENCE_REQUEST_CONTRACT_VERSION,
                "scope_id": self.scope.scope_id,
                "snapshot_policy": self.snapshot_policy.value,
            },
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

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
    """Derive the only admissible package scope from deterministic repository evidence."""
    if type(execution) is not PublicRepositoryEvidenceExecution:
        raise PublicAnalysisValidationError(
            "public threat scope requires admitted public repository evidence"
        )
    inventory = execution.normalization_inventory
    if inventory.unsupported_normalization:
        raise PublicAnalysisValidationError(
            "public threat scope refuses incomplete PyPI normalization evidence"
        )

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
    return PublicThreatEvidenceScope(
        source_execution_id=execution.execution_id,
        source_evidence_sha256=execution.evidence_sha256,
        dependencies=dependencies,
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
    "build_public_threat_evidence_scope",
    "load_public_repository_threat_evidence",
]
