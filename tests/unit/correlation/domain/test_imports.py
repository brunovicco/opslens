"""Import-surface tests for the correlation domain package."""

from opslens.correlation import domain


def test_domain_exports_pypi_identity_contract() -> None:
    """The public domain surface exposes the frozen PyPI identity primitives."""
    assert domain.PyPIEcosystem.PYPI.value == "pypi"
    assert domain.canonicalize_pypi_package("Friendly_Bard").canonical == "friendly-bard"
    assert domain.canonicalize_pypi_version("1.0RC1").canonical == "1.0rc1"
