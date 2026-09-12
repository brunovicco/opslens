"""Deterministic offline evaluation contracts for the Phase 11 single-agent baseline."""

import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256

from opslens.agent_baseline.domain.errors import AgentEvaluationValidationError
from opslens.agent_baseline.domain.execution import (
    MAX_AGENT_EXECUTIONS_PER_CALL,
    SINGLE_AGENT_EXECUTION_CONTRACT_VERSION,
)
from opslens.agent_baseline.domain.models import (
    SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION,
    AgentActionProposal,
    AgentCapability,
    SingleAgentTask,
)
from opslens.shared.evidence import canonical_json

SINGLE_AGENT_EVALUATION_CONTRACT_VERSION = "single-agent-evaluation:v1"
MAX_AGENT_EVALUATION_CASES = 128

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_CASE_KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$", re.ASCII)
_CASE_ID_PATTERN = re.compile(
    rf"^{re.escape(SINGLE_AGENT_EVALUATION_CONTRACT_VERSION)}:case:[0-9a-f]{{64}}$",
    re.ASCII,
)
_RESULT_ID_PATTERN = re.compile(
    rf"^{re.escape(SINGLE_AGENT_EVALUATION_CONTRACT_VERSION)}:result:[0-9a-f]{{64}}$",
    re.ASCII,
)
_REPORT_ID_PATTERN = re.compile(
    rf"^{re.escape(SINGLE_AGENT_EVALUATION_CONTRACT_VERSION)}:report:[0-9a-f]{{64}}$",
    re.ASCII,
)


class AgentEvaluationExecutionMode(StrEnum):
    """Whether one admitted authorization should stop or replay one typed execution."""

    AUTHORIZATION_ONLY = "authorization_only"
    EXECUTE_AUTHORIZED = "execute_authorized"


class AgentEvaluationAuthorizationOutcome(StrEnum):
    """Stable authorization outcomes scored by the offline evaluator."""

    AUTHORIZED = "authorized"
    ABSTAINED = "abstained"
    REJECTED = "rejected"


class AgentEvaluationExecutionOutcome(StrEnum):
    """Stable typed-execution outcomes scored independently from authorization."""

    NOT_ATTEMPTED = "not_attempted"
    ADMITTED = "admitted"
    FAILED = "failed"


class AgentEvaluationFailureCategory(StrEnum):
    """Content-free failure categories admitted into evaluation evidence."""

    AUTHORITY_VALIDATION = "authority_validation"
    CAPABILITY_AUTHORIZATION = "capability_authorization"
    INVOCATION_CONTRACT = "invocation_contract"
    EXECUTOR_FAILURE = "executor_failure"
    RESULT_CONTRACT = "result_contract"


def _canonical_json(value: object) -> bytes:
    """Serialize one deterministic evaluation identity payload."""
    return canonical_json(value)


def _canonical_sha256(value: object) -> str:
    """Hash one canonical evaluation identity payload."""
    return sha256(_canonical_json(value)).hexdigest()


def _validate_sha256(value: object, *, label: str, expected: str | None = None) -> str:
    """Validate one lowercase SHA-256 value and optional deterministic expectation."""
    if type(value) is not str or _SHA256_PATTERN.fullmatch(value) is None:
        raise AgentEvaluationValidationError(f"{label} must be lowercase SHA-256")
    if expected is not None and value != expected:
        raise AgentEvaluationValidationError(f"{label} must match canonical semantics")
    return value


def _validate_case_key(value: object) -> str:
    """Validate one bounded human-readable case key."""
    if type(value) is not str or _CASE_KEY_PATTERN.fullmatch(value) is None:
        raise AgentEvaluationValidationError("case_key violates the evaluation contract")
    return value


