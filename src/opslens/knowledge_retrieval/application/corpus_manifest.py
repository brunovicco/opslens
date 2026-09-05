"""Build and verify deterministic hash-only manifests for the canonical corpus."""

from __future__ import annotations

import json

from opslens.knowledge_retrieval.domain import (
    CORPUS_MANIFEST_ID,
    CorpusChunkManifestEntry,
    CorpusDocumentManifestEntry,
    KnowledgeCorpusManifest,
    KnowledgeCorpusSpec,
    KnowledgeSourceRegistry,
    MaterializedKnowledgeDocument,
)


class CorpusManifestError(ValueError):
    """Raised when materialized evidence cannot satisfy the frozen corpus inputs."""


class CorpusManifestMismatchError(CorpusManifestError):
    """Raised when a replay differs from previously recorded manifest evidence."""


def build_corpus_manifest(
    registry: KnowledgeSourceRegistry,
    spec: KnowledgeCorpusSpec,
    materialized_documents: tuple[MaterializedKnowledgeDocument, ...],
) -> KnowledgeCorpusManifest:
    """Project one complete corpus replay into deterministic hash-only evidence."""
    if spec.source_registry_id != registry.registry_id:
        raise CorpusManifestError("corpus spec must reference the supplied source registry")
    if not (
        len(registry.entries)
        == len(spec.documents)
        == len(materialized_documents)
    ):
        raise CorpusManifestError(
            "registry, corpus spec, and materialized documents must have equal lengths"
        )

    manifest_documents: list[CorpusDocumentManifestEntry] = []
    for descriptor, document_spec, materialized in zip(
        registry.entries,
        spec.documents,
        materialized_documents,
        strict=True,
    ):
        document = materialized.document
        if not (
            descriptor.document_id
            == document_spec.document_id
            == document.document_id
        ):
            raise CorpusManifestError("document identities must remain aligned")

        expected_chunk_ids = tuple(
            selection.chunk_id for selection in document_spec.selections
        )
        actual_chunk_ids = tuple(chunk.chunk_id for chunk in materialized.chunks)
        if (
            expected_chunk_ids != descriptor.expected_chunk_ids
            or actual_chunk_ids != expected_chunk_ids
        ):
            raise CorpusManifestError("chunk identities and order must remain aligned")

        chunks = tuple(
            CorpusChunkManifestEntry(
                chunk_id=chunk.chunk_id,
                section_path=chunk.section_path,
                content_utf8_byte_count=len(chunk.text.encode("utf-8")),
                chunk_content_sha256=chunk.chunk_content_sha256,
            )
            for chunk in materialized.chunks
        )
        manifest_documents.append(
            CorpusDocumentManifestEntry(
                document_id=descriptor.document_id,
                source_id=descriptor.source_id,
                source_type=descriptor.source_type,
                canonical_uri=descriptor.canonical_uri,
                acquisition_uri=descriptor.acquisition_uri,
                upstream_repository=descriptor.upstream_repository,
                upstream_commit_sha=descriptor.upstream_commit_sha,
                upstream_path=descriptor.upstream_path,
                source_byte_count=materialized.source_byte_count,
                source_bytes_sha256=materialized.source_bytes_sha256,
                title=document.title,
                content_utf8_byte_count=len(document.text.encode("utf-8")),
                content_sha256=document.content_sha256,
                chunks=chunks,
            )
        )

    return KnowledgeCorpusManifest(
        manifest_id=CORPUS_MANIFEST_ID,
        source_registry_id=registry.registry_id,
        corpus_spec_id=spec.spec_id,
        documents=tuple(manifest_documents),
    )


def manifest_to_dict(manifest: KnowledgeCorpusManifest) -> dict[str, object]:
    """Convert typed evidence to the stable JSON-compatible v1 field order."""
    return {
        "manifest_id": manifest.manifest_id,
        "source_registry_id": manifest.source_registry_id,
        "corpus_spec_id": manifest.corpus_spec_id,
        "documents": [
            {
                "document_id": document.document_id,
                "source_id": document.source_id,
                "source_type": document.source_type.value,
                "canonical_uri": document.canonical_uri,
                "acquisition_uri": document.acquisition_uri,
                "upstream_repository": document.upstream_repository,
                "upstream_commit_sha": document.upstream_commit_sha,
                "upstream_path": document.upstream_path,
                "source_byte_count": document.source_byte_count,
                "source_bytes_sha256": document.source_bytes_sha256,
                "title": document.title,
                "content_utf8_byte_count": document.content_utf8_byte_count,
                "content_sha256": document.content_sha256,
                "chunks": [
                    {
                        "chunk_id": chunk.chunk_id,
                        "section_path": list(chunk.section_path),
                        "content_utf8_byte_count": chunk.content_utf8_byte_count,
                        "chunk_content_sha256": chunk.chunk_content_sha256,
                    }
                    for chunk in document.chunks
                ],
            }
            for document in manifest.documents
        ],
    }


def serialize_corpus_manifest(manifest: KnowledgeCorpusManifest) -> str:
    """Serialize one manifest byte-for-byte deterministically with no timestamp."""
    return json.dumps(
        manifest_to_dict(manifest),
        indent=2,
        ensure_ascii=False,
    ) + "\n"


def verify_corpus_manifest(
    expected: KnowledgeCorpusManifest,
    registry: KnowledgeSourceRegistry,
    spec: KnowledgeCorpusSpec,
    materialized_documents: tuple[MaterializedKnowledgeDocument, ...],
) -> None:
    """Fail closed when any replayed source/document/chunk evidence differs."""
    actual = build_corpus_manifest(registry, spec, materialized_documents)
    if actual != expected:
        raise CorpusManifestMismatchError(
            "materialized corpus evidence does not match the expected manifest"
        )
