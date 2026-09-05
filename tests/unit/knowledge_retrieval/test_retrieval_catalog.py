"""Tests for deterministic Gate 7.4 checked-corpus retrieval lookup."""

from __future__ import annotations

import pytest

from opslens.knowledge_retrieval.application.bedrock_publication import (
    BEDROCK_PUBLICATION_PREFIX,
)
from opslens.knowledge_retrieval.application.retrieval_catalog import (
    CanonicalRetrievalCatalog,
    CanonicalRetrievalChunk,
    RetrievalCatalogError,
    build_retrieval_catalog,
)
from opslens.knowledge_retrieval.domain import (
    CORPUS_MANIFEST_ID,
    CORPUS_SPEC_ID,
    SOURCE_REGISTRY_ID,
    CorpusChunkManifestEntry,
    CorpusDocumentManifestEntry,
    KnowledgeCorpusManifest,
    KnowledgeSourceType,
)

_CHUNK_DIGEST = "a" * 64
_DOCUMENT_DIGEST = "b" * 64


def _manifest() -> KnowledgeCorpusManifest:
    """Return one minimal typed checked manifest for lookup tests."""
    return KnowledgeCorpusManifest(
        manifest_id=CORPUS_MANIFEST_ID,
        source_registry_id=SOURCE_REGISTRY_ID,
        corpus_spec_id=CORPUS_SPEC_ID,
        documents=(
            CorpusDocumentManifestEntry(
                document_id="knowledge-doc:test-retrieve:v1",
                source_id="example:test-retrieve",
                source_type=KnowledgeSourceType.SECURITY_GUIDANCE,
                canonical_uri="https://example.com/security/guide/",
                acquisition_uri=(
                    "https://raw.githubusercontent.com/example/security-guide/"
                    f"{'c' * 40}/guide.md"
                ),
                upstream_repository="example/security-guide",
                upstream_commit_sha="c" * 40,
                upstream_path="guide.md",
                source_byte_count=100,
                source_bytes_sha256="d" * 64,
                title="Security Guide",
                content_utf8_byte_count=50,
                content_sha256=_DOCUMENT_DIGEST,
                chunks=(
                    CorpusChunkManifestEntry(
                        chunk_id="knowledge-chunk:test-retrieve:first:v1",
                        section_path=("Guide", "First"),
                        content_utf8_byte_count=20,
                        chunk_content_sha256=_CHUNK_DIGEST,
                    ),
                ),
            ),
        ),
    )


def _expected_key() -> str:
    """Return the frozen content-addressed key for the test chunk."""
    return f"{BEDROCK_PUBLICATION_PREFIX}/chunks/{_CHUNK_DIGEST}.txt"


def test_catalog_projects_checked_manifest_identity_without_provider_metadata() -> None:
    """Manifest evidence alone must own canonical chunk/source identity."""
    catalog = build_retrieval_catalog(_manifest())

    assert len(catalog.chunks) == 1
    resolved = catalog.resolve_content_key(_expected_key())
    assert resolved.content_key == _expected_key()
    assert resolved.chunk_id == "knowledge-chunk:test-retrieve:first:v1"
    assert resolved.document_id == "knowledge-doc:test-retrieve:v1"
    assert resolved.source_id == "example:test-retrieve"
    assert resolved.source_type is KnowledgeSourceType.SECURITY_GUIDANCE
    assert resolved.canonical_uri == "https://example.com/security/guide/"
    assert resolved.document_content_sha256 == _DOCUMENT_DIGEST
    assert resolved.chunk_content_sha256 == _CHUNK_DIGEST
    assert resolved.title == "Security Guide"
    assert resolved.section_path == ("Guide", "First")
    assert resolved.content_utf8_byte_count == 20


def test_catalog_rejects_key_outside_frozen_publication_shape() -> None:
    """Arbitrary provider locations cannot become canonical corpus authority."""
    catalog = build_retrieval_catalog(_manifest())

    with pytest.raises(RetrievalCatalogError, match="outside"):
        catalog.resolve_content_key(
            f"knowledge/corpus/v1/other/{_CHUNK_DIGEST}.txt"
        )


def test_catalog_rejects_unknown_well_formed_digest() -> None:
    """A well-shaped but unknown content address still fails closed."""
    catalog = build_retrieval_catalog(_manifest())

    with pytest.raises(RetrievalCatalogError, match="exactly one"):
        catalog.resolve_content_key(
            f"{BEDROCK_PUBLICATION_PREFIX}/chunks/{'e' * 64}.txt"
        )


def test_chunk_rejects_key_digest_that_disagrees_with_manifest_digest() -> None:
    """The key cannot claim a different content identity than checked manifest evidence."""
    with pytest.raises(RetrievalCatalogError, match="must equal"):
        CanonicalRetrievalChunk(
            content_key=f"{BEDROCK_PUBLICATION_PREFIX}/chunks/{'e' * 64}.txt",
            chunk_id="knowledge-chunk:test-retrieve:first:v1",
            document_id="knowledge-doc:test-retrieve:v1",
            source_id="example:test-retrieve",
            source_type=KnowledgeSourceType.SECURITY_GUIDANCE,
            canonical_uri="https://example.com/security/guide/",
            document_content_sha256=_DOCUMENT_DIGEST,
            chunk_content_sha256=_CHUNK_DIGEST,
            title="Security Guide",
            section_path=("Guide", "First"),
            content_utf8_byte_count=20,
        )


def test_catalog_rejects_ambiguous_content_address() -> None:
    """Two canonical chunks cannot share one published content-addressed key."""
    first = build_retrieval_catalog(_manifest()).chunks[0]
    second = CanonicalRetrievalChunk(
        content_key=first.content_key,
        chunk_id="knowledge-chunk:test-retrieve:second:v1",
        document_id=first.document_id,
        source_id=first.source_id,
        source_type=first.source_type,
        canonical_uri=first.canonical_uri,
        document_content_sha256=first.document_content_sha256,
        chunk_content_sha256=first.chunk_content_sha256,
        title=first.title,
        section_path=("Guide", "Second"),
        content_utf8_byte_count=first.content_utf8_byte_count,
    )

    with pytest.raises(RetrievalCatalogError, match="globally unique"):
        CanonicalRetrievalCatalog(chunks=(first, second))
