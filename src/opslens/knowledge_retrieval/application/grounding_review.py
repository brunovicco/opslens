"""Metadata-only evaluation of the preserved Gate 7.7 grounded-synthesis run."""

from __future__ import annotations

import math
from dataclasses import dataclass
from hashlib import sha256
from typing import cast

from opslens.knowledge_retrieval.application.grounding_evaluation import (
    ClaimCitationSupportJudgment,
    GoldenGroundingCase,
    GoldenGroundingDataset,
    GroundingCaseMetrics,
    GroundingEvaluationError,
    GroundingEvaluationReport,
    GroundingEvaluationSummary,
    GroundingSupportJudgmentSource,
)
from opslens.knowledge_retrieval.application.retrieval_catalog import (
    CanonicalRetrievalCatalog,
)
from opslens.knowledge_retrieval.domain import SynthesisDecision


def _is_runtime_instance(value: object, expected_type: type[object]) -> bool:
    """Check untrusted runtime values without weakening public annotations."""
    return isinstance(value, expected_type)


def _safe_rate(numerator: int, denominator: int) -> float | None:
    """Return one bounded ratio or None when the denominator is zero."""
    if denominator == 0:
        return None
    value = numerator / denominator
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise GroundingEvaluationError("computed reviewed metric rate is invalid")
    return value


@dataclass(frozen=True, slots=True)
class ReviewedCitationSelection:
    """One runtime citation ID mapped to its deterministic canonical chunk."""

    citation_id: str
    chunk_id: str

    def __post_init__(self) -> None:
        """Require normalized non-empty identities."""
        for field_name, max_length in (("citation_id", 8), ("chunk_id", 256)):
            value = getattr(self, field_name)
            if (
                not _is_runtime_instance(value, str)
                or not value
                or value != value.strip()
                or len(value) > max_length
            ):
                raise GroundingEvaluationError(
                    f"{field_name} must be one normalized bounded string"
                )


@dataclass(frozen=True, slots=True)
class ReviewedGroundingCase:
    """Content-free first-run case with complete human pair-level judgments."""

    case_id: str
    question_sha256: str
    actual_decision: SynthesisDecision
    runtime_claim_count: int
    runtime_claim_citation_pair_count: int
    selected_citations: tuple[ReviewedCitationSelection, ...]
    support_judgments: tuple[ClaimCitationSupportJudgment, ...]

    def __post_init__(self) -> None:
        """Require counts and human judgments to cover the preserved runtime exactly."""
        if not _is_runtime_instance(self.case_id, str) or not self.case_id.strip():
            raise GroundingEvaluationError("case_id must be a non-empty string")
        if (
            not _is_runtime_instance(self.question_sha256, str)
            or len(self.question_sha256) != 64
            or any(ch not in "0123456789abcdef" for ch in self.question_sha256)
        ):
            raise GroundingEvaluationError("question_sha256 must be lowercase SHA-256")
        if not _is_runtime_instance(self.actual_decision, SynthesisDecision):
            raise GroundingEvaluationError(
                "actual_decision must be one SynthesisDecision"
            )
        for field_name in (
            "runtime_claim_count",
            "runtime_claim_citation_pair_count",
        ):
            value = getattr(self, field_name)
            if type(value) is not int or value < 0:
                raise GroundingEvaluationError(
                    f"{field_name} must be a non-negative integer"
                )

        if not _is_runtime_instance(self.selected_citations, tuple):
            raise GroundingEvaluationError("selected_citations must be a tuple")
        raw_selections = cast(tuple[object, ...], self.selected_citations)
        if any(
            not _is_runtime_instance(item, ReviewedCitationSelection)
            for item in raw_selections
        ):
            raise GroundingEvaluationError(
                "selected_citations must contain ReviewedCitationSelection values"
            )
        selections = cast(tuple[ReviewedCitationSelection, ...], raw_selections)
        if len({item.citation_id for item in selections}) != len(selections):
            raise GroundingEvaluationError("selected citation IDs must be unique")
        if len({item.chunk_id for item in selections}) != len(selections):
            raise GroundingEvaluationError("selected citation chunks must be unique")

        if not _is_runtime_instance(self.support_judgments, tuple):
            raise GroundingEvaluationError("support_judgments must be a tuple")
        raw_judgments = cast(tuple[object, ...], self.support_judgments)
        if any(
            not _is_runtime_instance(item, ClaimCitationSupportJudgment)
            for item in raw_judgments
        ):
            raise GroundingEvaluationError(
                "support_judgments must contain ClaimCitationSupportJudgment values"
            )
        judgments = cast(tuple[ClaimCitationSupportJudgment, ...], raw_judgments)
        pairs = tuple(
            (item.claim_sha256, item.citation_id)
            for item in judgments
        )
        if len(set(pairs)) != len(pairs):
            raise GroundingEvaluationError(
                "support judgments cannot duplicate claim/citation pairs"
            )
        if any(
            item.source is not GroundingSupportJudgmentSource.HUMAN_REVIEWED
            for item in judgments
        ):
            raise GroundingEvaluationError(
                "first-run support judgments must be human_reviewed"
            )
        if len({item.claim_sha256 for item in judgments}) != self.runtime_claim_count:
            raise GroundingEvaluationError(
                "reviewed claim hashes must match runtime_claim_count"
            )
        if len(judgments) != self.runtime_claim_citation_pair_count:
            raise GroundingEvaluationError(
                "support judgments must match runtime pair count"
            )
        if {item.citation_id for item in judgments} != {
            item.citation_id for item in selections
        }:
            raise GroundingEvaluationError(
                "selected citation IDs must equal judged citation IDs"
            )

        if self.actual_decision is SynthesisDecision.ANSWER:
            if self.runtime_claim_count == 0 or not judgments or not selections:
                raise GroundingEvaluationError(
                    "answer cases require claims, judgments, and selected citations"
                )
        elif self.runtime_claim_count or judgments or selections:
            raise GroundingEvaluationError(
                "insufficient_evidence cases cannot contain claim review evidence"
            )


