"""Tests preserving original package-name evidence."""

from opslens.correlation.domain.pypi import canonicalize_pypi_package


def test_package_original_spelling_is_preserved_alongside_lookup_identity() -> None:
    """Lookup normalization preserves the exact source package spelling for evidence."""
    package = canonicalize_pypi_package("Friendly_Bard")
    assert package.original == "Friendly_Bard"
    assert package.canonical == "friendly-bard"
