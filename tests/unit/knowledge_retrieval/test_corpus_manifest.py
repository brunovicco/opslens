"""Tests for deterministic hash-only Gate 7.2 corpus manifests."""

from __future__ import annotations

import json
from typing import cast

import pytest

from opslens.knowledge_retrieval.adapters.http_source import AcquiredKnowledgeSource
from opslens.knowledge_retrieval.application.corpus_manifest import (
    CorpusManifestError,
    CorpusManifestMismatchError,
    build_corpus_manifest,
    serialize_corpus_manifest,
    verify_corpus_manifest,
)
from opslens.knowledge_retrieval.application.corpus_materialization import (
    materialize_knowledge_document,
)
from opslens.knowledge_retrieval.domain import (
    CORPUS_MANIFEST_ID,
    CORPUS_SPEC_ID,
    SOURCE_REGISTRY_ID,
    ChunkSelectionSpec,
    DocumentMaterializationSpec,
    KnowledgeCorpusSpec,
    KnowledgeSourceDescriptor,
    KnowledgeSourceRegistry,
    KnowledgeSourceType,
    MaterializedKnowledgeDocument,
)


def _descriptor() -> KnowledgeSourceDescriptor:
    """Return one immutable source pin for manifest tests."""
    return KnowledgeSourceDescriptor(
        document_id="knowledge-doc:test:v1",
        source_id="example:test",
        source_type=KnowledgeSourceType.MAINTAINER_DOCUMENTATION,
        canonical_uri="https://example.com/guide/",
        upstream_repository="example/docs",
        upstream_commit_sha="a" * 40,
        upstream_path="guide.md",
        expected_chunk_ids=(
            "knowledge-chunk:test:first:v1",
            "knowledge-chunk:test:second:v1",
        ),
    )


def _registry() -> KnowledgeSourceRegistry:
    """Return one source registry aligned with the test corpus spec."""
    return KnowledgeSourceRegistry(
        registry_id=SOURCE_REGISTRY_ID,
        entries=(_descriptor(),),
    )


def _spec() -> KnowledgeCorpusSpec:
    """Return one deterministic two-chunk corpus spec."""
    document = DocumentMaterializationSpec(
        document_id="knowledge-doc:test:v1",
        title="Test Guide",
        selections=(
            ChunkSelectionSpec(
                chunk_id="knowledge-chunk:test:first:v1",
                section_path=("Guide", "First"),
                start_marker="## First",
                end_marker="## Second",
            ),
            ChunkSelectionSpec(
                chunk_id="knowledge-chunk:test:second:v1",
                section_path=("Guide", "Second"),
                start_marker="## Second",
                end_marker="## End",
            ),
        ),
    )
    return KnowledgeCorpusSpec(
        spec_id=CORPUS_SPEC_ID,
        source_registry_id=SOURCE_REGISTRY_ID,
        documents=(document,),
    )


def _materialized(*, first_text: str = "alpha") -> MaterializedKnowledgeDocument:
    """Materialize inert source bytes without any network dependency."""
    body = (
        f"# Guide\n\n## First\n{first_text}\n\n"
        "## Second\nbeta\n\n## End\nignored\n"
    ).encode()
    acquired = AcquiredKnowledgeSource.from_body(
        descriptor=_descriptor(),
        body=body,
        content_type="text/plain; charset=utf-8",
    )
    return materialize_knowledge_document(acquired, _spec().documents[0])


def test_manifest_contains_hash_evidence_and_no_third_party_text() -> None:
    """The checked evidence is sufficient for replay verification without vendored source text."""
    manifest = build_corpus_manifest(_registry(), _spec(), (_materialized(),))
    serialized = serialize_corpus_manifest(manifest)
    parsed = cast(dict[str, object], json.loads(serialized))
    documents = cast(list[dict[str, object]], parsed["documents"])
    document = documents[0]
    chunks = cast(list[dict[str, object]], document["chunks"])

    assert manifest.manifest_id == CORPUS_MANIFEST_ID
    assert serialized.endswith("\n")
    assert "alpha" not in serialized
    assert "beta" not in serialized
    assert "generated_at" not in serialized
    assert cast(int, document["source_byte_count"]) > cast(
        int,
        document["content_utf8_byte_count"],
    )
    assert len(cast(str, document["source_bytes_sha256"])) == 64
    assert len(cast(str, document["content_sha256"])) == 64
    assert [cast(str, chunk["chunk_id"]) for chunk in chunks] == [
        "knowledge-chunk:test:first:v1",
        "knowledge-chunk:test:second:v1",
    ]
    assert all(len(cast(str, chunk["chunk_content_sha256"])) == 64 for chunk in chunks)


def test_manifest_serialization_is_byte_for_byte_deterministic() -> None:
    """Identical pins and source bytes produce identical JSON bytes with no runtime metadata."""
    first = build_corpus_manifest(_registry(), _spec(), (_materialized(),))
    second = build_corpus_manifest(_registry(), _spec(), (_materialized(),))

    assert first == second
    assert serialize_corpus_manifest(first) == serialize_corpus_manifest(second)


def test_manifest_verification_detects_source_and_canonical_content_drift() -> None:
    """A replay with changed admitted content fails closed even when markers still match."""
    registry = _registry()
    spec = _spec()
    expected_materialized = _materialized(first_text="alpha")
    expected = build_corpus_manifest(registry, spec, (expected_materialized,))
    drifted_materialized = _materialized(first_text="alpha changed upstream")

    with pytest.raises(CorpusManifestMismatchError, match="does not match"):
        verify_corpus_manifest(
            expected,
            registry,
            spec,
            (drifted_materialized,),
        )


def test_manifest_builder_rejects_incomplete_materialization() -> None:
    """Partial corpus evidence cannot be admitted as a complete v1 manifest."""
    with pytest.raises(CorpusManifestError, match="equal lengths"):
        build_corpus_manifest(_registry(), _spec(), ())
