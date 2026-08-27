"""Tests for deterministic GHSA one-to-many vulnerability normalization."""

import json
from copy import deepcopy
from typing import cast

import pytest

from opslens.transformation.ghsa.domain.errors import (
    InvalidGhsaVulnerabilityEntriesError,
)
from opslens.transformation.ghsa.domain.vulnerabilities_transformer import (
    GhsaVulnerabilitiesTransformer,
)
from opslens.transformation.ghsa.domain.vulnerability_models import (
    GhsaPackageEcosystem,
)


def _source_advisory() -> dict[str, object]:
    """Return a minimal advisory with two package/range/fix occurrences."""
    return {
        "ghsa_id": "GHSA-2345-6789-cfgh",
        "vulnerabilities": [
            {
                "package": {
                    "ecosystem": "pip",
                    "name": "example-package",
                },
                "vulnerable_version_range": ">= 1.0.0, < 1.2.0",
                "first_patched_version": "1.2.0",
                "vulnerable_functions": ["unsafe_load"],
            },
            {
                "package": {
                    "ecosystem": "npm",
                    "name": "other-package",
                },
                "vulnerable_version_range": "<= 4.5.6",
                "first_patched_version": None,
                "vulnerable_functions": [],
            },
        ],
    }


def _object_list(value: object) -> list[object]:
    """Narrow one JSON-like test value to a mutable object list."""
    assert isinstance(value, list)
    return cast(list[object], value)


def _object_dict(value: object) -> dict[str, object]:
    """Narrow one JSON-like test value to a string-keyed object mapping."""
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def test_preserves_one_to_many_package_range_fix_evidence() -> None:
    """Keep every vulnerability entry and its exact source order."""
    result = GhsaVulnerabilitiesTransformer().transform(_source_advisory())

    assert len(result.entries) == 2
    assert result.entries[0].source_index == 0
    assert result.entries[0].package.ecosystem is GhsaPackageEcosystem.PIP
    assert result.entries[0].package.name == "example-package"
    assert result.entries[0].vulnerable_version_range == ">= 1.0.0, < 1.2.0"
    assert result.entries[0].first_patched_version == "1.2.0"
    assert result.entries[0].vulnerable_functions == ("unsafe_load",)

    assert result.entries[1].source_index == 1
    assert result.entries[1].package.ecosystem is GhsaPackageEcosystem.NPM
    assert result.entries[1].first_patched_version is None


def test_range_expression_is_preserved_without_interpretation() -> None:
    """Keep the source expression byte-for-byte at the semantic string layer."""
    source = _source_advisory()
    vulnerabilities = _object_list(source["vulnerabilities"])
    first = _object_dict(vulnerabilities[0])
    first["vulnerable_version_range"] = ">= 1.0.0, != 1.1.5, < 2.0.0"

    result = GhsaVulnerabilitiesTransformer().transform(source)

    assert result.entries[0].vulnerable_version_range == ">= 1.0.0, != 1.1.5, < 2.0.0"


def test_nullable_first_patched_version_is_preserved() -> None:
    """Represent missing structured fixed-version evidence as null."""
    result = GhsaVulnerabilitiesTransformer().transform(_source_advisory())

    assert result.entries[1].first_patched_version is None


def test_duplicate_source_entries_remain_distinct_occurrences() -> None:
    """Use source index so duplicate array occurrences do not collapse."""
    source = _source_advisory()
    vulnerabilities = _object_list(source["vulnerabilities"])
    vulnerabilities[1] = deepcopy(vulnerabilities[0])

    result = GhsaVulnerabilitiesTransformer().transform(source)

    assert result.entries[0].source_entry_sha256 == result.entries[1].source_entry_sha256
    assert result.entries[0].vulnerability_entry_id != result.entries[1].vulnerability_entry_id


def test_entry_canonical_json_preserves_additive_source_fields() -> None:
    """Keep additive entry evidence even before it gains a dedicated column."""
    source = _source_advisory()
    vulnerabilities = _object_list(source["vulnerabilities"])
    first = _object_dict(vulnerabilities[0])
    first["future_source_field"] = {"enabled": True}

    result = GhsaVulnerabilitiesTransformer().transform(source)
    persisted = json.loads(result.entries[0].source_entry_json)

    assert persisted["future_source_field"] == {"enabled": True}


def test_changed_entry_content_changes_entry_identity() -> None:
    """Change the exact vulnerability occurrence identity when evidence changes."""
    original = _source_advisory()
    changed = deepcopy(original)
    vulnerabilities = _object_list(changed["vulnerabilities"])
    first = _object_dict(vulnerabilities[0])
    first["first_patched_version"] = "1.2.1"

    original_result = GhsaVulnerabilitiesTransformer().transform(original)
    changed_result = GhsaVulnerabilitiesTransformer().transform(changed)

    assert (
        original_result.entries[0].source_entry_sha256
        != changed_result.entries[0].source_entry_sha256
    )
    assert (
        original_result.entries[0].vulnerability_entry_id
        != changed_result.entries[0].vulnerability_entry_id
    )


def test_empty_vulnerability_array_is_valid_source_evidence() -> None:
    """Allow an advisory observation with no package vulnerability entries."""
    source = _source_advisory()
    source["vulnerabilities"] = []

    result = GhsaVulnerabilitiesTransformer().transform(source)

    assert result.entries == ()


def test_unknown_ecosystem_fails_closed() -> None:
    """Reject source ecosystem values outside the versioned contract vocabulary."""
    source = _source_advisory()
    vulnerabilities = _object_list(source["vulnerabilities"])
    first = _object_dict(vulnerabilities[0])
    package = _object_dict(first["package"])
    package["ecosystem"] = "future-ecosystem"

    with pytest.raises(
        InvalidGhsaVulnerabilityEntriesError,
        match="unsupported package ecosystem",
    ):
        GhsaVulnerabilitiesTransformer().transform(source)


def test_other_ecosystem_remains_supported() -> None:
    """Preserve GitHub's documented generic other ecosystem value."""
    source = _source_advisory()
    vulnerabilities = _object_list(source["vulnerabilities"])
    first = _object_dict(vulnerabilities[0])
    package = _object_dict(first["package"])
    package["ecosystem"] = "other"

    result = GhsaVulnerabilitiesTransformer().transform(source)

    assert result.entries[0].package.ecosystem is GhsaPackageEcosystem.OTHER


def test_missing_known_entry_field_fails_closed() -> None:
    """Reject malformed known vulnerability structures."""
    source = _source_advisory()
    vulnerabilities = _object_list(source["vulnerabilities"])
    first = _object_dict(vulnerabilities[0])
    del first["vulnerable_version_range"]

    with pytest.raises(
        InvalidGhsaVulnerabilityEntriesError,
        match="missing fields",
    ):
        GhsaVulnerabilitiesTransformer().transform(source)


def test_malformed_vulnerable_function_fails_closed() -> None:
    """Reject non-string known vulnerable function evidence."""
    source = _source_advisory()
    vulnerabilities = _object_list(source["vulnerabilities"])
    first = _object_dict(vulnerabilities[0])
    first["vulnerable_functions"] = ["safe", 123]

    with pytest.raises(
        InvalidGhsaVulnerabilityEntriesError,
        match="must be a non-empty string",
    ):
        GhsaVulnerabilitiesTransformer().transform(source)
