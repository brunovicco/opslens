"""Tests that the frozen Phase 3 PyPI corpus remains consumable by identity primitives."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from opslens.correlation.domain.pypi import (
    canonicalize_pypi_package,
    canonicalize_pypi_version,
)

_FIXTURE_PATH = Path("tests/fixtures/correlation/pypi_v1_cases.json")


def test_frozen_pypi_corpus_identity_expectations() -> None:
    """Every corpus case with valid identity evidence matches the frozen canonical values."""
    payload = cast(dict[str, Any], json.loads(_FIXTURE_PATH.read_text(encoding="utf-8")))
    assert payload["schema_version"] == 1
    assert payload["ecosystem"] == "pypi"

    cases = cast(list[dict[str, Any]], payload["cases"])
    assert len(cases) == 15

    for case in cases:
        package = canonicalize_pypi_package(cast(str, case["package"]))
        assert package.canonical == case["expected_package_canonical"]

        if case.get("expected_reason_code") == "invalid_version":
            continue

        version = canonicalize_pypi_version(cast(str, case["version"]))
        assert version.canonical == case["expected_version_canonical"]
