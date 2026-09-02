"""Canonicalization tests for PyPI Package-URLs."""

from opslens.correlation.domain.pypi import canonicalize_pypi_purl


def test_safe_purl_component_characters_are_not_over_encoded() -> None:
    """Canonical PURL keeps the standard unencoded punctuation set when valid for PEP 440."""
    purl = canonicalize_pypi_purl("pkg:pypi/demo_package@1.0.dev1")
    assert purl.canonical == "pkg:pypi/demo-package@1.0.dev1"


def test_percent_encoded_epoch_is_decoded_then_reencoded_canonically() -> None:
    """Opaque PURL version bytes are decoded before ecosystem-specific version normalization."""
    purl = canonicalize_pypi_purl("pkg:pypi/demo-package@1%211.0")
    assert purl.version.canonical == "1!1.0"
    assert purl.canonical == "pkg:pypi/demo-package@1%211.0"
