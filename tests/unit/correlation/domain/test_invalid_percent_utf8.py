"""Tests for strict UTF-8 handling in percent-encoded purl evidence."""

import pytest

from opslens.correlation.domain.errors import InvalidPackagePurlError
from opslens.correlation.domain.pypi import canonicalize_pypi_purl


def test_purl_rejects_percent_encoded_bytes_that_are_not_valid_utf8() -> None:
    """Malformed encoded evidence is never repaired or interpreted heuristically."""
    with pytest.raises(InvalidPackagePurlError):
        canonicalize_pypi_purl("pkg:pypi/django@1.0%FF")
