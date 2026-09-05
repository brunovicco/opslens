"""Pure deterministic transformation from acquired source bytes to canonical corpus text."""

from __future__ import annotations

from opslens.knowledge_retrieval.adapters.http_source import AcquiredKnowledgeSource
from opslens.knowledge_retrieval.domain import KnowledgeDocument
from opslens.knowledge_retrieval.domain.corpus import (
    CanonicalKnowledgeChunk,
    ChunkSelectionSpec,
    DocumentMaterializationSpec,
    MaterializedKnowledgeDocument,
)


class CanonicalSourceTextError(ValueError):
    """Raised when pinned source bytes cannot satisfy the frozen canonical-text contract."""


def normalize_source_text(body: bytes) -> str:
    """Decode strict UTF-8 and normalize only line endings plus outer blank space."""
    try:
        text = body.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise CanonicalSourceTextError("source bytes must be valid strict UTF-8") from exc

    if text.startswith("\ufeff"):
        raise CanonicalSourceTextError("UTF-8 BOM is not admitted by the v1 corpus contract")
    if "\x00" in text:
        raise CanonicalSourceTextError("source text must not contain NUL characters")

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise CanonicalSourceTextError("normalized source text must not be blank")
    return normalized


def _line_aligned_marker_positions(source_text: str, marker: str) -> tuple[int, ...]:
    """Return occurrences that start and end on exact normalized line boundaries."""
    positions: list[int] = []
    search_from = 0
    while True:
        index = source_text.find(marker, search_from)
        if index < 0:
            return tuple(positions)
        end_index = index + len(marker)
        starts_on_boundary = index == 0 or source_text[index - 1] == "\n"
        ends_on_boundary = end_index == len(source_text) or source_text[end_index] == "\n"
        if starts_on_boundary and ends_on_boundary:
            positions.append(index)
        search_from = index + 1


def select_exact_section(source_text: str, selection: ChunkSelectionSpec) -> str:
    """Select one exact line-aligned start-inclusive/end-exclusive source section."""
    start_positions = _line_aligned_marker_positions(source_text, selection.start_marker)
    if len(start_positions) != 1:
        raise CanonicalSourceTextError(
            f"start marker for {selection.chunk_id!r} must occur exactly once; "
            f"found {len(start_positions)}"
        )

    start_index = start_positions[0]
    end_positions = _line_aligned_marker_positions(source_text, selection.end_marker)
    following_end_positions = tuple(
        position
        for position in end_positions
        if position >= start_index + len(selection.start_marker)
    )
    if not following_end_positions:
        raise CanonicalSourceTextError(
            f"end marker for {selection.chunk_id!r} was not found after its start marker"
        )
    end_index = following_end_positions[0]

    selected = source_text[start_index:end_index].strip()
    if not selected:
        raise CanonicalSourceTextError(
            f"selection for {selection.chunk_id!r} produced blank canonical text"
        )
    return selected


def materialize_knowledge_document(
    acquired: AcquiredKnowledgeSource,
    spec: DocumentMaterializationSpec,
) -> MaterializedKnowledgeDocument:
    """Build one canonical document and deterministic chunks from already acquired inert bytes."""
    descriptor = acquired.descriptor
    if descriptor.document_id != spec.document_id:
        raise CanonicalSourceTextError(
            "materialization spec document_id must match the acquired source descriptor"
        )

    spec_chunk_ids = tuple(selection.chunk_id for selection in spec.selections)
    if spec_chunk_ids != descriptor.expected_chunk_ids:
        raise CanonicalSourceTextError(
            "materialization chunk order must exactly match source-registry expectations"
        )

    source_text = normalize_source_text(acquired.body)
    selected_texts = tuple(
        select_exact_section(source_text, selection) for selection in spec.selections
    )
    if len(set(selected_texts)) != len(selected_texts):
        raise CanonicalSourceTextError(
            "canonical chunk selections must not materialize duplicate text"
        )

    document_text = "\n\n".join(selected_texts)
    document = KnowledgeDocument.from_text(
        document_id=descriptor.document_id,
        source_id=descriptor.source_id,
        source_type=descriptor.source_type,
        title=spec.title,
        canonical_uri=descriptor.canonical_uri,
        text=document_text,
    )
    chunks = tuple(
        CanonicalKnowledgeChunk.from_text(
            chunk_id=selection.chunk_id,
            document_id=document.document_id,
            document_content_sha256=document.content_sha256,
            text=selected_text,
            section_path=selection.section_path,
        )
        for selection, selected_text in zip(spec.selections, selected_texts, strict=True)
    )
    return MaterializedKnowledgeDocument(
        source_byte_count=acquired.byte_count,
        source_bytes_sha256=acquired.source_bytes_sha256,
        document=document,
        chunks=chunks,
    )
