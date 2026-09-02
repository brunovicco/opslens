"""Bridge normalized GHSA Silver package evidence into deterministic PyPI correlation."""

from __future__ import annotations

from dataclasses import dataclass

from opslens.correlation.domain.errors import (
    CorrelationContractError,
    InvalidGhsaEvidenceBridgeError,
    UnsupportedEcosystemError,
)
from opslens.correlation.domain.pypi import (
    build_pypi_purl,
    canonicalize_pypi_ecosystem,
    canonicalize_pypi_package,
    canonicalize_pypi_purl,
    canonicalize_pypi_version,
)
from opslens.correlation.domain.pypi_ranges import (
    CorrelationResult,
    PyPICorrelationEvidence,
    evaluate_pypi_correlation,
)
from opslens.transformation.ghsa.domain.collections_models import GhsaAdvisoryCollections
from opslens.transformation.ghsa.domain.models import ObservedGhsaAdvisoryVersion
from opslens.transformation.ghsa.domain.vulnerability_models import (
    GhsaPackageEcosystem,
    GhsaVulnerabilityEntry,
)


@dataclass(frozen=True, slots=True)
class GhsaSourceIdentifierEvidence:
    """Preserve one GitHub-emitted advisory identifier without changing its authority."""

    identifier_type: str
    value: str


@dataclass(frozen=True, slots=True)
class GhsaPyPIVulnerabilityEvidence:
    """Link one normalized GHSA PyPI vulnerability occurrence to Phase 3 correlation."""

    observed_advisory_version_id: str
    source_advisory_sha256: str
    ghsa_id: str
    github_cve_id: str | None
    github_identifiers: tuple[GhsaSourceIdentifierEvidence, ...]
    vulnerability_entry_id: str
    source_index: int
    source_entry_sha256: str
    ecosystem_original: str
    package_name_original: str
    vulnerable_range_original: str
    first_patched_version_original: str | None


@dataclass(frozen=True, slots=True)
class GhsaPyPICorrelationDecision:
    """Combine source-local GHSA provenance with one installed-package decision."""

    source: GhsaPyPIVulnerabilityEvidence
    installed_ecosystem_original: str
    installed_package_name_original: str
    installed_version_original: str
    installed_purl_original: str | None
    source_package_name_canonical: str | None
    installed_package_name_canonical: str | None
    installed_version_canonical: str | None
    installed_purl_canonical: str | None
    package_identity_matched: bool | None
    applicability: PyPICorrelationEvidence | None
    result: CorrelationResult
    reason_code: str


def project_ghsa_pypi_vulnerability(
    *,
    observed_version: ObservedGhsaAdvisoryVersion,
    collections: GhsaAdvisoryCollections,
    entry: GhsaVulnerabilityEntry,
) -> GhsaPyPIVulnerabilityEvidence:
    """Project one exact GHSA PyPI occurrence while retaining source-local authority."""
    expected_observed_version_id = observed_version.observed_advisory_version_id

    if entry.observed_advisory_version_id != expected_observed_version_id:
        raise InvalidGhsaEvidenceBridgeError(
            "GHSA vulnerability entry does not belong to the supplied advisory version."
        )

    if collections.ghsa_id != observed_version.ghsa_id:
        raise InvalidGhsaEvidenceBridgeError(
            "GHSA collections do not belong to the supplied advisory version."
        )

    if entry.package.ecosystem is not GhsaPackageEcosystem.PIP:
        raise UnsupportedEcosystemError(
            f"GHSA ecosystem {entry.package.ecosystem.value!r} is outside the PyPI bridge."
        )

    identifiers = tuple(
        GhsaSourceIdentifierEvidence(
            identifier_type=identifier.identifier_type,
            value=identifier.value,
        )
        for identifier in collections.identifiers
    )

    return GhsaPyPIVulnerabilityEvidence(
        observed_advisory_version_id=expected_observed_version_id,
        source_advisory_sha256=observed_version.source_advisory_sha256,
        ghsa_id=observed_version.ghsa_id,
        github_cve_id=collections.cve_id,
        github_identifiers=identifiers,
        vulnerability_entry_id=entry.vulnerability_entry_id,
        source_index=entry.source_index,
        source_entry_sha256=entry.source_entry_sha256,
        ecosystem_original=entry.package.ecosystem.value,
        package_name_original=entry.package.name,
        vulnerable_range_original=entry.vulnerable_version_range,
        first_patched_version_original=entry.first_patched_version,
    )


