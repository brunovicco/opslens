"""Application services for deterministic knowledge-corpus materialization."""

from opslens.knowledge_retrieval.application.corpus_config import (
    CorpusConfigError,
    load_corpus_spec,
    load_source_registry,
)
from opslens.knowledge_retrieval.application.corpus_materialization import (
    CanonicalSourceTextError,
    materialize_knowledge_document,
    normalize_source_text,
    select_exact_section,
)

__all__ = [
    "CanonicalSourceTextError",
    "CorpusConfigError",
    "load_corpus_spec",
    "load_source_registry",
    "materialize_knowledge_document",
    "normalize_source_text",
    "select_exact_section",
]
