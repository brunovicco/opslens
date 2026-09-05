"""Public domain surface for bounded knowledge retrieval."""

from opslens.knowledge_retrieval.domain.errors import KnowledgeRetrievalValidationError
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
    "DEFAULT_RETRIEVAL_TOP_K",
    "MAX_RETRIEVAL_QUERY_CHARS",
    "MAX_RETRIEVAL_TOP_K",
    "SOURCE_REGISTRY_ID",
    "Citation",
    "KnowledgeDocument",
    "KnowledgeRetrievalValidationError",
    "KnowledgeSourceDescriptor",
    "KnowledgeSourceRegistry",
    "KnowledgeSourceType",
    "RetrievalBackend",
    "RetrievalEvidence",
    "RetrievalRequest",
    "RetrievedChunk",
]