def _question_sha256(question: str) -> str:
    return sha256(question.encode("utf-8")).hexdigest()


def _evaluate_case(
    case: GoldenGroundingCase,
    review: ReviewedGroundingCase,
    *,
    known_chunk_ids: set[str],
) -> GroundingCaseMetrics:
    """Compute one reviewed case using frozen target and support semantics."""
    if case.case_id != review.case_id:
        raise GroundingEvaluationError("golden and reviewed case IDs must match")
    if _question_sha256(case.question) != review.question_sha256:
        raise GroundingEvaluationError(
            "review question identity must match the frozen case"
        )

    selected_chunk_ids = {item.chunk_id for item in review.selected_citations}
    if selected_chunk_ids - known_chunk_ids:
        raise GroundingEvaluationError(
            "review selected citations reference unknown canonical chunks"
        )
    expected_targets = set(case.expected_citation_chunk_ids)
    correct_targets = selected_chunk_ids & expected_targets

    target_precision: float | None
    target_recall: float | None
    if case.expected_decision is SynthesisDecision.ANSWER:
        target_precision = _safe_rate(
            len(correct_targets),
            len(selected_chunk_ids),
        )
        target_recall = _safe_rate(
            len(correct_targets),
            len(expected_targets),
        )
    else:
        target_precision = None
        target_recall = None

    support_by_claim: dict[str, list[bool]] = {}
    for judgment in review.support_judgments:
        support_by_claim.setdefault(judgment.claim_sha256, []).append(
            judgment.supports_claim
        )
    supported_claim_count = sum(
        any(pair_values) for pair_values in support_by_claim.values()
    )
    supporting_pair_count = sum(
        item.supports_claim for item in review.support_judgments
    )
    claim_count = review.runtime_claim_count
    unsupported_claim_count = claim_count - supported_claim_count
    pair_count = review.runtime_claim_citation_pair_count

    return GroundingCaseMetrics(
        case_id=case.case_id,
        expected_decision=case.expected_decision,
        actual_decision=review.actual_decision,
        decision_correct=(case.expected_decision is review.actual_decision),
        selected_citation_target_count=len(selected_chunk_ids),
        expected_citation_target_count=len(expected_targets),
        correct_citation_target_count=len(correct_targets),
        citation_target_precision=target_precision,
        citation_target_recall=target_recall,
        claim_count=claim_count,
        supported_claim_count=supported_claim_count,
        unsupported_claim_count=unsupported_claim_count,
        claim_supportedness_rate=_safe_rate(supported_claim_count, claim_count),
        unsupported_claim_rate=_safe_rate(unsupported_claim_count, claim_count),
        claim_citation_pair_count=pair_count,
        supporting_claim_citation_pair_count=supporting_pair_count,
        citation_correctness_rate=_safe_rate(supporting_pair_count, pair_count),
    )


