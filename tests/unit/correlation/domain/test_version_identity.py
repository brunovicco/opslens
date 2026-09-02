"""Focused PEP 440 identity-equivalence tests."""

from opslens.correlation.domain.pypi import canonicalize_pypi_version


def test_release_segments_compare_with_pep440_zero_padding() -> None:
    """Equivalent release segments compare by PEP 440 identity, not source spelling."""
    short = canonicalize_pypi_version("2.31")
    explicit = canonicalize_pypi_version("2.31.0")
    assert short.parsed == explicit.parsed
    assert short.original != explicit.original


def test_original_version_spelling_remains_available_for_evidence() -> None:
    """Normalization does not destroy the exact source spelling used as evidence."""
    version = canonicalize_pypi_version("1.0RC1")
    assert version.original == "1.0RC1"
    assert version.canonical == "1.0rc1"
