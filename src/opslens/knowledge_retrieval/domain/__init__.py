"""Public domain surface for bounded knowledge retrieval."""

from opslens.knowledge_retrieval.domain.corpus import (
    CORPUS_SPEC_ID,
    CanonicalKnowledgeChunk,
    ChunkSelectionSpec,
    DocumentMaterializationSpec,
    KnowledgeCorpusSpec,
    MaterializedKnowledgeDocument,
)
from opslens.knowledge_retrieval.domain.errors import KnowledgeRetrievalValidationError
from opslens.knowledge_retrieval.domain.manifest import (
    CORPUS_MANIFEST_ID,
    CorpusChunkManifestEntry,
    CorpusDocumentManifestEntry,
    KnowledgeCorpusManifest,
)
from opslens.knowledge_retrieval.domain.models import (
    CANONICAL_METADATA_FIELDS,
    DEFAULT_RETRIEVAL_TOP_K,
    MAX_RETRIEVAL_QUERY_CHARS,
    MAX_RETRIEVAL_TOP_K,
    Citation,
    KnowledgeDocument,
    KnowledgeSourceType,
    RetrievalBackend,
    RetrievalEvidence,
    RetrievalRequest,
    RetrievedChunk,
)
from opslens.knowledge_retrieval.domain.source_registry import (
    SOURCE_REGISTRY_ID,
    KnowledgeSourceDescriptor,
    KnowledgeSourceRegistry,
)

__all__ = [
    "CANONICAL_METADATA_FIELDS",
    "CORPUS_MANIFEST_ID",
    "CORPUS_SPEC_ID",
    "DEFAULT_RETRIEVAL_TOP_K",
    "MAX_RETRIEVAL_QUERY_CHARS",
    "MAX_RETRIEVAL_TOP_K",
    "SOURCE_REGISTRY_ID",
    "CanonicalKnowledgeChunk",
    "ChunkSelectionSpec",
    "Citation",
    "CorpusChunkManifestEntry",
    "CorpusDocumentManifestEntry",
    "DocumentMaterializationSpec",
    "KnowledgeCorpusManifest",
    "KnowledgeCorpusSpec",
    "KnowledgeDocument",
    "KnowledgeRetrievalValidationError",
    "KnowledgeSourceDescriptor",
    "KnowledgeSourceRegistry",
    "KnowledgeSourceType",
    "MaterializedKnowledgeDocument",
    "RetrievalBackend",
    "RetrievalEvidence",
    "RetrievalRequest",
    "RetrievedChunk",
]
