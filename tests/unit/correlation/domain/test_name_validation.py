"""Focused PyPI project-name validation tests."""

import pytest

from opslens.correlation.domain.errors import InvalidPackageNameError
from opslens.correlation.domain.pypi import canonicalize_pypi_package


@pytest.mark.parametrize("value", ["a", "A", "a.b", "a_b", "a-b", "a...b", "a___b"])
def test_valid_pypi_project_names_are_accepted(value: str) -> None:
    """Names satisfying the PyPA distribution-name grammar remain valid."""
    canonicalize_pypi_package(value)


@pytest.mark.parametrize("value", [".", "_", "-", ".a", "a.", "_a", "a_", "-a", "a-"])
def test_name_must_start_and_end_with_alphanumeric(value: str) -> None:
    """Normalization never repairs invalid leading or trailing punctuation."""
    with pytest.raises(InvalidPackageNameError):
        canonicalize_pypi_package(value)
