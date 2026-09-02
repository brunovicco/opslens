"""Tests for linking GHSA Silver evidence to deterministic PyPI applicability."""

from __future__ import annotations

import pytest

from opslens.correlation.adapters.ghsa import (
    evaluate_ghsa_pypi_vulnerability,
    project_ghsa_pypi_vulnerability,
)
from opslens.correlation.domain.errors import (
    InvalidGhsaEvidenceBridgeError,
    UnsupportedEcosystemError,
)
from opslens.correlation.domain.pypi_ranges import CorrelationResult
from opslens.transformation.ghsa.domain.canonicalization import (
    canonicalize_json_object,
    sha256_hex,
)
from opslens.transformation.ghsa.domain.collections_models import (
    GhsaAdvisoryCollections,
    GhsaAdvisoryIdentifier,
    GhsaCvssSeverities,
)
from opslens.transformation.ghsa.domain.models import ObservedGhsaAdvisoryVersion
from opslens.transformation.ghsa.domain.vulnerability_models import (
    GhsaPackageEcosystem,
    GhsaPackageIdentity,
    GhsaVulnerabilityEntry,
)

_GHSA_ID = "GHSA-2345-6789-cfgh"
_OTHER_GHSA_ID = "GHSA-3456-789c-fghj"
_CVE_ID = "CVE-2026-12345"


def _observed(ghsa_id: str = _GHSA_ID) -> ObservedGhsaAdvisoryVersion:
    """Build one minimal exact GHSA advisory observation."""
    return ObservedGhsaAdvisoryVersion.from_source({"ghsa_id": ghsa_id})


def _collections(
    *,
    ghsa_id: str = _GHSA_ID,
    cve_id: str | None = _CVE_ID,
) -> GhsaAdvisoryCollections:
    """Build normalized GitHub identifier evidence for one advisory."""
    identifiers = [GhsaAdvisoryIdentifier(identifier_type="GHSA", value=ghsa_id)]
    if cve_id is not None:
        identifiers.append(GhsaAdvisoryIdentifier(identifier_type="CVE", value=cve_id))
    identifiers.append(GhsaAdvisoryIdentifier(identifier_type="OSV", value="OSV-source-alias"))

    return GhsaAdvisoryCollections(
        ghsa_id=ghsa_id,
        cve_id=cve_id,
        identifiers=tuple(identifiers),
        references=(),
        cwes=(),
        cvss_severities=GhsaCvssSeverities(metrics=(), canonical_json="{}"),
    )


def _entry(
    observed: ObservedGhsaAdvisoryVersion,
    *,
    ecosystem: GhsaPackageEcosystem = GhsaPackageEcosystem.PIP,
    package_name: str = "Friendly_Bard",
    vulnerable_range: str = ">= 1.0.0, < 2.0.0",
    first_patched_version: str | None = "2.0.0",
) -> GhsaVulnerabilityEntry:
    """Build one exact normalized GHSA vulnerability-array occurrence."""
    source_object: dict[str, object] = {
        "package": {"ecosystem": ecosystem.value, "name": package_name},
        "vulnerable_version_range": vulnerable_range,
        "first_patched_version": first_patched_version,
        "vulnerable_functions": [],
    }
    canonical_bytes = canonicalize_json_object(source_object)
    canonical_json = canonical_bytes.decode("utf-8")

    return GhsaVulnerabilityEntry(
        observed_advisory_version_id=observed.observed_advisory_version_id,
        source_index=0,
        package=GhsaPackageIdentity(ecosystem=ecosystem, name=package_name),
        vulnerable_version_range=vulnerable_range,
        first_patched_version=first_patched_version,
        vulnerable_functions=(),
        source_entry_json=canonical_json,
        source_entry_sha256=sha256_hex(canonical_bytes),
    )


def test_projection_preserves_github_authority_and_exact_source_coordinates() -> None:
    """Keep GitHub assertions and source hashes linked instead of merging authorities."""
    observed = _observed()
    entry = _entry(observed)

    source = project_ghsa_pypi_vulnerability(
        observed_version=observed,
        collections=_collections(),
        entry=entry,
    )

    assert source.observed_advisory_version_id == observed.observed_advisory_version_id
    assert source.source_advisory_sha256 == observed.source_advisory_sha256
    assert source.ghsa_id == _GHSA_ID
    assert source.github_cve_id == _CVE_ID
    assert tuple(
        (identifier.identifier_type, identifier.value)
        for identifier in source.github_identifiers
    ) == (
        ("GHSA", _GHSA_ID),
        ("CVE", _CVE_ID),
        ("OSV", "OSV-source-alias"),
    )
    assert source.vulnerability_entry_id == entry.vulnerability_entry_id
    assert source.source_entry_sha256 == entry.source_entry_sha256
    assert source.source_index == 0


def test_normalized_package_identity_and_range_produce_affected_decision() -> None:
    """Match equivalent PyPI names before evaluating the published vulnerable range."""
    observed = _observed()
    source = project_ghsa_pypi_vulnerability(
        observed_version=observed,
        collections=_collections(),
        entry=_entry(observed),
    )

    decision = evaluate_ghsa_pypi_vulnerability(
        source,
        installed_ecosystem="pypi",
        installed_package="friendly-bard",
        installed_version="1.5.0",
        installed_purl="pkg:pypi/friendly-bard@1.5.0",
    )

    assert decision.package_identity_matched is True
    assert decision.source_package_name_canonical == "friendly-bard"
    assert decision.installed_package_name_canonical == "friendly-bard"
    assert decision.installed_purl_canonical == "pkg:pypi/friendly-bard@1.5.0"
    assert decision.result is CorrelationResult.AFFECTED
    assert decision.reason_code == "version_matches_vulnerable_range"
    assert decision.applicability is not None
    assert decision.applicability.first_patched_version_canonical == "2.0.0"