def evaluate_ghsa_pypi_vulnerability(
    source: GhsaPyPIVulnerabilityEvidence,
    *,
    installed_ecosystem: str,
    installed_package: str,
    installed_version: str,
    installed_purl: str | None = None,
) -> GhsaPyPICorrelationDecision:
    """Evaluate one installed PyPI package against one exact GHSA vulnerability occurrence."""
    source_package_name_canonical: str | None = None
    installed_package_name_canonical: str | None = None
    installed_version_canonical: str | None = None
    installed_purl_canonical: str | None = None
    package_identity_matched: bool | None = None
    applicability: PyPICorrelationEvidence | None = None

    try:
        canonicalize_pypi_ecosystem(installed_ecosystem)
        source_package = canonicalize_pypi_package(source.package_name_original)
        source_package_name_canonical = source_package.canonical

        installed_package_identity = canonicalize_pypi_package(installed_package)
        installed_package_name_canonical = installed_package_identity.canonical
        installed_version_identity = canonicalize_pypi_version(installed_version)
        installed_version_canonical = installed_version_identity.canonical

        if installed_purl is None:
            installed_purl_canonical = build_pypi_purl(
                package=installed_package_identity,
                version=installed_version_identity,
            )
        else:
            installed_purl_identity = canonicalize_pypi_purl(
                installed_purl,
                expected_package=installed_package_identity,
                expected_version=installed_version_identity,
            )
            installed_purl_canonical = installed_purl_identity.canonical

        package_identity_matched = (
            source_package.canonical == installed_package_identity.canonical
        )

        if not package_identity_matched:
            return GhsaPyPICorrelationDecision(
                source=source,
                installed_ecosystem_original=installed_ecosystem,
                installed_package_name_original=installed_package,
                installed_version_original=installed_version,
                installed_purl_original=installed_purl,
                source_package_name_canonical=source_package_name_canonical,
                installed_package_name_canonical=installed_package_name_canonical,
                installed_version_canonical=installed_version_canonical,
                installed_purl_canonical=installed_purl_canonical,
                package_identity_matched=False,
                applicability=None,
                result=CorrelationResult.NOT_AFFECTED,
                reason_code="package_identity_mismatch",
            )

        applicability = evaluate_pypi_correlation(
            package=installed_package,
            version=installed_version,
            vulnerable_range=source.vulnerable_range_original,
            first_patched_version=source.first_patched_version_original,
        )

        return GhsaPyPICorrelationDecision(
            source=source,
            installed_ecosystem_original=installed_ecosystem,
            installed_package_name_original=installed_package,
            installed_version_original=installed_version,
            installed_purl_original=installed_purl,
            source_package_name_canonical=source_package_name_canonical,
            installed_package_name_canonical=installed_package_name_canonical,
            installed_version_canonical=installed_version_canonical,
            installed_purl_canonical=installed_purl_canonical,
            package_identity_matched=True,
            applicability=applicability,
            result=applicability.result,
            reason_code=applicability.reason_code,
        )
    except CorrelationContractError as exc:
        return GhsaPyPICorrelationDecision(
            source=source,
            installed_ecosystem_original=installed_ecosystem,
            installed_package_name_original=installed_package,
            installed_version_original=installed_version,
            installed_purl_original=installed_purl,
            source_package_name_canonical=source_package_name_canonical,
            installed_package_name_canonical=installed_package_name_canonical,
            installed_version_canonical=installed_version_canonical,
            installed_purl_canonical=installed_purl_canonical,
            package_identity_matched=package_identity_matched,
            applicability=applicability,
            result=CorrelationResult.UNSUPPORTED,
            reason_code=exc.reason_code,
        )
