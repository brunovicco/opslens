"""Tests preserving original version evidence."""

from opslens.correlation.domain.pypi import canonicalize_pypi_version


def test_version_original_spelling_is_preserved_alongside_pep440_identity() -> None:
    """PEP 440 normalization preserves exact source spelling for evidence reconstruction."""
    version = canonicalize_pypi_version("1.0RC1")
    assert version.original == "1.0RC1"
    assert version.canonical == "1.0rc1"
