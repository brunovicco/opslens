"""Deterministic Gate 7.7 groundedness/citation evaluation contracts and metrics."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import cast

from opslens.knowledge_retrieval.application.retrieval_catalog import (
    CanonicalRetrievalCatalog,
)
from opslens.knowledge_retrieval.domain import (
    CitationCatalog,
    GroundedSynthesisResult,
    SynthesisDecision,
)

GROUNDING_EVALUATION_DATASET_ID = "knowledge-grounding-golden:v1"
GROUNDING_JUDGMENT_AUTHORITY = "human_reviewed_claim_citation_pairs_v1"

_EXPECTED_CASE_COUNT = 4
_EXPECTED_ANSWER_CASE_COUNT = 3
_EXPECTED_ABSTENTION_CASE_COUNT = 1

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_CITATION_ID_PATTERN = re.compile(r"^C[1-9][0-9]*$")


class GroundingEvaluationError(ValueError):
    """Raised when groundedness evaluation evidence cannot be admitted safely."""


class GroundingEvaluationIncompleteError(GroundingEvaluationError):
    """Raised when the frozen evaluation case set is incomplete."""


class GroundingSupportJudgmentSource(StrEnum):
    """Explicit authorities allowed to label claim/citation semantic support."""

    HUMAN_REVIEWED = "human_reviewed"


def _is_runtime_instance(value: object, expected_type: type[object]) -> bool:
    """Check untrusted runtime values without weakening public annotations."""
    return isinstance(value, expected_type)


def _require_trimmed(value: object, *, field: str, max_length: int = 4096) -> str:
    """Require one trimmed non-empty bounded string."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise GroundingEvaluationError(f"{field} must be one trimmed non-empty string")
    if len(value) > max_length:
        raise GroundingEvaluationError(f"{field} must be at most {max_length} characters")
    return value


def _require_sha256(value: object, *, field: str) -> str:
    """Require one lowercase SHA-256 digest."""
    normalized = _require_trimmed(value, field=field, max_length=64)
    if _SHA256_PATTERN.fullmatch(normalized) is None:
        raise GroundingEvaluationError(
            f"{field} must be a 64-character lowercase hexadecimal SHA-256 digest"
        )
    return normalized


def _sha256_text(text: str) -> str:
    """Return the exact UTF-8 SHA-256 digest for one text payload."""
    return sha256(text.encode("utf-8")).hexdigest()


def _require_citation_id(value: object, *, field: str) -> str:
    """Require one deterministic citation ID."""
    normalized = _require_trimmed(value, field=field, max_length=8)
    if _CITATION_ID_PATTERN.fullmatch(normalized) is None:
        raise GroundingEvaluationError(f"{field} must use the C1, C2, ... form")
    return normalized


def _require_bool(value: object, *, field: str) -> bool:
    """Require an actual boolean instead of truthy/falsy coercion."""
    if type(value) is not bool:
        raise GroundingEvaluationError(f"{field} must be a boolean")
    return value


def _require_object(value: object, *, field: str) -> dict[str, object]:
    """Require one JSON object with string keys."""
    if not isinstance(value, dict):
        raise GroundingEvaluationError(f"{field} must be a JSON object")
    raw = cast(dict[object, object], value)
    if any(not isinstance(key, str) for key in raw):
        raise GroundingEvaluationError(f"{field} keys must be strings")
    return cast(dict[str, object], raw)


def _require_exact_keys(
    value: dict[str, object],
    *,
    expected: set[str],
    field: str,
) -> None:
    """Reject both missing and unreviewed fixture fields."""
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise GroundingEvaluationError(
            f"{field} keys must match frozen schema; "
            f"missing={missing}, unknown={unknown}"
        )


def _require_string_tuple(
    value: object,
    *,
    field: str,
    allow_empty: bool,
) -> tuple[str, ...]:
    """Require one JSON array containing unique trimmed strings."""
    if not isinstance(value, list):
        raise GroundingEvaluationError(f"{field} must be a JSON array")
    items = tuple(
        _require_trimmed(item, field=field, max_length=4096)
        for item in cast(list[object], value)
    )
    if not allow_empty and not items:
        raise GroundingEvaluationError(f"{field} must not be empty")
    if len(set(items)) != len(items):
        raise GroundingEvaluationError(f"{field} values must be unique")
    return items


