"""Deterministic provider-neutral contracts for multi-agent comparison evidence."""

import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import cast

from opslens.agent_baseline.domain.models import AgentCapability, SingleAgentTask
from opslens.multi_agent.domain.errors import MultiAgentComparisonValidationError
from opslens.multi_agent.domain.handoff import (
    MAX_SPECIALIST_CAPABILITIES,
    AgentSpecialization,
    MultiAgentHandoffDecision,
    MultiAgentHandoffProposal,
    capabilities_for_specialization,
)
from opslens.shared.evidence import canonical_json

MULTI_AGENT_COMPARISON_CONTRACT_VERSION = "multi-agent-comparison:v1"
MAX_MULTI_AGENT_COMPARISON_CASES = 32
PHASE11_REFERENCE_CORPUS_SHA256 = (
    "3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc"
)
PHASE11_REFERENCE_REPORT_SHA256 = (
    "724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145"
)


class MultiAgentComparisonAdmissionOutcome(StrEnum):
    """Closed deterministic outcomes visible to comparison scoring."""

    HANDOFF = "handoff"
    ABSTAINED = "abstained"
    REJECTED = "rejected"


_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_CASE_KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$", re.ASCII)
_CASE_ID_PATTERN = re.compile(
    rf"^{re.escape(MULTI_AGENT_COMPARISON_CONTRACT_VERSION)}:case:[0-9a-f]{{64}}$",
    re.ASCII,
)
_SCORE_ID_PATTERN = re.compile(
    rf"^{re.escape(MULTI_AGENT_COMPARISON_CONTRACT_VERSION)}:score:[0-9a-f]{{64}}$",
    re.ASCII,
)
_DATASET_ID_PATTERN = re.compile(
    rf"^{re.escape(MULTI_AGENT_COMPARISON_CONTRACT_VERSION)}:dataset:[0-9a-f]{{64}}$",
    re.ASCII,
)
_REPORT_ID_PATTERN = re.compile(
    rf"^{re.escape(MULTI_AGENT_COMPARISON_CONTRACT_VERSION)}:report:[0-9a-f]{{64}}$",
    re.ASCII,
)


def _canonical_json(value: object) -> bytes:
    """Serialize one comparison identity payload deterministically."""
    return canonical_json(value)


def _canonical_sha256(value: object) -> str:
    """Hash one canonical comparison payload."""
    return sha256(_canonical_json(value)).hexdigest()


def _validate_digest(value: object, *, label: str, expected: str) -> str:
    """Validate a caller-visible digest against canonical semantics."""
    if (
        type(value) is not str
        or _SHA256_PATTERN.fullmatch(value) is None
        or value != expected
    ):
        raise MultiAgentComparisonValidationError(
            f"{label} must match canonical comparison semantics"
        )
    return value


def _validate_identifier(
    value: object,
    *,
    label: str,
    pattern: re.Pattern[str],
) -> str:
    """Validate one versioned content-addressed comparison identifier."""
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise MultiAgentComparisonValidationError(
            f"{label} violates the comparison identity contract"
        )
    return value


def _normalize_case_key(value: object) -> str:
    """Validate one stable low-cardinality comparison case key."""
    if type(value) is not str or _CASE_KEY_PATTERN.fullmatch(value) is None:
        raise MultiAgentComparisonValidationError("case_key violates the comparison contract")
    return value


def _normalize_capabilities(
    value: object,
    *,
    allow_empty: bool,
) -> tuple[AgentCapability, ...]:
    """Validate and canonically order an expected or observed capability scope."""
    if type(value) is not tuple:
        raise MultiAgentComparisonValidationError("capability scope must be a tuple")
    raw_values = cast(tuple[object, ...], value)
    if not allow_empty and not raw_values:
        raise MultiAgentComparisonValidationError("capability scope cannot be empty")
    if len(raw_values) > MAX_SPECIALIST_CAPABILITIES:
        raise MultiAgentComparisonValidationError(
            "capability scope exceeds the specialist capability limit"
        )
    if any(type(item) is not AgentCapability for item in raw_values):
        raise MultiAgentComparisonValidationError(
            "capability scope must contain only AgentCapability values"
        )
    typed_values = cast(tuple[AgentCapability, ...], raw_values)
    if len(set(typed_values)) != len(typed_values):
        raise MultiAgentComparisonValidationError("capability scope cannot contain duplicates")
    normalized = tuple(sorted(typed_values, key=lambda item: item.value))
    if typed_values != normalized:
        raise MultiAgentComparisonValidationError("capability scope must be canonically ordered")
    return typed_values


