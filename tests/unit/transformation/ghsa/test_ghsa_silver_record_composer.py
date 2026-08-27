"""Tests for composed GHSA Silver logical records and row mapping."""

from typing import cast

from opslens.transformation.ghsa.application.record_composer import (
    GhsaSilverRecordComposerV1,
)
from opslens.transformation.ghsa.domain.collections_transformer import (
    GhsaAdvisoryCollectionsTransformer,
)
from opslens.transformation.ghsa.domain.transformer import (
    GhsaAdvisoryCoreTransformer,
)
from opslens.transformation.ghsa.domain.vulnerabilities_transformer import (
    GhsaVulnerabilitiesTransformer,
)
from opslens.transformation.ghsa.serialization.row_mapper import (
    map_ghsa_silver_record_v1,
)


def _source_advisory() -> dict[str, object]:
    """Return one complete reviewed advisory accepted by all Silver transformers."""
    return {
        "ghsa_id": "GHSA-2345-6789-cfgh",
        "cve_id": "CVE-2026-12345",
        "url": "https://api.github.com/advisories/GHSA-2345-6789-cfgh",
        "html_url": "https://github.com/advisories/GHSA-2345-6789-cfgh",
        "repository_advisory_url": None,
        "summary": "Example reviewed advisory",
        "description": "Example advisory description.",
        "type": "reviewed",
        "severity": "high",
        "source_code_location": None,
        "published_at": "2026-08-20T10:00:00Z",
        "updated_at": "2026-08-21T11:00:00Z",
        "github_reviewed_at": "2026-08-21T12:00:00Z",
        "nvd_published_at": None,
        "withdrawn_at": None,
        "identifiers": [
            {"type": "GHSA", "value": "GHSA-2345-6789-cfgh"},
            {"type": "CVE", "value": "CVE-2026-12345"},
        ],
        "references": ["https://example.com/advisory"],
        "cwes": [{"cwe_id": "CWE-79", "name": "Cross-site Scripting"}],
        "cvss_severities": {
            "cvss_v3": {
                "vector_string": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                "score": 9.8,
            },
        },
        "vulnerabilities": [
            {
                "package": {"ecosystem": "pip", "name": "example-package"},
                "vulnerable_version_range": ">= 1.0.0, < 1.2.0",
                "first_patched_version": "1.2.0",
                "vulnerable_functions": ["unsafe_load"],
            },
        ],
    }


def _composer() -> GhsaSilverRecordComposerV1:
    """Build the deterministic GHSA logical-record composer."""
    return GhsaSilverRecordComposerV1(
        core_transformer=GhsaAdvisoryCoreTransformer(),
        collections_transformer=GhsaAdvisoryCollectionsTransformer(),
        vulnerabilities_transformer=GhsaVulnerabilitiesTransformer(),
    )


def _object_list(value: object) -> list[object]:
    """Narrow one mapped row value to an object list."""
    assert isinstance(value, list)
    return cast(list[object], value)


def _object_dict(value: object) -> dict[str, object]:
    """Narrow one mapped row value to a string-keyed object."""
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def test_composes_one_logical_record_from_one_complete_advisory() -> None:
    """Bind core, collections, and package evidence to one observed version."""
    record = _composer().compose(_source_advisory())

    assert record.core.observed_version.ghsa_id == "GHSA-2345-6789-cfgh"
    assert record.collections.ghsa_id == "GHSA-2345-6789-cfgh"
    assert record.vulnerabilities.observed_version == record.core.observed_version
    assert len(record.vulnerabilities.entries) == 1


def test_maps_nested_collections_and_vulnerabilities_without_flattening() -> None:
    """Keep advisory-level and one-to-many package evidence in one nested row."""
    row = map_ghsa_silver_record_v1(_composer().compose(_source_advisory()))

    assert row["schema_version"] == 1
    assert row["ghsa_id"] == "GHSA-2345-6789-cfgh"
    assert row["cve_id"] == "CVE-2026-12345"
    assert row["vulnerability_entry_count"] == 1

    identifiers = _object_list(row["identifiers"])
    assert _object_dict(identifiers[0]) == {
        "type": "GHSA",
        "value": "GHSA-2345-6789-cfgh",
    }

    vulnerabilities = _object_list(row["vulnerabilities"])
    first = _object_dict(vulnerabilities[0])
    assert first["ecosystem"] == "pip"
    assert first["package_name"] == "example-package"
    assert first["vulnerable_version_range"] == ">= 1.0.0, < 1.2.0"
    assert first["first_patched_version"] == "1.2.0"