def test_package_identity_mismatch_is_a_deterministic_non_match() -> None:
    """Return not affected when package identity is certainly different."""
    observed = _observed()
    source = project_ghsa_pypi_vulnerability(
        observed_version=observed,
        collections=_collections(),
        entry=_entry(observed),
    )

    decision = evaluate_ghsa_pypi_vulnerability(
        source,
        installed_ecosystem="pip",
        installed_package="different-package",
        installed_version="1.5.0",
    )

    assert decision.package_identity_matched is False
    assert decision.result is CorrelationResult.NOT_AFFECTED
    assert decision.reason_code == "package_identity_mismatch"
    assert decision.applicability is None


def test_invalid_installed_purl_fails_closed_before_package_matching() -> None:
    """Reject inconsistent installed identity evidence instead of ignoring the purl."""
    observed = _observed()
    source = project_ghsa_pypi_vulnerability(
        observed_version=observed,
        collections=_collections(),
        entry=_entry(observed),
    )

    decision = evaluate_ghsa_pypi_vulnerability(
        source,
        installed_ecosystem="pypi",
        installed_package="friendly-bard",
        installed_version="1.5.0",
        installed_purl="pkg:pypi/other-package@1.5.0",
    )

    assert decision.result is CorrelationResult.UNSUPPORTED
    assert decision.reason_code == "invalid_purl"
    assert decision.package_identity_matched is None
    assert decision.applicability is None


def test_unsupported_installed_ecosystem_fails_closed() -> None:
    """Do not apply PyPI semantics to a dependency from another ecosystem."""
    observed = _observed()
    source = project_ghsa_pypi_vulnerability(
        observed_version=observed,
        collections=_collections(),
        entry=_entry(observed),
    )

    decision = evaluate_ghsa_pypi_vulnerability(
        source,
        installed_ecosystem="npm",
        installed_package="friendly-bard",
        installed_version="1.5.0",
    )

    assert decision.result is CorrelationResult.UNSUPPORTED
    assert decision.reason_code == "unsupported_ecosystem"
    assert decision.package_identity_matched is None


def test_matched_package_with_unsupported_range_remains_unsupported() -> None:
    """Propagate fail-closed range semantics after package identity is established."""
    observed = _observed()
    source = project_ghsa_pypi_vulnerability(
        observed_version=observed,
        collections=_collections(),
        entry=_entry(observed, vulnerable_range="~= 1.4"),
    )

    decision = evaluate_ghsa_pypi_vulnerability(
        source,
        installed_ecosystem="pypi",
        installed_package="friendly-bard",
        installed_version="1.5.0",
    )

    assert decision.package_identity_matched is True
    assert decision.result is CorrelationResult.UNSUPPORTED
    assert decision.reason_code == "unsupported_range_operator"
    assert decision.applicability is not None
    assert decision.applicability.result is CorrelationResult.UNSUPPORTED


def test_non_pypi_ghsa_entry_is_rejected_at_source_boundary() -> None:
    """Reject a GHSA ecosystem before any PyPI interpretation can occur."""
    observed = _observed()

    with pytest.raises(UnsupportedEcosystemError) as exc_info:
        project_ghsa_pypi_vulnerability(
            observed_version=observed,
            collections=_collections(),
            entry=_entry(observed, ecosystem=GhsaPackageEcosystem.NPM),
        )

    assert exc_info.value.reason_code == "unsupported_ecosystem"


def test_advisory_version_mismatch_is_rejected_before_projection() -> None:
    """Do not attach a vulnerability occurrence to a different observed advisory version."""
    observed = _observed()
    other_observed = _observed(_OTHER_GHSA_ID)
    entry = _entry(observed)

    with pytest.raises(InvalidGhsaEvidenceBridgeError) as exc_info:
        project_ghsa_pypi_vulnerability(
            observed_version=other_observed,
            collections=_collections(ghsa_id=_OTHER_GHSA_ID, cve_id=None),
            entry=entry,
        )

    assert exc_info.value.reason_code == "invalid_ghsa_evidence_bridge"


def test_collections_from_different_ghsa_are_rejected() -> None:
    """Keep identifier collections bound to their own GitHub advisory authority."""
    observed = _observed()
    entry = _entry(observed)

    with pytest.raises(InvalidGhsaEvidenceBridgeError) as exc_info:
        project_ghsa_pypi_vulnerability(
            observed_version=observed,
            collections=_collections(ghsa_id=_OTHER_GHSA_ID, cve_id=None),
            entry=entry,
        )

    assert exc_info.value.reason_code == "invalid_ghsa_evidence_bridge"


def test_missing_github_cve_remains_unknown_not_synthesized() -> None:
    """Preserve an absent GitHub CVE assertion without inventing a cross-source alias."""
    observed = _observed()
    source = project_ghsa_pypi_vulnerability(
        observed_version=observed,
        collections=_collections(cve_id=None),
        entry=_entry(observed),
    )

    assert source.github_cve_id is None
    assert all(identifier.identifier_type != "CVE" for identifier in source.github_identifiers)
