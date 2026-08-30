"""Tests for GHSA Silver immutable persistence orchestration."""

from opslens.transformation.ghsa.application.record_composer import (
    GhsaSilverRecordComposerV1,
)
from opslens.transformation.ghsa.completion.key_factory import (
    GhsaSilverKeyFactoryV1,
)
from opslens.transformation.ghsa.completion.manifest import (
    GhsaSilverCompletionArtifactV1,
    GhsaSilverCompletionManifestFactoryV1,
    GhsaSilverCompletionManifestSerializerV1,
)
from opslens.transformation.ghsa.completion.models import (
    GhsaSilverStoredCompletionV1,
    GhsaSilverStoredContentObjectV1,
)
from opslens.transformation.ghsa.completion.preparation import (
    GhsaSilverContentPreparerV1,
    GhsaSilverPreparedContentObjectV1,
)
from opslens.transformation.ghsa.completion.service import (
    GhsaSilverPersistenceServiceV1,
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


class RecordingContentRepository:
    """Persist prepared objects in memory and record ordering."""

    def __init__(
        self,
        events: list[str],
        *,
        fail_on_call: int | None = None,
    ) -> None:
        """Initialize deterministic repository behavior."""
        self._events = events
        self._fail_on_call = fail_on_call
        self.calls = 0

    def put_if_absent(
        self,
        prepared: GhsaSilverPreparedContentObjectV1,
    ) -> GhsaSilverStoredContentObjectV1:
        """Return exact stored evidence or inject one configured failure."""
        self.calls += 1
        self._events.append(
            f"content:{prepared.observed_advisory_version_id}"
        )

        if self._fail_on_call == self.calls:
            raise RuntimeError("content persistence failed")

        artifact = prepared.parquet_artifact

        return GhsaSilverStoredContentObjectV1(
            key=prepared.key,
            version_id=f"content-version-{self.calls}",
            observed_advisory_version_id=(
                prepared.observed_advisory_version_id
            ),
            ghsa_id=prepared.ghsa_id,
            source_advisory_sha256=prepared.source_advisory_sha256,
            parquet_sha256=artifact.parquet_sha256,
            size_bytes=artifact.size_bytes,
            row_count=artifact.row_count,
        )


class RecordingCompletionRepository:
    """Persist COMPLETE in memory and record publication ordering."""

    def __init__(self, events: list[str]) -> None:
        """Initialize completion repository state."""
        self._events = events
        self.calls: list[GhsaSilverCompletionArtifactV1] = []

    def put_if_absent(
        self,
        artifact: GhsaSilverCompletionArtifactV1,
    ) -> GhsaSilverStoredCompletionV1:
        """Record COMPLETE publication and return exact stored evidence."""
        self._events.append("complete")
        self.calls.append(artifact)

        return GhsaSilverStoredCompletionV1(
            key=artifact.key,
            version_id="complete-version",
            sha256=artifact.manifest_sha256,
            size_bytes=len(artifact.manifest_bytes),
        )


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
        manifest_key="bronze/ghsa/advisories/manifest.json",
        manifest_version_id="manifest-version",
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


def _materialization(
    *,
    record_count: int = 2,
) -> GhsaSilverMaterializationV1:
    """Build one deterministic logical attempt with zero or two records."""
    context = GhsaSilverAttemptContextV1(
        sync_id=SYNC_ID,
        attempt_id=ATTEMPT_ID,
        manifest_key="bronze/ghsa/advisories/manifest.json",
        manifest_version_id="manifest-version",
    )
    bindings: tuple[GhsaSilverOccurrenceRecordV1, ...]

    if record_count == 0:
        bindings = ()
    else:
        bindings = (
            _binding(
                ghsa_id="GHSA-2345-6789-cfgh",
                cve_id="CVE-2026-12345",
                summary="First advisory",
                source_index=0,
            ),
            _binding(
                ghsa_id="GHSA-2345-6789-cfgj",
                cve_id="CVE-2026-54321",
                summary="Second advisory",
                source_index=1,
            ),
        )

    return GhsaSilverMaterializerV1(
        logical_hasher=GhsaLogicalRecordSetHasherV1(),
    ).materialize(
        context=context,
        bindings=bindings,
    )


def _service(
    *,
    content_repository: RecordingContentRepository,
    completion_repository: RecordingCompletionRepository,
) -> GhsaSilverPersistenceServiceV1:
    """Build deterministic persistence orchestration with in-memory ports."""
    key_factory = GhsaSilverKeyFactoryV1()

    return GhsaSilverPersistenceServiceV1(
        content_preparer=GhsaSilverContentPreparerV1(
            key_factory=key_factory,
            parquet_serializer=GhsaSilverParquetSerializerV1(),
        ),
        content_repository=content_repository,
        manifest_factory=GhsaSilverCompletionManifestFactoryV1(
            key_factory=key_factory,
        ),
        manifest_serializer=GhsaSilverCompletionManifestSerializerV1(
            key_factory=key_factory,
        ),
        completion_repository=completion_repository,
    )


def test_persists_all_content_before_publishing_complete() -> None:
    """Publish COMPLETE only after every authoritative content object exists."""
    events: list[str] = []
    content_repository = RecordingContentRepository(events)
    completion_repository = RecordingCompletionRepository(events)
    materialization = _materialization()

    result = _service(
        content_repository=content_repository,
        completion_repository=completion_repository,
    ).persist(materialization)

    assert result.record_count == 2
    assert len(result.stored_content_objects) == 2
    assert result.stored_completion.version_id == "complete-version"
    assert events[-1] == "complete"
    assert events[:2] == [
        (
            "content:"
            f"{materialization.bindings[0].observed_advisory_version_id}"
        ),
        (
            "content:"
            f"{materialization.bindings[1].observed_advisory_version_id}"
        ),
    ]
    assert len(completion_repository.calls) == 1
    assert completion_repository.calls[0].manifest.record_count == 2


def test_content_failure_prevents_complete_publication() -> None:
    """Never publish COMPLETE after a partial content persistence failure."""
    events: list[str] = []
    content_repository = RecordingContentRepository(
        events,
        fail_on_call=2,
    )
    completion_repository = RecordingCompletionRepository(events)

    try:
        _service(
            content_repository=content_repository,
            completion_repository=completion_repository,
        ).persist(_materialization())
    except RuntimeError as exc:
        assert str(exc) == "content persistence failed"
    else:
        raise AssertionError("Expected injected content persistence failure.")

    assert "complete" not in events
    assert completion_repository.calls == []


def test_zero_result_attempt_publishes_complete_without_content() -> None:
    """Publish COMPLETE for valid zero-result attempts without fake Parquet."""
    events: list[str] = []
    content_repository = RecordingContentRepository(events)
    completion_repository = RecordingCompletionRepository(events)

    result = _service(
        content_repository=content_repository,
        completion_repository=completion_repository,
    ).persist(
        _materialization(record_count=0)
    )

    assert result.record_count == 0
    assert result.stored_content_objects == ()
    assert events == ["complete"]
    assert completion_repository.calls[0].manifest.record_count == 0
