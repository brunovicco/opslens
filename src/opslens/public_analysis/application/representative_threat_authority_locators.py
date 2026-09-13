"""Admit immutable physical source locators for representative threat authority."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from opslens.public_analysis.application.representative_threat_evidence_coordinate_loaders import (
    RepresentativeThreatEvidenceCoordinates,
)


class RepresentativeThreatAuthorityLocatorError(ValueError):
    """Reject malformed, incomplete, or contradictory physical source locators."""


@dataclass(frozen=True, slots=True)
class S3ImmutableObjectLocator:
    """Identify one immutable S3 object by exact key and VersionId."""

    object_key: str
    version_id: str

    def __post_init__(self) -> None:
        """Reject empty or whitespace-mutated S3 physical coordinates."""
        if not self.object_key or self.object_key != self.object_key.strip():
            raise RepresentativeThreatAuthorityLocatorError(
                "object_key must be a non-empty trimmed string"
            )
        if not self.version_id or self.version_id != self.version_id.strip():
            raise RepresentativeThreatAuthorityLocatorError(
                "version_id must be a non-empty trimmed string"
            )


@dataclass(frozen=True, slots=True)
class RepresentativeGhsaAuthorityLocator:
    """Bind one GHSA logical package occurrence to an immutable S3 object."""

    observed_advisory_version_id: str
    source_index: int
    s3: S3ImmutableObjectLocator


@dataclass(frozen=True, slots=True)
class RepresentativeNvdAuthorityLocator:
    """Bind one NVD observed version to an immutable S3 object."""

    observed_cve_version_id: str
    s3: S3ImmutableObjectLocator


@dataclass(frozen=True, slots=True)
class RepresentativeSnapshotAuthorityLocator:
    """Bind one dated source snapshot to an immutable S3 object."""

    snapshot_date: str
    s3: S3ImmutableObjectLocator


@dataclass(frozen=True, slots=True)
class RepresentativeThreatAuthorityLocatorManifestV1:
    """Represent one admitted bridge from logical evidence to physical source objects."""

    cve_id: str
    ghsa: tuple[RepresentativeGhsaAuthorityLocator, ...]
    nvd: tuple[RepresentativeNvdAuthorityLocator, ...]
    kev: RepresentativeSnapshotAuthorityLocator
    epss: RepresentativeSnapshotAuthorityLocator


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RepresentativeThreatAuthorityLocatorError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _sequence(value: object, *, field: str) -> Sequence[object]:
    if not isinstance(value, list):
        raise RepresentativeThreatAuthorityLocatorError(f"{field} must be an array")
    return cast(Sequence[object], value)


def _string(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise RepresentativeThreatAuthorityLocatorError(
            f"{field} must be a non-empty trimmed string"
        )
    return value


def _integer(value: object, *, field: str) -> int:
    if type(value) is not int:
        raise RepresentativeThreatAuthorityLocatorError(f"{field} must be an integer")
    return value


def _s3_locator(value: object, *, field: str) -> S3ImmutableObjectLocator:
    item = _mapping(value, field=field)
    return S3ImmutableObjectLocator(
        object_key=_string(item.get("object_key"), field=f"{field}.object_key"),
        version_id=_string(item.get("version_id"), field=f"{field}.version_id"),
    )


def admit_representative_threat_authority_locator_manifest(
    manifest: Mapping[str, object],
    *,
    coordinates: RepresentativeThreatEvidenceCoordinates,
) -> RepresentativeThreatAuthorityLocatorManifestV1:
    """Validate one locator manifest against already-admitted logical coordinates."""
    if _integer(manifest.get("schema_version"), field="schema_version") != 1:
        raise RepresentativeThreatAuthorityLocatorError("schema_version must equal 1")
    if (
        _string(manifest.get("manifest_type"), field="manifest_type")
        != "RepresentativeThreatAuthorityLocatorManifestV1"
    ):
        raise RepresentativeThreatAuthorityLocatorError(
            "manifest_type must equal RepresentativeThreatAuthorityLocatorManifestV1"
        )
    cve_id = _string(manifest.get("cve_id"), field="cve_id")
    if cve_id != coordinates.cve_id:
        raise RepresentativeThreatAuthorityLocatorError("locator CVE identity mismatch")

    ghsa_items = _sequence(manifest.get("ghsa"), field="ghsa")
    ghsa: list[RepresentativeGhsaAuthorityLocator] = []
    ghsa_seen: set[tuple[str, int]] = set()
    for index, raw in enumerate(ghsa_items):
        item = _mapping(raw, field=f"ghsa[{index}]")
        observed_id = _string(
            item.get("observed_advisory_version_id"),
            field=f"ghsa[{index}].observed_advisory_version_id",
        )
        source_index = _integer(
            item.get("source_index"), field=f"ghsa[{index}].source_index"
        )
        key = (observed_id, source_index)
        if key in ghsa_seen:
            raise RepresentativeThreatAuthorityLocatorError("duplicate GHSA locator")
        ghsa_seen.add(key)
        ghsa.append(
            RepresentativeGhsaAuthorityLocator(
                observed_advisory_version_id=observed_id,
                source_index=source_index,
                s3=_s3_locator(item.get("s3"), field=f"ghsa[{index}].s3"),
            )
        )

    expected_ghsa = {
        (item.observed_advisory_version_id, item.source_index)
        for item in coordinates.ghsa_occurrences
    }
    if ghsa_seen != expected_ghsa:
        raise RepresentativeThreatAuthorityLocatorError(
            "GHSA locator set must exactly match admitted logical coordinates"
        )

    nvd_items = _sequence(manifest.get("nvd"), field="nvd")
    nvd: list[RepresentativeNvdAuthorityLocator] = []
    nvd_seen: set[str] = set()
    for index, raw in enumerate(nvd_items):
        item = _mapping(raw, field=f"nvd[{index}]")
        observed_id = _string(
            item.get("observed_cve_version_id"),
            field=f"nvd[{index}].observed_cve_version_id",
        )
        if observed_id in nvd_seen:
            raise RepresentativeThreatAuthorityLocatorError("duplicate NVD locator")
        nvd_seen.add(observed_id)
        nvd.append(
            RepresentativeNvdAuthorityLocator(
                observed_cve_version_id=observed_id,
                s3=_s3_locator(item.get("s3"), field=f"nvd[{index}].s3"),
            )
        )

    if nvd_seen != set(coordinates.nvd_observed_version_ids):
        raise RepresentativeThreatAuthorityLocatorError(
            "NVD locator set must exactly match admitted logical coordinates"
        )

    kev_raw = _mapping(manifest.get("kev"), field="kev")
    kev_date = _string(kev_raw.get("snapshot_date"), field="kev.snapshot_date")
    if kev_date != coordinates.kev_snapshot_date:
        raise RepresentativeThreatAuthorityLocatorError("KEV locator snapshot mismatch")
    kev = RepresentativeSnapshotAuthorityLocator(
        snapshot_date=kev_date,
        s3=_s3_locator(kev_raw.get("s3"), field="kev.s3"),
    )

    epss_raw = _mapping(manifest.get("epss"), field="epss")
    epss_date = _string(epss_raw.get("snapshot_date"), field="epss.snapshot_date")
    if epss_date != coordinates.epss_snapshot_date:
        raise RepresentativeThreatAuthorityLocatorError("EPSS locator snapshot mismatch")
    epss = RepresentativeSnapshotAuthorityLocator(
        snapshot_date=epss_date,
        s3=_s3_locator(epss_raw.get("s3"), field="epss.s3"),
    )

    return RepresentativeThreatAuthorityLocatorManifestV1(
        cve_id=cve_id,
        ghsa=tuple(ghsa),
        nvd=tuple(nvd),
        kev=kev,
        epss=epss,
    )