def _parse_decision(value: object, *, field: str) -> SynthesisDecision:
    """Parse only the frozen synthesis decisions used by grounded evaluation."""
    normalized = _require_trimmed(value, field=field, max_length=64)
    if normalized == SynthesisDecision.ANSWER.value:
        return SynthesisDecision.ANSWER
    if normalized == SynthesisDecision.INSUFFICIENT_EVIDENCE.value:
        return SynthesisDecision.INSUFFICIENT_EVIDENCE
    raise GroundingEvaluationError(f"{field} has an unsupported decision")


@dataclass(frozen=True, slots=True)
class GoldenGroundingCase:
    """One pre-provider groundedness evaluation case."""

    case_id: str
    question: str
    authority_decision: str
    expected_decision: SynthesisDecision
    expected_citation_chunk_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """Require supported authority and decision/target consistency."""
        object.__setattr__(
            self,
            "case_id",
            _require_trimmed(self.case_id, field="case_id", max_length=128),
        )
        object.__setattr__(
            self,
            "question",
            _require_trimmed(self.question, field="question", max_length=1000),
        )
        authority = _require_trimmed(
            self.authority_decision,
            field="authority_decision",
            max_length=32,
        )
        object.__setattr__(self, "authority_decision", authority)
        if authority != "supported":
            raise GroundingEvaluationError(
                "grounding fixture cases must be pre-authorized as supported"
            )
        if not _is_runtime_instance(self.expected_decision, SynthesisDecision):
            raise GroundingEvaluationError(
                "expected_decision must be one SynthesisDecision"
            )
        if not _is_runtime_instance(self.expected_citation_chunk_ids, tuple):
            raise GroundingEvaluationError(
                "expected_citation_chunk_ids must be a tuple"
            )
        raw_targets = cast(tuple[object, ...], self.expected_citation_chunk_ids)
        targets = tuple(
            _require_trimmed(
                item,
                field="expected_citation_chunk_id",
                max_length=256,
            )
            for item in raw_targets
        )
        if len(set(targets)) != len(targets):
            raise GroundingEvaluationError(
                "expected_citation_chunk_ids values must be unique"
            )
        object.__setattr__(self, "expected_citation_chunk_ids", targets)

        if self.expected_decision is SynthesisDecision.ANSWER and not targets:
            raise GroundingEvaluationError(
                "answer cases require expected citation chunk targets"
            )
        if (
            self.expected_decision is SynthesisDecision.INSUFFICIENT_EVIDENCE
            and targets
        ):
            raise GroundingEvaluationError(
                "insufficient-evidence cases cannot declare citation targets"
            )


def _require_cases(value: object) -> tuple[GoldenGroundingCase, ...]:
    """Require one tuple containing only golden grounding cases."""
    if not isinstance(value, tuple):
        raise GroundingEvaluationError("dataset cases must be a tuple")
    items = cast(tuple[object, ...], value)
    if any(not isinstance(item, GoldenGroundingCase) for item in items):
        raise GroundingEvaluationError(
            "dataset cases must contain only GoldenGroundingCase values"
        )
    return cast(tuple[GoldenGroundingCase, ...], items)


