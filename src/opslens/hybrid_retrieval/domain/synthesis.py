"""Provider-independent contracts for bounded Phase 8 hybrid synthesis."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import Self, cast

from opslens.hybrid_retrieval.domain.errors import HybridRetrievalValidationError
from opslens.hybrid_retrieval.domain.evidence import (
    HybridEvidenceEnvelope,
    StructuredScalar,
)
from opslens.hybrid_retrieval.domain.models import HybridRoute

HYBRID_SYNTHESIS_CONTRACT_VERSION = "hybrid-synthesis:v1"
MAX_HYBRID_SYNTHESIS_QUESTION_CHARS = 1_000
MAX_HYBRID_SYNTHESIS_OUTPUT_CHARS = 4_000
MAX_HYBRID_SYNTHESIS_CLAIMS = 16
MAX_HYBRID_SYNTHESIS_CLAIM_CHARS = 1_000
MAX_HYBRID_SYNTHESIS_MODEL_CALLS = 1
MAX_HYBRID_SYNTHESIS_STRUCTURED_FACTS = 64
MAX_HYBRID_SYNTHESIS_SEMANTIC_CHUNKS = 10

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_FACT_ID_PATTERN = re.compile(r"^F[1-9][0-9]*$")
_CITATION_ID_PATTERN = re.compile(r"^S[1-9][0-9]*$")


def _canonical_json(payload: object) -> str:
    """Serialize deterministic identity evidence."""
    return json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _canonical_sha256(payload: object) -> str:
    """Return a SHA-256 digest for canonical JSON evidence."""
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _normalize_required_text(value: object, label: str) -> str:
    """Return one normalized non-empty string."""
    if not isinstance(value, str):
        raise HybridRetrievalValidationError(f"{label} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise HybridRetrievalValidationError(f"{label} cannot be blank.")
    return normalized


def _validate_sha256(value: object, label: str) -> str:
    """Require one lowercase hexadecimal SHA-256 digest."""
    normalized = _normalize_required_text(value, label)
    if _SHA256_PATTERN.fullmatch(normalized) is None:
        raise HybridRetrievalValidationError(
            f"{label} must be a 64-character lowercase hexadecimal SHA-256 digest."
        )
    return normalized


def _require_runtime_instance(value: object, expected_type: type[object], label: str) -> None:
    """Validate untrusted runtime values without weakening public annotations."""
    if not isinstance(value, expected_type):
        raise HybridRetrievalValidationError(f"{label} has an unsupported value.")


def _normalize_id_tuple(
    value: object,
    *,
    label: str,
    pattern: re.Pattern[str],
) -> tuple[str, ...]:
    """Validate one duplicate-free tuple of deterministic short IDs."""
    if not isinstance(value, tuple):
        raise HybridRetrievalValidationError(f"{label} must be a tuple.")
    raw = cast(tuple[object, ...], value)
    normalized = tuple(_normalize_required_text(item, f"{label} item") for item in raw)
    if any(pattern.fullmatch(item) is None for item in normalized):
        raise HybridRetrievalValidationError(f"{label} contains an invalid identifier.")
    if len(set(normalized)) != len(normalized):
        raise HybridRetrievalValidationError(f"{label} cannot contain duplicates.")
    return normalized


def _id_number(value: str) -> int:
    """Return the numeric suffix of one validated F/S identifier."""
    return int(value[1:])


class HybridSynthesisDecision(StrEnum):
    """Allowed model decisions after deterministic synthesis admission."""

    ANSWER = "answer"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True, slots=True)
class HybridSynthesisLimits:
    """Hard per-request limits for the first bounded hybrid synthesis contract."""

    max_output_chars: int = MAX_HYBRID_SYNTHESIS_OUTPUT_CHARS
    max_model_calls: int = MAX_HYBRID_SYNTHESIS_MODEL_CALLS

    def __post_init__(self) -> None:
        """Reject iterative or unbounded synthesis authority."""
        if type(self.max_output_chars) is not int or not (
            1 <= self.max_output_chars <= MAX_HYBRID_SYNTHESIS_OUTPUT_CHARS
        ):
            raise HybridRetrievalValidationError(
                "max_output_chars must be a positive bounded integer."
            )
        if type(self.max_model_calls) is not int or self.max_model_calls != 1:
            raise HybridRetrievalValidationError(
                "max_model_calls must equal one for hybrid synthesis v1."
            )


@dataclass(frozen=True, slots=True)
class HybridStructuredFactProjection:
    """One deterministic structured fact exposed to synthesis by short reference only."""

    fact_id: str
    evidence_id: str
    evidence_need: str
    authority: str
    source_artifact_id: str
    source_artifact_sha256: str
    row_key: str
    field_name: str
    value: StructuredScalar

    def __post_init__(self) -> None:
        """Validate deterministic projection fields without changing source authority."""
        fact_id = _normalize_required_text(self.fact_id, "fact_id")
        if _FACT_ID_PATTERN.fullmatch(fact_id) is None:
            raise HybridRetrievalValidationError("fact_id must use F1, F2, ... syntax.")
        object.__setattr__(self, "fact_id", fact_id)
        for field_name in (
            "evidence_id",
            "evidence_need",
            "authority",
            "source_artifact_id",
            "row_key",
            "field_name",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalize_required_text(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "source_artifact_sha256",
            _validate_sha256(self.source_artifact_sha256, "source_artifact_sha256"),
        )

    def to_prompt_payload(self) -> dict[str, object]:
        """Return canonical model-visible structured evidence without inventing prose."""
        return {
            "authority": self.authority,
            "evidence_id": self.evidence_id,
            "evidence_need": self.evidence_need,
            "fact_id": self.fact_id,
            "field_name": self.field_name,
            "row_key": self.row_key,
            "source_artifact_id": self.source_artifact_id,
            "source_artifact_sha256": self.source_artifact_sha256,
            "value": self.value,
        }


@dataclass(frozen=True, slots=True)
class HybridSemanticCitationProjection:
    """One deterministic citation handle for an admitted semantic evidence chunk."""

    citation_id: str
    evidence_id: str
    chunk_id: str
    document_id: str
    source_id: str
    source_type: str
    canonical_uri: str
    document_content_sha256: str
    chunk_content_sha256: str
    rank: int
    text: str
    title: str | None
    section_path: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate short citation identity and immutable provenance projection."""
        citation_id = _normalize_required_text(self.citation_id, "citation_id")
        if _CITATION_ID_PATTERN.fullmatch(citation_id) is None:
            raise HybridRetrievalValidationError(
                "citation_id must use S1, S2, ... syntax."
            )
        object.__setattr__(self, "citation_id", citation_id)
        for field_name in (
            "evidence_id",
            "chunk_id",
            "document_id",
            "source_id",
            "source_type",
            "canonical_uri",
            "text",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalize_required_text(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "document_content_sha256",
            _validate_sha256(self.document_content_sha256, "document_content_sha256"),
        )
        object.__setattr__(
            self,
            "chunk_content_sha256",
            _validate_sha256(self.chunk_content_sha256, "chunk_content_sha256"),
        )
        if type(self.rank) is not int or self.rank < 1:
            raise HybridRetrievalValidationError("semantic citation rank must be positive.")
        if self.title is not None:
            object.__setattr__(
                self,
                "title",
                _normalize_required_text(self.title, "title"),
            )
        if not isinstance(self.section_path, tuple) or any(
            not isinstance(item, str) or not item.strip() for item in self.section_path
        ):
            raise HybridRetrievalValidationError(
                "section_path must contain only non-empty strings."
            )

    def to_prompt_payload(self) -> dict[str, object]:
        """Return canonical model-visible semantic evidence as untrusted data."""
        return {
            "canonical_uri": self.canonical_uri,
            "chunk_content_sha256": self.chunk_content_sha256,
            "chunk_id": self.chunk_id,
            "citation_id": self.citation_id,
            "document_content_sha256": self.document_content_sha256,
            "document_id": self.document_id,
            "evidence_id": self.evidence_id,
            "rank": self.rank,
            "section_path": list(self.section_path),
            "source_id": self.source_id,
            "source_type": self.source_type,
            "text": self.text,
            "title": self.title,
        }


def project_hybrid_structured_facts(
    envelope: HybridEvidenceEnvelope,
) -> tuple[HybridStructuredFactProjection, ...]:
    """Project exact structured fields to deterministic F1, F2, ... handles."""
    _require_runtime_instance(envelope, HybridEvidenceEnvelope, "envelope")
    projections: list[HybridStructuredFactProjection] = []
    for row in envelope.structured_evidence:
        for field in row.fields:
            projections.append(
                HybridStructuredFactProjection(
                    fact_id=f"F{len(projections) + 1}",
                    evidence_id=row.evidence_id,
                    evidence_need=row.evidence_need.value,
                    authority=row.authority.value,
                    source_artifact_id=row.source_artifact_id,
                    source_artifact_sha256=row.source_artifact_sha256,
                    row_key=row.row_key,
                    field_name=field.name,
                    value=field.value,
                )
            )
    if len(projections) > MAX_HYBRID_SYNTHESIS_STRUCTURED_FACTS:
        raise HybridRetrievalValidationError(
            "structured fact projection exceeds the Gate 8.4 hard bound."
        )
    return tuple(projections)


def project_hybrid_semantic_citations(
    envelope: HybridEvidenceEnvelope,
) -> tuple[HybridSemanticCitationProjection, ...]:
    """Project admitted semantic chunks to deterministic S1, S2, ... handles."""
    _require_runtime_instance(envelope, HybridEvidenceEnvelope, "envelope")
    if len(envelope.semantic_evidence) > MAX_HYBRID_SYNTHESIS_SEMANTIC_CHUNKS:
        raise HybridRetrievalValidationError(
            "semantic evidence exceeds the Gate 8.4 hard chunk bound."
        )
    return tuple(
        HybridSemanticCitationProjection(
            citation_id=f"S{item.rank}",
            evidence_id=item.evidence_id,
            chunk_id=item.chunk_id,
            document_id=item.document_id,
            source_id=item.source_id,
            source_type=item.source_type,
            canonical_uri=item.canonical_uri,
            document_content_sha256=item.document_content_sha256,
            chunk_content_sha256=item.chunk_content_sha256,
            rank=item.rank,
            text=item.text,
            title=item.title,
            section_path=item.section_path,
        )
        for item in envelope.semantic_evidence
    )


@dataclass(frozen=True, slots=True)
class HybridSynthesisRequest:
    """One admitted semantic/hybrid model request bound to an exact evidence envelope."""

    question: str
    question_sha256: str
    envelope: HybridEvidenceEnvelope
    limits: HybridSynthesisLimits
    structured_catalog_sha256: str
    semantic_catalog_sha256: str
    request_sha256: str

    def __post_init__(self) -> None:
        """Reject model execution outside admitted semantic/hybrid authority."""
        question = _normalize_required_text(self.question, "question")
        if len(question) > MAX_HYBRID_SYNTHESIS_QUESTION_CHARS:
            raise HybridRetrievalValidationError(
                f"question cannot exceed {MAX_HYBRID_SYNTHESIS_QUESTION_CHARS} characters."
            )
        object.__setattr__(self, "question", question)
        question_sha256 = _validate_sha256(self.question_sha256, "question_sha256")
        if question_sha256 != sha256(question.encode("utf-8")).hexdigest():
            raise HybridRetrievalValidationError(
                "question_sha256 must match the exact normalized question."
            )
        object.__setattr__(self, "question_sha256", question_sha256)
        _require_runtime_instance(self.envelope, HybridEvidenceEnvelope, "envelope")
        if self.envelope.authority_decision.route not in {
            HybridRoute.SEMANTIC,
            HybridRoute.HYBRID,
        }:
            raise HybridRetrievalValidationError(
                "only semantic or hybrid routes may form a model synthesis request."
            )
        if not self.envelope.semantic_evidence:
            raise HybridRetrievalValidationError(
                "model synthesis requires admitted semantic evidence."
            )
        _require_runtime_instance(self.limits, HybridSynthesisLimits, "limits")

        structured = project_hybrid_structured_facts(self.envelope)
        semantic = project_hybrid_semantic_citations(self.envelope)
        expected_structured_catalog_sha256 = _canonical_sha256(
            [item.to_prompt_payload() for item in structured]
        )
        expected_semantic_catalog_sha256 = _canonical_sha256(
            [item.to_prompt_payload() for item in semantic]
        )
        structured_digest = _validate_sha256(
            self.structured_catalog_sha256,
            "structured_catalog_sha256",
        )
        semantic_digest = _validate_sha256(
            self.semantic_catalog_sha256,
            "semantic_catalog_sha256",
        )
        if structured_digest != expected_structured_catalog_sha256:
            raise HybridRetrievalValidationError(
                "structured catalog hash does not match exact envelope projection."
            )
        if semantic_digest != expected_semantic_catalog_sha256:
            raise HybridRetrievalValidationError(
                "semantic catalog hash does not match exact envelope projection."
            )
        object.__setattr__(self, "structured_catalog_sha256", structured_digest)
        object.__setattr__(self, "semantic_catalog_sha256", semantic_digest)

        request_digest = _validate_sha256(self.request_sha256, "request_sha256")
        expected_request_sha256 = _canonical_sha256(
            {
                "contract_version": HYBRID_SYNTHESIS_CONTRACT_VERSION,
                "envelope_id": self.envelope.envelope_id,
                "limits": {
                    "max_model_calls": self.limits.max_model_calls,
                    "max_output_chars": self.limits.max_output_chars,
                },
                "question_sha256": question_sha256,
                "semantic_catalog_sha256": semantic_digest,
                "structured_catalog_sha256": structured_digest,
            }
        )
        if request_digest != expected_request_sha256:
            raise HybridRetrievalValidationError(
                "request_sha256 must match exact hybrid synthesis authority evidence."
            )
        object.__setattr__(self, "request_sha256", request_digest)

    @classmethod
    def create(
        cls,
        *,
        question: str,
        envelope: HybridEvidenceEnvelope,
        limits: HybridSynthesisLimits | None = None,
    ) -> Self:
        """Create a model request only after deterministic envelope admission."""
        normalized_question = _normalize_required_text(question, "question")
        admitted_limits = limits if limits is not None else HybridSynthesisLimits()
        _require_runtime_instance(envelope, HybridEvidenceEnvelope, "envelope")
        _require_runtime_instance(admitted_limits, HybridSynthesisLimits, "limits")
        structured = project_hybrid_structured_facts(envelope)
        semantic = project_hybrid_semantic_citations(envelope)
        structured_digest = _canonical_sha256(
            [item.to_prompt_payload() for item in structured]
        )
        semantic_digest = _canonical_sha256(
            [item.to_prompt_payload() for item in semantic]
        )
        question_digest = sha256(normalized_question.encode("utf-8")).hexdigest()
        request_digest = _canonical_sha256(
            {
                "contract_version": HYBRID_SYNTHESIS_CONTRACT_VERSION,
                "envelope_id": envelope.envelope_id,
                "limits": {
                    "max_model_calls": admitted_limits.max_model_calls,
                    "max_output_chars": admitted_limits.max_output_chars,
                },
                "question_sha256": question_digest,
                "semantic_catalog_sha256": semantic_digest,
                "structured_catalog_sha256": structured_digest,
            }
        )
        return cls(
            question=normalized_question,
            question_sha256=question_digest,
            envelope=envelope,
            limits=admitted_limits,
            structured_catalog_sha256=structured_digest,
            semantic_catalog_sha256=semantic_digest,
            request_sha256=request_digest,
        )

    @property
    def structured_facts(self) -> tuple[HybridStructuredFactProjection, ...]:
        """Return exact deterministic structured facts; the model does not author them."""
        return project_hybrid_structured_facts(self.envelope)

    @property
    def semantic_citations(self) -> tuple[HybridSemanticCitationProjection, ...]:
        """Return exact semantic evidence citation handles."""
        return project_hybrid_semantic_citations(self.envelope)


@dataclass(frozen=True, slots=True)
class HybridSynthesisClaim:
    """One model-proposed explanatory claim bound to admitted evidence handles."""

    claim_index: int
    text: str
    semantic_citation_ids: tuple[str, ...]
    structured_fact_ids: tuple[str, ...]
    request_sha256: str

    def __post_init__(self) -> None:
        """Enforce bounded text, citation syntax, and request identity syntax."""
        if type(self.claim_index) is not int or not (
            1 <= self.claim_index <= MAX_HYBRID_SYNTHESIS_CLAIMS
        ):
            raise HybridRetrievalValidationError(
                "claim_index is outside the hybrid synthesis claim bound."
            )
        text = _normalize_required_text(self.text, "claim text")
        if len(text) > MAX_HYBRID_SYNTHESIS_CLAIM_CHARS:
            raise HybridRetrievalValidationError(
                "hybrid synthesis claim exceeds the hard character bound."
            )
        object.__setattr__(self, "text", text)
        semantic_ids = _normalize_id_tuple(
            self.semantic_citation_ids,
            label="semantic_citation_ids",
            pattern=_CITATION_ID_PATTERN,
        )
        if not semantic_ids:
            raise HybridRetrievalValidationError(
                "model-authored claims require at least one semantic citation."
            )
        structured_ids = _normalize_id_tuple(
            self.structured_fact_ids,
            label="structured_fact_ids",
            pattern=_FACT_ID_PATTERN,
        )
        object.__setattr__(self, "semantic_citation_ids", semantic_ids)
        object.__setattr__(self, "structured_fact_ids", structured_ids)
        object.__setattr__(
            self,
            "request_sha256",
            _validate_sha256(self.request_sha256, "request_sha256"),
        )

    @classmethod
    def create(
        cls,
        *,
        request: HybridSynthesisRequest,
        claim_index: int,
        text: str,
        semantic_citation_ids: tuple[str, ...],
        structured_fact_ids: tuple[str, ...] = (),
    ) -> Self:
        """Admit model references only when they resolve inside the exact request."""
        _require_runtime_instance(request, HybridSynthesisRequest, "request")
        semantic_ids = _normalize_id_tuple(
            semantic_citation_ids,
            label="semantic_citation_ids",
            pattern=_CITATION_ID_PATTERN,
        )
        structured_ids = _normalize_id_tuple(
            structured_fact_ids,
            label="structured_fact_ids",
            pattern=_FACT_ID_PATTERN,
        )
        allowed_semantic = {item.citation_id for item in request.semantic_citations}
        allowed_structured = {item.fact_id for item in request.structured_facts}
        if set(semantic_ids) - allowed_semantic:
            raise HybridRetrievalValidationError(
                "claim references semantic citation IDs outside the admitted request."
            )
        if set(structured_ids) - allowed_structured:
            raise HybridRetrievalValidationError(
                "claim references structured fact IDs outside the admitted request."
            )
        if (
            request.envelope.authority_decision.route is HybridRoute.SEMANTIC
            and structured_ids
        ):
            raise HybridRetrievalValidationError(
                "semantic-only synthesis cannot reference structured fact IDs."
            )
        canonical_semantic = tuple(sorted(semantic_ids, key=_id_number))
        canonical_structured = tuple(sorted(structured_ids, key=_id_number))
        return cls(
            claim_index=claim_index,
            text=text,
            semantic_citation_ids=canonical_semantic,
            structured_fact_ids=canonical_structured,
            request_sha256=request.request_sha256,
        )


@dataclass(frozen=True, slots=True)
class HybridSynthesisResult:
    """Provider-independent admitted model result; structured truth remains separate."""

    request_sha256: str
    decision: HybridSynthesisDecision
    claims: tuple[HybridSynthesisClaim, ...]
    rendered_explanation: str | None
    result_sha256: str

    def __post_init__(self) -> None:
        """Enforce answer/abstention shape and deterministic result identity."""
        request_digest = _validate_sha256(self.request_sha256, "request_sha256")
        object.__setattr__(self, "request_sha256", request_digest)
        _require_runtime_instance(self.decision, HybridSynthesisDecision, "decision")
        if not isinstance(self.claims, tuple) or any(
            not isinstance(item, HybridSynthesisClaim) for item in self.claims
        ):
            raise HybridRetrievalValidationError(
                "claims must contain only HybridSynthesisClaim values."
            )
        claims = cast(tuple[HybridSynthesisClaim, ...], self.claims)
        if any(item.request_sha256 != request_digest for item in claims):
            raise HybridRetrievalValidationError(
                "all claims must reference the exact hybrid synthesis request."
            )
        object.__setattr__(self, "claims", claims)

        if self.decision is HybridSynthesisDecision.ANSWER:
            if not claims:
                raise HybridRetrievalValidationError(
                    "answer decision requires at least one explanatory claim."
                )
            expected_indices = tuple(range(1, len(claims) + 1))
            if tuple(item.claim_index for item in claims) != expected_indices:
                raise HybridRetrievalValidationError(
                    "claim indices must be contiguous from one."
                )
            rendered = "\n\n".join(item.text for item in claims)
            if self.rendered_explanation != rendered:
                raise HybridRetrievalValidationError(
                    "rendered_explanation must equal deterministic claim rendering."
                )
        elif claims or self.rendered_explanation is not None:
            raise HybridRetrievalValidationError(
                "insufficient_evidence must not contain claims or explanation text."
            )

        result_digest = _validate_sha256(self.result_sha256, "result_sha256")
        expected_result_digest = _canonical_sha256(
            {
                "claims": [
                    {
                        "claim_index": item.claim_index,
                        "semantic_citation_ids": list(item.semantic_citation_ids),
                        "structured_fact_ids": list(item.structured_fact_ids),
                        "text": item.text,
                    }
                    for item in claims
                ],
                "decision": self.decision.value,
                "request_sha256": request_digest,
            }
        )
        if result_digest != expected_result_digest:
            raise HybridRetrievalValidationError(
                "result_sha256 must match exact admitted hybrid model output."
            )
        object.__setattr__(self, "result_sha256", result_digest)

    @classmethod
    def create(
        cls,
        *,
        request: HybridSynthesisRequest,
        decision: HybridSynthesisDecision,
        claims: tuple[HybridSynthesisClaim, ...],
    ) -> Self:
        """Create one admitted hybrid model result under exact request limits."""
        _require_runtime_instance(request, HybridSynthesisRequest, "request")
        _require_runtime_instance(decision, HybridSynthesisDecision, "decision")
        if not isinstance(claims, tuple) or any(
            not isinstance(item, HybridSynthesisClaim) for item in claims
        ):
            raise HybridRetrievalValidationError(
                "claims must contain only HybridSynthesisClaim values."
            )
        if len(claims) > MAX_HYBRID_SYNTHESIS_CLAIMS:
            raise HybridRetrievalValidationError("too many hybrid synthesis claims.")
        if any(item.request_sha256 != request.request_sha256 for item in claims):
            raise HybridRetrievalValidationError(
                "claims do not belong to the admitted hybrid synthesis request."
            )
        rendered: str | None
        if decision is HybridSynthesisDecision.ANSWER:
            if not claims:
                raise HybridRetrievalValidationError(
                    "answer decision requires at least one explanatory claim."
                )
            rendered = "\n\n".join(item.text for item in claims)
            if len(rendered) > request.limits.max_output_chars:
                raise HybridRetrievalValidationError(
                    "hybrid explanation exceeds the admitted output bound."
                )
        else:
            if claims:
                raise HybridRetrievalValidationError(
                    "insufficient_evidence cannot contain explanatory claims."
                )
            rendered = None
        result_digest = _canonical_sha256(
            {
                "claims": [
                    {
                        "claim_index": item.claim_index,
                        "semantic_citation_ids": list(item.semantic_citation_ids),
                        "structured_fact_ids": list(item.structured_fact_ids),
                        "text": item.text,
                    }
                    for item in claims
                ],
                "decision": decision.value,
                "request_sha256": request.request_sha256,
            }
        )
        return cls(
            request_sha256=request.request_sha256,
            decision=decision,
            claims=claims,
            rendered_explanation=rendered,
            result_sha256=result_digest,
        )