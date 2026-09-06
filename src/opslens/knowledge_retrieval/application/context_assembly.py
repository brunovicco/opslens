"""Deterministically assemble a bounded rank prefix for later LLM synthesis."""

from __future__ import annotations

from opslens.knowledge_retrieval.domain import (
    AssembledContext,
    ContextAssemblyLimits,
    ContextAssemblyStopReason,
    ContextEvidenceBlock,
    RetrievalEvidence,
)


class ContextAssemblyError(ValueError):
    """Raised when admitted retrieval evidence cannot form bounded synthesis context."""


def assemble_retrieval_context(
    evidence: RetrievalEvidence,
    *,
    limits: ContextAssemblyLimits | None = None,
) -> AssembledContext:
    """Select whole chunks as one contiguous rank prefix under deterministic limits."""
    if not isinstance(evidence, RetrievalEvidence):
        raise ContextAssemblyError("evidence must be a RetrievalEvidence value")
    resolved_limits = limits if limits is not None else ContextAssemblyLimits()
    if not isinstance(resolved_limits, ContextAssemblyLimits):
        raise ContextAssemblyError("limits must be a ContextAssemblyLimits value")
    if not evidence.chunks:
        raise ContextAssemblyError("cannot assemble synthesis context from empty retrieval evidence")

    selected: list[ContextEvidenceBlock] = []
    total_utf8_bytes = 0
    stop_reason = ContextAssemblyStopReason.EXHAUSTED_RETRIEVAL

    for chunk in evidence.chunks:
        if len(selected) >= resolved_limits.max_chunks:
            stop_reason = ContextAssemblyStopReason.MAX_CHUNKS
            break

        block = ContextEvidenceBlock.from_chunk(chunk)
        next_total = total_utf8_bytes + block.utf8_byte_count
        if next_total > resolved_limits.max_utf8_bytes:
            stop_reason = ContextAssemblyStopReason.MAX_UTF8_BYTES
            break

        selected.append(block)
        total_utf8_bytes = next_total

    if not selected:
        raise ContextAssemblyError(
            "highest-ranked admitted chunk exceeds the synthesis context byte budget"
        )

    return AssembledContext.create(
        retrieval_id=evidence.retrieval_id,
        query=evidence.request.query,
        limits=resolved_limits,
        blocks=tuple(selected),
        retrieved_chunk_count=len(evidence.chunks),
        stop_reason=stop_reason,
    )