@dataclass(frozen=True, slots=True)
class GoldenGroundingDataset:
    """Frozen Gate 7.7 groundedness/citation evaluation dataset."""

    dataset_id: str
    cases: tuple[GoldenGroundingCase, ...]

    def __post_init__(self) -> None:
        """Require the exact v1 cardinality and answer/abstention split."""
        if self.dataset_id != GROUNDING_EVALUATION_DATASET_ID:
            raise GroundingEvaluationError(
                f"dataset_id must equal {GROUNDING_EVALUATION_DATASET_ID!r}"
            )
        cases = _require_cases(self.cases)
        object.__setattr__(self, "cases", cases)
        if len(cases) != _EXPECTED_CASE_COUNT:
            raise GroundingEvaluationError(
                f"dataset must contain exactly {_EXPECTED_CASE_COUNT} cases"
            )
        ids = tuple(case.case_id for case in cases)
        if len(set(ids)) != len(ids):
            raise GroundingEvaluationError("dataset case_id values must be unique")

        answer_count = sum(
            case.expected_decision is SynthesisDecision.ANSWER for case in cases
        )
        if answer_count != _EXPECTED_ANSWER_CASE_COUNT:
            raise GroundingEvaluationError(
                "dataset must contain exactly "
                f"{_EXPECTED_ANSWER_CASE_COUNT} answer cases"
            )
        if len(cases) - answer_count != _EXPECTED_ABSTENTION_CASE_COUNT:
            raise GroundingEvaluationError(
                "dataset must contain exactly "
                f"{_EXPECTED_ABSTENTION_CASE_COUNT} abstention cases"
            )


def load_golden_grounding_dataset(path: Path) -> GoldenGroundingDataset:
    """Load the exact checked Gate 7.7 fixture without silent schema drift."""
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GroundingEvaluationError(
            f"could not read grounding fixture {path}"
        ) from exc
    try:
        parsed = cast(object, json.loads(raw_text))
    except json.JSONDecodeError as exc:
        raise GroundingEvaluationError(
            "grounding fixture must contain valid JSON"
        ) from exc

    root = _require_object(parsed, field="grounding fixture")
    _require_exact_keys(
        root,
        expected={
            "dataset_id",
            "purpose",
            "authority_boundary",
            "judgment_authority",
            "cases",
        },
        field="grounding fixture",
    )
    dataset_id = _require_trimmed(root["dataset_id"], field="dataset_id")
    _require_trimmed(root["purpose"], field="purpose")
    _require_trimmed(root["authority_boundary"], field="authority_boundary")
    if root["judgment_authority"] != GROUNDING_JUDGMENT_AUTHORITY:
        raise GroundingEvaluationError(
            "judgment_authority must match the frozen v1 authority"
        )
    raw_cases = root["cases"]
    if not isinstance(raw_cases, list):
        raise GroundingEvaluationError("cases must be a JSON array")

    cases: list[GoldenGroundingCase] = []
    for index, raw_case in enumerate(cast(list[object], raw_cases)):
        case = _require_object(raw_case, field=f"case {index}")
        _require_exact_keys(
            case,
            expected={
                "case_id",
                "question",
                "authority_decision",
                "expected_decision",
                "expected_citation_chunk_ids",
            },
            field=f"case {index}",
        )
        decision = _parse_decision(
            case["expected_decision"],
            field=f"case {index} expected_decision",
        )
        cases.append(
            GoldenGroundingCase(
                case_id=_require_trimmed(
                    case["case_id"],
                    field=f"case {index} case_id",
                    max_length=128,
                ),
                question=_require_trimmed(
                    case["question"],
                    field=f"case {index} question",
                    max_length=1000,
                ),
                authority_decision=_require_trimmed(
                    case["authority_decision"],
                    field=f"case {index} authority_decision",
                    max_length=32,
                ),
                expected_decision=decision,
                expected_citation_chunk_ids=_require_string_tuple(
                    case["expected_citation_chunk_ids"],
                    field=f"case {index} expected_citation_chunk_ids",
                    allow_empty=(
                        decision is SynthesisDecision.INSUFFICIENT_EVIDENCE
                    ),
                ),
            )
        )
    return GoldenGroundingDataset(dataset_id=dataset_id, cases=tuple(cases))


def validate_grounding_dataset_catalog(
    dataset: GoldenGroundingDataset,
    catalog: CanonicalRetrievalCatalog,
) -> None:
    """Require every expected citation target to resolve to the checked corpus."""
    known_chunk_ids = {chunk.chunk_id for chunk in catalog.chunks}
    for case in dataset.cases:
        unknown = set(case.expected_citation_chunk_ids) - known_chunk_ids
        if unknown:
            raise GroundingEvaluationError(
                f"case {case.case_id!r} references unknown canonical chunks"
            )


