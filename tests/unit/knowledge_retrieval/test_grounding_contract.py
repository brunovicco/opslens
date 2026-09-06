"""Unit tests for the offline grounded claim-to-citation synthesis contract."""

from __future__ import annotations

import json

import pytest

from opslens.knowledge_retrieval.application.citation_projection import (
    project_citation_catalog,
)
from opslens.knowledge_retrieval.application.context_assembly import (
    assemble_retrieval_context,
)
from opslens.knowledge_retrieval.application.grounding_contract import (
    GroundedSynthesisOutputError,
    build_grounded_synthesis_request,
    parse_grounded_synthesis_output,
)
from opslens.knowledge_retrieval.application.synthesis_contract import (
    build_synthesis_request,
)
from opslens.knowledge_retrieval.domain import (
    KnowledgeSourceType,
    RetrievalBackend,
    RetrievalEvidence,
    RetrievalRequest,
    RetrievedChunk,
    SynthesisAuthorityDecision,
    SynthesisDecision,
    SynthesisLimits,
)

QUESTION = "How should I verify dependency artifacts?"


def _context(*, suffix: str = "base"):
    """Build one two-chunk admitted context for grounded-output tests."""
    chunks = (
        RetrievedChunk.from_text(
            chunk_id=f"knowledge-chunk:test:grounded:{suffix}:one:v1",
            document_id=f"knowledge-doc:test:grounded:{suffix}:one:v1",
            source_id=f"source:test:grounded:{suffix}:one",
            source_type=KnowledgeSourceType.SECURITY_GUIDANCE,
            canonical_uri=f"https://example.com/grounded/{suffix}/one",
            document_content_sha256="1" * 64,
            text="Require hashes for dependency artifacts.",
            rank=1,
            relevance_score=0.9,
            title="Hash verification",
            section_path=("Hashes",),
        ),
        RetrievedChunk.from_text(
            chunk_id=f"knowledge-chunk:test:grounded:{suffix}:two:v1",
            document_id=f"knowledge-doc:test:grounded:{suffix}:two:v1",
            source_id=f"source:test:grounded:{suffix}:two",
            source_type=KnowledgeSourceType.MAINTAINER_DOCUMENTATION,
            canonical_uri=f"https://example.com/grounded/{suffix}/two",
            document_content_sha256="2" * 64,
            text="Pin dependency versions before installation.",
            rank=2,
            relevance_score=0.8,
            title="Version pinning",
            section_path=("Pinning",),
        ),
    )
    evidence = RetrievalEvidence(
        retrieval_id=f"retrieval:gate-7-7b:{suffix}",
        request=RetrievalRequest(query=QUESTION, top_k=2),
        chunks=chunks,
        backend=RetrievalBackend.OFFLINE_GOLDEN,
    )
    return assemble_retrieval_context(evidence)


def _request(*, max_output_chars: int = 4_000):
    """Bind one synthesis request to the exact deterministic citation catalog."""
    context = _context()
    synthesis = build_synthesis_request(
        question=QUESTION,
        context=context,
        authority_decision=SynthesisAuthorityDecision.SUPPORTED,
        limits=SynthesisLimits(max_output_chars=max_output_chars),
    )
    return build_grounded_synthesis_request(
        synthesis_request=synthesis,
        citation_catalog=project_citation_catalog(context),
    )


def test_parser_returns_cited_claims_with_deterministic_rendering() -> None:
    """Answer text is composed only from claims that carry admitted citation IDs."""
    payload = json.dumps(
        {
            "decision": "answer",
            "claims": [
                {
                    "text": "Verify dependency artifacts with hashes.",
                    "citation_ids": ["C2", "C1"],
                },
                {
                    "text": "Pin dependency versions before installation.",
                    "citation_ids": ["C2"],
                },
            ],
        }
    )

    result = parse_grounded_synthesis_output(payload, request=_request())

    assert result.decision is SynthesisDecision.ANSWER
    assert tuple(claim.claim_index for claim in result.claims) == (1, 2)
    assert result.claims[0].citation_ids == ("C1", "C2")
    assert result.claims[1].citation_ids == ("C2",)
    assert result.rendered_answer == (
        "Verify dependency artifacts with hashes.\n\n"
        "Pin dependency versions before installation."
    )