def _expectation_payload(
    *,
    decision: MultiAgentHandoffDecision,
    target_specialization: AgentSpecialization | None,
    admission_outcome: MultiAgentComparisonAdmissionOutcome,
    target_capabilities: tuple[AgentCapability, ...],
) -> dict[str, object]:
    """Project one expectation into canonical identity semantics."""
    return {
        "admission_outcome": admission_outcome.value,
        "decision": decision.value,
        "target_capabilities": [item.value for item in target_capabilities],
        "target_specialization": (
            target_specialization.value if target_specialization is not None else None
        ),
    }


@dataclass(frozen=True, slots=True)
class MultiAgentComparisonExpectation:
    """Deterministic expected outcome for one synthetic comparison proposal."""

    decision: MultiAgentHandoffDecision
    target_specialization: AgentSpecialization | None
    admission_outcome: MultiAgentComparisonAdmissionOutcome
    target_capabilities: tuple[AgentCapability, ...]

    def __post_init__(self) -> None:
        """Reject inconsistent expected routing and admission semantics."""
        if type(self.decision) is not MultiAgentHandoffDecision:
            raise MultiAgentComparisonValidationError(
                "expected decision must be MultiAgentHandoffDecision"
            )
        if self.target_specialization is not None and type(
            self.target_specialization
        ) is not AgentSpecialization:
            raise MultiAgentComparisonValidationError(
                "expected specialization must be AgentSpecialization or null"
            )
        if type(self.admission_outcome) is not MultiAgentComparisonAdmissionOutcome:
            raise MultiAgentComparisonValidationError(
                "expected admission outcome is not supported"
            )
        capabilities = _normalize_capabilities(
            self.target_capabilities,
            allow_empty=self.admission_outcome
            is not MultiAgentComparisonAdmissionOutcome.HANDOFF,
        )
        object.__setattr__(self, "target_capabilities", capabilities)

        if self.admission_outcome is MultiAgentComparisonAdmissionOutcome.HANDOFF:
            if self.decision is not MultiAgentHandoffDecision.HANDOFF:
                raise MultiAgentComparisonValidationError(
                    "HANDOFF admission requires a HANDOFF decision"
                )
            specialization = self.target_specialization
            if specialization is None:
                raise MultiAgentComparisonValidationError(
                    "HANDOFF admission requires one specialization"
                )
            if not set(capabilities).issubset(capabilities_for_specialization(specialization)):
                raise MultiAgentComparisonValidationError(
                    "expected target capabilities exceed specialization scope"
                )
        elif self.admission_outcome is MultiAgentComparisonAdmissionOutcome.ABSTAINED:
            if self.decision is not MultiAgentHandoffDecision.ABSTAIN:
                raise MultiAgentComparisonValidationError(
                    "ABSTAINED admission requires an ABSTAIN decision"
                )
            if self.target_specialization is not None or capabilities:
                raise MultiAgentComparisonValidationError(
                    "ABSTAINED admission cannot carry specialization or target capabilities"
                )
        else:
            if self.decision is not MultiAgentHandoffDecision.HANDOFF:
                raise MultiAgentComparisonValidationError(
                    "REJECTED admission requires a HANDOFF decision"
                )
            if self.target_specialization is None or capabilities:
                raise MultiAgentComparisonValidationError(
                    "REJECTED admission requires specialization and no target capabilities"
                )


