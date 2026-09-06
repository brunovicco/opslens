"""Application services for bounded hybrid synthesis and output admission."""

from __future__ import annotations

import json
from typing import cast

from opslens.hybrid_retrieval.domain.errors import HybridRetrievalValidationError
from opslens.hybrid_retrieval.domain.evidence import HybridEvidenceEnvelope
from opslens.hybrid_retrieval.domain.models import HybridRoute
from opslens.hybrid_retrieval.domain.synthesis import (
    MAX_HYBRID_SYNTHESIS_CLAIMS,
    HybridStructuredFactProjection,
    HybridSynthesisClaim,
    HybridSynthesisDecision,
    HybridSynthesisLimits,
    HybridSynthesisRequest,
    HybridSynthesisResult,
    project_hybrid_structured_facts,
)

MAX_HYBRID_PROVIDER_RESPONSE_CHARS = 65_536


class HybridSynthesisOutputError(ValueError):
    """Raised when untrusted hybrid model output violates deterministic admission."""


def _admit_envelope(value: object) -> HybridEvidenceEnvelope:
    """Admit one runtime evidence envelope without weakening public annotations."""
    if not isinstance(value, HybridEvidenceEnvelope):
        raise HybridSynthesisOutputError(
            "envelope must be one admitted HybridEvidenceEnvelope"
        )
    return value


def _admit_payload(value: object) -> str:
    """Admit one runtime provider payload as text."""
    if not isinstance(value, str):
        raise HybridSynthesisOutputError("payload must be a string")
    return value


def _admit_request(value: object) -> HybridSynthesisRequest:
    """Admit one exact hybrid synthesis request at the output boundary."""
    if not isinstance(value, HybridSynthesisRequest):
        raise HybridSynthesisOutputError(
            "request must be an admitted HybridSynthesisRequest"
        )
    return value


def build_hybrid_synthesis_request(
    *,
    question: str,
    envelope: HybridEvidenceEnvelope,
    limits: HybridSynthesisLimits | None = None,
) -> HybridSynthesisRequest:
    """Admit one model request only from a complete semantic/hybrid envelope."""
    try:
        return HybridSynthesisRequest.create(
            question=question,
            envelope=envelope,
            limits=limits,
        )
    except HybridRetrievalValidationError as exc:
        raise HybridSynthesisOutputError(
            "hybrid synthesis request violates the deterministic authority contract"
        ) from exc


def project_deterministic_structured_answer(
    envelope: HybridEvidenceEnvelope,
) -> tuple[HybridStructuredFactProjection, ...]:
    """Expose exact structured facts without giving their truth authority to a model."""
    admitted_envelope = _admit_envelope(envelope)
    if admitted_envelope.authority_decision.route not in {
        HybridRoute.STRUCTURED,
        HybridRoute.HYBRID,
    }:
        if admitted_envelope.structured_evidence:
            raise HybridSynthesisOutputError(
                "structured evidence is inconsistent with the admitted route"
            )
        return ()
    try:
        return project_hybrid_structured_facts(admitted_envelope)
    except HybridRetrievalValidationError as exc:
        raise HybridSynthesisOutputError(
            "structured answer projection violates the deterministic evidence contract"
        ) from exc


def _parse_decision(value: object) -> HybridSynthesisDecision:
    """Admit only the frozen answer-or-insufficient-evidence decision set."""
    if not isinstance(value, str):
        raise HybridSynthesisOutputError("decision must be a string")
    try:
        return HybridSynthesisDecision(value)
    except ValueError as exc:
        raise HybridSynthesisOutputError(
            "decision must be answer or insufficient_evidence"
        ) from exc


def _parse_id_array(value: object, *, label: str) -> tuple[str, ...]:
    """Parse one JSON array containing only string evidence handles."""
    if not isinstance(value, list):
        raise HybridSynthesisOutputError(f"{label} must be an array")
    raw = cast(list[object], value)
    if any(not isinstance(item, str) for item in raw):
        raise HybridSynthesisOutputError(f"{label} must contain only strings")
    return tuple(cast(list[str], raw))


def _parse_claim(
    value: object,
    *,
    claim_index: int,
    request: HybridSynthesisRequest,
) -> HybridSynthesisClaim:
    """Parse one exact explanatory claim and enforce both evidence allowlists."""
    if not isinstance(value, dict):
        raise HybridSynthesisOutputError("each claim must be one JSON object")
    mapping = cast(dict[object, object], value)
    if set(mapping) != {
        "text",
        "semantic_citation_ids",
        "structured_fact_ids",
    }:
        raise HybridSynthesisOutputError(
            "each claim must contain exactly text, semantic_citation_ids, and "
            "structured_fact_ids"
        )
    text = mapping["text"]
    if not isinstance(text, str):
        raise HybridSynthesisOutputError("claim text must be a string")
    semantic_ids = _parse_id_array(
        mapping["semantic_citation_ids"],
        label="semantic_citation_ids",
    )
    structured_ids = _parse_id_array(
        mapping["structured_fact_ids"],
        label="structured_fact_ids",
    )
    try:
        return HybridSynthesisClaim.create(
            request=request,
            claim_index=claim_index,
            text=text,
            semantic_citation_ids=semantic_ids,
            structured_fact_ids=structured_ids,
        )
    except HybridRetrievalValidationError as exc:
        raise HybridSynthesisOutputError(
            "claim violates text or admitted hybrid evidence authority"
        ) from exc


def parse_hybrid_synthesis_output(
    payload: str,
    *,
    request: HybridSynthesisRequest,
) -> HybridSynthesisResult:
    """Parse exact JSON and reject invented facts, citations, or extra output fields."""
    admitted_payload = _admit_payload(payload)
    admitted_request = _admit_request(request)
    if len(admitted_payload) > MAX_HYBRID_PROVIDER_RESPONSE_CHARS:
        raise HybridSynthesisOutputError(
            "hybrid model output exceeds the hard response-size bound"
        )
    try:
        parsed: object = json.loads(admitted_payload)
    except json.JSONDecodeError as exc:
        raise HybridSynthesisOutputError(
            "hybrid model output must be one JSON object"
        ) from exc
    if not isinstance(parsed, dict):
        raise HybridSynthesisOutputError(
            "hybrid model output must be one JSON object"
        )
    mapping = cast(dict[object, object], parsed)
    if set(mapping) != {"decision", "claims"}:
        raise HybridSynthesisOutputError(
            "hybrid model output must contain exactly decision and claims"
        )
    decision = _parse_decision(mapping["decision"])
    raw_claims = mapping["claims"]
    if not isinstance(raw_claims, list):
        raise HybridSynthesisOutputError("claims must be an array")
    claim_values = cast(list[object], raw_claims)

    if decision is HybridSynthesisDecision.INSUFFICIENT_EVIDENCE:
        if claim_values:
            raise HybridSynthesisOutputError(
                "insufficient_evidence requires an empty claims array"
            )
        claims: tuple[HybridSynthesisClaim, ...] = ()
    else:
        if not 1 <= len(claim_values) <= MAX_HYBRID_SYNTHESIS_CLAIMS:
            raise HybridSynthesisOutputError(
                "answer requires at least one bounded explanatory claim"
            )
        claims = tuple(
            _parse_claim(
                item,
                claim_index=index,
                request=admitted_request,
            )
            for index, item in enumerate(claim_values, start=1)
        )

    try:
        return HybridSynthesisResult.create(
            request=admitted_request,
            decision=decision,
            claims=claims,
        )
    except HybridRetrievalValidationError as exc:
        raise HybridSynthesisOutputError(
            "hybrid model output violates result invariants"
        ) from exc