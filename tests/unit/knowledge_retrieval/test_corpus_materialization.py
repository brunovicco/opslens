"""Tests for pure Gate 7.2 canonical corpus materialization."""

from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from opslens.knowledge_retrieval.adapters.http_source import AcquiredKnowledgeSource
from opslens.knowledge_retrieval.application.corpus_materialization import (
    CanonicalSourceTextError,
    materialize_knowledge_document,
    normalize_source_text,
    select_exact_section,
)
from opslens.knowledge_retrieval.domain import (
    ChunkSelectionSpec,
    DocumentMaterializationSpec,
    KnowledgeSourceDescriptor,
    KnowledgeSourceType,
)


def _descriptor() -> KnowledgeSourceDescriptor:
    """Return one pinned source descriptor for pure materialization tests."""
    return KnowledgeSourceDescriptor(
        document_id="knowledge-doc:test:v1",
        source_id="example:test-source",
        source_type=KnowledgeSourceType.MAINTAINER_DOCUMENTATION,
        canonical_uri="https://example.com/docs/test/",
        upstream_repository="example/example",
        upstream_commit_sha="a" * 40,
        upstream_path="docs/test.md",
        expected_chunk_ids=(
            "knowledge-chunk:test:first:v1",
            "knowledge-chunk:test:second:v1",
        ),
    )


def _spec() -> DocumentMaterializationSpec:
    """Return two non-overlapping exact selectors with stable section paths."""
    return DocumentMaterializationSpec(
        document_id="knowledge-doc:test:v1",
        title="Test Source",
        selections=(
            ChunkSelectionSpec(
                chunk_id="knowledge-chunk:test:first:v1",
                section_path=("Guide", "First"),
                start_marker="## First",
                end_marker="## Second",
            ),
            ChunkSelectionSpec(
                chunk_id="knowledge-chunk:test:second:v1",
                section_path=("Guide", "Second"),
                start_marker="## Second",
                end_marker="## End",
            ),
        ),
    )


def _acquired(body: bytes) -> AcquiredKnowledgeSource:
    """Wrap inert fixture bytes in the validated raw-source identity contract."""
    return AcquiredKnowledgeSource.from_body(
        descriptor=_descriptor(),
        body=body,
        content_type="text/plain; charset=utf-8",
    )


def test_source_normalization_is_minimal_and_deterministic() -> None:
    """Only newline representation and outer blank space change in v1."""
    body = "  alpha  \r\nβeta\r\nline with trailing spaces   \r\n".encode()

    assert normalize_source_text(body) == "alpha  \nβeta\nline with trailing spaces"


def test_source_normalization_rejects_invalid_utf8_bom_nul_and_blank() -> None:
    """Ambiguous or non-text source bytes fail closed before section selection."""
    for body, expected_message in (
        (b"\xff", "valid strict UTF-8"),
        (b"\xef\xbb\xbfheading", "BOM"),
        (b"heading\x00body", "NUL"),
        (b"\r\n\r\n", "must not be blank"),
    ):
        with pytest.raises(CanonicalSourceTextError, match=expected_message):
            normalize_source_text(body)


def test_exact_section_requires_one_start_and_a_following_end_marker() -> None:
    """Marker drift or ambiguity cannot silently select a different source span."""
    selection = _spec().selections[0]
    source_text = "# Guide\n\n## First\nalpha\n\n## Second\nbeta\n\n## End"

    assert select_exact_section(source_text, selection) == "## First\nalpha"

    with pytest.raises(CanonicalSourceTextError, match="exactly once"):
        select_exact_section(
            source_text + "\n\n## First\nshadow",
            selection,
        )

    with pytest.raises(CanonicalSourceTextError, match="was not found"):
        select_exact_section(
            source_text,
            replace(selection, end_marker="## Missing"),
        )


def test_materialization_builds_content_addressed_document_and_chunks() -> None:
    """Raw bytes, canonical document text, and each chunk have distinct exact identities."""
    body = (
        b"# Guide\r\n\r\n"
        b"## First\r\nalpha\r\n\r\n"
        b"## Second\r\nbeta\r\n\r\n"
        b"## End\r\nignored\r\n"
    )
    acquired = _acquired(body)

    materialized = materialize_knowledge_document(acquired, _spec())

    assert materialized.source_byte_count == len(body)
    assert materialized.source_bytes_sha256 == hashlib.sha256(body).hexdigest()
    assert materialized.document.text == "## First\nalpha\n\n## Second\nbeta"
    assert materialized.document.content_sha256 == hashlib.sha256(
        materialized.document.text.encode("utf-8")
    ).hexdigest()
    assert [chunk.chunk_id for chunk in materialized.chunks] == [
        "knowledge-chunk:test:first:v1",
        "knowledge-chunk:test:second:v1",
    ]
    assert [chunk.text for chunk in materialized.chunks] == [
        "## First\nalpha",
        "## Second\nbeta",
    ]
    for chunk in materialized.chunks:
        assert chunk.document_id == materialized.document.document_id
        assert chunk.document_content_sha256 == materialized.document.content_sha256
        assert chunk.chunk_content_sha256 == hashlib.sha256(
            chunk.text.encode("utf-8")
        ).hexdigest()
        assert chunk.text in materialized.document.text


def test_materialization_rejects_wrong_document_or_chunk_order() -> None:
    """The source registry remains authority for the exact document and chunk identities."""
    body = b"## First\nalpha\n## Second\nbeta\n## End"
    acquired = _acquired(body)

    with pytest.raises(CanonicalSourceTextError, match="document_id"):
        materialize_knowledge_document(
            acquired,
            replace(_spec(), document_id="knowledge-doc:other:v1"),
        )

    reversed_spec = replace(_spec(), selections=tuple(reversed(_spec().selections)))
    with pytest.raises(CanonicalSourceTextError, match="chunk order"):
        materialize_knowledge_document(acquired, reversed_spec)


def test_materialization_fails_closed_when_pinned_source_markers_drift() -> None:
    """A source snapshot that no longer matches the frozen selector is not partially admitted."""
    body = b"## First changed\nalpha\n## Second\nbeta\n## End"

    with pytest.raises(CanonicalSourceTextError, match="exactly once"):
        materialize_knowledge_document(_acquired(body), _spec())