@dataclass(frozen=True, slots=True)
class MultiAgentComparisonCase:
    """One content-addressed offline case with a synthetic untrusted proposal."""

    case_key: str
    task: SingleAgentTask
    proposal: MultiAgentHandoffProposal
    expected: MultiAgentComparisonExpectation
    case_sha256: str
    case_id: str

    def __post_init__(self) -> None:
        """Bind source task, synthetic proposal, expectation, and case identity."""
        case_key = _normalize_case_key(self.case_key)
        if type(self.task) is not SingleAgentTask:
            raise MultiAgentComparisonValidationError(
                "comparison case task must be one admitted SingleAgentTask"
            )
        if type(self.proposal) is not MultiAgentHandoffProposal:
            raise MultiAgentComparisonValidationError(
                "comparison case proposal must be MultiAgentHandoffProposal"
            )
        if type(self.expected) is not MultiAgentComparisonExpectation:
            raise MultiAgentComparisonValidationError(
                "comparison case expected value must be MultiAgentComparisonExpectation"
            )
        if self.proposal.source_task_id != self.task.task_id:
            raise MultiAgentComparisonValidationError(
                "synthetic proposal must bind to the comparison source task"
            )
        expected_sha256 = _canonical_sha256(
            {
                "case_key": case_key,
                "contract_version": MULTI_AGENT_COMPARISON_CONTRACT_VERSION,
                "expected": _expectation_payload(
                    decision=self.expected.decision,
                    target_specialization=self.expected.target_specialization,
                    admission_outcome=self.expected.admission_outcome,
                    target_capabilities=self.expected.target_capabilities,
                ),
                "proposal_id": self.proposal.proposal_id,
                "task_id": self.task.task_id,
            }
        )
        _validate_digest(
            self.case_sha256,
            label="case_sha256",
            expected=expected_sha256,
        )
        expected_id = f"{MULTI_AGENT_COMPARISON_CONTRACT_VERSION}:case:{expected_sha256}"
        if self.case_id != expected_id:
            raise MultiAgentComparisonValidationError(
                "case_id must match the content-addressed comparison case"
            )


@dataclass(frozen=True, slots=True)
class MultiAgentComparisonDataset:
    """Frozen comparison corpus bound to the exact Phase 11 reference evidence."""

    phase11_reference_corpus_sha256: str
    phase11_reference_report_sha256: str
    cases: tuple[MultiAgentComparisonCase, ...]
    dataset_sha256: str
    dataset_id: str

    def __post_init__(self) -> None:
        """Reject reference drift, duplicate cases, and forged dataset identity."""
        if self.phase11_reference_corpus_sha256 != PHASE11_REFERENCE_CORPUS_SHA256:
            raise MultiAgentComparisonValidationError(
                "Phase 11 reference corpus digest does not match the frozen baseline"
            )
        if self.phase11_reference_report_sha256 != PHASE11_REFERENCE_REPORT_SHA256:
            raise MultiAgentComparisonValidationError(
                "Phase 11 reference report digest does not match the frozen baseline"
            )
        if type(self.cases) is not tuple or not self.cases:
            raise MultiAgentComparisonValidationError("comparison dataset cases cannot be empty")
        if len(self.cases) > MAX_MULTI_AGENT_COMPARISON_CASES:
            raise MultiAgentComparisonValidationError(
                "comparison dataset exceeds the case-count limit"
            )
        if any(type(case) is not MultiAgentComparisonCase for case in self.cases):
            raise MultiAgentComparisonValidationError(
                "comparison dataset contains an unsupported case value"
            )
        keys = tuple(case.case_key for case in self.cases)
        if len(set(keys)) != len(keys):
            raise MultiAgentComparisonValidationError(
                "comparison dataset case keys must be unique"
            )
        expected_sha256 = _canonical_sha256(
            {
                "case_ids": [case.case_id for case in self.cases],
                "contract_version": MULTI_AGENT_COMPARISON_CONTRACT_VERSION,
                "phase11_reference_corpus_sha256": self.phase11_reference_corpus_sha256,
                "phase11_reference_report_sha256": self.phase11_reference_report_sha256,
            }
        )
        _validate_digest(
            self.dataset_sha256,
            label="dataset_sha256",
            expected=expected_sha256,
        )
        expected_id = (
            f"{MULTI_AGENT_COMPARISON_CONTRACT_VERSION}:dataset:{expected_sha256}"
        )
        if self.dataset_id != expected_id:
            raise MultiAgentComparisonValidationError(
                "dataset_id must match the content-addressed comparison dataset"
            )


