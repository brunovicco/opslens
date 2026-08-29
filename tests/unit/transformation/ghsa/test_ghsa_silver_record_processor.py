"""Tests for GHSA verified Bronze-to-Silver record composition."""

import hashlib
import json
from collections.abc import Sequence

import pytest

from opslens.transformation.ghsa.application.record_composer import (
    GhsaSilverRecordComposerV1,
)
from opslens.transformation.ghsa.domain.collections_transformer import (
    GhsaAdvisoryCollectionsTransformer,
)
from opslens.transformation.ghsa.domain.errors import (
    InvalidGhsaAdvisoryCoreRecordError,
)
from opslens.transformation.ghsa.domain.transformer import (
    GhsaAdvisoryCoreTransformer,
)
from opslens.transformation.ghsa.domain.vulnerabilities_transformer import (
    GhsaVulnerabilitiesTransformer,
)
from opslens.transformation.ghsa.runtime.page_processor import (
    GhsaBronzePageEvidenceV1,
    GhsaBronzePageProcessorV1,
    GhsaVerifiedBronzePageV1,
)
from opslens.transformation.ghsa.runtime.record_processor import (
    GhsaSilverOccurrenceRecordV1,
    GhsaSilverRecordProcessorV1,
)

SYNC_ID = "1" * 64
ATTEMPT_ID = "2" * 64


def _source_advisory() -> dict[str, object]:
    """Return one complete reviewed advisory accepted by Silver v1."""
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
            {
                "type": "GHSA",
                "value": "GHSA-2345-6789-cfgh",
            },
            {
                "type": "CVE",
                "value": "CVE-2026-12345",
            },
        ],
        "references": [
            "https://example.com/advisory",
        ],
        "cwes": [
            {
                "cwe_id": "CWE-79",
                "name": "Cross-site Scripting",
            },
        ],
        "cvss_severities": {
            "cvss_v3": {
                "vector_string": (
                    "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
                ),
                "score": 9.8,
            },
        },
        "vulnerabilities": [
            {
                "package": {
                    "ecosystem": "pip",
                    "name": "example-package",
                },
                "vulnerable_version_range": ">= 1.0.0, < 1.2.0",
                "first_patched_version": "1.2.0",
                "vulnerable_functions": [
                    "unsafe_load",
                ],
            },
        ],
    }


def _composer() -> GhsaSilverRecordComposerV1:
    """Build the deterministic Silver v1 composer."""
    return GhsaSilverRecordComposerV1(
        core_transformer=GhsaAdvisoryCoreTransformer(),
        collections_transformer=GhsaAdvisoryCollectionsTransformer(),
        vulnerabilities_transformer=GhsaVulnerabilitiesTransformer(),
    )


def _record_processor() -> GhsaSilverRecordProcessorV1:
    """Build the verified Bronze-to-Silver record processor."""
    return GhsaSilverRecordProcessorV1(
        composer=_composer(),
    )


def _verified_page(
    advisories: Sequence[object],
) -> GhsaVerifiedBronzePageV1:
    """Build one exact verified Bronze page from supplied source objects."""
    page_bytes = json.dumps(
        advisories,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    evidence = GhsaBronzePageEvidenceV1(
        sync_id=SYNC_ID,
        attempt_id=ATTEMPT_ID,
        manifest_key="bronze/ghsa/advisories/manifest.json",
        manifest_version_id="manifest-version",
        page_ordinal=1,
        page_key=(
            "bronze/ghsa/advisories/"
            "page=000001/response.json"
        ),
        page_version_id="page-version",
        expected_size_bytes=len(page_bytes),
        expected_sha256=hashlib.sha256(page_bytes).hexdigest(),
    )

    return GhsaBronzePageProcessorV1().process(
        evidence=evidence,
        page_bytes=page_bytes,
    )


def test_composes_silver_record_from_verified_bronze_occurrence() -> None:
    """Compose one Silver record from one physically verified occurrence."""
    verified_page = _verified_page([_source_advisory()])

    records = _record_processor().process_page(verified_page)

    assert len(records) == 1

    bound = records[0]

    assert (
        bound.record.core.observed_version
        == bound.occurrence.observed_version
    )

    assert (
        bound.observed_advisory_version_id
        == bound.occurrence.observed_advisory_version_id
    )

    assert (
        bound.record.core.observed_version.ghsa_id
        == "GHSA-2345-6789-cfgh"
    )

    assert len(bound.record.vulnerabilities.entries) == 1

    vulnerability = bound.record.vulnerabilities.entries[0]

    assert vulnerability.vulnerable_version_range == (
        ">= 1.0.0, < 1.2.0"
    )
    assert vulnerability.first_patched_version == "1.2.0"


def test_preserves_exact_bronze_physical_provenance() -> None:
    """Keep physical Bronze coordinates attached to the Silver record."""
    verified_page = _verified_page([_source_advisory()])

    bound = _record_processor().process_page(verified_page)[0]

    assert bound.occurrence.sync_id == SYNC_ID
    assert bound.occurrence.attempt_id == ATTEMPT_ID
    assert bound.occurrence.source_index == 0

    assert bound.occurrence.physical_occurrence_id == (
        f"{ATTEMPT_ID}/page:000001/item:000"
    )


def test_rejects_incomplete_source_during_silver_composition() -> None:
    """Fail closed when verified Bronze content violates Silver v1."""
    incomplete: dict[str, object] = {
        "ghsa_id": "GHSA-2345-6789-cfgh",
        "type": "reviewed",
    }

    verified_page = _verified_page([incomplete])

    with pytest.raises(
        InvalidGhsaAdvisoryCoreRecordError,
        match="missing required core fields",
    ):
        _record_processor().process_page(verified_page)


def test_empty_verified_page_produces_no_silver_records() -> None:
    """Keep an exact empty Bronze page as an empty Silver record set."""
    verified_page = _verified_page([])

    records = _record_processor().process_page(verified_page)

    assert records == ()


def test_rejects_cross_binding_between_occurrence_and_silver_record() -> None:
    """Reject a Silver record belonging to different advisory content."""
    first_source = _source_advisory()

    second_source = {
        **_source_advisory(),
        "summary": "Different exact advisory content",
    }

    first_page = _verified_page([first_source])
    second_page = _verified_page([second_source])

    first_bound = _record_processor().process_page(first_page)[0]
    second_bound = _record_processor().process_page(second_page)[0]

    assert (
        first_bound.occurrence.observed_advisory_version_id
        != second_bound.occurrence.observed_advisory_version_id
    )

    with pytest.raises(
        ValueError,
        match="does not match the exact Bronze advisory content version",
    ):
        GhsaSilverOccurrenceRecordV1(
            occurrence=first_bound.occurrence,
            record=second_bound.record,
        )
