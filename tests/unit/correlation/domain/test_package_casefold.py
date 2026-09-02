"""PyPI package-name case-folding tests."""

from opslens.correlation.domain.pypi import canonicalize_pypi_package


def test_pypi_package_lookup_identity_is_case_insensitive() -> None:
    """Distribution lookup identity is lowercased while source spelling is preserved."""
    assert canonicalize_pypi_package("REQUESTS").canonical == "requests"
