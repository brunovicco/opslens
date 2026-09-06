"""Tests for Gate 7.6a deterministic retrieval-context assembly."""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from typing import cast

import pytest

from opslens.knowledge_retrieval.application.context_assembly import (
    ContextAssemblyError,
    assemble_retrieval_context,
)
from opslens.knowledge_retrieval.domain import (
    DEFAULT_CONTEXT_MAX_CHUNKS,
    DEFAULT_CONTEXT_MAX_UTF8_BYTES,
    MAX_CONTEXT_CHUNKS,
    MAX_CONTEXT_UTF8_BYTES,
    AssembledContext,
    ContextAssemblyLimits,
    ContextAssemblyStopReason,
    ContextEvidenceBlock,
    KnowledgeRetrievalValidationError,
    KnowledgeSourceType,
    RetrievalBackend,
    RetrievalEvidence,
    RetrievalRequest,
    RetrievedChunk,
)


def _digest(text: str) -> str:
    """Return the exact UTF-8 SHA-256 identity used by the contracts."""
    return sha256(text.encode("utf-8")).hexdigest()


def _chunk(
    *,
    rank: int,
    text: str,
    relevance_score: float = 0.8,
) -> RetrievedChunk:
    """Build one valid admitted chunk with deterministic fixture provenance."""
    return RetrievedChunk.from_text(
        chunk_id=f"knowledge-chunk:test:{rank}:v1",
        document_id=f"knowledge-doc:test:{rank}:v1",
        source_id=f"source:test:{rank}",
        source_type=KnowledgeSourceType.SECURITY_GUIDANCE,
        canonical_uri=f"https://example.com/guidance/{rank}",
        document_content_sha256="1" * 64,
        text=text,
        rank=rank,
        relevance_score=relevance_score,
        title=f"Guidance {rank}",
        section_path=("Remediation", f"Step {rank}"),
    )


def _evidence(*chunks: RetrievedChunk) -> RetrievalEvidence:
    """Build one valid retrieval operation around the supplied contiguous chunks."""
    return RetrievalEvidence(
        retrieval_id="retrieval:gate-7-6a-test",
        request=RetrievalRequest(
            query="How should I remediate this dependency?",
            top_k=len(chunks) or 1,
        ),
        chunks=tuple(chunks),
        backend=RetrievalBackend.OFFLINE_GOLDEN,
    )


def test_context_limits_are_explicit_and_bounded() -> None:
    """Context assembly has model-independent hard ceilings before provider token limits."""
    limits = ContextAssemblyLimits()

    assert limits.max_chunks == DEFAULT_CONTEXT_MAX_CHUNKS == 5
    assert limits.max_utf8_bytes == DEFAULT_CONTEXT_MAX_UTF8_BYTES == 16_384
    assert MAX_CONTEXT_CHUNKS == 10
    assert MAX_CONTEXT_UTF8_BYTES == 16_384

    with pytest.raises(KnowledgeRetrievalValidationError, match="max_chunks"):
        ContextAssemblyLimits(max_chunks=cast(int, True))
    with pytest.raises(KnowledgeRetrievalValidationError, match="max_utf8_bytes"):
        ContextAssemblyLimits(max_utf8_bytes=MAX_CONTEXT_UTF8_BYTES + 1)


def test_context_block_projects_whole_admitted_chunk_without_provider_score() -> None:
    """Context keeps exact text/provenance but excludes score-as-confidence cues."""
    chunk = _chunk(rank=1, text="Use a patched dependency version.", relevance_score=1.37)

    block = ContextEvidenceBlock.from_chunk(chunk)

    assert block.retrieval_rank == 1
    assert block.text == chunk.text
    assert block.chunk_content_sha256 == _digest(chunk.text)
    assert block.utf8_byte_count == len(chunk.text.encode("utf-8"))
    assert not hasattr(block, "relevance_score")


