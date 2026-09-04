"""Tests for the offline-first Phase 7 knowledge-retrieval contracts."""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from typing import cast

import pytest

from opslens.knowledge_retrieval.domain import (
    CANONICAL_METADATA_FIELDS,
    DEFAULT_RETRIEVAL_TOP_K,
    MAX_RETRIEVAL_QUERY_CHARS,
    MAX_RETRIEVAL_TOP_K,
    Citation,
    KnowledgeDocument,
    KnowledgeRetrievalValidationError,
    KnowledgeSourceType,
    RetrievalBackend,
    RetrievalEvidence,
    RetrievalRequest,
    RetrievedChunk,
)


def _digest(text: str) -> str:
    """Return the exact SHA-256 identity used by the domain contract."""
    return sha256(text.encode("utf-8")).hexdigest()


def _document() -> KnowledgeDocument:
    """Build one valid explanatory document fixture."""
    return KnowledgeDocument.from_text(
        document_id="knowledge-doc:pypa-remediation:v1",
        source_id="source:pypa-remediation",
        source_type=KnowledgeSourceType.MAINTAINER_DOCUMENTATION,
        title="Python dependency remediation",
        canonical_uri="https://packaging.python.org/example-remediation/",
        text="Upgrade to a supported patched dependency version and validate the result.",
        vulnerability_ids=("CVE-2099-0001",),
        ecosystem="PyPI",
        package_name="example-package",
    )


def _chunk(
    *,
    rank: int = 1,
    chunk_id: str = "knowledge-chunk:pypa-remediation:upgrade:v1",
) -> RetrievedChunk:
    """Build one valid retrieved chunk tied to the document fixture."""
    document = _document()
    return RetrievedChunk.from_text(
        chunk_id=chunk_id,
        document_id=document.document_id,
        source_id=document.source_id,
        source_type=document.source_type,
        canonical_uri=document.canonical_uri,
        document_content_sha256=document.content_sha256,
        text="Upgrade to a supported patched dependency version.",
        rank=rank,
        relevance_score=0.91,
        title=document.title,
        section_path=("Remediation", "Upgrade"),
    )


def test_knowledge_document_preserves_exact_content_identity_and_provenance() -> None:
    """Canonical text, provenance, and SHA-256 identity remain explicit and reproducible."""
    document = _document()

    assert document.content_sha256 == _digest(document.text)
    assert document.canonical_uri.startswith("https://")
    assert document.source_type is KnowledgeSourceType.MAINTAINER_DOCUMENTATION
    assert document.vulnerability_ids == ("CVE-2099-0001",)


def test_knowledge_document_fails_closed_on_bad_uri_or_content_identity() -> None:
    """Malformed provenance and mismatched content hashes cannot enter the corpus contract."""
    valid = _document()

    with pytest.raises(KnowledgeRetrievalValidationError, match="absolute HTTPS URI"):
        replace(valid, canonical_uri="file:///tmp/source.txt")

    with pytest.raises(KnowledgeRetrievalValidationError, match="must match"):
        replace(valid, content_sha256="0" * 64)


def test_retrieval_request_is_trimmed_typed_and_bounded() -> None:
    """Retrieval input is normalized without exposing an arbitrary provider filter DSL."""
    request = RetrievalRequest(
        query="  How should I remediate this vulnerable Python dependency?  ",
        source_types=(KnowledgeSourceType.MAINTAINER_DOCUMENTATION,),
        vulnerability_ids=("CVE-2099-0001",),
        ecosystem="PyPI",
        package_name="example-package",
    )

    assert request.query == "How should I remediate this vulnerable Python dependency?"
    assert request.top_k == DEFAULT_RETRIEVAL_TOP_K
    assert MAX_RETRIEVAL_TOP_K == 10

    with pytest.raises(KnowledgeRetrievalValidationError, match="blank"):
        RetrievalRequest(query="   ")
    with pytest.raises(KnowledgeRetrievalValidationError, match="cannot exceed"):
        RetrievalRequest(query="x" * (MAX_RETRIEVAL_QUERY_CHARS + 1))


