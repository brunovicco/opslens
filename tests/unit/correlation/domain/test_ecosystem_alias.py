"""Focused tests for the first ecosystem alias boundary."""

from opslens.correlation.domain.pypi import PyPIEcosystem, canonicalize_pypi_ecosystem


def test_ghsa_pip_alias_maps_to_canonical_pypi_without_changing_authority() -> None:
    """The source alias is normalized only for matching; source provenance remains external."""
    assert canonicalize_pypi_ecosystem("pip") is PyPIEcosystem.PYPI
