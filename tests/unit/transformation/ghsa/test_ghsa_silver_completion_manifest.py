"""Tests for deterministic GHSA Silver COMPLETE evidence."""

from dataclasses import replace

import pytest

from opslens.transformation.ghsa.application.record_composer import (
    GhsaSilverRecordComposerV1,
)
from opslens.transformation.ghsa.completion.key_factory import (
    GhsaSilverKeyFactoryV1,
)
from opslens.transformation.ghsa.completion.manifest import (
    GhsaSilverCompletionManifestFactoryV1,
    GhsaSilverCompletionManifestSerializerV1,
)
from opslens.transformation.ghsa.completion.models import (
    GhsaSilverStoredContentObjectV1,
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
    GhsaSilverMaterializationV1,
    GhsaSilverMaterializerV1,
)
from opslens.transformation.ghsa.runtime.provenance import (
    GhsaBronzeAdvisoryOccurrenceV1,
)
from opslens.transformation.ghsa.runtime.record_processor import (
    GhsaSilverOccurrenceRecordV1,
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
    summary: str,
) -> dict[str, object]:
    """Return one complete reviewed advisory accepted by Silver v1."""
    return {
        "ghsa_id": ghsa_id,
        "cve_id": cve_id,
        "url": f"https://api.github.com/advisories/{ghsa_id}",
        "html_url": f"https://github.com/advisories/{ghsa_id}",
        "repository_advisory_url": None,
        "summary": summary,
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
        "references": [f"https://github.com/advisories/{ghsa_id}"],
        "cwes": [
            {
                "cwe_id": "CWE-79",
                "name": "Cross-site Scripting",
            },
        ],
        "cvss_severities": {
            "cvss_v3": {
                "vector_string": (
                    "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/"
                    "S:U/C:H/I:H/A:H"
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


def _binding(
    *,
    ghsa_id: str,
    cve_id: str,
    summary: str,
    source_index: int,
) -> GhsaSilverOccurrenceRecordV1:
    """Build one exact Bronze occurrence bound to one normalized record."""
    source = _source_advisory(
        ghsa_id=ghsa_id,
        cve_id=cve_id,
        summary=summary,
    )
    occurrence = GhsaBronzeAdvisoryOccurrenceV1.from_source(
        sync_id=SYNC_ID,
        attempt_id=ATTEMPT_ID,
        manifest_key=MANIFEST_KEY,
        manifest_version_id=MANIFEST_VERSION_ID,
        page_ordinal=1,
        page_key="bronze/ghsa/advisories/page=000001/response.json",
        page_version_id="page-version",
        source_index=source_index,
        source_advisory=source,
    )
    composer = GhsaSilverRecordComposerV1(
        core_transformer=GhsaAdvisoryCoreTransformer(),
        collections_transformer=GhsaAdvisoryCollectionsTransformer(),
        vulnerabilities_transformer=GhsaVulnerabilitiesTransformer(),
    )

    return GhsaSilverOccurrenceRecordV1(
        occurrence=occurrence,
        record=composer.compose(source),
    )


def _materialization() -> tuple[
    GhsaSilverMaterializationV1,
    tuple[GhsaSilverStoredContentObjectV1, ...],
]:
    """Build deterministic logical materialization plus exact stored objects."""
    first = _binding(
        ghsa_id="GHSA-2345-6789-cfgh",
        cve_id="CVE-2026-12345",
        summary="First advisory",
        source_index=0,
    )
    second = _binding(
        ghsa_id="GHSA-2345-6789-cfgj",
        cve_id="CVE-2026-54321",
        summary="Second advisory",
        source_index=1,
    )
    context = GhsaSilverAttemptContextV1(
        sync_id=SYNC_ID,
        attempt_id=ATTEMPT_ID,
        manifest_key=MANIFEST_KEY,
        manifest_version_id=MANIFEST_VERSION_ID,
    )
    materialization = GhsaSilverMaterializerV1(
        logical_hasher=GhsaLogicalRecordSetHasherV1(),
    ).materialize(
        context=context,
        bindings=(first, second),
    )
    serializer = GhsaSilverParquetSerializerV1()
    key_factory = GhsaSilverKeyFactoryV1()
    stored: list[GhsaSilverStoredContentObjectV1] = []

    for ordinal, binding in enumerate(materialization.bindings, start=1):
        artifact = serializer.serialize((binding.record,))
        observed = binding.occurrence.observed_version
        stored.append(
            GhsaSilverStoredContentObjectV1(
                key=key_factory.build_content_object_key(observed),
                version_id=f"silver-version-{ordinal}",
                observed_advisory_version_id=(
                    observed.observed_advisory_version_id
                ),
                ghsa_id=observed.ghsa_id,
                source_advisory_sha256=(
                    observed.source_advisory_sha256
                ),
                parquet_sha256=artifact.parquet_sha256,
                size_bytes=artifact.size_bytes,
                row_count=1,
            )
        )

    return materialization, tuple(stored)


def _factory() -> GhsaSilverCompletionManifestFactoryV1:
    """Build the deterministic completion manifest factory."""
    return GhsaSilverCompletionManifestFactoryV1(
        key_factory=GhsaSilverKeyFactoryV1(),
    )


def _serializer() -> GhsaSilverCompletionManifestSerializerV1:
    """Build the deterministic completion manifest serializer."""
    return GhsaSilverCompletionManifestSerializerV1(
        key_factory=GhsaSilverKeyFactoryV1(),
    )


def test_builds_completion_only_from_exact_stored_content() -> None:
    """Bind every logical occurrence to one exact authoritative object."""
    materialization, stored = _materialization()
    manifest = _factory().build(
        materialization=materialization,
        stored_objects=stored,
    )

    assert manifest.context.attempt_id == ATTEMPT_ID
    assert manifest.record_count == 2
    assert manifest.logical_record_set_sha256 == (
        materialization.logical_record_set_sha256
    )
    assert tuple(
        item.silver_object.version_id for item in manifest.occurrences
    ) == (
        "silver-version-1",
        "silver-version-2",
    )


def test_rejects_completion_when_one_content_object_is_missing() -> None:
    """Never mark an attempt COMPLETE when one logical record is not persisted."""
    materialization, stored = _materialization()

    with pytest.raises(
        ValueError,
        match="lacks persisted content",
    ):
        _factory().build(
            materialization=materialization,
            stored_objects=stored[:1],
        )


def test_rejects_completion_with_extra_persisted_content() -> None:
    """Reject persisted content that does not belong to the logical attempt."""
    materialization, stored = _materialization()
    extra = replace(
        stored[0],
        observed_advisory_version_id=(
            f"{stored[0].ghsa_id}@sha256:{'9' * 64}"
        ),
        source_advisory_sha256="9" * 64,
    )

    with pytest.raises(
        ValueError,
        match="not present in the logical materialization",
    ):
        _factory().build(
            materialization=materialization,
            stored_objects=stored + (extra,),
        )


def test_rejects_completion_with_wrong_deterministic_content_key() -> None:
    """Require content-addressed storage coordinates to match logical identity."""
    materialization, stored = _materialization()
    wrong = replace(
        stored[0],
        key="silver/ghsa/advisory_versions/wrong.parquet",
    )

    with pytest.raises(
        ValueError,
        match="stored content key does not match",
    ):
        _factory().build(
            materialization=materialization,
            stored_objects=(wrong, stored[1]),
        )


def test_serializes_canonical_attempt_completion_evidence() -> None:
    """Serialize Bronze provenance and exact Silver object versions canonically."""
    materialization, stored = _materialization()
    manifest = _factory().build(
        materialization=materialization,
        stored_objects=stored,
    )
    artifact = _serializer().serialize(manifest)
    text = artifact.manifest_bytes.decode("utf-8")

    assert artifact.key == (
        "silver/ghsa/completions/"
        "schema_version=1/"
        f"sync_id={SYNC_ID}/"
        f"attempt_id={ATTEMPT_ID}/"
        "manifest.json"
    )
    assert text.endswith("\n")
    assert '"completion_status":"complete"' in text
    assert '"dataset":"ghsa_advisory_versions"' in text
    assert '"record_count":2' in text
    assert (
        f'"attempt_occurrence_id":"{ATTEMPT_ID}/'
        'page:000001/item:000"'
    ) in text
    assert '"version_id":"silver-version-1"' in text
    assert f'"version_id":"{MANIFEST_VERSION_ID}"' in text


def test_completion_serialization_is_deterministic() -> None:
    """Produce identical COMPLETE bytes from identical logical evidence."""
    materialization, stored = _materialization()
    manifest = _factory().build(
        materialization=materialization,
        stored_objects=tuple(reversed(stored)),
    )

    first = _serializer().serialize(manifest)
    second = _serializer().serialize(manifest)

    assert first.key == second.key
    assert first.manifest_bytes == second.manifest_bytes
    assert first.manifest_sha256 == second.manifest_sha256


def test_zero_result_attempt_can_complete_without_content_objects() -> None:
    """Preserve a valid zero-result attempt as COMPLETE evidence."""
    context = GhsaSilverAttemptContextV1(
        sync_id=SYNC_ID,
        attempt_id=ATTEMPT_ID,
        manifest_key=MANIFEST_KEY,
        manifest_version_id=MANIFEST_VERSION_ID,
    )
    materialization = GhsaSilverMaterializerV1(
        logical_hasher=GhsaLogicalRecordSetHasherV1(),
    ).materialize(
        context=context,
        bindings=(),
    )
    manifest = _factory().build(
        materialization=materialization,
        stored_objects=(),
    )
    artifact = _serializer().serialize(manifest)

    assert manifest.record_count == 0
    assert manifest.occurrences == ()
    assert '"record_count":0' in artifact.manifest_bytes.decode("utf-8")
