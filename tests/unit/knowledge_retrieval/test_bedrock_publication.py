"""Tests for the deterministic Gate 7.3 Bedrock publication projection."""

from __future__ import annotations

import json
from typing import cast

import pytest

from opslens.knowledge_retrieval.adapters.http_source import AcquiredKnowledgeSource
from opslens.knowledge_retrieval.application.bedrock_publication import (
    BEDROCK_PUBLICATION_PREFIX,
    MAX_BEDROCK_CUSTOM_METADATA_BYTES,
    BedrockPublicationError,
    build_bedrock_publication_plan,
    serialize_bedrock_publication_plan,
)
from opslens.knowledge_retrieval.application.corpus_manifest import (
    build_corpus_manifest,
    serialize_corpus_manifest,
)
from opslens.knowledge_retrieval.application.corpus_materialization import (
    materialize_knowledge_document,
)
from opslens.knowledge_retrieval.domain import (
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
    """Return one immutable source descriptor for offline publication tests."""
    return KnowledgeSourceDescriptor(
        document_id="knowledge-doc:test-publication:v1",
        source_id="example:test-publication",
        source_type=KnowledgeSourceType.SECURITY_GUIDANCE,
        canonical_uri="https://example.com/security/guide/",
        upstream_repository="example/security-guide",
        upstream_commit_sha="b" * 40,
        upstream_path="guide.md",
        expected_chunk_ids=(
            "knowledge-chunk:test-publication:first:v1",
            "knowledge-chunk:test-publication:second:v1",
        ),
    )


def _registry() -> KnowledgeSourceRegistry:
    """Return one source registry aligned with the test specification."""
    return KnowledgeSourceRegistry(
        registry_id=SOURCE_REGISTRY_ID,
        entries=(_descriptor(),),
    )


def _spec(*, title: str = "Security Guide") -> KnowledgeCorpusSpec:
    """Return one two-chunk deterministic corpus specification."""
    return KnowledgeCorpusSpec(
        spec_id=CORPUS_SPEC_ID,
        source_registry_id=SOURCE_REGISTRY_ID,
        documents=(
            DocumentMaterializationSpec(
                document_id="knowledge-doc:test-publication:v1",
                title=title,
                selections=(
                    ChunkSelectionSpec(
                        chunk_id="knowledge-chunk:test-publication:first:v1",
                        section_path=("Guide", "First"),
                        start_marker="## First",
                        end_marker="## Second",
                    ),
                    ChunkSelectionSpec(
                        chunk_id="knowledge-chunk:test-publication:second:v1",
                        section_path=("Guide", "Second"),
                        start_marker="## Second",
                        end_marker="## End",
                    ),
                ),
            ),
        ),
    )


def _materialized(
    *,
    title: str = "Security Guide",
    first_text: str = "alpha",
) -> MaterializedKnowledgeDocument:
    """Materialize two canonical chunks entirely offline."""
    spec = _spec(title=title)
    body = (
        f"# Guide\n\n## First\n{first_text}\n\n"
        "## Second\nbeta\n\n## End\nignored\n"
    ).encode()
    acquired = AcquiredKnowledgeSource.from_body(
        descriptor=_descriptor(),
        body=body,
        content_type="text/plain; charset=utf-8",
    )
    return materialize_knowledge_document(acquired, spec.documents[0])


def _expected_manifest_text(
    *,
    title: str = "Security Guide",
    first_text: str = "alpha",
) -> str:
    """Return canonical checked-manifest bytes for one offline replay."""
    registry = _registry()
    spec = _spec(title=title)
    materialized = _materialized(title=title, first_text=first_text)
    return serialize_corpus_manifest(
        build_corpus_manifest(registry, spec, (materialized,))
    )


def test_publication_plan_preserves_exact_chunks_and_sidecars() -> None:
    """Each canonical chunk becomes exactly one hash-addressed text object and sidecar."""
    registry = _registry()
    spec = _spec()
    materialized = _materialized()
    plan = build_bedrock_publication_plan(
        registry,
        spec,
        (materialized,),
        expected_manifest_text=_expected_manifest_text(),
    )

    assert plan.prefix == BEDROCK_PUBLICATION_PREFIX
    assert len(plan.objects) == 2
    assert [item.chunk_id for item in plan.objects] == [
        "knowledge-chunk:test-publication:first:v1",
        "knowledge-chunk:test-publication:second:v1",
    ]
    for item, chunk in zip(plan.objects, materialized.chunks, strict=True):
        assert item.content_text == chunk.text
        assert item.content_sha256 == chunk.chunk_content_sha256
        assert item.content_key == (
            f"{BEDROCK_PUBLICATION_PREFIX}/chunks/{chunk.chunk_content_sha256}.txt"
        )
        assert item.metadata_key == f"{item.content_key}.metadata.json"
        assert item.custom_metadata_byte_count <= MAX_BEDROCK_CUSTOM_METADATA_BYTES

        parsed = cast(dict[str, object], json.loads(item.metadata_json))
        attributes = cast(dict[str, dict[str, object]], parsed["metadataAttributes"])
        assert set(attributes) == {
            "canonical_uri",
            "content_sha256",
            "document_id",
            "section_path",
            "source_id",
            "source_type",
            "title",
        }
        assert all(attribute["includeForEmbedding"] is False for attribute in attributes.values())
        section_value = cast(dict[str, object], attributes["section_path"]["value"])
        assert section_value["type"] == "STRING_LIST"
        assert section_value["stringListValue"] == list(chunk.section_path)


def test_hash_only_serialization_is_deterministic_and_omits_chunk_text() -> None:
    """Publication evidence can be persisted later without vendoring third-party text."""
    registry = _registry()
    spec = _spec()
    materialized = _materialized()
    expected_manifest = _expected_manifest_text()

    first = build_bedrock_publication_plan(
        registry,
        spec,
        (materialized,),
        expected_manifest_text=expected_manifest,
    )
    second = build_bedrock_publication_plan(
        registry,
        spec,
        (materialized,),
        expected_manifest_text=expected_manifest,
    )
    serialized = serialize_bedrock_publication_plan(first)

    assert first == second
    assert serialized == serialize_bedrock_publication_plan(second)
    assert serialized.endswith("\n")
    assert "alpha" not in serialized
    assert "beta" not in serialized
    assert "metadataAttributes" not in serialized


def test_publication_fails_before_projection_when_manifest_does_not_match() -> None:
    """Fresh source drift cannot be published against stale checked evidence."""
    registry = _registry()
    spec = _spec()
    drifted = _materialized(first_text="changed upstream")

    with pytest.raises(BedrockPublicationError, match="does not exactly match"):
        build_bedrock_publication_plan(
            registry,
            spec,
            (drifted,),
            expected_manifest_text=_expected_manifest_text(first_text="alpha"),
        )


def test_publication_rejects_metadata_that_exceeds_s3_vectors_budget() -> None:
    """Oversized custom metadata fails locally before any future S3 write."""
    title = "x" * 1_100
    registry = _registry()
    spec = _spec(title=title)
    materialized = _materialized(title=title)

    with pytest.raises(BedrockPublicationError, match="1 KB limit"):
        build_bedrock_publication_plan(
            registry,
            spec,
            (materialized,),
            expected_manifest_text=_expected_manifest_text(title=title),
        )