def _aggregate(
    dataset_id: str,
    metrics: tuple[GroundingCaseMetrics, ...],
) -> GroundingEvaluationReport:
    """Aggregate reviewed cases with the frozen Gate 7.7 formulas."""
    expected_answers = tuple(
        item for item in metrics if item.expected_decision is SynthesisDecision.ANSWER
    )
    expected_abstentions = tuple(
        item
        for item in metrics
        if item.expected_decision is SynthesisDecision.INSUFFICIENT_EVIDENCE
    )
    observed_abstentions = tuple(
        item
        for item in metrics
        if item.actual_decision is SynthesisDecision.INSUFFICIENT_EVIDENCE
    )

    selected = sum(item.selected_citation_target_count for item in expected_answers)
    expected = sum(item.expected_citation_target_count for item in expected_answers)
    correct = sum(item.correct_citation_target_count for item in expected_answers)
    claims = sum(item.claim_count for item in metrics)
    supported = sum(item.supported_claim_count for item in metrics)
    unsupported = sum(item.unsupported_claim_count for item in metrics)
    pairs = sum(item.claim_citation_pair_count for item in metrics)
    supporting_pairs = sum(
        item.supporting_claim_citation_pair_count for item in metrics
    )
    correct_decisions = sum(item.decision_correct for item in metrics)
    correct_abstentions = sum(
        item.actual_decision is SynthesisDecision.INSUFFICIENT_EVIDENCE
        for item in expected_abstentions
    )

    decision_accuracy = _safe_rate(correct_decisions, len(metrics))
    target_recall = _safe_rate(correct, expected)
    abstention_recall = _safe_rate(correct_abstentions, len(expected_abstentions))
    if decision_accuracy is None or target_recall is None or abstention_recall is None:
        raise GroundingEvaluationError(
            "frozen first-run review produced an undefined required metric"
        )

    summary = GroundingEvaluationSummary(
        case_count=len(metrics),
        expected_answer_case_count=len(expected_answers),
        expected_abstention_case_count=len(expected_abstentions),
        actual_answer_case_count=sum(
            item.actual_decision is SynthesisDecision.ANSWER for item in metrics
        ),
        actual_abstention_case_count=len(observed_abstentions),
        decision_correct_count=correct_decisions,
        decision_accuracy=decision_accuracy,
        citation_target_selected_count=selected,
        citation_target_expected_count=expected,
        citation_target_correct_count=correct,
        citation_target_precision=_safe_rate(correct, selected),
        citation_target_recall=target_recall,
        claim_count=claims,
        supported_claim_count=supported,
        unsupported_claim_count=unsupported,
        claim_supportedness_rate=_safe_rate(supported, claims),
        unsupported_claim_rate=_safe_rate(unsupported, claims),
        claim_citation_pair_count=pairs,
        supporting_claim_citation_pair_count=supporting_pairs,
        citation_correctness_rate=_safe_rate(supporting_pairs, pairs),
        expected_abstention_count=len(expected_abstentions),
        observed_abstention_count=len(observed_abstentions),
        correct_abstention_count=correct_abstentions,
        abstention_precision=_safe_rate(
            correct_abstentions,
            len(observed_abstentions),
        ),
        abstention_recall=abstention_recall,
    )
    return GroundingEvaluationReport(
        dataset_id=dataset_id,
        cases=metrics,
        summary=summary,
    )


def evaluate_reviewed_grounding_run(
    dataset: GoldenGroundingDataset,
    catalog: CanonicalRetrievalCatalog,
    reviews: tuple[ReviewedGroundingCase, ...],
) -> GroundingEvaluationReport:
    """Evaluate exact first-run metadata without retaining model/source text."""
    if not _is_runtime_instance(reviews, tuple):
        raise GroundingEvaluationError("reviews must be a tuple")
    raw_reviews = cast(tuple[object, ...], reviews)
    if any(
        not _is_runtime_instance(item, ReviewedGroundingCase)
        for item in raw_reviews
    ):
        raise GroundingEvaluationError(
            "reviews must contain ReviewedGroundingCase values"
        )
    typed_reviews = cast(tuple[ReviewedGroundingCase, ...], raw_reviews)
    by_case = {item.case_id: item for item in typed_reviews}
    if len(by_case) != len(typed_reviews):
        raise GroundingEvaluationError("review case IDs must be unique")
    expected_ids = {item.case_id for item in dataset.cases}
    if set(by_case) != expected_ids:
        raise GroundingEvaluationError(
            "reviews must exactly cover the frozen grounding dataset"
        )

    known_chunk_ids = {item.chunk_id for item in catalog.chunks}
    metrics = tuple(
        _evaluate_case(
            case,
            by_case[case.case_id],
            known_chunk_ids=known_chunk_ids,
        )
        for case in dataset.cases
    )
    return _aggregate(dataset.dataset_id, metrics)