@dataclass(frozen=True, slots=True)
class AgentEvaluationExpectation:
    """Deterministic golden expectation for one authorization/execution replay."""

    authorization_outcome: AgentEvaluationAuthorizationOutcome
    capability: AgentCapability | None
    execution_outcome: AgentEvaluationExecutionOutcome
    failure_category: AgentEvaluationFailureCategory | None

    def __post_init__(self) -> None:
        """Reject internally inconsistent golden expectations."""
        if type(self.authorization_outcome) is not AgentEvaluationAuthorizationOutcome:
            raise AgentEvaluationValidationError(
                "authorization_outcome must be AgentEvaluationAuthorizationOutcome"
            )
        if self.capability is not None and type(self.capability) is not AgentCapability:
            raise AgentEvaluationValidationError("capability must be AgentCapability or null")
        if type(self.execution_outcome) is not AgentEvaluationExecutionOutcome:
            raise AgentEvaluationValidationError(
                "execution_outcome must be AgentEvaluationExecutionOutcome"
            )
        if (
            self.failure_category is not None
            and type(self.failure_category) is not AgentEvaluationFailureCategory
        ):
            raise AgentEvaluationValidationError(
                "failure_category must be AgentEvaluationFailureCategory or null"
            )

        if self.authorization_outcome is AgentEvaluationAuthorizationOutcome.AUTHORIZED:
            if self.capability is None:
                raise AgentEvaluationValidationError(
                    "authorized expectations require one capability"
                )
        elif self.capability is not None:
            raise AgentEvaluationValidationError(
                "non-authorized expectations cannot carry a capability"
            )

        if (
            self.authorization_outcome is not AgentEvaluationAuthorizationOutcome.AUTHORIZED
            and self.execution_outcome is not AgentEvaluationExecutionOutcome.NOT_ATTEMPTED
        ):
            raise AgentEvaluationValidationError(
                "non-authorized expectations cannot expect capability execution"
            )

        auth_failure = self.failure_category in {
            AgentEvaluationFailureCategory.AUTHORITY_VALIDATION,
            AgentEvaluationFailureCategory.CAPABILITY_AUTHORIZATION,
        }
        execution_failure = self.failure_category in {
            AgentEvaluationFailureCategory.INVOCATION_CONTRACT,
            AgentEvaluationFailureCategory.EXECUTOR_FAILURE,
            AgentEvaluationFailureCategory.RESULT_CONTRACT,
        }
        if self.authorization_outcome is AgentEvaluationAuthorizationOutcome.REJECTED:
            if not auth_failure:
                raise AgentEvaluationValidationError(
                    "rejected authorization expectations require an authorization failure category"
                )
        elif auth_failure:
            raise AgentEvaluationValidationError(
                "authorization failure categories require a rejected expectation"
            )

        if self.execution_outcome is AgentEvaluationExecutionOutcome.FAILED:
            if not execution_failure:
                raise AgentEvaluationValidationError(
                    "failed execution expectations require an execution failure category"
                )
        elif execution_failure:
            raise AgentEvaluationValidationError(
                "execution failure categories require a failed execution expectation"
            )

        if (
            self.authorization_outcome is not AgentEvaluationAuthorizationOutcome.REJECTED
            and self.execution_outcome is not AgentEvaluationExecutionOutcome.FAILED
            and self.failure_category is not None
        ):
            raise AgentEvaluationValidationError(
                "successful or abstained expectations cannot carry a failure category"
            )


def _expectation_payload(expectation: AgentEvaluationExpectation) -> dict[str, object]:
    """Project exact golden expectation semantics."""
    return {
        "authorization_outcome": expectation.authorization_outcome.value,
        "capability": expectation.capability.value if expectation.capability is not None else None,
        "execution_outcome": expectation.execution_outcome.value,
        "failure_category": (
            expectation.failure_category.value
            if expectation.failure_category is not None
            else None
        ),
    }


