"""Bind representative threat-authority loaders to exact analytical coordinates."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Protocol, cast

from opslens.correlation.adapters.ghsa import GhsaPyPIVulnerabilityEvidence
from opslens.ingestion.epss.domain.history import HistoricalEpssSnapshot
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.transformation.nvd.domain.models import NvdCveCoreRecord


class RepresentativeThreatEvidenceCoordinateError(ValueError):
    """Reject malformed, ambiguous, or contradictory analytical coordinates."""


@dataclass(frozen=True, slots=True)
class RepresentativeGhsaOccurrenceCoordinate:
    """Identify one exact GHSA package occurrence without evaluating its range."""

    observed_advisory_version_id: str
    source_index: int


@dataclass(frozen=True, slots=True)
class RepresentativeThreatEvidenceCoordinates:
    """Collect exact source coordinates admitted from one cross-source bundle."""

    cve_id: str
    ghsa_occurrences: tuple[RepresentativeGhsaOccurrenceCoordinate, ...]
    nvd_observed_version_ids: tuple[str, ...]
    kev_snapshot_date: str
    epss_snapshot_date: str


class RepresentativeGhsaAuthoritySource(Protocol):
    """Provide one already-validated typed GHSA occurrence by exact identity."""

    def get_occurrence(
        self,
        *,
        cve_id: str,
        observed_advisory_version_id: str,
        source_index: int,
    ) -> GhsaPyPIVulnerabilityEvidence:
        """Return one exact GHSA occurrence without evaluating applicability."""
        ...


class RepresentativeNvdAuthoritySource(Protocol):
    """Provide one already-validated typed NVD record by exact identity."""

    def get_record(
        self,
        *,
        cve_id: str,
        observed_cve_version_id: str,
    ) -> NvdCveCoreRecord:
        """Return one exact NVD record."""
        ...


class RepresentativeKevAuthoritySource(Protocol):
    """Provide one complete already-validated KEV snapshot by exact date."""

    def get_snapshot(self, *, snapshot_date: str) -> KevCatalogSnapshot:
        """Return the complete immutable KEV snapshot for the requested date."""
        ...


class RepresentativeEpssAuthoritySource(Protocol):
    """Provide one complete already-validated EPSS snapshot by exact date."""

    def get_snapshot(
        self,
        *,
        snapshot_date: str,
    ) -> EpssSnapshot | HistoricalEpssSnapshot:
        """Return the complete immutable EPSS snapshot for the requested date."""
        ...


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RepresentativeThreatEvidenceCoordinateError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _sequence(value: object, *, field: str) -> Sequence[object]:
    if not isinstance(value, list):
        raise RepresentativeThreatEvidenceCoordinateError(f"{field} must be an array")
    return cast(Sequence[object], value)


def _string(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise RepresentativeThreatEvidenceCoordinateError(
            f"{field} must be a non-empty trimmed string"
        )
    return value


def _integer(value: object, *, field: str) -> int:
    if type(value) is not int:
        raise RepresentativeThreatEvidenceCoordinateError(f"{field} must be an integer")
    return value


def _boolean(value: object, *, field: str) -> bool:
    if type(value) is not bool:
        raise RepresentativeThreatEvidenceCoordinateError(f"{field} must be a boolean")
    return value


def _snapshot_date(value: object, *, field: str) -> str:
    text = _string(value, field=field)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise RepresentativeThreatEvidenceCoordinateError(
            f"{field} must use YYYY-MM-DD"
        ) from exc
    if parsed.isoformat() != text:
        raise RepresentativeThreatEvidenceCoordinateError(
            f"{field} must use canonical YYYY-MM-DD"
        )
    return text


def parse_representative_threat_evidence_coordinates(
    bundle: Mapping[str, object],
) -> RepresentativeThreatEvidenceCoordinates:
    """Extract source lookup coordinates without reconstructing source authority."""
    if _integer(bundle.get("schema_version"), field="schema_version") != 1:
        raise RepresentativeThreatEvidenceCoordinateError("schema_version must equal 1")
    if (
        _string(bundle.get("bundle_type"), field="bundle_type")
        != "CrossSourceCveEvidenceV1"
    ):
        raise RepresentativeThreatEvidenceCoordinateError(
            "bundle_type must equal CrossSourceCveEvidenceV1"
        )
    if _boolean(bundle.get("read_only"), field="read_only") is not True:
        raise RepresentativeThreatEvidenceCoordinateError("read_only must equal true")

    cve_id = _string(bundle.get("cve_id"), field="cve_id")
    ghsa = _mapping(bundle.get("ghsa"), field="ghsa")
    ghsa_versions = _sequence(
        ghsa.get("advisory_versions"), field="ghsa.advisory_versions"
    )
    ghsa_occurrences: list[RepresentativeGhsaOccurrenceCoordinate] = []
    ghsa_seen: set[tuple[str, int]] = set()

    for version_index, raw_version in enumerate(ghsa_versions):
        version = _mapping(raw_version, field=f"ghsa.advisory_versions[{version_index}]")
        if _string(version.get("cve_id"), field="ghsa.cve_id") != cve_id:
            raise RepresentativeThreatEvidenceCoordinateError("GHSA CVE identity mismatch")
        observed_id = _string(
            version.get("observed_advisory_version_id"),
            field="ghsa.observed_advisory_version_id",
        )
        packages = _sequence(version.get("package_evidence"), field="ghsa.package_evidence")
        for package_index, raw_package in enumerate(packages):
            package = _mapping(
                raw_package,
                field=f"ghsa.package_evidence[{package_index}]",
            )
            source_index = _integer(package.get("source_index"), field="ghsa.source_index")
            if source_index < 0:
                raise RepresentativeThreatEvidenceCoordinateError(
                    "ghsa.source_index must be non-negative"
                )
            key = (observed_id, source_index)
            if key in ghsa_seen:
                raise RepresentativeThreatEvidenceCoordinateError(
                    "duplicate GHSA advisory/package coordinate"
                )
            ghsa_seen.add(key)
            ghsa_occurrences.append(
                RepresentativeGhsaOccurrenceCoordinate(
                    observed_advisory_version_id=observed_id,
                    source_index=source_index,
                )
            )

    if not ghsa_occurrences:
        raise RepresentativeThreatEvidenceCoordinateError(
            "representative bundle must contain GHSA package coordinates"
        )

    nvd = _mapping(bundle.get("nvd"), field="nvd")
    nvd_observations = _sequence(nvd.get("observations"), field="nvd.observations")
    nvd_ids: list[str] = []
    nvd_seen: set[str] = set()
    for index, raw_observation in enumerate(nvd_observations):
        observation = _mapping(raw_observation, field=f"nvd.observations[{index}]")
        if _string(observation.get("cve_id"), field="nvd.cve_id") != cve_id:
            raise RepresentativeThreatEvidenceCoordinateError("NVD CVE identity mismatch")
        observed_id = _string(
            observation.get("observed_cve_version_id"),
            field="nvd.observed_cve_version_id",
        )
        if observed_id in nvd_seen:
            raise RepresentativeThreatEvidenceCoordinateError(
                "duplicate NVD observed-version coordinate"
            )
        nvd_seen.add(observed_id)
        nvd_ids.append(observed_id)

    kev = _mapping(bundle.get("kev"), field="kev")
    epss = _mapping(bundle.get("epss"), field="epss")

    return RepresentativeThreatEvidenceCoordinates(
        cve_id=cve_id,
        ghsa_occurrences=tuple(ghsa_occurrences),
        nvd_observed_version_ids=tuple(nvd_ids),
        kev_snapshot_date=_snapshot_date(
            kev.get("snapshot_date"), field="kev.snapshot_date"
        ),
        epss_snapshot_date=_snapshot_date(
            epss.get("snapshot_date"), field="epss.snapshot_date"
        ),
    )


@dataclass(frozen=True, slots=True)
class BundleBoundRepresentativeGhsaAuthorityLoader:
    """Load GHSA authority only through exact coordinates declared by the bundle."""

    source: RepresentativeGhsaAuthoritySource

    def load(
        self,
        bundle: Mapping[str, object],
    ) -> tuple[GhsaPyPIVulnerabilityEvidence, ...]:
        """Read every exact GHSA occurrence once and reject provider mismatch."""
        coordinates = parse_representative_threat_evidence_coordinates(bundle)
        result: list[GhsaPyPIVulnerabilityEvidence] = []
        for occurrence in coordinates.ghsa_occurrences:
            item = self.source.get_occurrence(
                cve_id=coordinates.cve_id,
                observed_advisory_version_id=occurrence.observed_advisory_version_id,
                source_index=occurrence.source_index,
            )
            if type(item) is not GhsaPyPIVulnerabilityEvidence:
                raise TypeError("GHSA authority source returned an invalid type")
            if (
                item.github_cve_id != coordinates.cve_id
                or item.observed_advisory_version_id
                != occurrence.observed_advisory_version_id
                or item.source_index != occurrence.source_index
            ):
                raise RepresentativeThreatEvidenceCoordinateError(
                    "GHSA authority source returned contradictory coordinates"
                )
            result.append(item)
        return tuple(result)


@dataclass(frozen=True, slots=True)
class BundleBoundRepresentativeNvdAuthorityLoader:
    """Load NVD authority only through exact observed-version coordinates."""

    source: RepresentativeNvdAuthoritySource

    def load(self, bundle: Mapping[str, object]) -> tuple[NvdCveCoreRecord, ...]:
        """Read every exact NVD record once and reject provider mismatch."""
        coordinates = parse_representative_threat_evidence_coordinates(bundle)
        result: list[NvdCveCoreRecord] = []
        for observed_id in coordinates.nvd_observed_version_ids:
            record = self.source.get_record(
                cve_id=coordinates.cve_id,
                observed_cve_version_id=observed_id,
            )
            if type(record) is not NvdCveCoreRecord:
                raise TypeError("NVD authority source returned an invalid type")
            if (
                record.observed_version.cve_id != coordinates.cve_id
                or record.observed_version.observed_cve_version_id != observed_id
            ):
                raise RepresentativeThreatEvidenceCoordinateError(
                    "NVD authority source returned contradictory coordinates"
                )
            result.append(record)
        return tuple(result)


@dataclass(frozen=True, slots=True)
class BundleBoundRepresentativeKevAuthorityLoader:
    """Load one complete KEV snapshot selected by the analytical bundle."""

    source: RepresentativeKevAuthoritySource

    def load(self, bundle: Mapping[str, object]) -> KevCatalogSnapshot:
        """Read the exact KEV snapshot once without synthesizing CVE absence."""
        coordinates = parse_representative_threat_evidence_coordinates(bundle)
        snapshot = self.source.get_snapshot(snapshot_date=coordinates.kev_snapshot_date)
        if type(snapshot) is not KevCatalogSnapshot:
            raise TypeError("KEV authority source returned an invalid type")
        if snapshot.snapshot_date != coordinates.kev_snapshot_date:
            raise RepresentativeThreatEvidenceCoordinateError(
                "KEV authority source returned a different snapshot date"
            )
        return snapshot


@dataclass(frozen=True, slots=True)
class BundleBoundRepresentativeEpssAuthorityLoader:
    """Load one complete EPSS snapshot selected by the analytical bundle."""

    source: RepresentativeEpssAuthoritySource

    def load(
        self,
        bundle: Mapping[str, object],
    ) -> EpssSnapshot | HistoricalEpssSnapshot:
        """Read the exact EPSS snapshot once and reject provider date mismatch."""
        coordinates = parse_representative_threat_evidence_coordinates(bundle)
        snapshot = self.source.get_snapshot(snapshot_date=coordinates.epss_snapshot_date)
        if type(snapshot) is EpssSnapshot:
            actual_date = snapshot.snapshot_date
        elif type(snapshot) is HistoricalEpssSnapshot:
            actual_date = snapshot.snapshot_date.isoformat()
        else:
            raise TypeError("EPSS authority source returned an invalid type")
        if actual_date != coordinates.epss_snapshot_date:
            raise RepresentativeThreatEvidenceCoordinateError(
                "EPSS authority source returned a different snapshot date"
            )
        return snapshot
