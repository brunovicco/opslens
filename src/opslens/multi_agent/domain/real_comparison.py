"""Deterministic evaluation contracts for the first real two-model comparison."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import cast

from opslens.agent_baseline.domain.models import (
    AgentCapability,
    AgentDecision,
    SingleAgentTask,
)
from opslens.agent_baseline.domain.reasoning import AgentReasoningAuthorizationOutcome
from opslens.multi_agent.domain.comparison import (
    PHASE11_REFERENCE_CORPUS_SHA256,
    PHASE11_REFERENCE_REPORT_SHA256,
    MultiAgentComparisonAdmissionOutcome,
)
from opslens.multi_agent.domain.errors import MultiAgentRealComparisonValidationError
from opslens.multi_agent.domain.handoff import (
    MAX_SPECIALIST_CAPABILITIES,
    AgentSpecialization,
    MultiAgentHandoffDecision,
    capabilities_for_specialization,
)
from opslens.multi_agent.domain.two_model_reasoning import (
    MAX_MULTI_AGENT_CAPABILITY_EXECUTIONS,
    MAX_MULTI_AGENT_MODEL_INVOCATIONS_PER_TASK,
    MultiAgentTwoModelOutcome,
    MultiAgentTwoModelReasoningResult,
)

MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION = "multi-agent-real-comparison:v1"
MAX_MULTI_AGENT_REAL_COMPARISON_CASES = 32
GATE12_REFERENCE_DATASET_SHA256 = (
    "1ad7f6274edea7d515f5827859d8a39bdde8edecc9a2ed58dc09df16b09dd491"
)
GATE12_REFERENCE_REPORT_SHA256 = (
    "0586822800f028d0bb5c7cdb937db4af2f685abde3e09c76afd979d4e1abc222"
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_CASE_KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$", re.ASCII)
_CASE_ID_PATTERN = re.compile(
    rf"^{re.escape(MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION)}:case:[0-9a-f]{{64}}$",
    re.ASCII,
)
_SCORE_ID_PATTERN = re.compile(
    rf"^{re.escape(MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION)}:score:[0-9a-f]{{64}}$",
    re.ASCII,
)
_DATASET_ID_PATTERN = re.compile(
    rf"^{re.escape(MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION)}:dataset:[0-9a-f]{{64}}$",
    re.ASCII,
)
_REPORT_ID_PATTERN = re.compile(
    rf"^{re.escape(MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION)}:report:[0-9a-f]{{64}}$",
    re.ASCII,
)


def _canonical_sha256(value: object) -> str:
    """Return SHA-256 over deterministic canonical JSON."""
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _validate_digest(value: object, *, label: str, expected: str) -> None:
    """Require one exact lowercase SHA-256 digest."""
    if (
        type(value) is not str
        or _SHA256_PATTERN.fullmatch(value) is None
        or value != expected
    ):
        raise MultiAgentRealComparisonValidationError(
            f"{label} must match canonical real-comparison semantics"
        )


def _validate_identifier(
    value: object,
    *,
    label: str,
    pattern: re.Pattern[str],
) -> str:
    """Require one versioned content-addressed identifier."""
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise MultiAgentRealComparisonValidationError(
            f"{label} violates the real-comparison identity contract"
        )
    return value


def _case_key(value: object) -> str:
    """Validate one stable bounded case key."""
    if type(value) is not str or _CASE_KEY_PATTERN.fullmatch(value) is None:
        raise MultiAgentRealComparisonValidationError(
            "case_key violates the real-comparison contract"
        )
    return value


def _capabilities(
    value: object,
    *,
    allow_empty: bool,
) -> tuple[AgentCapability, ...]:
    """Validate one canonical specialist capability scope."""
    if type(value) is not tuple:
        raise MultiAgentRealComparisonValidationError("capability scope must be a tuple")
    raw = cast(tuple[object, ...], value)
    if not allow_empty and not raw:
        raise MultiAgentRealComparisonValidationError("capability scope cannot be empty")
    if len(raw) > MAX_SPECIALIST_CAPABILITIES:
        raise MultiAgentRealComparisonValidationError(
            "capability scope exceeds the specialist limit"
        )
    if any(type(item) is not AgentCapability for item in raw):
        raise MultiAgentRealComparisonValidationError(
            "capability scope must contain only AgentCapability values"
        )
    typed = cast(tuple[AgentCapability, ...], raw)
    if len(set(typed)) != len(typed):
        raise MultiAgentRealComparisonValidationError(
            "capability scope cannot contain duplicates"
        )
    canonical = tuple(sorted(typed, key=lambda item: item.value))
    if typed != canonical:
        raise MultiAgentRealComparisonValidationError(
            "capability scope must use canonical order"
        )
    return typed


@dataclass(frozen=True, slots=True)
class MultiAgentRealComparisonExpectation:
    """Expected triage, handoff, and final specialist behavior for one real case."""

    triage_decision: MultiAgentHandoffDecision
    target_specialization: AgentSpecialization | None
    admission_outcome: MultiAgentComparisonAdmissionOutcome
    target_capabilities: tuple[AgentCapability, ...]
    specialist_capability: AgentCapability | None

    def __post_init__(self) -> None:
        """Reject inconsistent expected multi-stage behavior."""
        if type(self.triage_decision) is not MultiAgentHandoffDecision:
            raise MultiAgentRealComparisonValidationError(
                "triage_decision must be MultiAgentHandoffDecision"
            )
        if self.target_specialization is not None and type(
            self.target_specialization
        ) is not AgentSpecialization:
            raise MultiAgentRealComparisonValidationError(
                "target_specialization must be AgentSpecialization or null"
            )
        if type(self.admission_outcome) is not MultiAgentComparisonAdmissionOutcome:
            raise MultiAgentRealComparisonValidationError(
                "admission_outcome is not supported"
            )
        scope = _capabilities(
            self.target_capabilities,
            allow_empty=self.admission_outcome
            is not MultiAgentComparisonAdmissionOutcome.HANDOFF,
        )
        object.__setattr__(self, "target_capabilities", scope)
        if self.specialist_capability is not None and type(
            self.specialist_capability
        ) is not AgentCapability:
            raise MultiAgentRealComparisonValidationError(
                "specialist_capability must be AgentCapability or null"
            )

        if self.admission_outcome is MultiAgentComparisonAdmissionOutcome.HANDOFF:
            if self.triage_decision is not MultiAgentHandoffDecision.HANDOFF:
                raise MultiAgentRealComparisonValidationError(
                    "HANDOFF expectation requires a HANDOFF triage decision"
                )
            specialization = self.target_specialization
            if specialization is None:
                raise MultiAgentRealComparisonValidationError(
                    "HANDOFF expectation requires one specialization"
                )
            if not set(scope).issubset(capabilities_for_specialization(specialization)):
                raise MultiAgentRealComparisonValidationError(
                    "target capabilities exceed the expected specialization scope"
                )
            capability = self.specialist_capability
            if capability is None or capability not in scope:
                raise MultiAgentRealComparisonValidationError(
                    "HANDOFF expectation requires one specialist capability in target scope"
                )
            return

        if self.triage_decision is not MultiAgentHandoffDecision.ABSTAIN:
            raise MultiAgentRealComparisonValidationError(
                "non-handoff baseline expectations must use triage ABSTAIN"
            )
        if self.target_specialization is not None or scope:
            raise MultiAgentRealComparisonValidationError(
                "triage abstention cannot carry specialization or target scope"
            )
        if self.specialist_capability is not None:
            raise MultiAgentRealComparisonValidationError(
                "triage abstention cannot expect specialist reasoning"
            )
        if self.admission_outcome is not MultiAgentComparisonAdmissionOutcome.ABSTAINED:
            raise MultiAgentRealComparisonValidationError(
                "the frozen baseline uses ABSTAINED for no-specialist cases"
            )


def _expectation_payload(
    expectation: MultiAgentRealComparisonExpectation,
) -> dict[str, object]:
    return {
        "admission_outcome": expectation.admission_outcome.value,
        "specialist_capability": (
            expectation.specialist_capability.value
            if expectation.specialist_capability is not None
            else None
        ),
        "target_capabilities": [item.value for item in expectation.target_capabilities],
        "target_specialization": (
            expectation.target_specialization.value
            if expectation.target_specialization is not None
            else None
        ),
        "triage_decision": expectation.triage_decision.value,
    }


@dataclass(frozen=True, slots=True)
class MultiAgentRealComparisonCase:
    """One content-addressed task and predeclared real two-model expectation."""

    case_key: str
    task: SingleAgentTask
    expected: MultiAgentRealComparisonExpectation
    case_sha256: str
    case_id: str

    def __post_init__(self) -> None:
        """Bind one case to task identity and exact expected semantics."""
        key = _case_key(self.case_key)
        if type(self.task) is not SingleAgentTask:
            raise MultiAgentRealComparisonValidationError(
                "case task must be one admitted SingleAgentTask"
            )
        if type(self.expected) is not MultiAgentRealComparisonExpectation:
            raise MultiAgentRealComparisonValidationError(
                "case expected value must be MultiAgentRealComparisonExpectation"
            )
        expected_digest = _canonical_sha256(
            {
                "case_key": key,
                "contract_version": MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION,
                "expected": _expectation_payload(self.expected),
                "task_id": self.task.task_id,
            }
        )
        _validate_digest(
            self.case_sha256,
            label="case_sha256",
            expected=expected_digest,
        )
        expected_id = (
            f"{MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION}:case:{expected_digest}"
        )
        if self.case_id != expected_id or _CASE_ID_PATTERN.fullmatch(self.case_id) is None:
            raise MultiAgentRealComparisonValidationError(
                "case_id must match the content-addressed case identity"
            )

    @classmethod
    def create(
        cls,
        *,
        case_key: str,
        task: SingleAgentTask,
        expected: MultiAgentRealComparisonExpectation,
    ) -> MultiAgentRealComparisonCase:
        """Create one deterministic predeclared real-comparison case."""
        key = _case_key(case_key)
        payload = {
            "case_key": key,
            "contract_version": MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION,
            "expected": _expectation_payload(expected),
            "task_id": task.task_id,
        }
        digest = _canonical_sha256(payload)
        return cls(
            case_key=key,
            task=task,
            expected=expected,
            case_sha256=digest,
            case_id=f"{MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION}:case:{digest}",
        )


@dataclass(frozen=True, slots=True)
class MultiAgentRealComparisonDataset:
    """Frozen real experiment corpus bound to Phase 11 and Gate 12.2 evidence."""

    phase11_reference_corpus_sha256: str
    phase11_reference_report_sha256: str
    gate12_reference_dataset_sha256: str
    gate12_reference_report_sha256: str
    cases: tuple[MultiAgentRealComparisonCase, ...]
    dataset_sha256: str
    dataset_id: str

    def __post_init__(self) -> None:
        """Reject reference drift, duplicate cases, or forged dataset identity."""
        if self.phase11_reference_corpus_sha256 != PHASE11_REFERENCE_CORPUS_SHA256:
            raise MultiAgentRealComparisonValidationError("Phase 11 corpus reference drifted")
        if self.phase11_reference_report_sha256 != PHASE11_REFERENCE_REPORT_SHA256:
            raise MultiAgentRealComparisonValidationError("Phase 11 report reference drifted")
        if self.gate12_reference_dataset_sha256 != GATE12_REFERENCE_DATASET_SHA256:
            raise MultiAgentRealComparisonValidationError("Gate 12.2 dataset reference drifted")
        if self.gate12_reference_report_sha256 != GATE12_REFERENCE_REPORT_SHA256:
            raise MultiAgentRealComparisonValidationError("Gate 12.2 report reference drifted")
        if type(self.cases) is not tuple or not self.cases:
            raise MultiAgentRealComparisonValidationError("real comparison cases cannot be empty")
        if len(self.cases) > MAX_MULTI_AGENT_REAL_COMPARISON_CASES:
            raise MultiAgentRealComparisonValidationError(
                "real comparison cases exceed the v1 limit"
            )
        if any(type(case) is not MultiAgentRealComparisonCase for case in self.cases):
            raise MultiAgentRealComparisonValidationError(
                "real comparison cases contain an unsupported value"
            )
        ordered = tuple(sorted(self.cases, key=lambda item: item.case_key))
        if ordered != self.cases:
            raise MultiAgentRealComparisonValidationError(
                "real comparison cases must use canonical order"
            )
        if len({case.case_key for case in self.cases}) != len(self.cases):
            raise MultiAgentRealComparisonValidationError(
                "real comparison case keys must be unique"
            )
        expected = _dataset_digest(
            phase11_corpus=self.phase11_reference_corpus_sha256,
            phase11_report=self.phase11_reference_report_sha256,
            gate12_dataset=self.gate12_reference_dataset_sha256,
            gate12_report=self.gate12_reference_report_sha256,
            cases=self.cases,
        )
        _validate_digest(self.dataset_sha256, label="dataset_sha256", expected=expected)
        expected_id = (
            f"{MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION}:dataset:{expected}"
        )
        if self.dataset_id != expected_id or _DATASET_ID_PATTERN.fullmatch(self.dataset_id) is None:
            raise MultiAgentRealComparisonValidationError(
                "dataset_id must match content-addressed dataset semantics"
            )

    @classmethod
    def create(
        cls,
        *,
        cases: tuple[MultiAgentRealComparisonCase, ...],
    ) -> MultiAgentRealComparisonDataset:
        """Create the canonical experiment dataset against frozen reference identities."""
        if type(cases) is not tuple:
            raise MultiAgentRealComparisonValidationError("cases must be a tuple")
        ordered = tuple(sorted(cases, key=lambda item: item.case_key))
        digest = _dataset_digest(
            phase11_corpus=PHASE11_REFERENCE_CORPUS_SHA256,
            phase11_report=PHASE11_REFERENCE_REPORT_SHA256,
            gate12_dataset=GATE12_REFERENCE_DATASET_SHA256,
            gate12_report=GATE12_REFERENCE_REPORT_SHA256,
            cases=ordered,
        )
        return cls(
            phase11_reference_corpus_sha256=PHASE11_REFERENCE_CORPUS_SHA256,
            phase11_reference_report_sha256=PHASE11_REFERENCE_REPORT_SHA256,
            gate12_reference_dataset_sha256=GATE12_REFERENCE_DATASET_SHA256,
            gate12_reference_report_sha256=GATE12_REFERENCE_REPORT_SHA256,
            cases=ordered,
            dataset_sha256=digest,
            dataset_id=(
                f"{MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION}:dataset:{digest}"
            ),
        )


def _dataset_digest(
    *,
    phase11_corpus: str,
    phase11_report: str,
    gate12_dataset: str,
    gate12_report: str,
    cases: tuple[MultiAgentRealComparisonCase, ...],
) -> str:
    return _canonical_sha256(
        {
            "case_ids": [case.case_id for case in cases],
            "contract_version": MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION,
            "gate12_reference_dataset_sha256": gate12_dataset,
            "gate12_reference_report_sha256": gate12_report,
            "phase11_reference_corpus_sha256": phase11_corpus,
            "phase11_reference_report_sha256": phase11_report,
        }
    )


def _observed_admission(
    result: MultiAgentTwoModelReasoningResult,
) -> MultiAgentComparisonAdmissionOutcome:
    if result.outcome is MultiAgentTwoModelOutcome.SPECIALIST_REASONED:
        return MultiAgentComparisonAdmissionOutcome.HANDOFF
    if result.outcome is MultiAgentTwoModelOutcome.TRIAGE_ABSTAINED:
        return MultiAgentComparisonAdmissionOutcome.ABSTAINED
    return MultiAgentComparisonAdmissionOutcome.REJECTED


def _observed_target_capabilities(
    result: MultiAgentTwoModelReasoningResult,
) -> tuple[AgentCapability, ...]:
    specialist = result.specialist_result
    if specialist is None:
        return ()
    return specialist.task.allowed_capabilities


@dataclass(frozen=True, slots=True)
class MultiAgentRealComparisonCaseScore:
    """Decomposed quality, authority, and runtime score for one real observation."""

    case_key: str
    case_id: str
    result_id: str
    triage_decision_match: bool
    specialization_match: bool
    admission_match: bool
    target_scope_match: bool
    non_broadening: bool
    specialist_decision_match: bool
    specialist_capability_match: bool
    specialist_authorization_match: bool
    runtime_bounds_compliant: bool
    passed: bool
    model_invocation_count: int
    triage_input_tokens: int
    triage_output_tokens: int
    triage_total_tokens: int
    triage_provider_latency_ms: int
    triage_client_elapsed_ms: int
    triage_retry_attempts: int
    specialist_input_tokens: int
    specialist_output_tokens: int
    specialist_total_tokens: int
    specialist_provider_latency_ms: int
    specialist_client_elapsed_ms: int
    specialist_retry_attempts: int
    capability_executions: int
    score_sha256: str
    score_id: str

    def __post_init__(self) -> None:
        """Validate score decomposition, runtime bounds, and evidence identity."""
        key = _case_key(self.case_key)
        case_id = _validate_identifier(
            self.case_id,
            label="case_id",
            pattern=_CASE_ID_PATTERN,
        )
        if type(self.result_id) is not str or not self.result_id.strip():
            raise MultiAgentRealComparisonValidationError(
                "result_id must be a non-empty string"
            )
        flags = (
            self.triage_decision_match,
            self.specialization_match,
            self.admission_match,
            self.target_scope_match,
            self.non_broadening,
            self.specialist_decision_match,
            self.specialist_capability_match,
            self.specialist_authorization_match,
            self.runtime_bounds_compliant,
            self.passed,
        )
        if any(type(flag) is not bool for flag in flags):
            raise MultiAgentRealComparisonValidationError("score flags must be bool")
        if self.passed is not all(flags[:-1]):
            raise MultiAgentRealComparisonValidationError(
                "passed must equal all decomposed quality and runtime dimensions"
            )
        for label, value in self._runtime_values().items():
            if type(value) is not int or value < 0:
                raise MultiAgentRealComparisonValidationError(
                    f"{label} must be a non-negative integer"
                )
        if not 1 <= self.model_invocation_count <= MAX_MULTI_AGENT_MODEL_INVOCATIONS_PER_TASK:
            raise MultiAgentRealComparisonValidationError(
                "model_invocation_count violates the frozen bound"
            )
        if self.capability_executions != MAX_MULTI_AGENT_CAPABILITY_EXECUTIONS:
            raise MultiAgentRealComparisonValidationError(
                "real comparison cannot execute capabilities"
            )
        expected = _canonical_sha256(self._identity_payload(case_id=case_id, key=key))
        _validate_digest(self.score_sha256, label="score_sha256", expected=expected)
        expected_id = f"{MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION}:score:{expected}"
        if self.score_id != expected_id or _SCORE_ID_PATTERN.fullmatch(self.score_id) is None:
            raise MultiAgentRealComparisonValidationError(
                "score_id must match content-addressed score semantics"
            )

    def _runtime_values(self) -> dict[str, int]:
        return {
            "capability_executions": self.capability_executions,
            "model_invocation_count": self.model_invocation_count,
            "specialist_client_elapsed_ms": self.specialist_client_elapsed_ms,
            "specialist_input_tokens": self.specialist_input_tokens,
            "specialist_output_tokens": self.specialist_output_tokens,
            "specialist_provider_latency_ms": self.specialist_provider_latency_ms,
            "specialist_retry_attempts": self.specialist_retry_attempts,
            "specialist_total_tokens": self.specialist_total_tokens,
            "triage_client_elapsed_ms": self.triage_client_elapsed_ms,
            "triage_input_tokens": self.triage_input_tokens,
            "triage_output_tokens": self.triage_output_tokens,
            "triage_provider_latency_ms": self.triage_provider_latency_ms,
            "triage_retry_attempts": self.triage_retry_attempts,
            "triage_total_tokens": self.triage_total_tokens,
        }

    def _identity_payload(self, *, case_id: str, key: str) -> dict[str, object]:
        return {
            **self._runtime_values(),
            "admission_match": self.admission_match,
            "case_id": case_id,
            "case_key": key,
            "contract_version": MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION,
            "non_broadening": self.non_broadening,
            "passed": self.passed,
            "result_id": self.result_id,
            "runtime_bounds_compliant": self.runtime_bounds_compliant,
            "specialist_authorization_match": self.specialist_authorization_match,
            "specialist_capability_match": self.specialist_capability_match,
            "specialist_decision_match": self.specialist_decision_match,
            "specialization_match": self.specialization_match,
            "target_scope_match": self.target_scope_match,
            "triage_decision_match": self.triage_decision_match,
        }

    @classmethod
    def create(
        cls,
        *,
        case: MultiAgentRealComparisonCase,
        result: MultiAgentTwoModelReasoningResult,
    ) -> MultiAgentRealComparisonCaseScore:
        """Score one real observation against predeclared deterministic expectations."""
        if result.source_task.task_id != case.task.task_id:
            raise MultiAgentRealComparisonValidationError(
                "result is not bound to the real-comparison case"
            )
        expected = case.expected
        proposal = result.triage_result.proposal
        observed_admission = _observed_admission(result)
        observed_scope = _observed_target_capabilities(result)
        triage_decision_match = proposal.decision is expected.triage_decision
        specialization_match = (
            proposal.target_specialization is expected.target_specialization
        )
        admission_match = observed_admission is expected.admission_outcome
        target_scope_match = observed_scope == expected.target_capabilities
        non_broadening = set(observed_scope).issubset(case.task.allowed_capabilities)

        specialist = result.specialist_result
        if expected.specialist_capability is None:
            specialist_decision_match = specialist is None
            specialist_capability_match = specialist is None
            specialist_authorization_match = specialist is None
        elif specialist is None:
            specialist_decision_match = False
            specialist_capability_match = False
            specialist_authorization_match = False
        else:
            specialist_decision_match = specialist.proposal.decision is AgentDecision.ACT
            specialist_capability_match = (
                specialist.proposal.capability is expected.specialist_capability
            )
            specialist_authorization_match = (
                specialist.authorization_outcome
                is AgentReasoningAuthorizationOutcome.AUTHORIZED
            )

        triage_evidence = result.triage_result.invocation_evidence
        specialist_evidence = specialist.invocation_evidence if specialist is not None else None
        expected_invocations = 2 if expected.specialist_capability is not None else 1
        runtime_bounds_compliant = (
            result.model_invocation_count == expected_invocations
            and triage_evidence.retry_attempts == 0
            and (
                specialist_evidence is None
                or specialist_evidence.retry_attempts == 0
            )
            and result.capability_executions == 0
        )
        flags = (
            triage_decision_match,
            specialization_match,
            admission_match,
            target_scope_match,
            non_broadening,
            specialist_decision_match,
            specialist_capability_match,
            specialist_authorization_match,
            runtime_bounds_compliant,
        )
        passed = all(flags)
        values: dict[str, object] = {
            "admission_match": admission_match,
            "capability_executions": result.capability_executions,
            "case_id": case.case_id,
            "case_key": case.case_key,
            "contract_version": MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION,
            "model_invocation_count": result.model_invocation_count,
            "non_broadening": non_broadening,
            "passed": passed,
            "result_id": result.result_id,
            "runtime_bounds_compliant": runtime_bounds_compliant,
            "specialist_authorization_match": specialist_authorization_match,
            "specialist_capability_match": specialist_capability_match,
            "specialist_client_elapsed_ms": (
                specialist_evidence.client_elapsed_ms if specialist_evidence else 0
            ),
            "specialist_decision_match": specialist_decision_match,
            "specialist_input_tokens": (
                specialist_evidence.input_tokens if specialist_evidence else 0
            ),
            "specialist_output_tokens": (
                specialist_evidence.output_tokens if specialist_evidence else 0
            ),
            "specialist_provider_latency_ms": (
                specialist_evidence.provider_latency_ms if specialist_evidence else 0
            ),
            "specialist_retry_attempts": (
                specialist_evidence.retry_attempts if specialist_evidence else 0
            ),
            "specialist_total_tokens": (
                specialist_evidence.total_tokens if specialist_evidence else 0
            ),
            "specialization_match": specialization_match,
            "target_scope_match": target_scope_match,
            "triage_client_elapsed_ms": triage_evidence.client_elapsed_ms,
            "triage_decision_match": triage_decision_match,
            "triage_input_tokens": triage_evidence.input_tokens,
            "triage_output_tokens": triage_evidence.output_tokens,
            "triage_provider_latency_ms": triage_evidence.provider_latency_ms,
            "triage_retry_attempts": triage_evidence.retry_attempts,
            "triage_total_tokens": triage_evidence.total_tokens,
        }
        digest = _canonical_sha256(values)
        return cls(
            case_key=case.case_key,
            case_id=case.case_id,
            result_id=result.result_id,
            triage_decision_match=triage_decision_match,
            specialization_match=specialization_match,
            admission_match=admission_match,
            target_scope_match=target_scope_match,
            non_broadening=non_broadening,
            specialist_decision_match=specialist_decision_match,
            specialist_capability_match=specialist_capability_match,
            specialist_authorization_match=specialist_authorization_match,
            runtime_bounds_compliant=runtime_bounds_compliant,
            passed=passed,
            model_invocation_count=result.model_invocation_count,
            triage_input_tokens=triage_evidence.input_tokens,
            triage_output_tokens=triage_evidence.output_tokens,
            triage_total_tokens=triage_evidence.total_tokens,
            triage_provider_latency_ms=triage_evidence.provider_latency_ms,
            triage_client_elapsed_ms=triage_evidence.client_elapsed_ms,
            triage_retry_attempts=triage_evidence.retry_attempts,
            specialist_input_tokens=(
                specialist_evidence.input_tokens if specialist_evidence else 0
            ),
            specialist_output_tokens=(
                specialist_evidence.output_tokens if specialist_evidence else 0
            ),
            specialist_total_tokens=(
                specialist_evidence.total_tokens if specialist_evidence else 0
            ),
            specialist_provider_latency_ms=(
                specialist_evidence.provider_latency_ms if specialist_evidence else 0
            ),
            specialist_client_elapsed_ms=(
                specialist_evidence.client_elapsed_ms if specialist_evidence else 0
            ),
            specialist_retry_attempts=(
                specialist_evidence.retry_attempts if specialist_evidence else 0
            ),
            capability_executions=result.capability_executions,
            score_sha256=digest,
            score_id=(
                f"{MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION}:score:{digest}"
            ),
        )


@dataclass(frozen=True, slots=True)
class MultiAgentRealComparisonMetrics:
    """Decomposed aggregate quality and observed runtime totals."""

    total_cases: int
    passed_cases: int
    triage_decision_matches: int
    specialization_matches: int
    admission_matches: int
    target_scope_matches: int
    non_broadening_cases: int
    specialist_decision_matches: int
    specialist_capability_matches: int
    specialist_authorization_matches: int
    runtime_bounds_compliant_cases: int
    specialist_cases: int
    model_invocations: int
    triage_input_tokens: int
    triage_output_tokens: int
    triage_total_tokens: int
    specialist_input_tokens: int
    specialist_output_tokens: int
    specialist_total_tokens: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    triage_provider_latency_ms: int
    specialist_provider_latency_ms: int
    triage_client_elapsed_ms: int
    specialist_client_elapsed_ms: int
    triage_retry_attempts: int
    specialist_retry_attempts: int
    total_retry_attempts: int
    capability_executions: int

    def __post_init__(self) -> None:
        """Reject impossible aggregate counts and token arithmetic."""
        if type(self.total_cases) is not int or self.total_cases <= 0:
            raise MultiAgentRealComparisonValidationError(
                "total_cases must be a positive integer"
            )
        for label, value in self.__dict__.items():
            if label == "total_cases":
                continue
            if type(value) is not int or value < 0:
                raise MultiAgentRealComparisonValidationError(
                    f"{label} must be a non-negative integer"
                )
        if self.total_input_tokens != self.triage_input_tokens + self.specialist_input_tokens:
            raise MultiAgentRealComparisonValidationError(
                "total_input_tokens must equal stage input token totals"
            )
        if self.total_output_tokens != (
            self.triage_output_tokens + self.specialist_output_tokens
        ):
            raise MultiAgentRealComparisonValidationError(
                "total_output_tokens must equal stage output token totals"
            )
        if self.total_tokens != self.total_input_tokens + self.total_output_tokens:
            raise MultiAgentRealComparisonValidationError(
                "total_tokens must equal total input plus output tokens"
            )
        if self.total_retry_attempts != (
            self.triage_retry_attempts + self.specialist_retry_attempts
        ):
            raise MultiAgentRealComparisonValidationError(
                "total_retry_attempts must equal stage retry totals"
            )
        if self.capability_executions != 0:
            raise MultiAgentRealComparisonValidationError(
                "real comparison metrics cannot contain capability execution"
            )


def _metrics(
    scores: tuple[MultiAgentRealComparisonCaseScore, ...],
) -> MultiAgentRealComparisonMetrics:
    triage_input = sum(item.triage_input_tokens for item in scores)
    triage_output = sum(item.triage_output_tokens for item in scores)
    specialist_input = sum(item.specialist_input_tokens for item in scores)
    specialist_output = sum(item.specialist_output_tokens for item in scores)
    triage_retries = sum(item.triage_retry_attempts for item in scores)
    specialist_retries = sum(item.specialist_retry_attempts for item in scores)
    return MultiAgentRealComparisonMetrics(
        total_cases=len(scores),
        passed_cases=sum(item.passed for item in scores),
        triage_decision_matches=sum(item.triage_decision_match for item in scores),
        specialization_matches=sum(item.specialization_match for item in scores),
        admission_matches=sum(item.admission_match for item in scores),
        target_scope_matches=sum(item.target_scope_match for item in scores),
        non_broadening_cases=sum(item.non_broadening for item in scores),
        specialist_decision_matches=sum(item.specialist_decision_match for item in scores),
        specialist_capability_matches=sum(item.specialist_capability_match for item in scores),
        specialist_authorization_matches=sum(
            item.specialist_authorization_match for item in scores
        ),
        runtime_bounds_compliant_cases=sum(
            item.runtime_bounds_compliant for item in scores
        ),
        specialist_cases=sum(item.specialist_total_tokens > 0 for item in scores),
        model_invocations=sum(item.model_invocation_count for item in scores),
        triage_input_tokens=triage_input,
        triage_output_tokens=triage_output,
        triage_total_tokens=sum(item.triage_total_tokens for item in scores),
        specialist_input_tokens=specialist_input,
        specialist_output_tokens=specialist_output,
        specialist_total_tokens=sum(item.specialist_total_tokens for item in scores),
        total_input_tokens=triage_input + specialist_input,
        total_output_tokens=triage_output + specialist_output,
        total_tokens=triage_input + specialist_input + triage_output + specialist_output,
        triage_provider_latency_ms=sum(
            item.triage_provider_latency_ms for item in scores
        ),
        specialist_provider_latency_ms=sum(
            item.specialist_provider_latency_ms for item in scores
        ),
        triage_client_elapsed_ms=sum(item.triage_client_elapsed_ms for item in scores),
        specialist_client_elapsed_ms=sum(
            item.specialist_client_elapsed_ms for item in scores
        ),
        triage_retry_attempts=triage_retries,
        specialist_retry_attempts=specialist_retries,
        total_retry_attempts=triage_retries + specialist_retries,
        capability_executions=sum(item.capability_executions for item in scores),
    )


@dataclass(frozen=True, slots=True)
class MultiAgentRealComparisonReport:
    """Content-addressed first-real-comparison report without pricing authority."""

    dataset_id: str
    dataset_sha256: str
    case_scores: tuple[MultiAgentRealComparisonCaseScore, ...]
    metrics: MultiAgentRealComparisonMetrics
    inference_cost_usd: None
    report_sha256: str
    report_id: str

    def __post_init__(self) -> None:
        """Bind exact dataset, scores, runtime totals, and explicit absent cost."""
        _validate_identifier(
            self.dataset_id,
            label="dataset_id",
            pattern=_DATASET_ID_PATTERN,
        )
        if type(self.dataset_sha256) is not str or _SHA256_PATTERN.fullmatch(
            self.dataset_sha256
        ) is None:
            raise MultiAgentRealComparisonValidationError(
                "dataset_sha256 must be one lowercase SHA-256 digest"
            )
        if type(self.case_scores) is not tuple or not self.case_scores:
            raise MultiAgentRealComparisonValidationError("case_scores cannot be empty")
        if any(type(item) is not MultiAgentRealComparisonCaseScore for item in self.case_scores):
            raise MultiAgentRealComparisonValidationError(
                "case_scores contain an unsupported value"
            )
        if type(self.metrics) is not MultiAgentRealComparisonMetrics:
            raise MultiAgentRealComparisonValidationError(
                "metrics must be MultiAgentRealComparisonMetrics"
            )
        if self.inference_cost_usd is not None:
            raise MultiAgentRealComparisonValidationError(
                "inference cost remains external until verified pricing is applied"
            )
        expected = _canonical_sha256(self._identity_payload())
        _validate_digest(self.report_sha256, label="report_sha256", expected=expected)
        expected_id = f"{MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION}:report:{expected}"
        if self.report_id != expected_id or _REPORT_ID_PATTERN.fullmatch(self.report_id) is None:
            raise MultiAgentRealComparisonValidationError(
                "report_id must match content-addressed report semantics"
            )

    def _identity_payload(self) -> dict[str, object]:
        return {
            "case_score_ids": [item.score_id for item in self.case_scores],
            "contract_version": MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION,
            "dataset_id": self.dataset_id,
            "dataset_sha256": self.dataset_sha256,
            "inference_cost_usd": None,
            "metrics": {
                name: value for name, value in self.metrics.__dict__.items()
            },
        }

    @classmethod
    def create(
        cls,
        *,
        dataset: MultiAgentRealComparisonDataset,
        scores: tuple[MultiAgentRealComparisonCaseScore, ...],
    ) -> MultiAgentRealComparisonReport:
        """Create one real comparison report from exact case observations."""
        if len(scores) != len(dataset.cases):
            raise MultiAgentRealComparisonValidationError(
                "score count must match real comparison case count"
            )
        score_keys = tuple(item.case_key for item in scores)
        case_keys = tuple(item.case_key for item in dataset.cases)
        if score_keys != case_keys:
            raise MultiAgentRealComparisonValidationError(
                "scores must preserve canonical dataset case order"
            )
        metrics = _metrics(scores)
        payload: dict[str, object] = {
            "case_score_ids": [item.score_id for item in scores],
            "contract_version": MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION,
            "dataset_id": dataset.dataset_id,
            "dataset_sha256": dataset.dataset_sha256,
            "inference_cost_usd": None,
            "metrics": {name: value for name, value in metrics.__dict__.items()},
        }
        digest = _canonical_sha256(payload)
        return cls(
            dataset_id=dataset.dataset_id,
            dataset_sha256=dataset.dataset_sha256,
            case_scores=scores,
            metrics=metrics,
            inference_cost_usd=None,
            report_sha256=digest,
            report_id=f"{MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION}:report:{digest}",
        )


__all__ = [
    "GATE12_REFERENCE_DATASET_SHA256",
    "GATE12_REFERENCE_REPORT_SHA256",
    "MAX_MULTI_AGENT_REAL_COMPARISON_CASES",
    "MULTI_AGENT_REAL_COMPARISON_CONTRACT_VERSION",
    "MultiAgentRealComparisonCase",
    "MultiAgentRealComparisonCaseScore",
    "MultiAgentRealComparisonDataset",
    "MultiAgentRealComparisonExpectation",
    "MultiAgentRealComparisonMetrics",
    "MultiAgentRealComparisonReport",
]
