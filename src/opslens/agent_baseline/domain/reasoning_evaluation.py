"""Deterministic evaluation contracts for bounded single-agent model reasoning."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from opslens.agent_baseline.domain.errors import AgentEvaluationValidationError
from opslens.agent_baseline.domain.models import AgentCapability, AgentDecision, SingleAgentTask
from opslens.agent_baseline.domain.reasoning import (
    MAX_AGENT_REASONING_INVOCATIONS_PER_TASK,
    SINGLE_AGENT_REASONING_CONTRACT_VERSION,
    AgentReasoningAuthorizationOutcome,
    AgentReasoningResult,
)

SINGLE_AGENT_REASONING_EVALUATION_CONTRACT_VERSION = "single-agent-reasoning-evaluation:v1"
MAX_AGENT_REASONING_EVALUATION_CASES = 64

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_CASE_KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$", re.ASCII)
_REPORT_ID_PATTERN = re.compile(
    rf"^{re.escape(SINGLE_AGENT_REASONING_EVALUATION_CONTRACT_VERSION)}:report:[0-9a-f]{{64}}$",
    re.ASCII,
)


def _canonical_sha256(value: object) -> str:
    """Return SHA-256 over one canonical JSON payload."""
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _validate_sha256(value: object, *, label: str, expected: str) -> None:
    """Require one exact lowercase SHA-256 digest."""
    if (
        type(value) is not str
        or _SHA256_PATTERN.fullmatch(value) is None
        or value != expected
    ):
        raise AgentEvaluationValidationError(f"{label} must match canonical semantics")


def _validate_case_key(value: object) -> str:
    """Require one bounded stable case key."""
    if type(value) is not str or _CASE_KEY_PATTERN.fullmatch(value) is None:
        raise AgentEvaluationValidationError("case_key violates the reasoning evaluation contract")
    return value


@dataclass(frozen=True, slots=True)
class AgentReasoningExpectation:
    """Golden expected proposal and authorization outcome for one model task."""

    decision: AgentDecision
    capability: AgentCapability | None
    authorization_outcome: AgentReasoningAuthorizationOutcome

    def __post_init__(self) -> None:
        """Reject internally inconsistent golden behavior."""
        if type(self.decision) is not AgentDecision:
            raise AgentEvaluationValidationError("decision must be AgentDecision")
        if self.capability is not None and type(self.capability) is not AgentCapability:
            raise AgentEvaluationValidationError("capability must be AgentCapability or null")
        if type(self.authorization_outcome) is not AgentReasoningAuthorizationOutcome:
            raise AgentEvaluationValidationError(
                "authorization_outcome must be AgentReasoningAuthorizationOutcome"
            )
        if self.decision is AgentDecision.ACT:
            if self.capability is None:
                raise AgentEvaluationValidationError("ACT expectation requires one capability")
            if self.authorization_outcome is not AgentReasoningAuthorizationOutcome.AUTHORIZED:
                raise AgentEvaluationValidationError(
                    "ACT golden behavior must expect deterministic authorization"
                )
            return
        if self.capability is not None:
            raise AgentEvaluationValidationError("ABSTAIN expectation cannot carry a capability")
        if self.authorization_outcome is not AgentReasoningAuthorizationOutcome.ABSTAINED:
            raise AgentEvaluationValidationError(
                "ABSTAIN golden behavior must expect deterministic abstention"
            )


def _expectation_payload(expectation: AgentReasoningExpectation) -> dict[str, object]:
    return {
        "authorization_outcome": expectation.authorization_outcome.value,
        "capability": expectation.capability.value if expectation.capability else None,
        "decision": expectation.decision.value,
    }


@dataclass(frozen=True, slots=True)
class AgentReasoningEvaluationCase:
    """Content-addressed reasoning-quality evaluation case."""

    case_key: str
    task: SingleAgentTask
    expectation: AgentReasoningExpectation
    case_sha256: str

    def __post_init__(self) -> None:
        """Reject forged case identity."""
        case_key = _validate_case_key(self.case_key)
        if type(self.task) is not SingleAgentTask:
            raise AgentEvaluationValidationError("task must be one SingleAgentTask")
        if type(self.expectation) is not AgentReasoningExpectation:
            raise AgentEvaluationValidationError("expectation must be AgentReasoningExpectation")
        expected = _case_digest(case_key, self.task, self.expectation)
        _validate_sha256(self.case_sha256, label="case_sha256", expected=expected)

    @classmethod
    def create(
        cls,
        *,
        case_key: str,
        task: SingleAgentTask,
        expectation: AgentReasoningExpectation,
    ) -> AgentReasoningEvaluationCase:
        """Create one deterministic reasoning-quality case."""
        case_key = _validate_case_key(case_key)
        if type(task) is not SingleAgentTask:
            raise AgentEvaluationValidationError("task must be one SingleAgentTask")
        if type(expectation) is not AgentReasoningExpectation:
            raise AgentEvaluationValidationError("expectation must be AgentReasoningExpectation")
        return cls(
            case_key=case_key,
            task=task,
            expectation=expectation,
            case_sha256=_case_digest(case_key, task, expectation),
        )


def _case_digest(
    case_key: str,
    task: SingleAgentTask,
    expectation: AgentReasoningExpectation,
) -> str:
    return _canonical_sha256(
        {
            "case_key": case_key,
            "contract_version": SINGLE_AGENT_REASONING_EVALUATION_CONTRACT_VERSION,
            "expectation": _expectation_payload(expectation),
            "reasoning_contract_version": SINGLE_AGENT_REASONING_CONTRACT_VERSION,
            "task_sha256": task.task_sha256,
        }
    )


def _corpus_digest(cases: tuple[AgentReasoningEvaluationCase, ...]) -> str:
    return _canonical_sha256(
        {
            "cases": [
                {"case_key": case.case_key, "case_sha256": case.case_sha256}
                for case in cases
            ],
            "contract_version": SINGLE_AGENT_REASONING_EVALUATION_CONTRACT_VERSION,
        }
    )


@dataclass(frozen=True, slots=True)
class AgentReasoningEvaluationDataset:
    """Canonical ordered reasoning corpus frozen before the real baseline."""

    cases: tuple[AgentReasoningEvaluationCase, ...]
    corpus_sha256: str

    def __post_init__(self) -> None:
        """Reject duplicated, reordered, oversized, or forged corpus identity."""
        if type(self.cases) is not tuple or not self.cases:
            raise AgentEvaluationValidationError("reasoning cases must be a non-empty tuple")
        if len(self.cases) > MAX_AGENT_REASONING_EVALUATION_CASES:
            raise AgentEvaluationValidationError("reasoning cases exceed the v1 limit")
        if any(type(case) is not AgentReasoningEvaluationCase for case in self.cases):
            raise AgentEvaluationValidationError("reasoning cases contain an invalid type")
        ordered = tuple(sorted(self.cases, key=lambda item: item.case_key))
        if ordered != self.cases:
            raise AgentEvaluationValidationError("reasoning cases must use canonical order")
        if len({case.case_key for case in self.cases}) != len(self.cases):
            raise AgentEvaluationValidationError("reasoning case keys must be unique")
        _validate_sha256(
            self.corpus_sha256,
            label="corpus_sha256",
            expected=_corpus_digest(self.cases),
        )

    @classmethod
    def create(
        cls,
        *,
        cases: tuple[AgentReasoningEvaluationCase, ...],
    ) -> AgentReasoningEvaluationDataset:
        """Create one canonical ordered reasoning corpus."""
        if type(cases) is not tuple:
            raise AgentEvaluationValidationError("reasoning cases must be a tuple")
        ordered = tuple(sorted(cases, key=lambda item: item.case_key))
        return cls(cases=ordered, corpus_sha256=_corpus_digest(ordered))


@dataclass(frozen=True, slots=True)
class AgentReasoningCaseScore:
    """Independent deterministic score dimensions for one admitted reasoning result."""

    case_key: str
    reasoning_result_id: str
    invocation_evidence_id: str
    decision_match: bool
    capability_match: bool
    authorization_match: bool
    bounds_compliant: bool
    passed: bool
    score_sha256: str

    def __post_init__(self) -> None:
        """Reject forged or internally inconsistent score evidence."""
        _validate_case_key(self.case_key)
        for label, value in (
            ("reasoning_result_id", self.reasoning_result_id),
            ("invocation_evidence_id", self.invocation_evidence_id),
        ):
            if type(value) is not str or not value.strip():
                raise AgentEvaluationValidationError(f"{label} must be a non-empty string")
        expected_pass = (
            self.decision_match
            and self.capability_match
            and self.authorization_match
            and self.bounds_compliant
        )
        if self.passed != expected_pass:
            raise AgentEvaluationValidationError(
                "passed must equal all decomposed score dimensions"
            )
        _validate_sha256(
            self.score_sha256,
            label="score_sha256",
            expected=_canonical_sha256(self._payload()),
        )

    def _payload(self) -> dict[str, object]:
        return {
            "authorization_match": self.authorization_match,
            "bounds_compliant": self.bounds_compliant,
            "capability_match": self.capability_match,
            "case_key": self.case_key,
            "contract_version": SINGLE_AGENT_REASONING_EVALUATION_CONTRACT_VERSION,
            "decision_match": self.decision_match,
            "invocation_evidence_id": self.invocation_evidence_id,
            "passed": self.passed,
            "reasoning_result_id": self.reasoning_result_id,
        }

    @classmethod
    def create(
        cls,
        *,
        case: AgentReasoningEvaluationCase,
        result: AgentReasoningResult,
    ) -> AgentReasoningCaseScore:
        """Score one admitted result against one exact golden case."""
        if type(case) is not AgentReasoningEvaluationCase:
            raise AgentEvaluationValidationError("case must be AgentReasoningEvaluationCase")
        if type(result) is not AgentReasoningResult:
            raise AgentEvaluationValidationError("result must be AgentReasoningResult")
        if result.task.task_id != case.task.task_id:
            raise AgentEvaluationValidationError("result is not bound to evaluation case")
        decision_match = result.proposal.decision is case.expectation.decision
        capability_match = result.proposal.capability is case.expectation.capability
        authorization_match = (
            result.authorization_outcome is case.expectation.authorization_outcome
        )
        bounds_compliant = (
            result.invocation_count == MAX_AGENT_REASONING_INVOCATIONS_PER_TASK
            and result.invocation_evidence.retry_attempts == 0
        )
        passed = all(
            (decision_match, capability_match, authorization_match, bounds_compliant)
        )
        values: dict[str, object] = {
            "authorization_match": authorization_match,
            "bounds_compliant": bounds_compliant,
            "capability_match": capability_match,
            "case_key": case.case_key,
            "contract_version": SINGLE_AGENT_REASONING_EVALUATION_CONTRACT_VERSION,
            "decision_match": decision_match,
            "invocation_evidence_id": result.invocation_evidence.evidence_id,
            "passed": passed,
            "reasoning_result_id": result.result_id,
        }
        return cls(
            case_key=case.case_key,
            reasoning_result_id=result.result_id,
            invocation_evidence_id=result.invocation_evidence.evidence_id,
            decision_match=decision_match,
            capability_match=capability_match,
            authorization_match=authorization_match,
            bounds_compliant=bounds_compliant,
            passed=passed,
            score_sha256=_canonical_sha256(values),
        )


@dataclass(frozen=True, slots=True)
class AgentReasoningEvaluationMetrics:
    """Decomposed integer metrics for the first reasoning baseline."""

    total_cases: int
    passed_cases: int
    decision_matches: int
    capability_matches: int
    authorization_matches: int
    bounds_compliant_cases: int

    def __post_init__(self) -> None:
        """Reject impossible metric counts."""
        if type(self.total_cases) is not int or self.total_cases <= 0:
            raise AgentEvaluationValidationError("total_cases must be a positive integer")
        for label, value in (
            ("passed_cases", self.passed_cases),
            ("decision_matches", self.decision_matches),
            ("capability_matches", self.capability_matches),
            ("authorization_matches", self.authorization_matches),
            ("bounds_compliant_cases", self.bounds_compliant_cases),
        ):
            if type(value) is not int or not 0 <= value <= self.total_cases:
                raise AgentEvaluationValidationError(f"{label} must be within total_cases")


def _metrics(scores: tuple[AgentReasoningCaseScore, ...]) -> AgentReasoningEvaluationMetrics:
    return AgentReasoningEvaluationMetrics(
        total_cases=len(scores),
        passed_cases=sum(score.passed for score in scores),
        decision_matches=sum(score.decision_match for score in scores),
        capability_matches=sum(score.capability_match for score in scores),
        authorization_matches=sum(score.authorization_match for score in scores),
        bounds_compliant_cases=sum(score.bounds_compliant for score in scores),
    )


def _report_payload(
    corpus_sha256: str,
    scores: tuple[AgentReasoningCaseScore, ...],
    metrics: AgentReasoningEvaluationMetrics,
) -> dict[str, object]:
    return {
        "contract_version": SINGLE_AGENT_REASONING_EVALUATION_CONTRACT_VERSION,
        "corpus_sha256": corpus_sha256,
        "metrics": {
            "authorization_matches": metrics.authorization_matches,
            "bounds_compliant_cases": metrics.bounds_compliant_cases,
            "capability_matches": metrics.capability_matches,
            "decision_matches": metrics.decision_matches,
            "passed_cases": metrics.passed_cases,
            "total_cases": metrics.total_cases,
        },
        "scores": [
            {"case_key": score.case_key, "score_sha256": score.score_sha256}
            for score in scores
        ],
    }


@dataclass(frozen=True, slots=True)
class AgentReasoningEvaluationReport:
    """Content-addressed report over one exact reasoning corpus replay."""

    corpus_sha256: str
    scores: tuple[AgentReasoningCaseScore, ...]
    metrics: AgentReasoningEvaluationMetrics
    report_sha256: str
    report_id: str

    def __post_init__(self) -> None:
        """Reject reordered scores, metric drift, or forged report identity."""
        if type(self.scores) is not tuple or not self.scores:
            raise AgentEvaluationValidationError("scores must be a non-empty tuple")
        if any(type(score) is not AgentReasoningCaseScore for score in self.scores):
            raise AgentEvaluationValidationError("scores contain an invalid type")
        ordered = tuple(sorted(self.scores, key=lambda item: item.case_key))
        if ordered != self.scores:
            raise AgentEvaluationValidationError("scores must use canonical case order")
        if type(self.metrics) is not AgentReasoningEvaluationMetrics:
            raise AgentEvaluationValidationError("metrics must be reasoning evaluation metrics")
        if self.metrics != _metrics(self.scores):
            raise AgentEvaluationValidationError("metrics must match score evidence")
        expected = _canonical_sha256(
            _report_payload(self.corpus_sha256, self.scores, self.metrics)
        )
        _validate_sha256(self.report_sha256, label="report_sha256", expected=expected)
        expected_id = (
            f"{SINGLE_AGENT_REASONING_EVALUATION_CONTRACT_VERSION}:report:{expected}"
        )
        if self.report_id != expected_id or _REPORT_ID_PATTERN.fullmatch(self.report_id) is None:
            raise AgentEvaluationValidationError("report_id must match canonical report semantics")

    @classmethod
    def create(
        cls,
        *,
        dataset: AgentReasoningEvaluationDataset,
        scores: tuple[AgentReasoningCaseScore, ...],
    ) -> AgentReasoningEvaluationReport:
        """Create one deterministic report over the exact frozen corpus."""
        if type(dataset) is not AgentReasoningEvaluationDataset:
            raise AgentEvaluationValidationError("dataset must be reasoning evaluation dataset")
        ordered = tuple(sorted(scores, key=lambda item: item.case_key))
        if tuple(case.case_key for case in dataset.cases) != tuple(
            score.case_key for score in ordered
        ):
            raise AgentEvaluationValidationError("scores must cover exact dataset case keys")
        metrics = _metrics(ordered)
        digest = _canonical_sha256(
            _report_payload(dataset.corpus_sha256, ordered, metrics)
        )
        return cls(
            corpus_sha256=dataset.corpus_sha256,
            scores=ordered,
            metrics=metrics,
            report_sha256=digest,
            report_id=(
                f"{SINGLE_AGENT_REASONING_EVALUATION_CONTRACT_VERSION}:report:{digest}"
            ),
        )


__all__ = [
    "MAX_AGENT_REASONING_EVALUATION_CASES",
    "SINGLE_AGENT_REASONING_EVALUATION_CONTRACT_VERSION",
    "AgentReasoningCaseScore",
    "AgentReasoningEvaluationCase",
    "AgentReasoningEvaluationDataset",
    "AgentReasoningEvaluationMetrics",
    "AgentReasoningEvaluationReport",
    "AgentReasoningExpectation",
]