def test_assembly_preserves_whole_contiguous_rank_prefix() -> None:
    """No chunk is truncated, reordered, or skipped while the bounded prefix fits."""
    evidence = _evidence(
        _chunk(rank=1, text="alpha"),
        _chunk(rank=2, text="beta"),
        _chunk(rank=3, text="gamma"),
    )

    context = assemble_retrieval_context(
        evidence,
        limits=ContextAssemblyLimits(max_chunks=3, max_utf8_bytes=64),
    )

    assert tuple(block.retrieval_rank for block in context.blocks) == (1, 2, 3)
    assert tuple(block.text for block in context.blocks) == ("alpha", "beta", "gamma")
    assert context.stop_reason is ContextAssemblyStopReason.EXHAUSTED_RETRIEVAL
    assert context.retrieved_chunk_count == 3
    assert context.total_utf8_bytes == 14


def test_byte_budget_stops_at_first_non_fitting_rank_without_backfill() -> None:
    """A smaller lower-ranked chunk cannot bypass one higher-ranked chunk that did not fit."""
    evidence = _evidence(
        _chunk(rank=1, text="alpha"),
        _chunk(rank=2, text="second-long"),
        _chunk(rank=3, text="x"),
    )

    context = assemble_retrieval_context(
        evidence,
        limits=ContextAssemblyLimits(max_chunks=3, max_utf8_bytes=6),
    )

    assert tuple(block.retrieval_rank for block in context.blocks) == (1,)
    assert context.total_utf8_bytes == 5
    assert context.stop_reason is ContextAssemblyStopReason.MAX_UTF8_BYTES


def test_chunk_limit_stops_before_retrieval_suffix() -> None:
    """Selection breadth remains independently bounded even when byte budget is ample."""
    evidence = _evidence(
        _chunk(rank=1, text="one"),
        _chunk(rank=2, text="two"),
        _chunk(rank=3, text="three"),
    )

    context = assemble_retrieval_context(
        evidence,
        limits=ContextAssemblyLimits(max_chunks=2, max_utf8_bytes=64),
    )

    assert tuple(block.retrieval_rank for block in context.blocks) == (1, 2)
    assert context.stop_reason is ContextAssemblyStopReason.MAX_CHUNKS


def test_empty_or_oversized_first_chunk_fails_closed() -> None:
    """Synthesis cannot proceed with no admitted context or by truncating the first chunk."""
    empty = _evidence()
    with pytest.raises(ContextAssemblyError, match="empty retrieval evidence"):
        assemble_retrieval_context(empty)

    oversized = _evidence(_chunk(rank=1, text="abcdef"))
    with pytest.raises(ContextAssemblyError, match="highest-ranked"):
        assemble_retrieval_context(
            oversized,
            limits=ContextAssemblyLimits(max_chunks=1, max_utf8_bytes=5),
        )


def test_provider_score_changes_do_not_change_synthesis_context_identity() -> None:
    """Provider similarity scores remain retrieval evidence and cannot alter context authority."""
    first = _chunk(rank=1, text="Use the checked remediation guidance.", relevance_score=0.2)
    second = replace(first, relevance_score=0.99)

    low_score_context = assemble_retrieval_context(_evidence(first))
    high_score_context = assemble_retrieval_context(_evidence(second))

    assert low_score_context.blocks == high_score_context.blocks
    assert low_score_context.context_sha256 == high_score_context.context_sha256


def test_assembled_context_fingerprint_and_totals_fail_closed_on_tampering() -> None:
    """Context identity covers query, limits, provenance, rank prefix, and content hashes."""
    context = assemble_retrieval_context(
        _evidence(_chunk(rank=1, text="evidence")),
        limits=ContextAssemblyLimits(max_chunks=1, max_utf8_bytes=64),
    )

    assert isinstance(context, AssembledContext)
    assert len(context.context_sha256) == 64

    with pytest.raises(KnowledgeRetrievalValidationError, match="total_utf8_bytes"):
        replace(context, total_utf8_bytes=context.total_utf8_bytes + 1)
    with pytest.raises(KnowledgeRetrievalValidationError, match="context_sha256"):
        replace(context, context_sha256="0" * 64)
