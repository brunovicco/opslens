"""Tests for the frozen Phase 3 PyPI package identity foundation."""

from __future__ import annotations

import pytest

from opslens.correlation.domain.errors import (
    InvalidPackageNameError,
    InvalidPackagePurlError,
    InvalidPackageVersionError,
    UnsupportedEcosystemError,
    UnsupportedPackagePurlFeatureError,
)
from opslens.correlation.domain.pypi import (
    PyPIEcosystem,
    build_pypi_purl,
    canonicalize_pypi_ecosystem,
    canonicalize_pypi_package,
    canonicalize_pypi_purl,
    canonicalize_pypi_version,
)


def test_canonicalize_pypi_ecosystem_accepts_canonical_and_ghsa_alias() -> None:
    """The first evaluator owns only PyPI and the explicit GHSA `pip` alias."""
    assert canonicalize_pypi_ecosystem("pypi") is PyPIEcosystem.PYPI
    assert canonicalize_pypi_ecosystem("pip") is PyPIEcosystem.PYPI
    assert canonicalize_pypi_ecosystem("PIP") is PyPIEcosystem.PYPI


def test_canonicalize_pypi_ecosystem_rejects_other_ecosystems_and_whitespace() -> None:
    """Unknown or contaminated ecosystem evidence fails closed."""
    with pytest.raises(UnsupportedEcosystemError):
        canonicalize_pypi_ecosystem("npm")
    with pytest.raises(UnsupportedEcosystemError):
        canonicalize_pypi_ecosystem(" pip ")


@pytest.mark.parametrize(
    ("original", "canonical"),
    [
        ("Requests", "requests"),
        ("Friendly_Bard", "friendly-bard"),
        ("zope.interface", "zope-interface"),
        ("FrIeNdLy-._.-bArD", "friendly-bard"),
    ],
)
def test_canonicalize_pypi_package_follows_pypa_name_normalization(
    original: str,
    canonical: str,
) -> None:
    """Lookup identity lowercases and collapses runs of dot, dash, and underscore."""
    package = canonicalize_pypi_package(original)
    assert package.original == original
    assert package.canonical == canonical


@pytest.mark.parametrize("value", ["", " package", "package ", "-package", "package-", "pkg/name"])
def test_canonicalize_pypi_package_rejects_invalid_project_names(value: str) -> None:
    """Package identity is validated before normalization so bad evidence is not repaired."""
    with pytest.raises(InvalidPackageNameError):
        canonicalize_pypi_package(value)


@pytest.mark.parametrize(
    ("original", "canonical"),
    [
        ("2.31.0", "2.31.0"),
        ("1.0RC1", "1.0rc1"),
        ("1.0-1", "1.0.post1"),
        ("1!1.0", "1!1.0"),
        ("v2.0", "2.0"),
    ],
)
def test_canonicalize_pypi_version_uses_pep440_normalization(
    original: str,
    canonical: str,
) -> None:
    """Concrete versions use the standards-conformant Packaging parser."""
    version = canonicalize_pypi_version(original)
    assert version.original == original
    assert version.canonical == canonical


def test_canonicalize_pypi_version_preserves_pep440_ordering() -> None:
    """Prerelease, final, post-release, and epoch ordering must not be lexical."""
    prerelease = canonicalize_pypi_version("2.0rc1")
    final = canonicalize_pypi_version("2.0")
    post = canonicalize_pypi_version("2.0.post1")
    epoch = canonicalize_pypi_version("1!1.0")

    assert prerelease.parsed < final.parsed < post.parsed < epoch.parsed


@pytest.mark.parametrize("value", ["", " 1.0", "1.0 ", "definitely-not-a-pep440-version"])
def test_canonicalize_pypi_version_rejects_invalid_evidence(value: str) -> None:
    """Malformed concrete versions fail closed instead of receiving an arbitrary ordering."""
    with pytest.raises(InvalidPackageVersionError) as exc_info:
        canonicalize_pypi_version(value)
    assert exc_info.value.reason_code == "invalid_version"


def test_build_pypi_purl_percent_encodes_pep440_local_and_epoch_separators() -> None:
    """Purl data characters outside the canonical allowed set are percent encoded."""
    package = canonicalize_pypi_package("Demo_Package")

    local = canonicalize_pypi_version("1.0+CPU.1")
    assert build_pypi_purl(package=package, version=local) == (
        "pkg:pypi/demo-package@1.0%2Bcpu.1"
    )

    epoch = canonicalize_pypi_version("1!2.0")
    assert build_pypi_purl(package=package, version=epoch) == (
        "pkg:pypi/demo-package@1%212.0"
    )


def test_canonicalize_pypi_purl_reconstructs_canonical_identity() -> None:
    """An incoming purl is decoded, ecosystem-normalized, and rebuilt deterministically."""
    purl = canonicalize_pypi_purl("pkg:PyPI/Friendly_Bard@1.0RC1")

    assert purl.original == "pkg:PyPI/Friendly_Bard@1.0RC1"
    assert purl.package.canonical == "friendly-bard"
    assert purl.version.canonical == "1.0rc1"
    assert purl.canonical == "pkg:pypi/friendly-bard@1.0rc1"


def test_canonicalize_pypi_purl_accepts_percent_encoded_local_version() -> None:
    """The purl parser validates UTF-8 percent decoding before PEP 440 parsing."""
    purl = canonicalize_pypi_purl("pkg:pypi/demo-package@1.0%2Bcpu.1")
    assert purl.version.canonical == "1.0+cpu.1"
    assert purl.canonical == "pkg:pypi/demo-package@1.0%2Bcpu.1"


def test_canonicalize_pypi_purl_cross_checks_separate_package_and_version_evidence() -> None:
    """A purl cannot silently disagree with package/version evidence from another field."""
    expected_package = canonicalize_pypi_package("requests")
    expected_version = canonicalize_pypi_version("2.31.0")

    canonical = canonicalize_pypi_purl(
        "pkg:pypi/Requests@2.31",
        expected_package=expected_package,
        expected_version=expected_version,
    )
    assert canonical.canonical == "pkg:pypi/requests@2.31"

    with pytest.raises(InvalidPackagePurlError):
        canonicalize_pypi_purl(
            "pkg:pypi/urllib3@2.31.0",
            expected_package=expected_package,
            expected_version=expected_version,
        )


def test_canonicalize_pypi_purl_rejects_qualifiers_and_subpaths() -> None:
    """Phase 3 v1 does not silently discard valid PURL features it has not modeled."""
    with pytest.raises(UnsupportedPackagePurlFeatureError) as qualifier_error:
        canonicalize_pypi_purl("pkg:pypi/django@5.0?file_name=Django-5.0.tar.gz")
    assert qualifier_error.value.reason_code == "unsupported_purl_feature"

    with pytest.raises(UnsupportedPackagePurlFeatureError):
        canonicalize_pypi_purl("pkg:pypi/django@5.0#django/core")


def test_canonicalize_pypi_purl_rejects_wrong_type_and_invalid_percent_escape() -> None:
    """Wrong ecosystem or malformed encoded evidence cannot become a PyPI identity."""
    with pytest.raises(UnsupportedEcosystemError):
        canonicalize_pypi_purl("pkg:npm/django@5.0")

    with pytest.raises(InvalidPackagePurlError):
        canonicalize_pypi_purl("pkg:pypi/django@1.0%ZZ")
