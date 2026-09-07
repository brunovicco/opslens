"""Typed deterministic execution evidence for Phase 11 single-agent capabilities."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import TypeAlias

from opslens.agent_baseline.domain.errors import AgentCapabilityExecutionValidationError
from opslens.agent_baseline.domain.models import AgentCapability, AuthorizedAgentAction
from opslens.hybrid_retrieval.domain.synthesis import HybridSynthesisRequest
from opslens.knowledge_retrieval.domain.synthesis import SynthesisRequest
from opslens.public_analysis.domain.request import PublicAnalysisRequest
from opslens.semantic_query.application.models import AthenaQueryResult
from opslens.semantic_query.domain.models import SemanticQuery

SINGLE_AGENT_EXECUTION_CONTRACT_VERSION = "single-agent-execution:v1"
MAX_AGENT_EXECUTIONS_PER_CALL = 1
MAX_AGENT_EXECUTION_RETRIES = 0
MAX_AGENT_EXECUTION_ADAPTIVE_FALLBACKS = 0

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_ACTION_ID_PATTERN = re.compile(r"^single-agent-authority:v1:action:[0-9a-f]{64}$", re.ASCII)
_INVOCATION_ID_PATTERN = re.compile(
    rf"^{re.escape(SINGLE_AGENT_EXECUTION_CONTRACT_VERSION)}:invocation:[0-9a-f]{{64}}$",
    re.ASCII,
)
_EXECUTION_ID_PATTERN = re.compile(
    rf"^{re.escape(SINGLE_AGENT_EXECUTION_CONTRACT_VERSION)}:execution:[0-9a-f]{{64}}$",
    re.ASCII,
)


def _canonical_json(value: object) -> bytes:
    """Serialize deterministic execution identity payloads."""
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_sha256(value: object) -> str:
    """Hash one canonical execution identity payload."""
    return sha256(_canonical_json(value)).hexdigest()


def _validate_sha256(value: object, *, label: str, expected: str | None = None) -> str:
    """Validate one SHA-256 field and optionally its deterministic expected value."""
    if type(value) is not str or _SHA256_PATTERN.fullmatch(value) is None:
        raise AgentCapabilityExecutionValidationError(f"{label} must be lowercase SHA-256")
    if expected is not None and value != expected:
        raise AgentCapabilityExecutionValidationError(f"{label} must match canonical semantics")
    return value


def _validate_action(action: object, capability: AgentCapability) -> AuthorizedAgentAction:
    """Require one exact Gate 11.1 authorization for the fixed binding capability."""
    if type(action) is not AuthorizedAgentAction:
        raise AgentCapabilityExecutionValidationError(
            "capability invocation requires one AuthorizedAgentAction"
        )
    typed_action = action
    if typed_action.capability is not capability:
        raise AgentCapabilityExecutionValidationError(
            "authorized action capability does not match the typed invocation"
        )
    if _ACTION_ID_PATTERN.fullmatch(typed_action.action_id) is None:
        raise AgentCapabilityExecutionValidationError("authorized action identity is invalid")
    return typed_action


def _semantic_query_payload(query: SemanticQuery) -> dict[str, object]:
    """Project the exact allowlisted SemanticQuery semantics without SQL."""
    return {
        "dimensions": [dimension.value for dimension in query.dimensions],
        "filters": {
            "minimum_score": query.filters.minimum_score,
            "snapshot_date": query.filters.snapshot_date.isoformat(),
        },
        "limit": query.limit,
        "metric": query.metric.value,
        "order_by": query.order_by.value,
        "order_direction": query.order_direction.value,
    }


def _invocation_payload(
    *,
    action_id: str,
    capability: AgentCapability,
    input_identity: object,
) -> dict[str, object]:
    """Build canonical semantics for one authorized typed invocation."""
    return {
        "action_id": action_id,
        "capability": capability.value,
        "contract_version": SINGLE_AGENT_EXECUTION_CONTRACT_VERSION,
        "input": input_identity,
    }


def _validate_invocation_identity(
    *,
    action_id: str,
    capability: AgentCapability,
    input_identity: object,
    invocation_sha256: object,
    invocation_id: object,
) -> tuple[str, str]:
    """Validate caller-visible invocation identity against exact typed semantics."""
    expected_sha = _canonical_sha256(
        _invocation_payload(
            action_id=action_id,
            capability=capability,
            input_identity=input_identity,
        )
    )
    digest = _validate_sha256(
        invocation_sha256,
        label="invocation_sha256",
        expected=expected_sha,
    )
    expected_id = f"{SINGLE_AGENT_EXECUTION_CONTRACT_VERSION}:invocation:{expected_sha}"
    if type(invocation_id) is not str or invocation_id != expected_id:
        raise AgentCapabilityExecutionValidationError(
            "invocation_id must match the content-addressed invocation identity"
        )
    return digest, expected_id


@dataclass(frozen=True, slots=True)
class StructuredSecurityQueryInvocation:
    """Authorized typed binding to the deterministic SemanticQuery boundary."""

    action: AuthorizedAgentAction
    query: SemanticQuery
    invocation_sha256: str
    invocation_id: str

    def __post_init__(self) -> None:
        """Bind an exact structured query to an exact authorization."""
        action = _validate_action(self.action, AgentCapability.STRUCTURED_SECURITY_QUERY)
        if type(self.query) is not SemanticQuery:
            raise AgentCapabilityExecutionValidationError("query must be one SemanticQuery")
        digest, identifier = _validate_invocation_identity(
            action_id=action.action_id,
            capability=AgentCapability.STRUCTURED_SECURITY_QUERY,
            input_identity=_semantic_query_payload(self.query),
            invocation_sha256=self.invocation_sha256,
            invocation_id=self.invocation_id,
        )
        object.__setattr__(self, "invocation_sha256", digest)
        object.__setattr__(self, "invocation_id", identifier)

    @classmethod
    def create(
        cls,
        *,
        action: AuthorizedAgentAction,
        query: SemanticQuery,
    ) -> StructuredSecurityQueryInvocation:
        """Create one deterministic structured-security invocation."""
        admitted_action = _validate_action(action, AgentCapability.STRUCTURED_SECURITY_QUERY)
        if type(query) is not SemanticQuery:
            raise AgentCapabilityExecutionValidationError("query must be one SemanticQuery")
        digest = _canonical_sha256(
            _invocation_payload(
                action_id=admitted_action.action_id,
                capability=AgentCapability.STRUCTURED_SECURITY_QUERY,
                input_identity=_semantic_query_payload(query),
            )
        )
        return cls(
            action=admitted_action,
            query=query,
            invocation_sha256=digest,
            invocation_id=(
                f"{SINGLE_AGENT_EXECUTION_CONTRACT_VERSION}:invocation:{digest}"
            ),
        )


@dataclass(frozen=True, slots=True)
class KnowledgeGuidanceInvocation:
    """Authorized typed binding to one admitted knowledge synthesis request."""

    action: AuthorizedAgentAction
    request: SynthesisRequest
    invocation_sha256: str
    invocation_id: str

    def __post_init__(self) -> None:
        """Bind an exact knowledge request to an exact authorization."""
        action = _validate_action(self.action, AgentCapability.KNOWLEDGE_GUIDANCE)
        if type(self.request) is not SynthesisRequest:
            raise AgentCapabilityExecutionValidationError(
                "request must be one SynthesisRequest"
            )
        digest, identifier = _validate_invocation_identity(
            action_id=action.action_id,
            capability=AgentCapability.KNOWLEDGE_GUIDANCE,
            input_identity={"request_sha256": self.request.request_sha256},
            invocation_sha256=self.invocation_sha256,
            invocation_id=self.invocation_id,
        )
        object.__setattr__(self, "invocation_sha256", digest)
        object.__setattr__(self, "invocation_id", identifier)

    @classmethod
    def create(
        cls,
        *,
        action: AuthorizedAgentAction,
        request: SynthesisRequest,
    ) -> KnowledgeGuidanceInvocation:
        """Create one deterministic knowledge-guidance invocation."""
        admitted_action = _validate_action(action, AgentCapability.KNOWLEDGE_GUIDANCE)
        if type(request) is not SynthesisRequest:
            raise AgentCapabilityExecutionValidationError(
                "request must be one SynthesisRequest"
            )
        digest = _canonical_sha256(
            _invocation_payload(
                action_id=admitted_action.action_id,
                capability=AgentCapability.KNOWLEDGE_GUIDANCE,
                input_identity={"request_sha256": request.request_sha256},
            )
        )
        return cls(
            action=admitted_action,
            request=request,
            invocation_sha256=digest,
            invocation_id=(
                f"{SINGLE_AGENT_EXECUTION_CONTRACT_VERSION}:invocation:{digest}"
            ),
        )


@dataclass(frozen=True, slots=True)
class HybridSecurityAnswerInvocation:
    """Authorized typed binding to one admitted hybrid synthesis request."""

    action: AuthorizedAgentAction
    request: HybridSynthesisRequest
    invocation_sha256: str
    invocation_id: str

    def __post_init__(self) -> None:
        """Bind an exact hybrid request to an exact authorization."""
        action = _validate_action(self.action, AgentCapability.HYBRID_SECURITY_ANSWER)
        if type(self.request) is not HybridSynthesisRequest:
            raise AgentCapabilityExecutionValidationError(
                "request must be one HybridSynthesisRequest"
            )
        digest, identifier = _validate_invocation_identity(
            action_id=action.action_id,
            capability=AgentCapability.HYBRID_SECURITY_ANSWER,
            input_identity={"request_sha256": self.request.request_sha256},
            invocation_sha256=self.invocation_sha256,
            invocation_id=self.invocation_id,
        )
        object.__setattr__(self, "invocation_sha256", digest)
        object.__setattr__(self, "invocation_id", identifier)

    @classmethod
    def create(
        cls,
        *,
        action: AuthorizedAgentAction,
        request: HybridSynthesisRequest,
    ) -> HybridSecurityAnswerInvocation:
        """Create one deterministic hybrid-security invocation."""
        admitted_action = _validate_action(action, AgentCapability.HYBRID_SECURITY_ANSWER)
        if type(request) is not HybridSynthesisRequest:
            raise AgentCapabilityExecutionValidationError(
                "request must be one HybridSynthesisRequest"
            )
        digest = _canonical_sha256(
            _invocation_payload(
                action_id=admitted_action.action_id,
                capability=AgentCapability.HYBRID_SECURITY_ANSWER,
                input_identity={"request_sha256": request.request_sha256},
            )
        )
        return cls(
            action=admitted_action,
            request=request,
            invocation_sha256=digest,
            invocation_id=(
                f"{SINGLE_AGENT_EXECUTION_CONTRACT_VERSION}:invocation:{digest}"
            ),
        )


@dataclass(frozen=True, slots=True)
class PublicRepositoryAnalysisInvocation:
    """Authorized typed binding to one admitted public-analysis request."""

    action: AuthorizedAgentAction
    request: PublicAnalysisRequest
    invocation_sha256: str
    invocation_id: str

    def __post_init__(self) -> None:
        """Bind an exact public request to an exact authorization."""
        action = _validate_action(self.action, AgentCapability.PUBLIC_REPOSITORY_ANALYSIS)
        if type(self.request) is not PublicAnalysisRequest:
            raise AgentCapabilityExecutionValidationError(
                "request must be one PublicAnalysisRequest"
            )
        digest, identifier = _validate_invocation_identity(
            action_id=action.action_id,
            capability=AgentCapability.PUBLIC_REPOSITORY_ANALYSIS,
            input_identity={
                "request_id": self.request.request_id,
                "request_sha256": self.request.request_sha256,
            },
            invocation_sha256=self.invocation_sha256,
            invocation_id=self.invocation_id,
        )
        object.__setattr__(self, "invocation_sha256", digest)
        object.__setattr__(self, "invocation_id", identifier)

    @classmethod
    def create(
        cls,
        *,
        action: AuthorizedAgentAction,
        request: PublicAnalysisRequest,
    ) -> PublicRepositoryAnalysisInvocation:
        """Create one deterministic public-repository invocation."""
        admitted_action = _validate_action(action, AgentCapability.PUBLIC_REPOSITORY_ANALYSIS)
        if type(request) is not PublicAnalysisRequest:
            raise AgentCapabilityExecutionValidationError(
                "request must be one PublicAnalysisRequest"
            )
        input_identity = {
            "request_id": request.request_id,
            "request_sha256": request.request_sha256,
        }
        digest = _canonical_sha256(
            _invocation_payload(
                action_id=admitted_action.action_id,
                capability=AgentCapability.PUBLIC_REPOSITORY_ANALYSIS,
                input_identity=input_identity,
            )
        )
        return cls(
            action=admitted_action,
            request=request,
            invocation_sha256=digest,
            invocation_id=(
                f"{SINGLE_AGENT_EXECUTION_CONTRACT_VERSION}:invocation:{digest}"
            ),
        )


AgentCapabilityInvocation: TypeAlias = (
    StructuredSecurityQueryInvocation
    | KnowledgeGuidanceInvocation
    | HybridSecurityAnswerInvocation
    | PublicRepositoryAnalysisInvocation
)


def _athena_result_payload(result: AthenaQueryResult) -> dict[str, object]:
    """Project exact bounded structured-query result evidence."""
    return {
        "columns": list(result.columns),
        "data_scanned_bytes": result.data_scanned_bytes,
        "engine_execution_time_ms": result.engine_execution_time_ms,
        "query_execution_id": result.query_execution_id,
        "rows": [list(row) for row in result.rows],
        "total_execution_time_ms": result.total_execution_time_ms,
    }


@dataclass(frozen=True, slots=True)
class StructuredSecurityQueryResultBinding:
    """Bind an Athena result to the exact structured capability invocation."""

    invocation_sha256: str
    result: AthenaQueryResult
    result_sha256: str

    def __post_init__(self) -> None:
        """Reject unbound or forged structured result evidence."""
        invocation_digest = _validate_sha256(
            self.invocation_sha256,
            label="invocation_sha256",
        )
        if type(self.result) is not AthenaQueryResult:
            raise AgentCapabilityExecutionValidationError(
                "structured result must be one AthenaQueryResult"
            )
        expected = _canonical_sha256(
            {
                "contract_version": SINGLE_AGENT_EXECUTION_CONTRACT_VERSION,
                "invocation_sha256": invocation_digest,
                "result": _athena_result_payload(self.result),
            }
        )
        _validate_sha256(self.result_sha256, label="result_sha256", expected=expected)

    @classmethod
    def create(
        cls,
        *,
        invocation: StructuredSecurityQueryInvocation,
        result: AthenaQueryResult,
    ) -> StructuredSecurityQueryResultBinding:
        """Create explicit query/result binding evidence after one executor call."""
        if type(invocation) is not StructuredSecurityQueryInvocation:
            raise AgentCapabilityExecutionValidationError(
                "structured result binding requires the structured invocation"
            )
        if type(result) is not AthenaQueryResult:
            raise AgentCapabilityExecutionValidationError(
                "structured result must be one AthenaQueryResult"
            )
        digest = _canonical_sha256(
            {
                "contract_version": SINGLE_AGENT_EXECUTION_CONTRACT_VERSION,
                "invocation_sha256": invocation.invocation_sha256,
                "result": _athena_result_payload(result),
            }
        )
        return cls(
            invocation_sha256=invocation.invocation_sha256,
            result=result,
            result_sha256=digest,
        )


@dataclass(frozen=True, slots=True)
class AgentCapabilityExecution:
    """Content-addressed evidence for one admitted capability execution result."""

    action_id: str
    capability: AgentCapability
    invocation_id: str
    downstream_result_sha256: str
    execution_sha256: str
    execution_id: str

    def __post_init__(self) -> None:
        """Reject forged execution evidence or authority drift."""
        if type(self.action_id) is not str or _ACTION_ID_PATTERN.fullmatch(self.action_id) is None:
            raise AgentCapabilityExecutionValidationError("action_id is invalid")
        if type(self.capability) is not AgentCapability:
            raise AgentCapabilityExecutionValidationError("capability must be AgentCapability")
        if (
            type(self.invocation_id) is not str
            or _INVOCATION_ID_PATTERN.fullmatch(self.invocation_id) is None
        ):
            raise AgentCapabilityExecutionValidationError("invocation_id is invalid")
        result_digest = _validate_sha256(
            self.downstream_result_sha256,
            label="downstream_result_sha256",
        )
        expected = _canonical_sha256(
            {
                "action_id": self.action_id,
                "capability": self.capability.value,
                "contract_version": SINGLE_AGENT_EXECUTION_CONTRACT_VERSION,
                "downstream_result_sha256": result_digest,
                "invocation_id": self.invocation_id,
            }
        )
        _validate_sha256(self.execution_sha256, label="execution_sha256", expected=expected)
        expected_id = f"{SINGLE_AGENT_EXECUTION_CONTRACT_VERSION}:execution:{expected}"
        if type(self.execution_id) is not str or self.execution_id != expected_id:
            raise AgentCapabilityExecutionValidationError(
                "execution_id must match content-addressed execution semantics"
            )
        if _EXECUTION_ID_PATTERN.fullmatch(self.execution_id) is None:
            raise AgentCapabilityExecutionValidationError("execution_id is invalid")

    @classmethod
    def create(
        cls,
        *,
        invocation: AgentCapabilityInvocation,
        downstream_result_sha256: str,
    ) -> AgentCapabilityExecution:
        """Create one execution identity from an exact invocation and admitted result hash."""
        capability = capability_for_invocation(invocation)
        action = action_for_invocation(invocation)
        result_digest = _validate_sha256(
            downstream_result_sha256,
            label="downstream_result_sha256",
        )
        digest = _canonical_sha256(
            {
                "action_id": action.action_id,
                "capability": capability.value,
                "contract_version": SINGLE_AGENT_EXECUTION_CONTRACT_VERSION,
                "downstream_result_sha256": result_digest,
                "invocation_id": invocation.invocation_id,
            }
        )
        return cls(
            action_id=action.action_id,
            capability=capability,
            invocation_id=invocation.invocation_id,
            downstream_result_sha256=result_digest,
            execution_sha256=digest,
            execution_id=f"{SINGLE_AGENT_EXECUTION_CONTRACT_VERSION}:execution:{digest}",
        )


def capability_for_invocation(invocation: AgentCapabilityInvocation) -> AgentCapability:
    """Resolve capability from the closed invocation type set, never a caller string."""
    if type(invocation) is StructuredSecurityQueryInvocation:
        return AgentCapability.STRUCTURED_SECURITY_QUERY
    if type(invocation) is KnowledgeGuidanceInvocation:
        return AgentCapability.KNOWLEDGE_GUIDANCE
    if type(invocation) is HybridSecurityAnswerInvocation:
        return AgentCapability.HYBRID_SECURITY_ANSWER
    if type(invocation) is PublicRepositoryAnalysisInvocation:
        return AgentCapability.PUBLIC_REPOSITORY_ANALYSIS
    raise AgentCapabilityExecutionValidationError("unknown capability invocation type")


def action_for_invocation(invocation: AgentCapabilityInvocation) -> AuthorizedAgentAction:
    """Return the exact Gate 11.1 authorization embedded in a typed invocation."""
    if type(invocation) is StructuredSecurityQueryInvocation:
        return invocation.action
    if type(invocation) is KnowledgeGuidanceInvocation:
        return invocation.action
    if type(invocation) is HybridSecurityAnswerInvocation:
        return invocation.action
    if type(invocation) is PublicRepositoryAnalysisInvocation:
        return invocation.action
    raise AgentCapabilityExecutionValidationError("unknown capability invocation type")


__all__ = [
    "MAX_AGENT_EXECUTION_ADAPTIVE_FALLBACKS",
    "MAX_AGENT_EXECUTION_RETRIES",
    "MAX_AGENT_EXECUTIONS_PER_CALL",
    "SINGLE_AGENT_EXECUTION_CONTRACT_VERSION",
    "AgentCapabilityExecution",
    "AgentCapabilityInvocation",
    "HybridSecurityAnswerInvocation",
    "KnowledgeGuidanceInvocation",
    "PublicRepositoryAnalysisInvocation",
    "StructuredSecurityQueryInvocation",
    "StructuredSecurityQueryResultBinding",
    "action_for_invocation",
    "capability_for_invocation",
]