@dataclass(frozen=True, slots=True)
class AgentEvaluationCase:
    """Content-addressed offline replay case over the frozen authority contracts."""

    case_key: str
    task: SingleAgentTask
    proposal: AgentActionProposal
    execution_mode: AgentEvaluationExecutionMode
    expectation: AgentEvaluationExpectation
    case_sha256: str
    case_id: str

    def __post_init__(self) -> None:
        """Reject forged case identity without pre-authorizing the proposal."""
        case_key = _validate_case_key(self.case_key)
        if type(self.task) is not SingleAgentTask:
            raise AgentEvaluationValidationError("task must be one SingleAgentTask")
        if type(self.proposal) is not AgentActionProposal:
            raise AgentEvaluationValidationError("proposal must be one AgentActionProposal")
        if type(self.execution_mode) is not AgentEvaluationExecutionMode:
            raise AgentEvaluationValidationError(
                "execution_mode must be AgentEvaluationExecutionMode"
            )
        if type(self.expectation) is not AgentEvaluationExpectation:
            raise AgentEvaluationValidationError(
                "expectation must be one AgentEvaluationExpectation"
            )
        expected = _canonical_sha256(
            {
                "case_key": case_key,
                "contract_version": SINGLE_AGENT_EVALUATION_CONTRACT_VERSION,
                "execution_mode": self.execution_mode.value,
                "expectation": _expectation_payload(self.expectation),
                "proposal_sha256": self.proposal.proposal_sha256,
                "task_sha256": self.task.task_sha256,
            }
        )
        _validate_sha256(self.case_sha256, label="case_sha256", expected=expected)
        expected_id = f"{SINGLE_AGENT_EVALUATION_CONTRACT_VERSION}:case:{expected}"
        if type(self.case_id) is not str or self.case_id != expected_id:
            raise AgentEvaluationValidationError(
                "case_id must match content-addressed case semantics"
            )
        if _CASE_ID_PATTERN.fullmatch(self.case_id) is None:
            raise AgentEvaluationValidationError("case_id is invalid")

    @classmethod
    def create(
        cls,
        *,
        case_key: str,
        task: SingleAgentTask,
        proposal: AgentActionProposal,
        execution_mode: AgentEvaluationExecutionMode,
        expectation: AgentEvaluationExpectation,
    ) -> "AgentEvaluationCase":
        """Create one deterministic offline evaluation case."""
        case_key = _validate_case_key(case_key)
        if type(task) is not SingleAgentTask:
            raise AgentEvaluationValidationError("task must be one SingleAgentTask")
        if type(proposal) is not AgentActionProposal:
            raise AgentEvaluationValidationError("proposal must be one AgentActionProposal")
        if type(execution_mode) is not AgentEvaluationExecutionMode:
            raise AgentEvaluationValidationError(
                "execution_mode must be AgentEvaluationExecutionMode"
            )
        if type(expectation) is not AgentEvaluationExpectation:
            raise AgentEvaluationValidationError(
                "expectation must be one AgentEvaluationExpectation"
            )
        digest = _canonical_sha256(
            {
                "case_key": case_key,
                "contract_version": SINGLE_AGENT_EVALUATION_CONTRACT_VERSION,
                "execution_mode": execution_mode.value,
                "expectation": _expectation_payload(expectation),
                "proposal_sha256": proposal.proposal_sha256,
                "task_sha256": task.task_sha256,
            }
        )
        return cls(
            case_key=case_key,
            task=task,
            proposal=proposal,
            execution_mode=execution_mode,
            expectation=expectation,
            case_sha256=digest,
            case_id=f"{SINGLE_AGENT_EVALUATION_CONTRACT_VERSION}:case:{digest}",
        )


