"""Application services for deterministic knowledge-corpus materialization."""

from opslens.knowledge_retrieval.application.corpus_materialization import (
    CanonicalSourceTextError,
    materialize_knowledge_document,
    normalize_source_text,
    select_exact_section,
)

__all__ = [
    "CanonicalSourceTextError",
    "materialize_knowledge_document",
    "normalize_source_text",
    "select_exact_section",
]
