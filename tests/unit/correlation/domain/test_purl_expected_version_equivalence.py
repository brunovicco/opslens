"""Tests for PEP 440-equivalent version evidence across purl and explicit fields."""

from opslens.correlation.domain.pypi import canonicalize_pypi_purl, canonicalize_pypi_version


def test_purl_cross_check_accepts_pep440_equivalent_version_spellings() -> None:
    """Cross-field consistency uses PEP 440 identity rather than raw string equality."""
    expected = canonicalize_pypi_version("2.31.0")
    purl = canonicalize_pypi_purl("pkg:pypi/requests@2.31", expected_version=expected)
    assert purl.version.parsed == expected.parsed
