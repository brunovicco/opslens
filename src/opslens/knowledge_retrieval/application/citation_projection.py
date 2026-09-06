"""Deterministic application projection for canonical citations over synthesis context."""

from __future__ import annotations

from opslens.knowledge_retrieval.domain import AssembledContext
from opslens.knowledge_retrieval.domain.citations import CitationCatalog


class CitationProjectionError(ValueError):
    """Raised when citation projection receives a value outside the admitted context boundary."""


def _is_runtime_instance(value: object, expected_type: type[object]) -> bool:
    """Check untrusted runtime values without weakening public annotations."""
    return isinstance(value, expected_type)


def project_citation_catalog(context: AssembledContext) -> CitationCatalog:
    """Project C1..Cn only from the exact selected context rank prefix."""
    if not _is_runtime_instance(context, AssembledContext):
        raise CitationProjectionError("context must be an AssembledContext value")
    return CitationCatalog.create(context)
