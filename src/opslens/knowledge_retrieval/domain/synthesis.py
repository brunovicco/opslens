"""Provider-independent contracts for bounded knowledge synthesis."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import Self

from opslens.knowledge_retrieval.domain.context import AssembledContext
from opslens.knowledge_retrieval.domain.errors import KnowledgeRetrievalValidationError
from opslens.knowledge_retrieval.domain.models import MAX_RETRIEVAL_QUERY_CHARS

SYNTHESIS_CONTRACT_ID = "knowledge-synthesis-contract:v1"
DEFAULT_SYNTHESIS_MAX_OUTPUT_CHARS = 4_000
MAX_SYNTHESIS_OUTPUT_CHARS = 4_000
MAX_SYNTHESIS_MODEL_CALLS = 1

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _is_runtime_instance(value: object, expected_type: type[object]) -> bool:
    """Check untrusted runtime values without weakening public annotations."""
    return isinstance(value, expected_type)


def _require_runtime_instance(value: object, expected_type: type[object], label: str) -> None:
    """Reject an untrusted runtime value outside the frozen synthesis contract."""
    if not _is_runtime_instance(value, expected_type):
        raise KnowledgeRetrievalValidationError(f"{label} has an unsupported value.")


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


def _sha256_text(text: str) -> str:
    """Return the exact UTF-8 SHA-256 digest for one text payload."""
    return sha256(text.encode("utf-8")).hexdigest()


def _canonical_json_bytes(payload: object) -> bytes:
    """Serialize one deterministic fingerprint payload."""
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


class SynthesisAuthorityDecision(StrEnum):
    """Deterministic authority decision made before any model invocation."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"


class SynthesisDecision(StrEnum):
    """Allowed model synthesis decisions after authority admission."""

    ANSWER = "answer"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True, slots=True)
class SynthesisLimits:
    """Provider-independent application limits applied to one synthesis request."""

    max_output_chars: int = DEFAULT_SYNTHESIS_MAX_OUTPUT_CHARS
    max_model_calls: int = MAX_SYNTHESIS_MODEL_CALLS

    def __post_init__(self) -> None:
        """Reject unbounded output or iterative model-call authority."""
        if type(self.max_output_chars) is not int or not (
            1 <= self.max_output_chars <= MAX_SYNTHESIS_OUTPUT_CHARS
        ):
            raise KnowledgeRetrievalValidationError(
                "max_output_chars must be an integer from 1 to "
                f"{MAX_SYNTHESIS_OUTPUT_CHARS}."
            )
        if type(self.max_model_calls) is not int or self.max_model_calls != 1:
            raise KnowledgeRetrievalValidationError(
                "max_model_calls must equal 1 for synthesis contract v1."
            )


def _request_fingerprint_payload(
    *,
    question_sha256: str,
    context_sha256: str,
    authority_decision: SynthesisAuthorityDecision,
    limits: SynthesisLimits,
) -> bytes:
    """Build content-free deterministic synthesis-request identity."""
    return _canonical_json_bytes(
        {
            "authority_decision": authority_decision.value,
            "context_sha256": context_sha256,
            "contract_id": SYNTHESIS_CONTRACT_ID,
            "limits": {
                "max_model_calls": limits.max_model_calls,
                "max_output_chars": limits.max_output_chars,
            },
            "question_sha256": question_sha256,
        }
    )


@dataclass(frozen=True, slots=True)
class SynthesisRequest:
    """One admitted, bounded request eligible for a future synthesis provider call."""

    question: str
    question_sha256: str
    context: AssembledContext
    authority_decision: SynthesisAuthorityDecision
    limits: SynthesisLimits
    request_sha256: str

    def __post_init__(self) -> None:
        """Bind the exact question, admitted context, authority, limits, and identity."""
        question = _normalize_required_text(self.question, "question")
        if len(question) > MAX_RETRIEVAL_QUERY_CHARS:
            raise KnowledgeRetrievalValidationError(
                f"question cannot exceed {MAX_RETRIEVAL_QUERY_CHARS} characters."
            )
        object.__setattr__(self, "question", question)

        question_sha256 = _validate_sha256(self.question_sha256, "question_sha256")
        if question_sha256 != _sha256_text(question):
            raise KnowledgeRetrievalValidationError(
                "question_sha256 must match the exact normalized synthesis question."
            )
        object.__setattr__(self, "question_sha256", question_sha256)

        _require_runtime_instance(self.context, AssembledContext, "context")
        _require_runtime_instance(
            self.authority_decision,
            SynthesisAuthorityDecision,
            "authority_decision",
        )
        if self.authority_decision is not SynthesisAuthorityDecision.SUPPORTED:
            raise KnowledgeRetrievalValidationError(
                "unsupported authority cannot form a synthesis request."
            )
        _require_runtime_instance(self.limits, SynthesisLimits, "limits")

        if question_sha256 != self.context.query_sha256:
            raise KnowledgeRetrievalValidationError(
                "synthesis question must match the exact query used to assemble context."
            )

        request_sha256 = _validate_sha256(self.request_sha256, "request_sha256")
        expected = sha256(
            _request_fingerprint_payload(
                question_sha256=question_sha256,
                context_sha256=self.context.context_sha256,
                authority_decision=self.authority_decision,
                limits=self.limits,
            )
        ).hexdigest()
        if request_sha256 != expected:
            raise KnowledgeRetrievalValidationError(
                "request_sha256 must match deterministic synthesis-request evidence."
            )
        object.__setattr__(self, "request_sha256", request_sha256)

    @classmethod
    def create(
        cls,
        *,
        question: str,
        context: AssembledContext,
        authority_decision: SynthesisAuthorityDecision,
        limits: SynthesisLimits,
    ) -> Self:
        """Create one synthesis request after deterministic pre-model authority admission."""
        normalized_question = _normalize_required_text(question, "question")
        question_sha256 = _sha256_text(normalized_question)
        _require_runtime_instance(context, AssembledContext, "context")
        _require_runtime_instance(
            authority_decision,
            SynthesisAuthorityDecision,
            "authority_decision",
        )
        _require_runtime_instance(limits, SynthesisLimits, "limits")
        request_sha256 = sha256(
            _request_fingerprint_payload(
                question_sha256=question_sha256,
                context_sha256=context.context_sha256,
                authority_decision=authority_decision,
                limits=limits,
            )
        ).hexdigest()
        return cls(
            question=normalized_question,
            question_sha256=question_sha256,
            context=context,
            authority_decision=authority_decision,
            limits=limits,
            request_sha256=request_sha256,
        )