@pytest.mark.parametrize("top_k", [0, 11, True])
def test_retrieval_request_rejects_unbounded_top_k(top_k: object) -> None:
    """Callers cannot increase retrieval breadth beyond the frozen v1 boundary."""
    with pytest.raises(KnowledgeRetrievalValidationError, match="top_k"):
        RetrievalRequest(query="How should I remediate this?", top_k=cast(int, top_k))


def test_retrieval_request_rejects_unknown_or_duplicate_source_types() -> None:
    """Metadata scope is typed instead of accepting arbitrary provider expressions."""
    with pytest.raises(KnowledgeRetrievalValidationError, match="allowlisted"):
        RetrievalRequest(
            query="How should I remediate this?",
            source_types=cast(tuple[KnowledgeSourceType, ...], ("anything",)),
        )

    with pytest.raises(KnowledgeRetrievalValidationError, match="duplicates"):
        RetrievalRequest(
            query="How should I remediate this?",
            source_types=(
                KnowledgeSourceType.SECURITY_GUIDANCE,
                KnowledgeSourceType.SECURITY_GUIDANCE,
            ),
        )


def test_retrieved_chunk_requires_exact_chunk_identity_and_explicit_rank() -> None:
    """Retrieved text is admitted only with exact chunk and document provenance."""
    chunk = _chunk()

    assert chunk.chunk_content_sha256 == _digest(chunk.text)
    assert chunk.rank == 1
    assert chunk.relevance_score == 0.91
    assert chunk.document_content_sha256 == _document().content_sha256

    with pytest.raises(KnowledgeRetrievalValidationError, match="must match"):
        replace(chunk, chunk_content_sha256="0" * 64)


def test_relevance_score_is_retrieval_evidence_not_a_probability_contract() -> None:
    """Finite provider scores are preserved without pretending they are calibrated confidence."""
    chunk = replace(_chunk(), relevance_score=1.37)

    assert chunk.relevance_score == 1.37

    with pytest.raises(KnowledgeRetrievalValidationError, match="finite"):
        replace(_chunk(), relevance_score=float("inf"))


def test_retrieval_evidence_enforces_top_k_unique_ids_and_ordered_ranks() -> None:
    """An adapter cannot return extra, duplicated, or ambiguously ranked retrieval evidence."""
    request = RetrievalRequest(query="How should I remediate this?", top_k=2)
    first = _chunk(rank=1, chunk_id="chunk:1")
    second = _chunk(rank=2, chunk_id="chunk:2")

    evidence = RetrievalEvidence(
        retrieval_id="retrieval:test-001",
        request=request,
        chunks=(first, second),
        backend=RetrievalBackend.OFFLINE_GOLDEN,
    )

    assert evidence.chunks == (first, second)

    with pytest.raises(KnowledgeRetrievalValidationError, match="contiguous"):
        replace(evidence, chunks=(replace(first, rank=2),))

    with pytest.raises(KnowledgeRetrievalValidationError, match="unique"):
        replace(evidence, chunks=(first, replace(second, chunk_id=first.chunk_id)))

    with pytest.raises(KnowledgeRetrievalValidationError, match="request.top_k"):
        replace(evidence, request=RetrievalRequest(query=request.query, top_k=1))


def test_citation_is_projected_from_admitted_chunk_provenance() -> None:
    """Citation metadata comes from retrieved evidence rather than model-authored URLs."""
    chunk = _chunk()

    citation = Citation.from_chunk(citation_id="C1", chunk=chunk)

    assert citation == Citation(
        citation_id="C1",
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        source_id=chunk.source_id,
        canonical_uri=chunk.canonical_uri,
        title=chunk.title,
        section_path=chunk.section_path,
    )

    with pytest.raises(KnowledgeRetrievalValidationError, match="C1"):
        replace(citation, citation_id="citation-one")


def test_canonical_metadata_allowlist_is_provider_independent() -> None:
    """Gate 7.1 freezes canonical provenance fields without choosing an AWS projection."""
    assert CANONICAL_METADATA_FIELDS == frozenset(
        {
            "source_id",
            "source_type",
            "canonical_uri",
            "document_id",
            "content_sha256",
            "title",
            "published_at",
            "updated_at",
            "vulnerability_ids",
            "ecosystem",
            "package_name",
            "section_path",
        }
    )