@dataclass(frozen=True, slots=True)
class MultiAgentComparisonCaseScore:
    """Decomposed deterministic score for one offline comparison case."""

    case_key: str
    case_id: str
    observed_decision: MultiAgentHandoffDecision
    observed_specialization: AgentSpecialization | None
    observed_admission_outcome: MultiAgentComparisonAdmissionOutcome
    observed_target_capabilities: tuple[AgentCapability, ...]
    decision_match: bool
    specialization_match: bool
    admission_match: bool
    target_scope_match: bool
    non_broadening: bool
    bounds_compliant: bool
    passed: bool
    source_capability_slots: int
    specialist_capability_slots: int
    score_sha256: str
    score_id: str

    def __post_init__(self) -> None:
        """Validate score decomposition and content-addressed identity."""
        case_key = _normalize_case_key(self.case_key)
        case_id = _validate_identifier(
            self.case_id,
            label="case_id",
            pattern=_CASE_ID_PATTERN,
        )
        if type(self.observed_decision) is not MultiAgentHandoffDecision:
            raise MultiAgentComparisonValidationError("observed decision is not supported")
        if self.observed_specialization is not None and type(
            self.observed_specialization
        ) is not AgentSpecialization:
            raise MultiAgentComparisonValidationError(
                "observed specialization must be AgentSpecialization or null"
            )
        if type(self.observed_admission_outcome) is not MultiAgentComparisonAdmissionOutcome:
            raise MultiAgentComparisonValidationError(
                "observed admission outcome is not supported"
            )
        capabilities = _normalize_capabilities(
            self.observed_target_capabilities,
            allow_empty=True,
        )
        object.__setattr__(self, "observed_target_capabilities", capabilities)
        flags = (
            self.decision_match,
            self.specialization_match,
            self.admission_match,
            self.target_scope_match,
            self.non_broadening,
            self.bounds_compliant,
            self.passed,
        )
        if any(type(flag) is not bool for flag in flags):
            raise MultiAgentComparisonValidationError("comparison score flags must be bool")
        expected_passed = all(flags[:-1])
        if self.passed is not expected_passed:
            raise MultiAgentComparisonValidationError(
                "passed must equal the conjunction of decomposed comparison dimensions"
            )
        if type(self.source_capability_slots) is not int or self.source_capability_slots < 1:
            raise MultiAgentComparisonValidationError(
                "source capability slots must be a positive integer"
            )
        if (
            type(self.specialist_capability_slots) is not int
            or self.specialist_capability_slots < 0
            or self.specialist_capability_slots > MAX_SPECIALIST_CAPABILITIES
        ):
            raise MultiAgentComparisonValidationError(
                "specialist capability slots violate comparison bounds"
            )
        if self.specialist_capability_slots != len(capabilities):
            raise MultiAgentComparisonValidationError(
                "specialist capability slots must match the observed target scope"
            )

        expected_sha256 = _canonical_sha256(
            {
                "admission_match": self.admission_match,
                "bounds_compliant": self.bounds_compliant,
                "case_id": case_id,
                "case_key": case_key,
                "contract_version": MULTI_AGENT_COMPARISON_CONTRACT_VERSION,
                "decision_match": self.decision_match,
                "non_broadening": self.non_broadening,
                "observed_admission_outcome": self.observed_admission_outcome.value,
                "observed_decision": self.observed_decision.value,
                "observed_specialization": (
                    self.observed_specialization.value
                    if self.observed_specialization is not None
                    else None
                ),
                "observed_target_capabilities": [item.value for item in capabilities],
                "passed": self.passed,
                "source_capability_slots": self.source_capability_slots,
                "specialist_capability_slots": self.specialist_capability_slots,
                "specialization_match": self.specialization_match,
                "target_scope_match": self.target_scope_match,
            }
        )
        _validate_digest(
            self.score_sha256,
            label="score_sha256",
            expected=expected_sha256,
        )
        expected_id = f"{MULTI_AGENT_COMPARISON_CONTRACT_VERSION}:score:{expected_sha256}"
        if self.score_id != expected_id:
            raise MultiAgentComparisonValidationError(
                "score_id must match the content-addressed comparison score"
            )


