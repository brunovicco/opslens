"""PURL type case-folding tests."""

from opslens.correlation.domain.pypi import canonicalize_pypi_purl


def test_registered_pypi_purl_type_is_case_insensitive() -> None:
    """PURL type parsing follows the standard case-insensitive type rule."""
    assert canonicalize_pypi_purl("pkg:PyPI/django@5.0").canonical == "pkg:pypi/django@5.0"
