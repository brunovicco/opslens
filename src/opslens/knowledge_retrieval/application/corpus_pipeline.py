"""Serial bounded replay pipeline for the reproducible knowledge corpus."""

from __future__ import annotations

from typing import Protocol

from opslens.knowledge_retrieval.adapters.http_source import AcquiredKnowledgeSource
from opslens.knowledge_retrieval.application.corpus_manifest import build_corpus_manifest
from opslens.knowledge_retrieval.application.corpus_materialization import (
    materialize_knowledge_document,
)
from opslens.knowledge_retrieval.domain import (
    KnowledgeCorpusManifest,
    KnowledgeCorpusSpec,
    KnowledgeSourceDescriptor,
    KnowledgeSourceRegistry,
    MaterializedKnowledgeDocument,
)

MAX_CORPUS_DOCUMENTS = 10


class KnowledgeSourceAcquirer(Protocol):
    """Minimal source-acquisition boundary required by corpus replay."""

    def acquire(self, descriptor: KnowledgeSourceDescriptor) -> AcquiredKnowledgeSource:
        """Acquire inert bytes for one already-authorized pinned descriptor."""
        ...


class CorpusPipelineError(ValueError):
    """Raised when corpus inputs cannot form one complete bounded replay."""


def materialize_corpus_documents(
    registry: KnowledgeSourceRegistry,
    spec: KnowledgeCorpusSpec,
    acquirer: KnowledgeSourceAcquirer,
) -> tuple[MaterializedKnowledgeDocument, ...]:
    """Acquire and materialize the complete bounded corpus while preserving canonical text."""
    if spec.source_registry_id != registry.registry_id:
        raise CorpusPipelineError("corpus spec must reference the supplied source registry")
    if len(registry.entries) != len(spec.documents):
        raise CorpusPipelineError("registry and corpus spec document counts must match")
    if not 1 <= len(registry.entries) <= MAX_CORPUS_DOCUMENTS:
        raise CorpusPipelineError(
            f"corpus replay must contain between 1 and {MAX_CORPUS_DOCUMENTS} documents"
        )

    materialized: list[MaterializedKnowledgeDocument] = []
    for descriptor, document_spec in zip(
        registry.entries,
        spec.documents,
        strict=True,
    ):
        if descriptor.document_id != document_spec.document_id:
            raise CorpusPipelineError(
                "registry and corpus spec document order must match exactly"
            )
        acquired = acquirer.acquire(descriptor)
        materialized.append(
            materialize_knowledge_document(acquired, document_spec)
        )

    return tuple(materialized)


def materialize_corpus(
    registry: KnowledgeSourceRegistry,
    spec: KnowledgeCorpusSpec,
    acquirer: KnowledgeSourceAcquirer,
) -> KnowledgeCorpusManifest:
    """Acquire and materialize authorized documents serially into one hash-only manifest."""
    materialized = materialize_corpus_documents(registry, spec, acquirer)
    return build_corpus_manifest(registry, spec, materialized)