@dataclass(frozen=True, slots=True)
class MultiAgentComparisonReport:
    """Content-addressed offline report with runtime measurements explicitly absent."""

    dataset_id: str
    phase11_reference_corpus_sha256: str
    phase11_reference_report_sha256: str
    case_scores: tuple[MultiAgentComparisonCaseScore, ...]
    total_cases: int
    passed_cases: int
    decision_matches: int
    specialization_matches: int
    admission_matches: int
    target_scope_matches: int
    non_broadening_cases: int
    bounds_compliant_cases: int
    handoff_cases: int
    abstention_cases: int
    source_capability_slots_for_handoffs: int
    specialist_capability_slots: int
    capability_slots_removed: int
    offline_capability_executions: int
    model_invocation_count: None
    input_tokens: None
    output_tokens: None
    total_tokens: None
    provider_latency_ms: None
    client_elapsed_ms: None
    sdk_retries: None
    inference_cost_usd: None
    report_sha256: str
    report_id: str

    def __post_init__(self) -> None:
        """Validate aggregate metrics, unmeasured runtime fields, and report identity."""
        dataset_id = _validate_identifier(
            self.dataset_id,
            label="dataset_id",
            pattern=_DATASET_ID_PATTERN,
        )
        if self.phase11_reference_corpus_sha256 != PHASE11_REFERENCE_CORPUS_SHA256:
            raise MultiAgentComparisonValidationError("report Phase 11 corpus reference drifted")
        if self.phase11_reference_report_sha256 != PHASE11_REFERENCE_REPORT_SHA256:
            raise MultiAgentComparisonValidationError("report Phase 11 result reference drifted")
        if type(self.case_scores) is not tuple or not self.case_scores:
            raise MultiAgentComparisonValidationError("comparison report scores cannot be empty")
        if any(type(score) is not MultiAgentComparisonCaseScore for score in self.case_scores):
            raise MultiAgentComparisonValidationError("comparison report score type is invalid")

        integer_metrics = (
            self.total_cases,
            self.passed_cases,
            self.decision_matches,
            self.specialization_matches,
            self.admission_matches,
            self.target_scope_matches,
            self.non_broadening_cases,
            self.bounds_compliant_cases,
            self.handoff_cases,
            self.abstention_cases,
            self.source_capability_slots_for_handoffs,
            self.specialist_capability_slots,
            self.capability_slots_removed,
            self.offline_capability_executions,
        )
        if any(type(value) is not int or value < 0 for value in integer_metrics):
            raise MultiAgentComparisonValidationError(
                "comparison report integer metrics must be non-negative integers"
            )
        if self.total_cases != len(self.case_scores):
            raise MultiAgentComparisonValidationError(
                "total_cases must match the number of case scores"
            )
        if self.handoff_cases + self.abstention_cases > self.total_cases:
            raise MultiAgentComparisonValidationError(
                "handoff and abstention counts exceed total cases"
            )
        if self.capability_slots_removed != (
            self.source_capability_slots_for_handoffs - self.specialist_capability_slots
        ):
            raise MultiAgentComparisonValidationError(
                "capability_slots_removed must match deterministic slot arithmetic"
            )
        if self.capability_slots_removed < 0:
            raise MultiAgentComparisonValidationError(
                "comparison report cannot claim capability-surface broadening"
            )
        if self.offline_capability_executions != 0:
            raise MultiAgentComparisonValidationError(
                "offline comparison cannot execute capabilities"
            )
        runtime_fields = (
            self.model_invocation_count,
            self.input_tokens,
            self.output_tokens,
            self.total_tokens,
            self.provider_latency_ms,
            self.client_elapsed_ms,
            self.sdk_retries,
            self.inference_cost_usd,
        )
        if any(value is not None for value in runtime_fields):
            raise MultiAgentComparisonValidationError(
                "Gate 12.2 runtime measurements must remain explicitly unmeasured"
            )

        expected_sha256 = _canonical_sha256(
            {
                "admission_matches": self.admission_matches,
                "bounds_compliant_cases": self.bounds_compliant_cases,
                "capability_slots_removed": self.capability_slots_removed,
                "case_score_ids": [score.score_id for score in self.case_scores],
                "client_elapsed_ms": None,
                "contract_version": MULTI_AGENT_COMPARISON_CONTRACT_VERSION,
                "dataset_id": dataset_id,
                "decision_matches": self.decision_matches,
                "handoff_cases": self.handoff_cases,
                "inference_cost_usd": None,
                "input_tokens": None,
                "model_invocation_count": None,
                "non_broadening_cases": self.non_broadening_cases,
                "offline_capability_executions": self.offline_capability_executions,
                "output_tokens": None,
                "passed_cases": self.passed_cases,
                "phase11_reference_corpus_sha256": self.phase11_reference_corpus_sha256,
                "phase11_reference_report_sha256": self.phase11_reference_report_sha256,
                "provider_latency_ms": None,
                "sdk_retries": None,
                "source_capability_slots_for_handoffs": (
                    self.source_capability_slots_for_handoffs
                ),
                "specialist_capability_slots": self.specialist_capability_slots,
                "specialization_matches": self.specialization_matches,
                "target_scope_matches": self.target_scope_matches,
                "total_cases": self.total_cases,
                "total_tokens": None,
                "abstention_cases": self.abstention_cases,
            }
        )
        _validate_digest(
            self.report_sha256,
            label="report_sha256",
            expected=expected_sha256,
        )
        expected_id = f"{MULTI_AGENT_COMPARISON_CONTRACT_VERSION}:report:{expected_sha256}"
        if self.report_id != expected_id:
            raise MultiAgentComparisonValidationError(
                "report_id must match the content-addressed comparison report"
            )