def compute_agent_evaluation_corpus_sha256(
    cases: tuple[AgentEvaluationCase, ...],
) -> str:
    """Compute canonical identity for one bounded ordered evaluation corpus."""
    if type(cases) is not tuple or not cases:
        raise AgentEvaluationValidationError("evaluation cases must be a non-empty tuple")
    if len(cases) > MAX_AGENT_EVALUATION_CASES:
        raise AgentEvaluationValidationError("evaluation cases exceed the v1 limit")
    if any(type(case) is not AgentEvaluationCase for case in cases):
        raise AgentEvaluationValidationError(
            "evaluation cases must contain only AgentEvaluationCase values"
        )
    ordered = tuple(sorted(cases, key=lambda item: item.case_key))
    if len({case.case_key for case in ordered}) != len(ordered):
        raise AgentEvaluationValidationError("evaluation case keys must be unique")
    return _canonical_sha256(
        {
            "cases": [
                {"case_key": case.case_key, "case_sha256": case.case_sha256}
                for case in ordered
            ],
            "contract_version": SINGLE_AGENT_EVALUATION_CONTRACT_VERSION,
        }
    )


@dataclass(frozen=True, slots=True)
class AgentEvaluationDataset:
    """Bounded content-addressed golden corpus for offline replay."""

    cases: tuple[AgentEvaluationCase, ...]
    corpus_sha256: str

    def __post_init__(self) -> None:
        """Reject reordered, duplicated, or forged corpus identity."""
        if type(self.cases) is not tuple:
            raise AgentEvaluationValidationError("cases must be a tuple")
        ordered = tuple(sorted(self.cases, key=lambda item: item.case_key))
        if self.cases != ordered:
            raise AgentEvaluationValidationError("cases must use canonical case_key order")
        expected = compute_agent_evaluation_corpus_sha256(self.cases)
        _validate_sha256(self.corpus_sha256, label="corpus_sha256", expected=expected)

    @classmethod
    def create(cls, *, cases: tuple[AgentEvaluationCase, ...]) -> "AgentEvaluationDataset":
        """Create one canonical dataset from typed evaluation cases."""
        if type(cases) is not tuple:
            raise AgentEvaluationValidationError("cases must be a tuple")
        ordered = tuple(sorted(cases, key=lambda item: item.case_key))
        digest = compute_agent_evaluation_corpus_sha256(ordered)
        return cls(cases=ordered, corpus_sha256=digest)


def _bounds_compliant(
    *,
    authorization_outcome: AgentEvaluationAuthorizationOutcome,
    execution_outcome: AgentEvaluationExecutionOutcome,
    failure_category: AgentEvaluationFailureCategory | None,
    execution_attempts: int,
) -> bool:
    """Verify one evaluator observation remained inside the frozen one-attempt boundary."""
    if execution_attempts < 0 or execution_attempts > MAX_AGENT_EXECUTIONS_PER_CALL:
        return False
    if authorization_outcome is not AgentEvaluationAuthorizationOutcome.AUTHORIZED:
        return (
            execution_attempts == 0
            and execution_outcome is AgentEvaluationExecutionOutcome.NOT_ATTEMPTED
        )
    if execution_outcome is AgentEvaluationExecutionOutcome.NOT_ATTEMPTED:
        return execution_attempts == 0
    if execution_outcome is AgentEvaluationExecutionOutcome.ADMITTED:
        return execution_attempts == 1
    if failure_category is AgentEvaluationFailureCategory.INVOCATION_CONTRACT:
        return execution_attempts == 0
    if failure_category in {
        AgentEvaluationFailureCategory.EXECUTOR_FAILURE,
        AgentEvaluationFailureCategory.RESULT_CONTRACT,
    }:
        return execution_attempts == 1
    return False