def test_parser_rejects_model_authored_unknown_citation_identity() -> None:
    """A model cannot invent a URL-equivalent citation ID outside deterministic authority."""
    payload = json.dumps(
        {
            "decision": "answer",
            "claims": [
                {
                    "text": "Verify dependency artifacts with hashes.",
                    "citation_ids": ["C99"],
                }
            ],
        }
    )

    with pytest.raises(
        GroundedSynthesisOutputError,
        match="admitted citation authority",
    ):
        parse_grounded_synthesis_output(payload, request=_request())


def test_parser_rejects_uncited_answer_claims() -> None:
    """Every answer claim must carry at least one admitted citation reference."""
    payload = json.dumps(
        {
            "decision": "answer",
            "claims": [
                {
                    "text": "Verify dependency artifacts with hashes.",
                    "citation_ids": [],
                }
            ],
        }
    )

    with pytest.raises(
        GroundedSynthesisOutputError,
        match="admitted citation authority",
    ):
        parse_grounded_synthesis_output(payload, request=_request())


def test_parser_rejects_model_authored_source_fields() -> None:
    """URLs or source IDs cannot enter through the model output object."""
    payload = json.dumps(
        {
            "decision": "answer",
            "claims": [
                {
                    "text": "Verify dependency artifacts with hashes.",
                    "citation_ids": ["C1"],
                    "canonical_uri": "https://attacker.example/forged",
                }
            ],
        }
    )

    with pytest.raises(
        GroundedSynthesisOutputError,
        match="exactly text and citation_ids",
    ):
        parse_grounded_synthesis_output(payload, request=_request())


def test_parser_rejects_model_authored_claim_ids() -> None:
    """Claim numbering belongs to deterministic output admission, not the model."""
    payload = json.dumps(
        {
            "decision": "answer",
            "claims": [
                {
                    "claim_id": "A100",
                    "text": "Verify dependency artifacts with hashes.",
                    "citation_ids": ["C1"],
                }
            ],
        }
    )

    with pytest.raises(
        GroundedSynthesisOutputError,
        match="exactly text and citation_ids",
    ):
        parse_grounded_synthesis_output(payload, request=_request())


def test_insufficient_evidence_requires_zero_claims() -> None:
    """Abstention remains citation-free and distinct from an answer."""
    result = parse_grounded_synthesis_output(
        json.dumps({"decision": "insufficient_evidence", "claims": []}),
        request=_request(),
    )

    assert result.decision is SynthesisDecision.INSUFFICIENT_EVIDENCE
    assert result.claims == ()
    assert result.rendered_answer is None


def test_insufficient_evidence_rejects_claim_text() -> None:
    """A model cannot hide uncited answer content inside an abstention response."""
    payload = json.dumps(
        {
            "decision": "insufficient_evidence",
            "claims": [{"text": "Maybe use hashes.", "citation_ids": ["C1"]}],
        }
    )

    with pytest.raises(
        GroundedSynthesisOutputError,
        match="empty claims array",
    ):
        parse_grounded_synthesis_output(payload, request=_request())


def test_rendered_answer_remains_under_original_synthesis_output_bound() -> None:
    """Citation-aware output cannot expand the Gate 7.6 application answer entitlement."""
    payload = json.dumps(
        {
            "decision": "answer",
            "claims": [
                {
                    "text": "This answer is longer than ten characters.",
                    "citation_ids": ["C1"],
                }
            ],
        }
    )

    with pytest.raises(
        GroundedSynthesisOutputError,
        match="result invariants",
    ):
        parse_grounded_synthesis_output(payload, request=_request(max_output_chars=10))


def test_grounded_request_rejects_catalog_from_another_context() -> None:
    """Citation authority cannot be rebound across synthesis contexts."""
    base_context = _context()
    other_context = _context(suffix="other")
    synthesis = build_synthesis_request(
        question=QUESTION,
        context=base_context,
        authority_decision=SynthesisAuthorityDecision.SUPPORTED,
    )

    with pytest.raises(
        GroundedSynthesisOutputError,
        match="not mutually admissible",
    ):
        build_grounded_synthesis_request(
            synthesis_request=synthesis,
            citation_catalog=project_citation_catalog(other_context),
        )