def create_multi_agent_comparison_case(
    *,
    case_key: str,
    task: SingleAgentTask,
    proposal: MultiAgentHandoffProposal,
    expected: MultiAgentComparisonExpectation,
) -> MultiAgentComparisonCase:
    """Create one content-addressed comparison case."""
    normalized_key = _normalize_case_key(case_key)
    if type(task) is not SingleAgentTask:
        raise MultiAgentComparisonValidationError("task must be one admitted SingleAgentTask")
    if type(proposal) is not MultiAgentHandoffProposal:
        raise MultiAgentComparisonValidationError("proposal must be MultiAgentHandoffProposal")
    if type(expected) is not MultiAgentComparisonExpectation:
        raise MultiAgentComparisonValidationError(
            "expected must be MultiAgentComparisonExpectation"
        )
    if proposal.source_task_id != task.task_id:
        raise MultiAgentComparisonValidationError(
            "synthetic proposal must bind to the comparison source task"
        )
    digest = _canonical_sha256(
        {
            "case_key": normalized_key,
            "contract_version": MULTI_AGENT_COMPARISON_CONTRACT_VERSION,
            "expected": _expectation_payload(
                decision=expected.decision,
                target_specialization=expected.target_specialization,
                admission_outcome=expected.admission_outcome,
                target_capabilities=expected.target_capabilities,
            ),
            "proposal_id": proposal.proposal_id,
            "task_id": task.task_id,
        }
    )
    return MultiAgentComparisonCase(
        case_key=normalized_key,
        task=task,
        proposal=proposal,
        expected=expected,
        case_sha256=digest,
        case_id=f"{MULTI_AGENT_COMPARISON_CONTRACT_VERSION}:case:{digest}",
    )


def create_multi_agent_comparison_dataset(
    *,
    phase11_reference_corpus_sha256: str,
    phase11_reference_report_sha256: str,
    cases: tuple[MultiAgentComparisonCase, ...],
) -> MultiAgentComparisonDataset:
    """Create a content-addressed comparison dataset bound to Phase 11 evidence."""
    if phase11_reference_corpus_sha256 != PHASE11_REFERENCE_CORPUS_SHA256:
        raise MultiAgentComparisonValidationError("Phase 11 corpus reference drifted")
    if phase11_reference_report_sha256 != PHASE11_REFERENCE_REPORT_SHA256:
        raise MultiAgentComparisonValidationError("Phase 11 report reference drifted")
    if type(cases) is not tuple or not cases:
        raise MultiAgentComparisonValidationError("comparison dataset cases cannot be empty")
    if any(type(case) is not MultiAgentComparisonCase for case in cases):
        raise MultiAgentComparisonValidationError("comparison dataset case type is invalid")
    digest = _canonical_sha256(
        {
            "case_ids": [case.case_id for case in cases],
            "contract_version": MULTI_AGENT_COMPARISON_CONTRACT_VERSION,
            "phase11_reference_corpus_sha256": phase11_reference_corpus_sha256,
            "phase11_reference_report_sha256": phase11_reference_report_sha256,
        }
    )
    return MultiAgentComparisonDataset(
        phase11_reference_corpus_sha256=phase11_reference_corpus_sha256,
        phase11_reference_report_sha256=phase11_reference_report_sha256,
        cases=cases,
        dataset_sha256=digest,
        dataset_id=f"{MULTI_AGENT_COMPARISON_CONTRACT_VERSION}:dataset:{digest}",
    )


__all__ = [
    "MAX_MULTI_AGENT_COMPARISON_CASES",
    "MULTI_AGENT_COMPARISON_CONTRACT_VERSION",
    "PHASE11_REFERENCE_CORPUS_SHA256",
    "PHASE11_REFERENCE_REPORT_SHA256",
    "MultiAgentComparisonAdmissionOutcome",
    "MultiAgentComparisonCase",
    "MultiAgentComparisonCaseScore",
    "MultiAgentComparisonDataset",
    "MultiAgentComparisonExpectation",
    "MultiAgentComparisonReport",
    "create_multi_agent_comparison_case",
    "create_multi_agent_comparison_dataset",
]
