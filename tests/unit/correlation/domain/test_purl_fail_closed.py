"""Additional fail-closed tests for the narrow Phase 3 PyPI purl contract."""

import pytest

from opslens.correlation.domain.errors import InvalidPackagePurlError
from opslens.correlation.domain.pypi import canonicalize_pypi_purl


@pytest.mark.parametrize(
    "value",
    [
        "pkg:pypi/django",
        "pkg:pypi/@5.0",
        "pkg:pypi/django@",
        "pkg:pypi/org/django@5.0",
        " pkg:pypi/django@5.0",
        "pkg:pypi/django@5.0 ",
    ],
)
def test_malformed_or_out_of_contract_purls_fail_closed(value: str) -> None:
    """Missing version, namespace, empty components, and whitespace are invalid in v1."""
    with pytest.raises(InvalidPackagePurlError):
        canonicalize_pypi_purl(value)
