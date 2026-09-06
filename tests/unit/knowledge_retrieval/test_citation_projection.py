"""Unit tests for deterministic citation projection over admitted synthesis context."""

from __future__ import annotations

from typing import cast

import pytest

from opslens.knowledge_retrieval.application.citation_projection import (
    CitationProjectionError,
    project_citation_catalog,
)
from opslens.knowledge_retrieval.application.context_assembly import (
    assemble_retrieval_context,
)
from opslens.knowledge_retrieval.domain import (
    AssembledContext,
    CitationCatalog,
    ContextAssemblyLimits,
    KnowledgeRetrievalValidationError,
    KnowledgeSourceType,
    ProjectedCitation,
    RetrievalBackend,
    RetrievalEvidence,
    RetrievalRequest,
    RetrievedChunk,
)

QUESTION = "How should I verify dependency artifacts?"


def _chunk(*, rank: int, suffix: str) -> RetrievedChunk:
    """Build one admitted retrieval chunk with distinct canonical provenance."""
    return RetrievedChunk.from_text(
        chunk_id=f"knowledge-chunk:test:citation:{suffix}:v1",
        document_id=f"knowledge-doc:test:citation:{suffix}:v1",
        source_id=f"source:test:citation:{suffix}",
        source_type=KnowledgeSourceType.SECURITY_GUIDANCE,
        canonical_uri=f"https://example.com/citation/{suffix}",
        document_content_sha256=f"{rank}" * 64,
        text=f"Verified guidance for citation block {suffix}.",
        rank=rank,
        relevance_score=0.95 - (rank / 10),
        title=f"Citation source {suffix}",
        section_path=("Guidance", suffix),
    )


def _context(*, max_chunks: int = 3) -> AssembledContext:
    """Build deterministic context from a three-result admitted retrieval."""
    evidence = RetrievalEvidence(
        retrieval_id="retrieval:gate-7-7a-test",
        request=RetrievalRequest(query=QUESTION, top_k=3),
        chunks=(
            _chunk(rank=1, suffix="one"),
            _chunk(rank=2, suffix="two"),
            _chunk(rank=3, suffix="three"),
        ),
        backend=RetrievalBackend.OFFLINE_GOLDEN,
    )
    return assemble_retrieval_context(
        evidence,
        limits=ContextAssemblyLimits(max_chunks=max_chunks),
    )


def test_catalog_projects_citations_in_exact_selected_context_order() -> None:
    """C1..Cn derive only from selected blocks and preserve canonical provenance."""
    context = _context()

    catalog = project_citation_catalog(context)

    assert catalog.context_sha256 == context.context_sha256
    assert tuple(item.retrieval_rank for item in catalog.citations) == (1, 2, 3)
    assert tuple(item.citation.citation_id for item in catalog.citations) == (
        "C1",
        "C2",
        "C3",
    )
    assert tuple(item.citation.chunk_id for item in catalog.citations) == tuple(
        block.chunk_id for block in context.blocks
    )
    assert tuple(item.chunk_content_sha256 for item in catalog.citations) == tuple(
        block.chunk_content_sha256 for block in context.blocks
    )


def test_catalog_excludes_retrieval_suffix_not_selected_for_context() -> None:
    """A retrieved chunk outside the admitted rank prefix cannot become citation authority."""
    context = _context(max_chunks=2)

    catalog = project_citation_catalog(context)

    assert tuple(item.citation.citation_id for item in catalog.citations) == ("C1", "C2")
    assert all("three" not in item.citation.chunk_id for item in catalog.citations)


def test_projected_citations_do_not_carry_provider_relevance_scores() -> None:
    """Similarity evidence cannot silently become citation confidence or authority."""
    catalog = project_citation_catalog(_context())

    assert all(not hasattr(item, "relevance_score") for item in catalog.citations)
    assert all(not hasattr(item.citation, "relevance_score") for item in catalog.citations)


def test_same_context_produces_same_content_addressed_catalog() -> None:
    """Citation identity is reproducible for identical admitted context evidence."""
    first = project_citation_catalog(_context())
    second = project_citation_catalog(_context())

    assert first == second
    assert first.catalog_sha256 == second.catalog_sha256
    assert tuple(item.citation_sha256 for item in first.citations) == tuple(
        item.citation_sha256 for item in second.citations
    )


def test_projected_citation_rejects_content_hash_tampering() -> None:
    """Citation evidence cannot be rebound to a different chunk hash after projection."""
    projected = project_citation_catalog(_context()).citations[0]

    with pytest.raises(
        KnowledgeRetrievalValidationError,
        match="citation_sha256 must match",
    ):
        ProjectedCitation(
            citation=projected.citation,
            retrieval_rank=projected.retrieval_rank,
            document_content_sha256=projected.document_content_sha256,
            chunk_content_sha256="f" * 64,
            citation_sha256=projected.citation_sha256,
        )


def test_catalog_rejects_reordered_citation_authority() -> None:
    """Citation ordering cannot diverge from the selected retrieval-rank prefix."""
    catalog = project_citation_catalog(_context())

    with pytest.raises(
        KnowledgeRetrievalValidationError,
        match="citation ranks must form",
    ):
        CitationCatalog(
            context_sha256=catalog.context_sha256,
            citations=tuple(reversed(catalog.citations)),
            catalog_sha256=catalog.catalog_sha256,
        )


def test_projection_rejects_non_context_runtime_values() -> None:
    """The application boundary accepts only already-admitted assembled context."""
    invalid = cast(AssembledContext, object())

    with pytest.raises(CitationProjectionError, match="AssembledContext"):
        project_citation_catalog(invalid)
