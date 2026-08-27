"""Tests for deterministic GHSA advisory collection normalization."""

import json
from typing import cast

import pytest

from opslens.transformation.ghsa.domain.collections_models import (
    GhsaCvssFamily,
)
from opslens.transformation.ghsa.domain.collections_transformer import (
    GhsaAdvisoryCollectionsTransformer,
)
from opslens.transformation.ghsa.domain.errors import (
    InvalidGhsaAdvisoryCollectionsError,
)


def _source_collections() -> dict[str, object]:
    """Return representative reviewed GHSA structured collection fields."""
    return {
        "ghsa_id": "GHSA-2345-6789-cfgh",
        "cve_id": "CVE-2026-12345",
        "identifiers": [
            {"type": "GHSA", "value": "GHSA-2345-6789-cfgh"},
            {"type": "CVE", "value": "CVE-2026-12345"},
        ],
        "references": [
            "https://github.com/advisories/GHSA-2345-6789-cfgh",
            "https://nvd.nist.gov/vuln/detail/CVE-2026-12345",
        ],
        "cwes": [
            {"cwe_id": "CWE-79", "name": "Improper Neutralization of Input"},
        ],
        "cvss_severities": {
            "cvss_v3": {
                "vector_string": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                "score": 9.8,
            },
            "cvss_v4": {
                "vector_string": (
                    "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/"
                    "SC:N/SI:N/SA:N"
                ),
                "score": 9.3,
            },
        },
    }


def _object_list(value: object) -> list[object]:
    """Narrow one JSON-like test value to a mutable object list."""
    assert isinstance(value, list)
    return cast(list[object], value)


def _object_dict(value: object) -> dict[str, object]:
    """Narrow one JSON-like test value to a string-keyed object mapping."""
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def test_normalizes_identifiers_references_cwes_and_cvss() -> None:
    """Preserve ordered collections and known CVSS families."""
    result = GhsaAdvisoryCollectionsTransformer().transform(_source_collections())

    assert result.ghsa_id == "GHSA-2345-6789-cfgh"
    assert result.cve_id == "CVE-2026-12345"
    assert [identifier.identifier_type for identifier in result.identifiers] == [
        "GHSA",
        "CVE",
    ]
    assert result.references[0].endswith("GHSA-2345-6789-cfgh")
    assert result.cwes[0].cwe_id == "CWE-79"
    assert tuple(metric.family for metric in result.cvss_severities.metrics) == (
        GhsaCvssFamily.V3,
        GhsaCvssFamily.V4,
    )


def test_nullable_cve_does_not_require_cve_identifier() -> None:
    """Allow reviewed GHSAs that do not expose a canonical CVE alias."""
    source = _source_collections()
    source["cve_id"] = None
    source["identifiers"] = [
        {"type": "GHSA", "value": "GHSA-2345-6789-cfgh"},
    ]

    result = GhsaAdvisoryCollectionsTransformer().transform(source)

    assert result.cve_id is None
    assert len(result.identifiers) == 1


def test_additional_identifier_types_are_preserved() -> None:
    """Preserve additive identifier types instead of inventing an enum."""
    source = _source_collections()
    identifiers = _object_list(source["identifiers"])
    identifiers.append({"type": "FUTURE", "value": "vendor-123"})

    result = GhsaAdvisoryCollectionsTransformer().transform(source)

    assert result.identifiers[-1].identifier_type == "FUTURE"
    assert result.identifiers[-1].value == "vendor-123"


def test_primary_ghsa_must_appear_in_identifiers() -> None:
    """Fail closed when identifier evidence contradicts the advisory key."""
    source = _source_collections()
    source["identifiers"] = [
        {"type": "GHSA", "value": "GHSA-2345-6789-cfgj"},
        {"type": "CVE", "value": "CVE-2026-12345"},
    ]

    with pytest.raises(
        InvalidGhsaAdvisoryCollectionsError,
        match="primary ghsa_id",
    ):
        GhsaAdvisoryCollectionsTransformer().transform(source)


def test_primary_cve_must_appear_when_present() -> None:
    """Require the scalar cve_id to be supported by identifier evidence."""
    source = _source_collections()
    source["identifiers"] = [
        {"type": "GHSA", "value": "GHSA-2345-6789-cfgh"},
        {"type": "CVE", "value": "CVE-2026-54321"},
    ]

    with pytest.raises(
        InvalidGhsaAdvisoryCollectionsError,
        match="primary cve_id",
    ):
        GhsaAdvisoryCollectionsTransformer().transform(source)


def test_malformed_cwe_fails_closed() -> None:
    """Reject malformed known CWE structure."""
    source = _source_collections()
    source["cwes"] = [{"cwe_id": "79", "name": "XSS"}]

    with pytest.raises(
        InvalidGhsaAdvisoryCollectionsError,
        match="canonical CWE format",
    ):
        GhsaAdvisoryCollectionsTransformer().transform(source)


def test_unknown_cvss_family_is_preserved_in_canonical_source_json() -> None:
    """Keep additive CVSS source evidence without pretending to understand it."""
    source = _source_collections()
    severities = _object_dict(source["cvss_severities"])
    severities["cvss_future"] = {
        "vector_string": "FUTURE:1/example",
        "score": 5.0,
    }

    result = GhsaAdvisoryCollectionsTransformer().transform(source)
    persisted = json.loads(result.cvss_severities.canonical_json)

    assert "cvss_future" in persisted
    assert len(result.cvss_severities.metrics) == 2


def test_malformed_known_cvss_score_fails_closed() -> None:
    """Reject malformed structures for CVSS families the contract understands."""
    source = _source_collections()
    severities = _object_dict(source["cvss_severities"])
    cvss_v3 = _object_dict(severities["cvss_v3"])
    cvss_v3["score"] = True

    with pytest.raises(
        InvalidGhsaAdvisoryCollectionsError,
        match="must be numeric",
    ):
        GhsaAdvisoryCollectionsTransformer().transform(source)


def test_deprecated_cvss_field_is_not_required_by_collection_contract() -> None:
    """Normalize cvss_severities without depending on deprecated top-level cvss."""
    source = _source_collections()
    assert "cvss" not in source

    result = GhsaAdvisoryCollectionsTransformer().transform(source)

    assert len(result.cvss_severities.metrics) == 2
