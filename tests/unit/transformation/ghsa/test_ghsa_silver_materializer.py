"""Tests for deterministic GHSA Silver in-memory materialization."""

import hashlib
import json

import pytest

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
from opslens.transformation.ghsa.runtime.materializer import (
    GhsaSilverAttemptContextV1,
    GhsaSilverMaterializerV1,
)
from opslens.transformation.ghsa.runtime.page_processor import (
    GhsaBronzePageEvidenceV1,
    GhsaBronzePageProcessorV1,
)
from opslens.transformation.ghsa.runtime.record_processor import (
    GhsaSilverOccurrenceRecordV1,
    GhsaSilverRecordProcessorV1,
)
from opslens.transformation.ghsa.serialization.logical_hash import (
    GhsaLogicalRecordSetHasherV1,
)
from opslens.transformation.ghsa.serialization.parquet import (
    GhsaSilverParquetSerializerV1,
)

SYNC_ID = "1" * 64
ATTEMPT_ID = "2" * 64
MANIFEST_KEY = "bronze/ghsa/advisories/manifest.json"
MANIFEST_VERSION_ID = "manifest-version"


def _source_advisory(
    *,
    ghsa_id: str,
    cve_id: str,
) -> dict[str, object]:
    """Return one complete reviewed advisory accepted by Silver v1."""
    return {
        "ghsa_id": ghsa_id,
        "cve_id": cve_id,
        "url": f"https://api.github.com/advisories/{ghsa_id}",
        "html_url": f"https://github.com/advisories/{ghsa_id}",
        "repository_advisory_url": None,
        "summary": f"Example advisory {ghsa_id}",
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
            {"type": "GHSA", "value": ghsa_id},
            {"type": "CVE", "value": cve_id},
        ],
        "references": [
            f"https://github.com/advisories/{ghsa_id}",
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
                "vulnerable_functions": ["unsafe_load"],
            },
        ],
    }


def _record_processor() -> GhsaSilverRecordProcessorV1:
    """Build the deterministic Bronze-to-Silver record processor."""
    composer = GhsaSilverRecordComposerV1(
        core_transformer=GhsaAdvisoryCoreTransformer(),
        collections_transformer=GhsaAdvisoryCollectionsTransformer(),
        vulnerabilities_transformer=GhsaVulnerabilitiesTransformer(),
    )

    return GhsaSilverRecordProcessorV1(
        composer=composer,
    )


def _bindings() -> tuple[GhsaSilverOccurrenceRecordV1, ...]:
    """Return two verified Bronze-to-Silver bindings."""
    advisories = [
        _source_advisory(
            ghsa_id="GHSA-2345-6789-cfgh",
            cve_id="CVE-2026-12345",
        ),
        _source_advisory(
            ghsa_id="GHSA-2345-6789-cfgj",
            cve_id="CVE-2026-54321",
        ),
    ]

    page_bytes = json.dumps(
        advisories,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    evidence = GhsaBronzePageEvidenceV1(
        sync_id=SYNC_ID,
        attempt_id=ATTEMPT_ID,
        manifest_key=MANIFEST_KEY,
        manifest_version_id=MANIFEST_VERSION_ID,
        page_ordinal=1,
        page_key="bronze/ghsa/page=000001/response.json",
        page_version_id="page-version",
        expected_size_bytes=len(page_bytes),
        expected_sha256=hashlib.sha256(page_bytes).hexdigest(),
    )

    verified = GhsaBronzePageProcessorV1().process(
        evidence=evidence,
        page_bytes=page_bytes,
    )

    return _record_processor().process_page(verified)


def _context() -> GhsaSilverAttemptContextV1:
    """Return the exact Bronze attempt context."""
    return GhsaSilverAttemptContextV1(
        sync_id=SYNC_ID,
        attempt_id=ATTEMPT_ID,
        manifest_key=MANIFEST_KEY,
        manifest_version_id=MANIFEST_VERSION_ID,
    )


def _materializer() -> GhsaSilverMaterializerV1:
    """Build the deterministic in-memory Silver materializer."""
    return GhsaSilverMaterializerV1(
        logical_hasher=GhsaLogicalRecordSetHasherV1(),
        parquet_serializer=GhsaSilverParquetSerializerV1(),
    )


def test_materializes_logical_hash_and_parquet_artifact() -> None:
    """Create deterministic logical and physical Silver evidence."""
    result = _materializer().materialize(
        context=_context(),
        bindings=_bindings(),
    )

    assert result.record_count == 2
    assert len(result.logical_record_set_sha256) == 64
    assert result.parquet_artifact is not None
    assert result.parquet_artifact.row_count == 2
    assert result.parquet_artifact.parquet_bytes.startswith(b"PAR1")


def test_materialization_is_independent_of_binding_input_order() -> None:
    """Keep logical and Parquet identity independent of caller ordering."""
    bindings = _bindings()

    forward = _materializer().materialize(
        context=_context(),
        bindings=bindings,
    )
    reverse = _materializer().materialize(
        context=_context(),
        bindings=tuple(reversed(bindings)),
    )

    assert (
        forward.logical_record_set_sha256
        == reverse.logical_record_set_sha256
    )

    assert forward.parquet_artifact is not None
    assert reverse.parquet_artifact is not None

    assert (
        forward.parquet_artifact.parquet_sha256
        == reverse.parquet_artifact.parquet_sha256
    )

    assert (
        forward.parquet_artifact.parquet_bytes
        == reverse.parquet_artifact.parquet_bytes
    )

    assert forward.bindings == reverse.bindings


def test_rejects_binding_from_different_attempt() -> None:
    """Reject records not belonging to the authorized Bronze attempt."""
    bindings = _bindings()

    wrong_context = GhsaSilverAttemptContextV1(
        sync_id=SYNC_ID,
        attempt_id="9" * 64,
        manifest_key=MANIFEST_KEY,
        manifest_version_id=MANIFEST_VERSION_ID,
    )

    with pytest.raises(ValueError, match="attempt_id"):
        _materializer().materialize(
            context=wrong_context,
            bindings=bindings,
        )


def test_rejects_duplicate_physical_occurrence() -> None:
    """Reject duplicate physical advisory provenance."""
    binding = _bindings()[0]

    with pytest.raises(
        ValueError,
        match="duplicate physical occurrence",
    ):
        _materializer().materialize(
            context=_context(),
            bindings=(binding, binding),
        )


def test_empty_attempt_has_logical_identity_without_parquet() -> None:
    """Represent a valid zero-result attempt without fabricating Parquet."""
    result = _materializer().materialize(
        context=_context(),
        bindings=(),
    )

    assert result.record_count == 0
    assert len(result.logical_record_set_sha256) == 64
    assert result.parquet_artifact is None
