"""Tests preserving original Package-URL evidence."""

from opslens.correlation.domain.pypi import canonicalize_pypi_purl


def test_purl_original_spelling_is_preserved_alongside_canonical_identity() -> None:
    """Canonical lookup identity does not erase the exact incoming purl spelling."""
    original = "pkg:PyPI/Friendly_Bard@1.0RC1"
    purl = canonicalize_pypi_purl(original)
    assert purl.original == original
    assert purl.canonical == "pkg:pypi/friendly-bard@1.0rc1"