@dataclass(frozen=True, slots=True)
class AgentEvaluationCaseResult:
    """Deterministic decomposed score and evidence for one replay case."""

    case: AgentEvaluationCase
    authorization_outcome: AgentEvaluationAuthorizationOutcome
    capability: AgentCapability | None
    execution_outcome: AgentEvaluationExecutionOutcome
    failure_category: AgentEvaluationFailureCategory | None
    authorization_evidence_id: str | None
    execution_id: str | None
    execution_attempts: int
    authorization_match: bool
    capability_match: bool
    execution_match: bool
    failure_category_match: bool
    bounds_compliant: bool
    passed: bool
    result_sha256: str
    result_id: str

    def __post_init__(self) -> None:
        """Recompute every score and reject forged result identity."""
        if type(self.case) is not AgentEvaluationCase:
            raise AgentEvaluationValidationError("case must be one AgentEvaluationCase")
        if type(self.authorization_outcome) is not AgentEvaluationAuthorizationOutcome:
            raise AgentEvaluationValidationError(
                "authorization_outcome must be AgentEvaluationAuthorizationOutcome"
            )
        if self.capability is not None and type(self.capability) is not AgentCapability:
            raise AgentEvaluationValidationError("capability must be AgentCapability or null")
        if type(self.execution_outcome) is not AgentEvaluationExecutionOutcome:
            raise AgentEvaluationValidationError(
                "execution_outcome must be AgentEvaluationExecutionOutcome"
            )
        if (
            self.failure_category is not None
            and type(self.failure_category) is not AgentEvaluationFailureCategory
        ):
            raise AgentEvaluationValidationError(
                "failure_category must be AgentEvaluationFailureCategory or null"
            )
        if (
            self.authorization_evidence_id is not None
            and type(self.authorization_evidence_id) is not str
        ):
            raise AgentEvaluationValidationError(
                "authorization_evidence_id must be a string or null"
            )
        if self.execution_id is not None and type(self.execution_id) is not str:
            raise AgentEvaluationValidationError("execution_id must be a string or null")
        if type(self.execution_attempts) is not int:
            raise AgentEvaluationValidationError("execution_attempts must be an integer")

        expected_authorization_match = (
            self.authorization_outcome is self.case.expectation.authorization_outcome
        )
        expected_capability_match = self.capability is self.case.expectation.capability
        expected_execution_match = (
            self.execution_outcome is self.case.expectation.execution_outcome
        )
        expected_failure_match = self.failure_category is self.case.expectation.failure_category
        expected_bounds = _bounds_compliant(
            authorization_outcome=self.authorization_outcome,
            execution_outcome=self.execution_outcome,
            failure_category=self.failure_category,
            execution_attempts=self.execution_attempts,
        )
        expected_passed = all(
            (
                expected_authorization_match,
                expected_capability_match,
                expected_execution_match,
                expected_failure_match,
                expected_bounds,
            )
        )
        for label, value, expected in (
            ("authorization_match", self.authorization_match, expected_authorization_match),
            ("capability_match", self.capability_match, expected_capability_match),
            ("execution_match", self.execution_match, expected_execution_match),
            ("failure_category_match", self.failure_category_match, expected_failure_match),
            ("bounds_compliant", self.bounds_compliant, expected_bounds),
            ("passed", self.passed, expected_passed),
        ):
            if type(value) is not bool or value is not expected:
                raise AgentEvaluationValidationError(f"{label} must match deterministic scoring")

        payload = self._identity_payload()
        expected_sha = _canonical_sha256(payload)
        _validate_sha256(self.result_sha256, label="result_sha256", expected=expected_sha)
        expected_id = f"{SINGLE_AGENT_EVALUATION_CONTRACT_VERSION}:result:{expected_sha}"
        if type(self.result_id) is not str or self.result_id != expected_id:
            raise AgentEvaluationValidationError(
                "result_id must match content-addressed result semantics"
            )
        if _RESULT_ID_PATTERN.fullmatch(self.result_id) is None:
            raise AgentEvaluationValidationError("result_id is invalid")

    def _identity_payload(self) -> dict[str, object]:
        """Return canonical result semantics without raw task/provider content."""
        return {
            "authorization_evidence_id": self.authorization_evidence_id,
            "authorization_match": self.authorization_match,
            "authorization_outcome": self.authorization_outcome.value,
            "bounds_compliant": self.bounds_compliant,
            "capability": self.capability.value if self.capability is not None else None,
            "capability_match": self.capability_match,
            "case_sha256": self.case.case_sha256,
            "contract_version": SINGLE_AGENT_EVALUATION_CONTRACT_VERSION,
            "execution_attempts": self.execution_attempts,
            "execution_id": self.execution_id,
            "execution_match": self.execution_match,
            "execution_outcome": self.execution_outcome.value,
            "failure_category": (
                self.failure_category.value if self.failure_category is not None else None
            ),
            "failure_category_match": self.failure_category_match,
            "passed": self.passed,
        }

    @classmethod
    def create(
        cls,
        *,
        case: AgentEvaluationCase,
        authorization_outcome: AgentEvaluationAuthorizationOutcome,
        capability: AgentCapability | None,
        execution_outcome: AgentEvaluationExecutionOutcome,
        failure_category: AgentEvaluationFailureCategory | None,
        authorization_evidence_id: str | None,
        execution_id: str | None,
        execution_attempts: int,
    ) -> "AgentEvaluationCaseResult":
        """Score and content-address one observed replay result."""
        if type(case) is not AgentEvaluationCase:
            raise AgentEvaluationValidationError("case must be one AgentEvaluationCase")
        authorization_match = authorization_outcome is case.expectation.authorization_outcome
        capability_match = capability is case.expectation.capability
        execution_match = execution_outcome is case.expectation.execution_outcome
        failure_match = failure_category is case.expectation.failure_category
        bounds = _bounds_compliant(
            authorization_outcome=authorization_outcome,
            execution_outcome=execution_outcome,
            failure_category=failure_category,
            execution_attempts=execution_attempts,
        )
        passed = all(
            (
                authorization_match,
                capability_match,
                execution_match,
                failure_match,
                bounds,
            )
        )
        payload: dict[str, object] = {
            "authorization_evidence_id": authorization_evidence_id,
            "authorization_match": authorization_match,
            "authorization_outcome": authorization_outcome.value,
            "bounds_compliant": bounds,
            "capability": capability.value if capability is not None else None,
            "capability_match": capability_match,
            "case_sha256": case.case_sha256,
            "contract_version": SINGLE_AGENT_EVALUATION_CONTRACT_VERSION,
            "execution_attempts": execution_attempts,
            "execution_id": execution_id,
            "execution_match": execution_match,
            "execution_outcome": execution_outcome.value,
            "failure_category": (
                failure_category.value if failure_category is not None else None
            ),
            "failure_category_match": failure_match,
            "passed": passed,
        }
        digest = _canonical_sha256(payload)
        return cls(
            case=case,
            authorization_outcome=authorization_outcome,
            capability=capability,
            execution_outcome=execution_outcome,
            failure_category=failure_category,
            authorization_evidence_id=authorization_evidence_id,
            execution_id=execution_id,
            execution_attempts=execution_attempts,
            authorization_match=authorization_match,
            capability_match=capability_match,
            execution_match=execution_match,
            failure_category_match=failure_match,
            bounds_compliant=bounds,
            passed=passed,
            result_sha256=digest,
            result_id=f"{SINGLE_AGENT_EVALUATION_CONTRACT_VERSION}:result:{digest}",
        )

    def to_dict(self) -> dict[str, object]:
        """Return bounded persistence-safe evidence without raw task or executor content."""
        return {
            "authorization_evidence_id": self.authorization_evidence_id,
            "authorization_match": self.authorization_match,
            "authorization_outcome": self.authorization_outcome.value,
            "bounds_compliant": self.bounds_compliant,
            "capability": self.capability.value if self.capability is not None else None,
            "capability_match": self.capability_match,
            "case_id": self.case.case_id,
            "case_key": self.case.case_key,
            "case_sha256": self.case.case_sha256,
            "execution_attempts": self.execution_attempts,
            "execution_id": self.execution_id,
            "execution_match": self.execution_match,
            "execution_outcome": self.execution_outcome.value,
            "failure_category": (
                self.failure_category.value if self.failure_category is not None else None
            ),
            "failure_category_match": self.failure_category_match,
            "passed": self.passed,
            "result_id": self.result_id,
            "result_sha256": self.result_sha256,
        }


