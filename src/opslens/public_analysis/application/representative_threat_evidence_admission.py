"""Admit cross-source analytical evidence against exact typed threat-source authority."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from opslens.correlation.adapters.ghsa import GhsaPyPIVulnerabilityEvidence
from opslens.ingestion.epss.domain.history import HistoricalEpssSnapshot
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.public_analysis.application.representative_repository_analysis import (
    RepresentativeRepositoryThreatEvidence,
)
from opslens.repository_intelligence.domain.epss_enrichment import (
    RepositoryEpssSnapshotEvidence,
)
from opslens.repository_intelligence.domain.kev_enrichment import (
    RepositoryKevSnapshotEvidence,
)
from opslens.transformation.nvd.domain.models import NvdCveCoreRecord


class RepresentativeThreatEvidenceAdmissionError(ValueError):
    """Reject contradictory or incomplete representative threat evidence."""


@dataclass(frozen=True, slots=True)
class RepresentativeThreatEvidenceAuthority:
    """Exact typed source material that may satisfy one analytical proof bundle."""

    ghsa_vulnerabilities: tuple[GhsaPyPIVulnerabilityEvidence, ...]
    nvd_records: tuple[NvdCveCoreRecord, ...]
    kev_snapshot: KevCatalogSnapshot
    epss_snapshot: EpssSnapshot | HistoricalEpssSnapshot

    def __post_init__(self) -> None:
        """Reject untyped or incomplete authority inputs before analytical admission."""
        if type(self.ghsa_vulnerabilities) is not tuple or any(
            type(item) is not GhsaPyPIVulnerabilityEvidence
            for item in self.ghsa_vulnerabilities
        ):
            raise TypeError("ghsa_vulnerabilities must be a typed tuple")
        if type(self.nvd_records) is not tuple or any(
            type(item) is not NvdCveCoreRecord for item in self.nvd_records
        ):
            raise TypeError("nvd_records must be a typed tuple")
        if type(self.kev_snapshot) is not KevCatalogSnapshot:
            raise TypeError("kev_snapshot must be one complete KevCatalogSnapshot")
        if type(self.epss_snapshot) not in {EpssSnapshot, HistoricalEpssSnapshot}:
            raise TypeError("epss_snapshot must be one complete supported EPSS snapshot")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RepresentativeThreatEvidenceAdmissionError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _sequence(value: object, *, field: str) -> Sequence[object]:
    if not isinstance(value, list):
        raise RepresentativeThreatEvidenceAdmissionError(f"{field} must be an array")
    return cast(Sequence[object], value)


def _string(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise RepresentativeThreatEvidenceAdmissionError(
            f"{field} must be a non-empty trimmed string"
        )
    return value


def _optional_string(value: object, *, field: str) -> str | None:
    if value is None:
        return None
    return _string(value, field=field)


def _boolean(value: object, *, field: str) -> bool:
    if type(value) is not bool:
        raise RepresentativeThreatEvidenceAdmissionError(f"{field} must be a boolean")
    return cast(bool, value)


def _integer(value: object, *, field: str) -> int:
    if type(value) is not int:
        raise RepresentativeThreatEvidenceAdmissionError(f"{field} must be an integer")
    return cast(int, value)


def _number(value: object, *, field: str) -> float:
    if type(value) not in {int, float}:
        raise RepresentativeThreatEvidenceAdmissionError(f"{field} must be numeric")
    return float(cast(int | float, value))


def _iso_datetime(value: object, *, field: str) -> datetime:
    text = _string(value, field=field)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise RepresentativeThreatEvidenceAdmissionError(
            f"{field} must contain an ISO-8601 timestamp"
        ) from exc
    if parsed.tzinfo is None:
        raise RepresentativeThreatEvidenceAdmissionError(
            f"{field} must contain a timezone-aware timestamp"
        )
    return parsed


def _optional_iso_datetime(value: object, *, field: str) -> datetime | None:
    if value is None:
        return None
    return _iso_datetime(value, field=field)


def _admit_bundle_root(bundle: Mapping[str, object]) -> str:
    if _integer(bundle.get("schema_version"), field="schema_version") != 1:
        raise RepresentativeThreatEvidenceAdmissionError("schema_version must equal 1")
    if (
        _string(bundle.get("bundle_type"), field="bundle_type")
        != "CrossSourceCveEvidenceV1"
    ):
        raise RepresentativeThreatEvidenceAdmissionError(
            "bundle_type must equal CrossSourceCveEvidenceV1"
        )
    if _boolean(bundle.get("read_only"), field="read_only") is not True:
        raise RepresentativeThreatEvidenceAdmissionError("read_only must equal true")
    return _string(bundle.get("cve_id"), field="cve_id")


def _ghsa_bundle_occurrences(
    bundle: Mapping[str, object], *, cve_id: str
) -> dict[tuple[str, int], Mapping[str, object]]:
    ghsa = _mapping(bundle.get("ghsa"), field="ghsa")
    versions = _sequence(ghsa.get("advisory_versions"), field="ghsa.advisory_versions")
    declared_versions = _integer(
        ghsa.get("advisory_version_count"), field="ghsa.advisory_version_count"
    )
    if declared_versions != len(versions):
        raise RepresentativeThreatEvidenceAdmissionError(
            "GHSA advisory version count does not match materialized versions"
        )

    occurrences: dict[tuple[str, int], Mapping[str, object]] = {}
    for version_index, raw_version in enumerate(versions):
        version = _mapping(raw_version, field=f"ghsa.advisory_versions[{version_index}]")
        if _string(version.get("cve_id"), field="ghsa.cve_id") != cve_id:
            raise RepresentativeThreatEvidenceAdmissionError("GHSA CVE identity mismatch")
        observed_id = _string(
            version.get("observed_advisory_version_id"),
            field="ghsa.observed_advisory_version_id",
        )
        packages = _sequence(version.get("package_evidence"), field="ghsa.package_evidence")
        for package_index, raw_package in enumerate(packages):
            package = _mapping(raw_package, field=f"ghsa.package_evidence[{package_index}]")
            source_index = _integer(package.get("source_index"), field="ghsa.source_index")
            if _string(package.get("ecosystem"), field="ghsa.ecosystem") != "pip":
                raise RepresentativeThreatEvidenceAdmissionError(
                    "representative GHSA package evidence must use the pip ecosystem"
                )
            if _boolean(
                package.get("range_evaluation_performed"),
                field="ghsa.range_evaluation_performed",
            ):
                raise RepresentativeThreatEvidenceAdmissionError(
                    "GHSA analytical bundle must not pre-evaluate vulnerable ranges"
                )
            key = (observed_id, source_index)
            if key in occurrences:
                raise RepresentativeThreatEvidenceAdmissionError(
                    "duplicate GHSA advisory/package occurrence"
                )
            occurrences[key] = package

    declared_entries = _integer(
        ghsa.get("vulnerability_entry_count"), field="ghsa.vulnerability_entry_count"
    )
    if declared_entries != len(occurrences):
        raise RepresentativeThreatEvidenceAdmissionError(
            "GHSA vulnerability entry count does not match materialized package evidence"
        )
    if not occurrences:
        raise RepresentativeThreatEvidenceAdmissionError(
            "representative workload requires at least one GHSA package occurrence"
        )
    return occurrences


def _validate_ghsa(
    bundle: Mapping[str, object],
    *,
    cve_id: str,
    authority: tuple[GhsaPyPIVulnerabilityEvidence, ...],
) -> None:
    occurrences = _ghsa_bundle_occurrences(bundle, cve_id=cve_id)
    observed_keys: set[tuple[str, int]] = set()
    versions = _sequence(
        _mapping(bundle.get("ghsa"), field="ghsa").get("advisory_versions"),
        field="ghsa.advisory_versions",
    )
    versions_by_id = {
        _string(
            _mapping(item, field="ghsa.advisory_version").get(
                "observed_advisory_version_id"
            ),
            field="ghsa.observed_advisory_version_id",
        ): _mapping(item, field="ghsa.advisory_version")
        for item in versions
    }

    for item in authority:
        key = (item.observed_advisory_version_id, item.source_index)
        package = occurrences.get(key)
        version = versions_by_id.get(item.observed_advisory_version_id)
        if package is None or version is None:
            raise RepresentativeThreatEvidenceAdmissionError(
                "typed GHSA evidence is not present in the analytical bundle"
            )
        if key in observed_keys:
            raise RepresentativeThreatEvidenceAdmissionError(
                "duplicate typed GHSA occurrence"
            )
        observed_keys.add(key)

        expected = (
            _string(version.get("ghsa_id"), field="ghsa.ghsa_id"),
            _string(
                version.get("source_advisory_sha256"),
                field="ghsa.source_advisory_sha256",
            ),
            _string(
                package.get("vulnerability_entry_id"),
                field="ghsa.vulnerability_entry_id",
            ),
            _string(
                package.get("source_entry_sha256"),
                field="ghsa.source_entry_sha256",
            ),
            _string(package.get("ecosystem"), field="ghsa.ecosystem"),
            _string(package.get("package_name"), field="ghsa.package_name"),
            _string(
                package.get("vulnerable_version_range"),
                field="ghsa.vulnerable_version_range",
            ),
            _optional_string(
                package.get("first_patched_version"),
                field="ghsa.first_patched_version",
            ),
        )
        actual = (
            item.ghsa_id,
            item.source_advisory_sha256,
            item.vulnerability_entry_id,
            item.source_entry_sha256,
            item.ecosystem_original,
            item.package_name_original,
            item.vulnerable_range_original,
            item.first_patched_version_original,
        )
        if item.github_cve_id != cve_id or actual != expected:
            raise RepresentativeThreatEvidenceAdmissionError(
                "typed GHSA evidence contradicts the analytical bundle"
            )

    if observed_keys != set(occurrences):
        raise RepresentativeThreatEvidenceAdmissionError(
            "typed GHSA evidence must cover every analytical package occurrence exactly once"
        )


def _validate_nvd(
    bundle: Mapping[str, object],
    *,
    cve_id: str,
    authority: tuple[NvdCveCoreRecord, ...],
) -> None:
    nvd = _mapping(bundle.get("nvd"), field="nvd")
    observations = _sequence(nvd.get("observations"), field="nvd.observations")
    by_id: dict[str, Mapping[str, object]] = {}
    for index, raw in enumerate(observations):
        observation = _mapping(raw, field=f"nvd.observations[{index}]")
        if _string(observation.get("cve_id"), field="nvd.cve_id") != cve_id:
            raise RepresentativeThreatEvidenceAdmissionError("NVD CVE identity mismatch")
        observed_id = _string(
            observation.get("observed_cve_version_id"),
            field="nvd.observed_cve_version_id",
        )
        if observed_id in by_id:
            raise RepresentativeThreatEvidenceAdmissionError(
                "duplicate NVD observed version identity"
            )
        by_id[observed_id] = observation

    if _boolean(nvd.get("exists"), field="nvd.exists") != bool(by_id):
        raise RepresentativeThreatEvidenceAdmissionError(
            "NVD exists flag contradicts materialized observations"
        )
    if _integer(nvd.get("observation_count"), field="nvd.observation_count") != len(by_id):
        raise RepresentativeThreatEvidenceAdmissionError(
            "NVD observation count contradicts materialized observations"
        )

    typed_ids: set[str] = set()
    for record in authority:
        observed = record.observed_version
        observed_id = observed.observed_cve_version_id
        source = by_id.get(observed_id)
        if source is None:
            raise RepresentativeThreatEvidenceAdmissionError(
                "typed NVD record is not present in the analytical bundle"
            )
        typed_ids.add(observed_id)
        if observed.cve_id != cve_id:
            raise RepresentativeThreatEvidenceAdmissionError(
                "typed NVD CVE identity mismatch"
            )
        published = _iso_datetime(source.get("published_at"), field="nvd.published_at")
        if record.published_at != published:
            raise RepresentativeThreatEvidenceAdmissionError("NVD published_at mismatch")
        modified = _iso_datetime(
            source.get("last_modified_at"), field="nvd.last_modified_at"
        )
        if record.last_modified_at != modified:
            raise RepresentativeThreatEvidenceAdmissionError("NVD last_modified_at mismatch")
        status = _string(source.get("vuln_status"), field="nvd.vuln_status")
        if record.vuln_status.value != status:
            raise RepresentativeThreatEvidenceAdmissionError(
                "NVD vulnerability status mismatch"
            )

    if typed_ids != set(by_id):
        raise RepresentativeThreatEvidenceAdmissionError(
            "typed NVD evidence must cover every analytical observation exactly once"
        )


def _validate_kev(
    bundle: Mapping[str, object], *, cve_id: str, snapshot: KevCatalogSnapshot
) -> None:
    kev = _mapping(bundle.get("kev"), field="kev")
    snapshot_date = _string(kev.get("snapshot_date"), field="kev.snapshot_date")
    evidence = RepositoryKevSnapshotEvidence(snapshot)
    if snapshot.snapshot_date != snapshot_date:
        raise RepresentativeThreatEvidenceAdmissionError("KEV snapshot date mismatch")

    record = evidence.record_for_cve(cve_id)
    is_kev = _boolean(kev.get("is_kev"), field="kev.is_kev")
    if is_kev != (record is not None):
        raise RepresentativeThreatEvidenceAdmissionError(
            "KEV membership contradicts the complete typed snapshot"
        )
    analytical_entry = kev.get("entry")
    if record is None:
        if analytical_entry is not None:
            raise RepresentativeThreatEvidenceAdmissionError(
                "KEV absence cannot contain an analytical entry"
            )
        absence = _optional_string(
            kev.get("absence_semantics"), field="kev.absence_semantics"
        )
        if absence != "not present in the selected KEV snapshot":
            raise RepresentativeThreatEvidenceAdmissionError(
                "KEV absence must preserve exact snapshot-local semantics"
            )
        return

    entry = _mapping(analytical_entry, field="kev.entry")
    comparisons = {
        "cve": record.cve,
        "vendor_project": record.vendor_project,
        "product": record.product,
        "vulnerability_name": record.vulnerability_name,
        "short_description": record.short_description,
        "required_action": record.required_action,
        "known_ransomware_campaign_use": record.known_ransomware_campaign_use.value,
        "catalog_version": record.catalog_version,
        "source": record.source,
        "source_sha256": record.source_sha256,
    }
    for field, expected in comparisons.items():
        if _string(entry.get(field), field=f"kev.entry.{field}") != expected:
            raise RepresentativeThreatEvidenceAdmissionError(
                f"KEV analytical field {field} contradicts the complete snapshot"
            )


def _validate_epss(
    bundle: Mapping[str, object],
    *,
    cve_id: str,
    snapshot: EpssSnapshot | HistoricalEpssSnapshot,
) -> None:
    epss = _mapping(bundle.get("epss"), field="epss")
    evidence = RepositoryEpssSnapshotEvidence(snapshot)
    snapshot_date = _string(epss.get("snapshot_date"), field="epss.snapshot_date")
    if str(evidence.snapshot_date) != snapshot_date:
        raise RepresentativeThreatEvidenceAdmissionError("EPSS snapshot date mismatch")

    record = evidence.record_for_cve(cve_id)
    present = _boolean(epss.get("evidence_present"), field="epss.evidence_present")
    if present != (record is not None):
        raise RepresentativeThreatEvidenceAdmissionError(
            "EPSS presence contradicts the complete typed snapshot"
        )
    score = epss.get("score")
    if record is None:
        if score is not None:
            raise RepresentativeThreatEvidenceAdmissionError(
                "EPSS absence cannot contain score evidence"
            )
        return

    score_object = _mapping(score, field="epss.score")
    if _string(score_object.get("cve"), field="epss.score.cve") != record.cve:
        raise RepresentativeThreatEvidenceAdmissionError("EPSS CVE identity mismatch")
    if _number(score_object.get("epss"), field="epss.score.epss") != record.epss:
        raise RepresentativeThreatEvidenceAdmissionError("EPSS score mismatch")

    raw_percentile = score_object.get("percentile")
    if record.percentile is None:
        if raw_percentile is not None:
            raise RepresentativeThreatEvidenceAdmissionError("EPSS percentile mismatch")
    elif _number(raw_percentile, field="epss.score.percentile") != record.percentile:
        raise RepresentativeThreatEvidenceAdmissionError("EPSS percentile mismatch")

    model_version = _optional_string(
        score_object.get("model_version"), field="epss.score.model_version"
    )
    if model_version != record.model_version:
        raise RepresentativeThreatEvidenceAdmissionError("EPSS model version mismatch")
    score_timestamp = _optional_iso_datetime(
        score_object.get("score_timestamp"), field="epss.score.score_timestamp"
    )
    if score_timestamp != record.score_timestamp:
        raise RepresentativeThreatEvidenceAdmissionError("EPSS score timestamp mismatch")
    source = _string(score_object.get("source"), field="epss.score.source")
    if source != record.source:
        raise RepresentativeThreatEvidenceAdmissionError("EPSS source mismatch")
    source_sha256 = _string(
        score_object.get("source_sha256"), field="epss.score.source_sha256"
    )
    if source_sha256 != record.source_sha256:
        raise RepresentativeThreatEvidenceAdmissionError("EPSS source digest mismatch")


def admit_representative_threat_evidence(
    bundle: Mapping[str, object],
    *,
    authority: RepresentativeThreatEvidenceAuthority,
) -> RepresentativeRepositoryThreatEvidence:
    """Admit analytical proof only when exact typed source authority independently agrees."""
    if not isinstance(bundle, Mapping):
        raise RepresentativeThreatEvidenceAdmissionError("bundle must be an object")
    if type(authority) is not RepresentativeThreatEvidenceAuthority:
        raise TypeError("authority must be RepresentativeThreatEvidenceAuthority")

    typed_bundle = cast(Mapping[str, object], bundle)
    cve_id = _admit_bundle_root(typed_bundle)
    _validate_ghsa(
        typed_bundle,
        cve_id=cve_id,
        authority=authority.ghsa_vulnerabilities,
    )
    _validate_nvd(
        typed_bundle,
        cve_id=cve_id,
        authority=authority.nvd_records,
    )
    _validate_kev(
        typed_bundle,
        cve_id=cve_id,
        snapshot=authority.kev_snapshot,
    )
    _validate_epss(
        typed_bundle,
        cve_id=cve_id,
        snapshot=authority.epss_snapshot,
    )

    return RepresentativeRepositoryThreatEvidence(
        ghsa_vulnerabilities=authority.ghsa_vulnerabilities,
        nvd_records=authority.nvd_records,
        kev_snapshot=authority.kev_snapshot,
        epss_snapshot=authority.epss_snapshot,
    )