def _result_fingerprint_payload(
    *,
    request_sha256: str,
    decision: SynthesisDecision,
    answer_sha256: str | None,
) -> bytes:
    """Build deterministic content-addressed model-result evidence."""
    return _canonical_json_bytes(
        {
            "answer_sha256": answer_sha256,
            "decision": decision.value,
            "request_sha256": request_sha256,
        }
    )


@dataclass(frozen=True, slots=True)
class SynthesisResult:
    """Provider-independent parsed model output linked to one synthesis request."""

    request_sha256: str
    decision: SynthesisDecision
    answer: str | None
    answer_sha256: str | None
    result_sha256: str

    def __post_init__(self) -> None:
        """Enforce answer/abstention semantics and exact output identity."""
        request_sha256 = _validate_sha256(self.request_sha256, "request_sha256")
        object.__setattr__(self, "request_sha256", request_sha256)
        _require_runtime_instance(self.decision, SynthesisDecision, "decision")

        normalized_answer: str | None
        if self.decision is SynthesisDecision.ANSWER:
            normalized_answer = _normalize_required_text(self.answer, "answer")
            if len(normalized_answer) > MAX_SYNTHESIS_OUTPUT_CHARS:
                raise KnowledgeRetrievalValidationError(
                    f"answer cannot exceed {MAX_SYNTHESIS_OUTPUT_CHARS} characters."
                )
            expected_answer_sha256 = _sha256_text(normalized_answer)
            answer_sha256 = _validate_sha256(self.answer_sha256, "answer_sha256")
            if answer_sha256 != expected_answer_sha256:
                raise KnowledgeRetrievalValidationError(
                    "answer_sha256 must match the exact normalized answer text."
                )
            object.__setattr__(self, "answer", normalized_answer)
            object.__setattr__(self, "answer_sha256", answer_sha256)
        else:
            if self.answer is not None or self.answer_sha256 is not None:
                raise KnowledgeRetrievalValidationError(
                    "insufficient_evidence must not contain answer text or answer_sha256."
                )
            normalized_answer = None

        result_sha256 = _validate_sha256(self.result_sha256, "result_sha256")
        expected_result_sha256 = sha256(
            _result_fingerprint_payload(
                request_sha256=request_sha256,
                decision=self.decision,
                answer_sha256=self.answer_sha256,
            )
        ).hexdigest()
        if result_sha256 != expected_result_sha256:
            raise KnowledgeRetrievalValidationError(
                "result_sha256 must match deterministic synthesis-result evidence."
            )
        object.__setattr__(self, "result_sha256", result_sha256)

    @classmethod
    def create(
        cls,
        *,
        request: SynthesisRequest,
        decision: SynthesisDecision,
        answer: str | None,
    ) -> Self:
        """Create exact parsed output evidence without provider-specific metadata."""
        _require_runtime_instance(request, SynthesisRequest, "request")
        _require_runtime_instance(decision, SynthesisDecision, "decision")

        normalized_answer: str | None
        answer_sha256: str | None
        if decision is SynthesisDecision.ANSWER:
            normalized_answer = _normalize_required_text(answer, "answer")
            if len(normalized_answer) > request.limits.max_output_chars:
                raise KnowledgeRetrievalValidationError(
                    "answer exceeds the admitted synthesis request output bound."
                )
            answer_sha256 = _sha256_text(normalized_answer)
        else:
            if answer is not None:
                raise KnowledgeRetrievalValidationError(
                    "insufficient_evidence must not contain answer text."
                )
            normalized_answer = None
            answer_sha256 = None

        result_sha256 = sha256(
            _result_fingerprint_payload(
                request_sha256=request.request_sha256,
                decision=decision,
                answer_sha256=answer_sha256,
            )
        ).hexdigest()
        return cls(
            request_sha256=request.request_sha256,
            decision=decision,
            answer=normalized_answer,
            answer_sha256=answer_sha256,
            result_sha256=result_sha256,
        )