@dataclass(frozen=True, slots=True)
class AgentEvaluationMetrics:
    """Decomposed integer metrics; no opaque aggregate correctness score."""

    total_cases: int
    passed_cases: int
    authorization_matches: int
    capability_matches: int
    execution_matches: int
    failure_category_matches: int
    bounds_compliant_cases: int

    def __post_init__(self) -> None:
        """Reject impossible metric counts."""
        values = (
            self.total_cases,
            self.passed_cases,
            self.authorization_matches,
            self.capability_matches,
            self.execution_matches,
            self.failure_category_matches,
            self.bounds_compliant_cases,
        )
        if any(type(value) is not int for value in values):
            raise AgentEvaluationValidationError("evaluation metrics must be integer counts")
        if self.total_cases <= 0:
            raise AgentEvaluationValidationError("total_cases must be positive")
        if any(value < 0 or value > self.total_cases for value in values[1:]):
            raise AgentEvaluationValidationError("evaluation metric count is out of bounds")

    def to_dict(self) -> dict[str, int]:
        """Return stable metric fields for report persistence."""
        return {
            "authorization_matches": self.authorization_matches,
            "bounds_compliant_cases": self.bounds_compliant_cases,
            "capability_matches": self.capability_matches,
            "execution_matches": self.execution_matches,
            "failure_category_matches": self.failure_category_matches,
            "passed_cases": self.passed_cases,
            "total_cases": self.total_cases,
        }


