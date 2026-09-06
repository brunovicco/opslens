"""Offline claim-to-citation admission for grounded knowledge synthesis."""

from __future__ import annotations

import json
from typing import cast

from opslens.knowledge_retrieval.domain import CitationCatalog, SynthesisDecision, SynthesisRequest
from opslens.knowledge_retrieval.domain.errors import KnowledgeRetrievalValidationError
from opslens.knowledge_retrieval.domain.grounding import (
    MAX_GROUNDED_CLAIMS,
    GroundedClaim,
    GroundedSynthesisRequest,
    GroundedSynthesisResult,
)

MAX_GROUNDED_PROVIDER_RESPONSE_CHARS = 65_536


class GroundedSynthesisOutputError(ValueError):
    """Raised when untrusted citation-aware model output violates the frozen contract."""


def _is_runtime_instance(value: object, expected_type: type[object]) -> bool:
    """Check untrusted runtime values without weakening public annotations."""
    return isinstance(value, expected_type)


def build_grounded_synthesis_request(
    *,
    synthesis_request: SynthesisRequest,
    citation_catalog: CitationCatalog,
) -> GroundedSynthesisRequest:
    """Bind existing synthesis authority to deterministic citation authority."""
    if not _is_runtime_instance(synthesis_request, SynthesisRequest):
        raise GroundedSynthesisOutputError(
            "synthesis_request must be a SynthesisRequest value"
        )
    if not _is_runtime_instance(citation_catalog, CitationCatalog):
        raise GroundedSynthesisOutputError(
            "citation_catalog must be a CitationCatalog value"
        )
    try:
        return GroundedSynthesisRequest.create(
            synthesis_request=synthesis_request,
            citation_catalog=citation_catalog,
        )
    except KnowledgeRetrievalValidationError as exc:
        raise GroundedSynthesisOutputError(
            "synthesis request and citation catalog are not mutually admissible"
        ) from exc


def _parse_decision(value: object) -> SynthesisDecision:
    """Accept only the existing answer-or-abstain semantic decision set."""
    if not isinstance(value, str):
        raise GroundedSynthesisOutputError("decision must be a string")
    try:
        return SynthesisDecision(value)
    except ValueError as exc:
        raise GroundedSynthesisOutputError(
            "decision must be answer or insufficient_evidence"
        ) from exc


def _parse_claim(
    value: object,
    *,
    claim_index: int,
    request: GroundedSynthesisRequest,
) -> GroundedClaim:
    """Parse one exact claim object and admit only allowlisted citation IDs."""
    if not isinstance(value, dict):
        raise GroundedSynthesisOutputError("each claim must be one JSON object")
    mapping = cast(dict[object, object], value)
    if set(mapping) != {"text", "citation_ids"}:
        raise GroundedSynthesisOutputError(
            "each claim must contain exactly text and citation_ids"
        )

    text = mapping["text"]
    if not isinstance(text, str):
        raise GroundedSynthesisOutputError("claim text must be a string")

    raw_ids = mapping["citation_ids"]
    if not isinstance(raw_ids, list):
        raise GroundedSynthesisOutputError("claim citation_ids must be an array")
    items = cast(list[object], raw_ids)
    if any(not isinstance(item, str) for item in items):
        raise GroundedSynthesisOutputError(
            "claim citation_ids must contain only strings"
        )

    try:
        return GroundedClaim.create(
            claim_index=claim_index,
            text=text,
            citation_ids=tuple(cast(list[str], items)),
            citation_catalog=request.citation_catalog,
        )
    except KnowledgeRetrievalValidationError as exc:
        raise GroundedSynthesisOutputError(
            "claim violates text or admitted citation authority"
        ) from exc


def parse_grounded_synthesis_output(
    payload: str,
    *,
    request: GroundedSynthesisRequest,
) -> GroundedSynthesisResult:
    """Parse exact JSON claims and reject uncited or non-canonical citation proposals."""
    if not _is_runtime_instance(payload, str):
        raise GroundedSynthesisOutputError("payload must be a string")
    if not _is_runtime_instance(request, GroundedSynthesisRequest):
        raise GroundedSynthesisOutputError(
            "request must be a GroundedSynthesisRequest value"
        )
    if len(payload) > MAX_GROUNDED_PROVIDER_RESPONSE_CHARS:
        raise GroundedSynthesisOutputError(
            "grounded model output exceeds the hard response-size bound"
        )

    try:
        parsed: object = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise GroundedSynthesisOutputError(
            "grounded model output must be one JSON object"
        ) from exc
    if not isinstance(parsed, dict):
        raise GroundedSynthesisOutputError(
            "grounded model output must be one JSON object"
        )
    mapping = cast(dict[object, object], parsed)
    if set(mapping) != {"decision", "claims"}:
        raise GroundedSynthesisOutputError(
            "grounded model output must contain exactly decision and claims"
        )

    decision = _parse_decision(mapping["decision"])
    raw_claims = mapping["claims"]
    if not isinstance(raw_claims, list):
        raise GroundedSynthesisOutputError("claims must be an array")
    claim_values = cast(list[object], raw_claims)

    if decision is SynthesisDecision.INSUFFICIENT_EVIDENCE:
        if claim_values:
            raise GroundedSynthesisOutputError(
                "insufficient_evidence requires an empty claims array"
            )
        claims: tuple[GroundedClaim, ...] = ()
    else:
        if not 1 <= len(claim_values) <= MAX_GROUNDED_CLAIMS:
            raise GroundedSynthesisOutputError(
                f"answer requires between 1 and {MAX_GROUNDED_CLAIMS} claims"
            )
        claims = tuple(
            _parse_claim(item, claim_index=index, request=request)
            for index, item in enumerate(claim_values, start=1)
        )

    try:
        return GroundedSynthesisResult.create(
            request=request,
            decision=decision,
            claims=claims,
        )
    except KnowledgeRetrievalValidationError as exc:
        raise GroundedSynthesisOutputError(
            "grounded model output violates result invariants"
        ) from exc