def _judgment_payload(
    *,
    claim_sha256: str,
    citation_id: str,
    supports_claim: bool,
    source: GroundingSupportJudgmentSource,
) -> bytes:
    """Build exact content-free identity for one semantic support judgment."""
    payload = {
        "citation_id": citation_id,
        "claim_sha256": claim_sha256,
        "source": source.value,
        "supports_claim": supports_claim,
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class ClaimCitationSupportJudgment:
    """One explicit semantic support label for one exact claim/citation pair."""

    claim_sha256: str
    citation_id: str
    supports_claim: bool
    source: GroundingSupportJudgmentSource
    judgment_sha256: str

    def __post_init__(self) -> None:
        """Require exact pair identity and human-reviewed v1 authority."""
        claim_digest = _require_sha256(
            self.claim_sha256,
            field="claim_sha256",
        )
        citation_id = _require_citation_id(
            self.citation_id,
            field="citation_id",
        )
        supports_claim = _require_bool(
            self.supports_claim,
            field="supports_claim",
        )
        if not _is_runtime_instance(self.source, GroundingSupportJudgmentSource):
            raise GroundingEvaluationError(
                "source must be one GroundingSupportJudgmentSource"
            )

        digest = _require_sha256(
            self.judgment_sha256,
            field="judgment_sha256",
        )
        expected = sha256(
            _judgment_payload(
                claim_sha256=claim_digest,
                citation_id=citation_id,
                supports_claim=supports_claim,
                source=self.source,
            )
        ).hexdigest()
        if digest != expected:
            raise GroundingEvaluationError(
                "judgment_sha256 must match exact support judgment evidence"
            )

        object.__setattr__(self, "claim_sha256", claim_digest)
        object.__setattr__(self, "citation_id", citation_id)
        object.__setattr__(self, "supports_claim", supports_claim)
        object.__setattr__(self, "judgment_sha256", digest)

    @classmethod
    def create(
        cls,
        *,
        claim_sha256: str,
        citation_id: str,
        supports_claim: bool,
        source: GroundingSupportJudgmentSource = (
            GroundingSupportJudgmentSource.HUMAN_REVIEWED
        ),
    ) -> ClaimCitationSupportJudgment:
        """Create one content-addressed semantic support label."""
        normalized_claim = _require_sha256(
            claim_sha256,
            field="claim_sha256",
        )
        normalized_citation = _require_citation_id(
            citation_id,
            field="citation_id",
        )
        normalized_support = _require_bool(
            supports_claim,
            field="supports_claim",
        )
        if not _is_runtime_instance(source, GroundingSupportJudgmentSource):
            raise GroundingEvaluationError(
                "source must be one GroundingSupportJudgmentSource"
            )
        digest = sha256(
            _judgment_payload(
                claim_sha256=normalized_claim,
                citation_id=normalized_citation,
                supports_claim=normalized_support,
                source=source,
            )
        ).hexdigest()
        return cls(
            claim_sha256=normalized_claim,
            citation_id=normalized_citation,
            supports_claim=normalized_support,
            source=source,
            judgment_sha256=digest,
        )


def _require_judgments(
    value: object,
) -> tuple[ClaimCitationSupportJudgment, ...]:
    """Require one tuple containing only explicit support judgments."""
    if not isinstance(value, tuple):
        raise GroundingEvaluationError("support_judgments must be a tuple")
    items = cast(tuple[object, ...], value)
    if any(
        not isinstance(item, ClaimCitationSupportJudgment)
        for item in items
    ):
        raise GroundingEvaluationError(
            "support_judgments must contain only "
            "ClaimCitationSupportJudgment values"
        )
    return cast(tuple[ClaimCitationSupportJudgment, ...], items)


@dataclass(frozen=True, slots=True)
class GroundingCaseObservation:
    """One grounded synthesis result plus complete explicit semantic judgments."""

    case_id: str
    question_sha256: str
    citation_catalog: CitationCatalog
    result: GroundedSynthesisResult
    support_judgments: tuple[ClaimCitationSupportJudgment, ...]

    def __post_init__(self) -> None:
        """Require catalog/result identity and complete pair-level adjudication."""
        object.__setattr__(
            self,
            "case_id",
            _require_trimmed(self.case_id, field="case_id", max_length=128),
        )
        object.__setattr__(
            self,
            "question_sha256",
            _require_sha256(self.question_sha256, field="question_sha256"),
        )
        if not _is_runtime_instance(self.citation_catalog, CitationCatalog):
            raise GroundingEvaluationError(
                "citation_catalog must be one CitationCatalog"
            )
        if not _is_runtime_instance(self.result, GroundedSynthesisResult):
            raise GroundingEvaluationError(
                "result must be one GroundedSynthesisResult"
            )
        if (
            self.result.citation_catalog_sha256
            != self.citation_catalog.catalog_sha256
        ):
            raise GroundingEvaluationError(
                "result and observation must use the exact same citation catalog"
            )

        judgments = _require_judgments(self.support_judgments)
        object.__setattr__(self, "support_judgments", judgments)

        expected_pairs = {
            (claim.claim_sha256, citation_id)
            for claim in self.result.claims
            for citation_id in claim.citation_ids
        }
        actual_pairs = {
            (judgment.claim_sha256, judgment.citation_id)
            for judgment in judgments
        }
        if len(actual_pairs) != len(judgments):
            raise GroundingEvaluationError(
                "support_judgments cannot duplicate claim/citation pairs"
            )
        if actual_pairs != expected_pairs:
            raise GroundingEvaluationError(
                "support_judgments must cover every and only emitted "
                "claim/citation pair"
            )


def _safe_rate(numerator: int, denominator: int) -> float | None:
    """Return one bounded ratio or None when the denominator is zero."""
    if denominator == 0:
        return None
    value = numerator / denominator
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise GroundingEvaluationError("computed metric rate is invalid")
    return value


@dataclass(frozen=True, slots=True)
class GroundingCaseMetrics:
    """Deterministic metrics for one frozen groundedness case."""

    case_id: str
    expected_decision: SynthesisDecision
    actual_decision: SynthesisDecision
    decision_correct: bool
    selected_citation_target_count: int
    expected_citation_target_count: int
    correct_citation_target_count: int
    citation_target_precision: float | None
    citation_target_recall: float | None
    claim_count: int
    supported_claim_count: int
    unsupported_claim_count: int
    claim_supportedness_rate: float | None
    unsupported_claim_rate: float | None
    claim_citation_pair_count: int
    supporting_claim_citation_pair_count: int
    citation_correctness_rate: float | None


def evaluate_grounding_case(
    case: GoldenGroundingCase,
    observation: GroundingCaseObservation,
) -> GroundingCaseMetrics:
    """Compute citation-target and semantic-support metrics deterministically."""
    if case.case_id != observation.case_id:
        raise GroundingEvaluationError(
            "case and observation identifiers must match"
        )
    if _sha256_text(case.question) != observation.question_sha256:
        raise GroundingEvaluationError(
            "observation question identity must match the frozen case"
        )

    citation_to_chunk = {
        item.citation.citation_id: item.citation.chunk_id
        for item in observation.citation_catalog.citations
    }
    selected_citation_ids = {
        citation_id
        for claim in observation.result.claims
        for citation_id in claim.citation_ids
    }
    try:
        selected_chunk_ids = {
            citation_to_chunk[citation_id]
            for citation_id in selected_citation_ids
        }
    except KeyError as exc:
        raise GroundingEvaluationError(
            "result references citation identity outside observation catalog"
        ) from exc

    expected_targets = set(case.expected_citation_chunk_ids)
    correct_targets = selected_chunk_ids & expected_targets

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

    judgment_by_pair = {
        (judgment.claim_sha256, judgment.citation_id): judgment.supports_claim
        for judgment in observation.support_judgments
    }
    supported_claim_count = 0
    supporting_pair_count = 0
    pair_count = 0

    for claim in observation.result.claims:
        pair_support = tuple(
            judgment_by_pair[(claim.claim_sha256, citation_id)]
            for citation_id in claim.citation_ids
        )
        pair_count += len(pair_support)
        supporting_pair_count += sum(pair_support)
        if any(pair_support):
            supported_claim_count += 1

    claim_count = len(observation.result.claims)
    unsupported_claim_count = claim_count - supported_claim_count

    return GroundingCaseMetrics(
        case_id=case.case_id,
        expected_decision=case.expected_decision,
        actual_decision=observation.result.decision,
        decision_correct=(
            case.expected_decision is observation.result.decision
        ),
        selected_citation_target_count=len(selected_chunk_ids),
        expected_citation_target_count=len(expected_targets),
        correct_citation_target_count=len(correct_targets),
        citation_target_precision=target_precision,
        citation_target_recall=target_recall,
        claim_count=claim_count,
        supported_claim_count=supported_claim_count,
        unsupported_claim_count=unsupported_claim_count,
        claim_supportedness_rate=_safe_rate(
            supported_claim_count,
            claim_count,
        ),
        unsupported_claim_rate=_safe_rate(
            unsupported_claim_count,
            claim_count,
        ),
        claim_citation_pair_count=pair_count,
        supporting_claim_citation_pair_count=supporting_pair_count,
        citation_correctness_rate=_safe_rate(
            supporting_pair_count,
            pair_count,
        ),
    )


@dataclass(frozen=True, slots=True)
class GroundingEvaluationSummary:
    """Aggregate deterministic Gate 7.7 grounding metrics."""

    case_count: int
    expected_answer_case_count: int
    expected_abstention_case_count: int
    actual_answer_case_count: int
    actual_abstention_case_count: int
    decision_correct_count: int
    decision_accuracy: float
    citation_target_selected_count: int
    citation_target_expected_count: int
    citation_target_correct_count: int
    citation_target_precision: float | None
    citation_target_recall: float
    claim_count: int
    supported_claim_count: int
    unsupported_claim_count: int
    claim_supportedness_rate: float | None
    unsupported_claim_rate: float | None
    claim_citation_pair_count: int
    supporting_claim_citation_pair_count: int
    citation_correctness_rate: float | None
    expected_abstention_count: int
    observed_abstention_count: int
    correct_abstention_count: int
    abstention_precision: float | None
    abstention_recall: float


@dataclass(frozen=True, slots=True)
class GroundingEvaluationReport:
    """Complete deterministic evaluation report for the frozen dataset."""

    dataset_id: str
    cases: tuple[GroundingCaseMetrics, ...]
    summary: GroundingEvaluationSummary


def evaluate_grounding_dataset(
    dataset: GoldenGroundingDataset,
    observations: tuple[GroundingCaseObservation, ...],
) -> GroundingEvaluationReport:
    """Evaluate one complete frozen case set without converting failures to misses."""
    if not _is_runtime_instance(observations, tuple):
        raise GroundingEvaluationError("observations must be a tuple")
    raw_observations = cast(tuple[object, ...], observations)
    if any(
        not isinstance(item, GroundingCaseObservation)
        for item in raw_observations
    ):
        raise GroundingEvaluationError(
            "observations must contain only GroundingCaseObservation values"
        )
    typed_observations = cast(
        tuple[GroundingCaseObservation, ...],
        raw_observations,
    )

    by_case = {observation.case_id: observation for observation in typed_observations}
    if len(by_case) != len(typed_observations):
        raise GroundingEvaluationError("observation case_id values must be unique")

    expected_ids = {case.case_id for case in dataset.cases}
    actual_ids = set(by_case)
    if actual_ids != expected_ids:
        missing = sorted(expected_ids - actual_ids)
        unknown = sorted(actual_ids - expected_ids)
        raise GroundingEvaluationIncompleteError(
            "grounding observations must exactly cover the frozen dataset; "
            f"missing={missing}, unknown={unknown}"
        )

    case_metrics = tuple(
        evaluate_grounding_case(case, by_case[case.case_id])
        for case in dataset.cases
    )

    expected_answer_cases = tuple(
        item
        for item in case_metrics
        if item.expected_decision is SynthesisDecision.ANSWER
    )
    expected_abstention_cases = tuple(
        item
        for item in case_metrics
        if item.expected_decision is SynthesisDecision.INSUFFICIENT_EVIDENCE
    )

    selected_target_count = sum(
        item.selected_citation_target_count
        for item in expected_answer_cases
    )
    expected_target_count = sum(
        item.expected_citation_target_count
        for item in expected_answer_cases
    )
    correct_target_count = sum(
        item.correct_citation_target_count
        for item in expected_answer_cases
    )

    claim_count = sum(item.claim_count for item in case_metrics)
    supported_claim_count = sum(
        item.supported_claim_count for item in case_metrics
    )
    unsupported_claim_count = sum(
        item.unsupported_claim_count for item in case_metrics
    )
    pair_count = sum(
        item.claim_citation_pair_count for item in case_metrics
    )
    supporting_pair_count = sum(
        item.supporting_claim_citation_pair_count
        for item in case_metrics
    )

    observed_abstentions = tuple(
        item
        for item in case_metrics
        if item.actual_decision is SynthesisDecision.INSUFFICIENT_EVIDENCE
    )
    correct_abstention_count = sum(
        item.actual_decision is SynthesisDecision.INSUFFICIENT_EVIDENCE
        for item in expected_abstention_cases
    )

    decision_correct_count = sum(item.decision_correct for item in case_metrics)
    decision_accuracy = _safe_rate(
        decision_correct_count,
        len(case_metrics),
    )
    target_recall = _safe_rate(
        correct_target_count,
        expected_target_count,
    )
    abstention_recall = _safe_rate(
        correct_abstention_count,
        len(expected_abstention_cases),
    )
    if decision_accuracy is None or target_recall is None or abstention_recall is None:
        raise GroundingEvaluationError(
            "frozen dataset unexpectedly produced an undefined required metric"
        )

    summary = GroundingEvaluationSummary(
        case_count=len(case_metrics),
        expected_answer_case_count=len(expected_answer_cases),
        expected_abstention_case_count=len(expected_abstention_cases),
        actual_answer_case_count=sum(
            item.actual_decision is SynthesisDecision.ANSWER
            for item in case_metrics
        ),
        actual_abstention_case_count=len(observed_abstentions),
        decision_correct_count=decision_correct_count,
        decision_accuracy=decision_accuracy,
        citation_target_selected_count=selected_target_count,
        citation_target_expected_count=expected_target_count,
        citation_target_correct_count=correct_target_count,
        citation_target_precision=_safe_rate(
            correct_target_count,
            selected_target_count,
        ),
        citation_target_recall=target_recall,
        claim_count=claim_count,
        supported_claim_count=supported_claim_count,
        unsupported_claim_count=unsupported_claim_count,
        claim_supportedness_rate=_safe_rate(
            supported_claim_count,
            claim_count,
        ),
        unsupported_claim_rate=_safe_rate(
            unsupported_claim_count,
            claim_count,
        ),
        claim_citation_pair_count=pair_count,
        supporting_claim_citation_pair_count=supporting_pair_count,
        citation_correctness_rate=_safe_rate(
            supporting_pair_count,
            pair_count,
        ),
        expected_abstention_count=len(expected_abstention_cases),
        observed_abstention_count=len(observed_abstentions),
        correct_abstention_count=correct_abstention_count,
        abstention_precision=_safe_rate(
            correct_abstention_count,
            len(observed_abstentions),
        ),
        abstention_recall=abstention_recall,
    )
    return GroundingEvaluationReport(
        dataset_id=dataset.dataset_id,
        cases=case_metrics,
        summary=summary,
    )