def _metrics_for_results(
    results: tuple[AgentEvaluationCaseResult, ...],
) -> AgentEvaluationMetrics:
    """Compute all Gate 11.3 metrics from deterministic booleans only."""
    return AgentEvaluationMetrics(
        total_cases=len(results),
        passed_cases=sum(result.passed for result in results),
        authorization_matches=sum(result.authorization_match for result in results),
        capability_matches=sum(result.capability_match for result in results),
        execution_matches=sum(result.execution_match for result in results),
        failure_category_matches=sum(result.failure_category_match for result in results),
        bounds_compliant_cases=sum(result.bounds_compliant for result in results),
    )


@dataclass(frozen=True, slots=True)
class AgentEvaluationReport:
    """Content-addressed decomposed evaluation report over one exact golden corpus."""

    corpus_sha256: str
    results: tuple[AgentEvaluationCaseResult, ...]
    metrics: AgentEvaluationMetrics
    report_sha256: str
    report_id: str

    def __post_init__(self) -> None:
        """Reject forged metrics, corpus binding, ordering, or report identity."""
        if type(self.results) is not tuple or not self.results:
            raise AgentEvaluationValidationError("results must be a non-empty tuple")
        if any(type(result) is not AgentEvaluationCaseResult for result in self.results):
            raise AgentEvaluationValidationError(
                "results must contain only AgentEvaluationCaseResult values"
            )
        ordered = tuple(sorted(self.results, key=lambda item: item.case.case_key))
        if self.results != ordered:
            raise AgentEvaluationValidationError("results must use canonical case_key order")
        if len({result.case.case_key for result in self.results}) != len(self.results):
            raise AgentEvaluationValidationError("result case keys must be unique")
        expected_corpus = compute_agent_evaluation_corpus_sha256(
            tuple(result.case for result in self.results)
        )
        _validate_sha256(
            self.corpus_sha256,
            label="corpus_sha256",
            expected=expected_corpus,
        )
        expected_metrics = _metrics_for_results(self.results)
        if self.metrics != expected_metrics:
            raise AgentEvaluationValidationError("metrics must match deterministic case scores")
        expected_sha = _canonical_sha256(self._identity_payload())
        _validate_sha256(self.report_sha256, label="report_sha256", expected=expected_sha)
        expected_id = f"{SINGLE_AGENT_EVALUATION_CONTRACT_VERSION}:report:{expected_sha}"
        if type(self.report_id) is not str or self.report_id != expected_id:
            raise AgentEvaluationValidationError(
                "report_id must match content-addressed report semantics"
            )
        if _REPORT_ID_PATTERN.fullmatch(self.report_id) is None:
            raise AgentEvaluationValidationError("report_id is invalid")

    def _identity_payload(self) -> dict[str, object]:
        """Return exact report semantics with frozen upstream contract versions."""
        return {
            "authority_contract_version": SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION,
            "contract_version": SINGLE_AGENT_EVALUATION_CONTRACT_VERSION,
            "corpus_sha256": self.corpus_sha256,
            "execution_contract_version": SINGLE_AGENT_EXECUTION_CONTRACT_VERSION,
            "metrics": self.metrics.to_dict(),
            "results": [result.result_sha256 for result in self.results],
        }

    @classmethod
    def create(
        cls,
        *,
        dataset: AgentEvaluationDataset,
        results: tuple[AgentEvaluationCaseResult, ...],
    ) -> "AgentEvaluationReport":
        """Create one deterministic report bound to one exact evaluation dataset."""
        if type(dataset) is not AgentEvaluationDataset:
            raise AgentEvaluationValidationError("dataset must be one AgentEvaluationDataset")
        if type(results) is not tuple:
            raise AgentEvaluationValidationError("results must be a tuple")
        ordered = tuple(sorted(results, key=lambda item: item.case.case_key))
        if tuple(result.case.case_sha256 for result in ordered) != tuple(
            case.case_sha256 for case in dataset.cases
        ):
            raise AgentEvaluationValidationError(
                "results must correspond exactly to the evaluation dataset"
            )
        metrics = _metrics_for_results(ordered)
        partial_payload: dict[str, object] = {
            "authority_contract_version": SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION,
            "contract_version": SINGLE_AGENT_EVALUATION_CONTRACT_VERSION,
            "corpus_sha256": dataset.corpus_sha256,
            "execution_contract_version": SINGLE_AGENT_EXECUTION_CONTRACT_VERSION,
            "metrics": metrics.to_dict(),
            "results": [result.result_sha256 for result in ordered],
        }
        digest = _canonical_sha256(partial_payload)
        return cls(
            corpus_sha256=dataset.corpus_sha256,
            results=ordered,
            metrics=metrics,
            report_sha256=digest,
            report_id=f"{SINGLE_AGENT_EVALUATION_CONTRACT_VERSION}:report:{digest}",
        )

    def to_dict(self) -> dict[str, object]:
        """Return bounded immutable evidence suitable for content-addressed persistence."""
        return {
            "authority_contract_version": SINGLE_AGENT_AUTHORITY_CONTRACT_VERSION,
            "contract_version": SINGLE_AGENT_EVALUATION_CONTRACT_VERSION,
            "corpus_sha256": self.corpus_sha256,
            "execution_contract_version": SINGLE_AGENT_EXECUTION_CONTRACT_VERSION,
            "metrics": self.metrics.to_dict(),
            "report_id": self.report_id,
            "report_sha256": self.report_sha256,
            "results": [result.to_dict() for result in self.results],
        }


__all__ = [
    "MAX_AGENT_EVALUATION_CASES",
    "SINGLE_AGENT_EVALUATION_CONTRACT_VERSION",
    "AgentEvaluationAuthorizationOutcome",
    "AgentEvaluationCase",
    "AgentEvaluationCaseResult",
    "AgentEvaluationDataset",
    "AgentEvaluationExecutionMode",
    "AgentEvaluationExecutionOutcome",
    "AgentEvaluationExpectation",
    "AgentEvaluationFailureCategory",
    "AgentEvaluationMetrics",
    "AgentEvaluationReport",
    "compute_agent_evaluation_corpus_sha256",
]
