"""Provider-independent claim/citation contracts for grounded knowledge synthesis."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Self, cast

from opslens.knowledge_retrieval.domain.citations import CitationCatalog
from opslens.knowledge_retrieval.domain.errors import KnowledgeRetrievalValidationError
from opslens.knowledge_retrieval.domain.synthesis import SynthesisDecision, SynthesisRequest

GROUNDED_SYNTHESIS_CONTRACT_ID = "knowledge-grounded-synthesis:v1"
MAX_GROUNDED_CLAIMS = 16
MAX_GROUNDED_CLAIM_CHARS = 1_000

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_CITATION_ID_PATTERN = re.compile(r"^C[1-9][0-9]*$")


def _is_runtime_instance(value: object, expected_type: type[object]) -> bool:
    """Check untrusted runtime values without weakening public annotations."""
    return isinstance(value, expected_type)


def _normalize_required_text(value: object, label: str) -> str:
    """Return one trimmed non-empty string or fail closed."""
    if not isinstance(value, str):
        raise KnowledgeRetrievalValidationError(f"{label} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise KnowledgeRetrievalValidationError(f"{label} cannot be blank.")
    return normalized


def _validate_sha256(value: object, label: str) -> str:
    """Require one lowercase hexadecimal SHA-256 digest."""
    normalized = _normalize_required_text(value, label)
    if _SHA256_PATTERN.fullmatch(normalized) is None:
        raise KnowledgeRetrievalValidationError(
            f"{label} must be a 64-character lowercase hexadecimal SHA-256 digest."
        )
    return normalized


def _canonical_json_bytes(payload: object) -> bytes:
    """Serialize deterministic grounded-synthesis identity evidence."""
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _grounded_request_payload(
    *,
    synthesis_request_sha256: str,
    citation_catalog_sha256: str,
) -> dict[str, object]:
    """Build content-free identity for one grounded synthesis request."""
    return {
        "citation_catalog_sha256": citation_catalog_sha256,
        "contract_id": GROUNDED_SYNTHESIS_CONTRACT_ID,
        "synthesis_request_sha256": synthesis_request_sha256,
    }


@dataclass(frozen=True, slots=True)
class GroundedSynthesisRequest:
    """Bind one admitted synthesis request to its deterministic citation catalog."""

    synthesis_request: SynthesisRequest
    citation_catalog: CitationCatalog
    grounded_request_sha256: str

    def __post_init__(self) -> None:
        """Require context/catalog identity before citation-aware model use is possible."""
        if not _is_runtime_instance(self.synthesis_request, SynthesisRequest):
            raise KnowledgeRetrievalValidationError(
                "synthesis_request must be a SynthesisRequest value."
            )
        if not _is_runtime_instance(self.citation_catalog, CitationCatalog):
            raise KnowledgeRetrievalValidationError(
                "citation_catalog must be a CitationCatalog value."
            )
        if (
            self.citation_catalog.context_sha256
            != self.synthesis_request.context.context_sha256
        ):
            raise KnowledgeRetrievalValidationError(
                "citation catalog must reference the exact synthesis context."
            )

        digest = _validate_sha256(
            self.grounded_request_sha256,
            "grounded_request_sha256",
        )
        expected = sha256(
            _canonical_json_bytes(
                _grounded_request_payload(
                    synthesis_request_sha256=self.synthesis_request.request_sha256,
                    citation_catalog_sha256=self.citation_catalog.catalog_sha256,
                )
            )
        ).hexdigest()
        if digest != expected:
            raise KnowledgeRetrievalValidationError(
                "grounded_request_sha256 must match synthesis and citation authority."
            )
        object.__setattr__(self, "grounded_request_sha256", digest)

    @classmethod
    def create(
        cls,
        *,
        synthesis_request: SynthesisRequest,
        citation_catalog: CitationCatalog,
    ) -> Self:
        """Create one grounded request only after deterministic context/citation admission."""
        if not _is_runtime_instance(synthesis_request, SynthesisRequest):
            raise KnowledgeRetrievalValidationError(
                "synthesis_request must be a SynthesisRequest value."
            )
        if not _is_runtime_instance(citation_catalog, CitationCatalog):
            raise KnowledgeRetrievalValidationError(
                "citation_catalog must be a CitationCatalog value."
            )
        digest = sha256(
            _canonical_json_bytes(
                _grounded_request_payload(
                    synthesis_request_sha256=synthesis_request.request_sha256,
                    citation_catalog_sha256=citation_catalog.catalog_sha256,
                )
            )
        ).hexdigest()
        return cls(
            synthesis_request=synthesis_request,
            citation_catalog=citation_catalog,
            grounded_request_sha256=digest,
        )


def _normalize_citation_ids(value: object) -> tuple[str, ...]:
    """Require one non-empty tuple of unique deterministic citation IDs."""
    if not isinstance(value, tuple):
        raise KnowledgeRetrievalValidationError("citation_ids must be a tuple.")
    values = cast(tuple[object, ...], value)
    if not values:
        raise KnowledgeRetrievalValidationError(
            "answer claims must reference at least one citation ID."
        )
    normalized = tuple(_normalize_required_text(item, "citation_id") for item in values)
    if any(_CITATION_ID_PATTERN.fullmatch(item) is None for item in normalized):
        raise KnowledgeRetrievalValidationError(
            "citation_ids must use deterministic C1, C2, ... identifiers."
        )
    if len(set(normalized)) != len(normalized):
        raise KnowledgeRetrievalValidationError("citation_ids cannot contain duplicates.")
    return normalized


def _claim_payload(
    *,
    claim_index: int,
    text: str,
    citation_ids: tuple[str, ...],
    citation_catalog_sha256: str,
) -> dict[str, object]:
    """Build exact claim identity without source bodies."""
    return {
        "citation_catalog_sha256": citation_catalog_sha256,
        "citation_ids": list(citation_ids),
        "claim_index": claim_index,
        "text": text,
    }


@dataclass(frozen=True, slots=True)
class GroundedClaim:
    """One model-proposed answer claim bound to allowlisted canonical citation IDs."""

    claim_index: int
    text: str
    citation_ids: tuple[str, ...]
    citation_catalog_sha256: str
    claim_sha256: str

    def __post_init__(self) -> None:
        """Require bounded claim text, citation syntax, and content-addressed identity."""
        if (
            type(self.claim_index) is not int
            or not 1 <= self.claim_index <= MAX_GROUNDED_CLAIMS
        ):
            raise KnowledgeRetrievalValidationError(
                f"claim_index must be an integer from 1 to {MAX_GROUNDED_CLAIMS}."
            )
        text = _normalize_required_text(self.text, "claim text")
        if len(text) > MAX_GROUNDED_CLAIM_CHARS:
            raise KnowledgeRetrievalValidationError(
                f"claim text cannot exceed {MAX_GROUNDED_CLAIM_CHARS} characters."
            )
        object.__setattr__(self, "text", text)
        citation_ids = _normalize_citation_ids(self.citation_ids)
        object.__setattr__(self, "citation_ids", citation_ids)
        catalog_digest = _validate_sha256(
            self.citation_catalog_sha256,
            "citation_catalog_sha256",
        )
        object.__setattr__(self, "citation_catalog_sha256", catalog_digest)

        claim_digest = _validate_sha256(self.claim_sha256, "claim_sha256")
        expected = sha256(
            _canonical_json_bytes(
                _claim_payload(
                    claim_index=self.claim_index,
                    text=text,
                    citation_ids=citation_ids,
                    citation_catalog_sha256=catalog_digest,
                )
            )
        ).hexdigest()
        if claim_digest != expected:
            raise KnowledgeRetrievalValidationError(
                "claim_sha256 must match exact grounded claim evidence."
            )
        object.__setattr__(self, "claim_sha256", claim_digest)

    @classmethod
    def create(
        cls,
        *,
        claim_index: int,
        text: str,
        citation_ids: tuple[str, ...],
        citation_catalog: CitationCatalog,
    ) -> Self:
        """Create one claim after validating references against the exact catalog."""
        if not _is_runtime_instance(citation_catalog, CitationCatalog):
            raise KnowledgeRetrievalValidationError(
                "citation_catalog must be a CitationCatalog value."
            )
        normalized_text = _normalize_required_text(text, "claim text")
        normalized_ids = _normalize_citation_ids(citation_ids)
        allowed = {
            item.citation.citation_id: item.retrieval_rank
            for item in citation_catalog.citations
        }
        unknown = set(normalized_ids) - set(allowed)
        if unknown:
            raise KnowledgeRetrievalValidationError(
                "claim references citation IDs outside the admitted citation catalog."
            )
        canonical_ids = tuple(sorted(normalized_ids, key=allowed.__getitem__))
        digest = sha256(
            _canonical_json_bytes(
                _claim_payload(
                    claim_index=claim_index,
                    text=normalized_text,
                    citation_ids=canonical_ids,
                    citation_catalog_sha256=citation_catalog.catalog_sha256,
                )
            )
        ).hexdigest()
        return cls(
            claim_index=claim_index,
            text=normalized_text,
            citation_ids=canonical_ids,
            citation_catalog_sha256=citation_catalog.catalog_sha256,
            claim_sha256=digest,
        )


def _normalize_claims(value: object) -> tuple[GroundedClaim, ...]:
    """Require one bounded tuple containing only grounded claims."""
    if not isinstance(value, tuple):
        raise KnowledgeRetrievalValidationError("claims must be a tuple.")
    values = cast(tuple[object, ...], value)
    if len(values) > MAX_GROUNDED_CLAIMS:
        raise KnowledgeRetrievalValidationError(
            f"claims cannot contain more than {MAX_GROUNDED_CLAIMS} entries."
        )
    if any(not _is_runtime_instance(item, GroundedClaim) for item in values):
        raise KnowledgeRetrievalValidationError(
            "claims must contain only GroundedClaim values."
        )
    return cast(tuple[GroundedClaim, ...], values)


def _result_payload(
    *,
    grounded_request_sha256: str,
    citation_catalog_sha256: str,
    decision: SynthesisDecision,
    claims: tuple[GroundedClaim, ...],
) -> dict[str, object]:
    """Build content-addressed grounded result identity."""
    return {
        "citation_catalog_sha256": citation_catalog_sha256,
        "claim_sha256s": [claim.claim_sha256 for claim in claims],
        "decision": decision.value,
        "grounded_request_sha256": grounded_request_sha256,
    }


@dataclass(frozen=True, slots=True)
class GroundedSynthesisResult:
    """Citation-aware answer/abstention result after deterministic output admission."""

    grounded_request_sha256: str
    citation_catalog_sha256: str
    decision: SynthesisDecision
    claims: tuple[GroundedClaim, ...]
    rendered_answer: str | None
    result_sha256: str

    def __post_init__(self) -> None:
        """Enforce claim coverage, answer bounds, catalog identity, and result hash."""
        request_digest = _validate_sha256(
            self.grounded_request_sha256,
            "grounded_request_sha256",
        )
        catalog_digest = _validate_sha256(
            self.citation_catalog_sha256,
            "citation_catalog_sha256",
        )
        object.__setattr__(self, "grounded_request_sha256", request_digest)
        object.__setattr__(self, "citation_catalog_sha256", catalog_digest)
        if not _is_runtime_instance(self.decision, SynthesisDecision):
            raise KnowledgeRetrievalValidationError(
                "decision must be a SynthesisDecision value."
            )
        claims = _normalize_claims(self.claims)
        object.__setattr__(self, "claims", claims)

        if self.decision is SynthesisDecision.ANSWER:
            if not claims:
                raise KnowledgeRetrievalValidationError(
                    "answer decision requires at least one grounded claim."
                )
            expected_indices = tuple(range(1, len(claims) + 1))
            actual_indices = tuple(claim.claim_index for claim in claims)
            if actual_indices != expected_indices:
                raise KnowledgeRetrievalValidationError(
                    "grounded claim indices must be contiguous from 1."
                )
            if any(
                claim.citation_catalog_sha256 != catalog_digest for claim in claims
            ):
                raise KnowledgeRetrievalValidationError(
                    "all grounded claims must reference the result citation catalog."
                )
            rendered = "\n\n".join(claim.text for claim in claims)
            if self.rendered_answer != rendered:
                raise KnowledgeRetrievalValidationError(
                    "rendered_answer must be the deterministic grounded claim rendering."
                )
        else:
            if claims or self.rendered_answer is not None:
                raise KnowledgeRetrievalValidationError(
                    "insufficient_evidence must not contain claims or rendered answer."
                )

        digest = _validate_sha256(self.result_sha256, "result_sha256")
        expected = sha256(
            _canonical_json_bytes(
                _result_payload(
                    grounded_request_sha256=request_digest,
                    citation_catalog_sha256=catalog_digest,
                    decision=self.decision,
                    claims=claims,
                )
            )
        ).hexdigest()
        if digest != expected:
            raise KnowledgeRetrievalValidationError(
                "result_sha256 must match deterministic grounded synthesis evidence."
            )
        object.__setattr__(self, "result_sha256", digest)

    @classmethod
    def create(
        cls,
        *,
        request: GroundedSynthesisRequest,
        decision: SynthesisDecision,
        claims: tuple[GroundedClaim, ...],
    ) -> Self:
        """Create one exact grounded result under the admitted request limits."""
        if not _is_runtime_instance(request, GroundedSynthesisRequest):
            raise KnowledgeRetrievalValidationError(
                "request must be a GroundedSynthesisRequest value."
            )
        if not _is_runtime_instance(decision, SynthesisDecision):
            raise KnowledgeRetrievalValidationError(
                "decision must be a SynthesisDecision value."
            )
        typed_claims = _normalize_claims(claims)

        rendered_answer: str | None
        if decision is SynthesisDecision.ANSWER:
            if not typed_claims:
                raise KnowledgeRetrievalValidationError(
                    "answer decision requires at least one grounded claim."
                )
            if any(
                claim.citation_catalog_sha256
                != request.citation_catalog.catalog_sha256
                for claim in typed_claims
            ):
                raise KnowledgeRetrievalValidationError(
                    "claims must reference the admitted request citation catalog."
                )
            allowed_ids = {
                item.citation.citation_id for item in request.citation_catalog.citations
            }
            if any(
                set(claim.citation_ids) - allowed_ids for claim in typed_claims
            ):
                raise KnowledgeRetrievalValidationError(
                    "claims reference citation IDs outside the admitted catalog."
                )
            rendered_answer = "\n\n".join(claim.text for claim in typed_claims)
            if len(rendered_answer) > request.synthesis_request.limits.max_output_chars:
                raise KnowledgeRetrievalValidationError(
                    "grounded rendered answer exceeds synthesis request output bounds."
                )
        else:
            if typed_claims:
                raise KnowledgeRetrievalValidationError(
                    "insufficient_evidence cannot contain grounded claims."
                )
            rendered_answer = None

        digest = sha256(
            _canonical_json_bytes(
                _result_payload(
                    grounded_request_sha256=request.grounded_request_sha256,
                    citation_catalog_sha256=request.citation_catalog.catalog_sha256,
                    decision=decision,
                    claims=typed_claims,
                )
            )
        ).hexdigest()
        return cls(
            grounded_request_sha256=request.grounded_request_sha256,
            citation_catalog_sha256=request.citation_catalog.catalog_sha256,
            decision=decision,
            claims=typed_claims,
            rendered_answer=rendered_answer,
            result_sha256=digest,
        )
