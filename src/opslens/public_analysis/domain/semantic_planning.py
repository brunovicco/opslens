"""Deterministic contracts for bounded public semantic-plan admission and handoff."""

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from opslens.hybrid_retrieval.domain import (
    CompletenessSemantics,
    EvidenceClass,
    EvidenceNeed,
    HybridRoute,
    HybridRouteDecision,
    HybridRoutingRequest,
)
from opslens.public_analysis.domain.errors import PublicAnalysisValidationError
from opslens.public_analysis.domain.evidence_execution import (
    PublicRepositoryEvidenceExecution,
)

PUBLIC_SEMANTIC_PLANNING_CONTRACT_VERSION = "public-semantic-planning:v1"
PUBLIC_ANALYSIS_HANDOFF_CONTRACT_VERSION = "public-analysis-handoff:v1"
PUBLIC_ANALYSIS_OPERATION = "analyze_public_repository"
MAX_PUBLIC_SEMANTIC_PLANNING_REQUEST_BYTES = 2_048

PUBLIC_ANALYSIS_V1_REQUIRED_EVIDENCE_NEEDS = tuple(
    sorted(
        (
            EvidenceNeed.VULNERABILITY_FACTS,
            EvidenceNeed.RISK_PRIORITY,
            EvidenceNeed.REMEDIATION_GUIDANCE,
        ),
        key=lambda item: item.value,
    )
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)


def _canonical_json(value: object) -> bytes:
    """Serialize one deterministic Phase 9 identity payload."""
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _validate_clean_text(value: object, *, field: str) -> str:
    """Require one non-empty exact string without normalization."""
    if type(value) is not str or not value or value != value.strip():
        raise PublicAnalysisValidationError(f"{field} must be one clean non-empty string")
    return value


def _validate_sha256(value: object, *, field: str) -> str:
    """Require one lowercase SHA-256 digest."""
    if type(value) is not str or _SHA256_PATTERN.fullmatch(value) is None:
        raise PublicAnalysisValidationError(f"{field} must be one lowercase SHA-256 digest")
    return value


def _validate_count(value: object, *, field: str) -> int:
    """Require one non-negative integer accounting value."""
    if type(value) is not int or value < 0:
        raise PublicAnalysisValidationError(f"{field} must be one non-negative integer")
    return value


@dataclass(frozen=True, slots=True)
class PublicSemanticPlanningRequest:
    """Content-free metadata projection presented to the public semantic planner."""

    source_execution_id: str
    source_execution_sha256: str
    public_request_id: str
    snapshot_id: str
    file_evidence_id: str
    normalized_dependency_count: int
    unsupported_package_count: int
    unsupported_normalization_count: int

    def __post_init__(self) -> None:
        """Keep the planner boundary content-free, bounded, and identity-preserving."""
        _validate_clean_text(self.source_execution_id, field="source_execution_id")
        _validate_sha256(
            self.source_execution_sha256,
            field="source_execution_sha256",
        )
        _validate_clean_text(self.public_request_id, field="public_request_id")
        _validate_clean_text(self.snapshot_id, field="snapshot_id")
        _validate_clean_text(self.file_evidence_id, field="file_evidence_id")
        _validate_count(
            self.normalized_dependency_count,
            field="normalized_dependency_count",
        )
        _validate_count(
            self.unsupported_package_count,
            field="unsupported_package_count",
        )
        _validate_count(
            self.unsupported_normalization_count,
            field="unsupported_normalization_count",
        )
        if len(self.canonical_json) > MAX_PUBLIC_SEMANTIC_PLANNING_REQUEST_BYTES:
            raise PublicAnalysisValidationError(
                "semantic planning request exceeds the hard byte limit"
            )

    @property
    def canonical_json(self) -> bytes:
        """Return the only payload authorized to cross the semantic-planner port."""
        return _canonical_json(
            {
                "allowed_evidence_needs": [
                    need.value for need in PUBLIC_ANALYSIS_V1_REQUIRED_EVIDENCE_NEEDS
                ],
                "contract_version": PUBLIC_SEMANTIC_PLANNING_CONTRACT_VERSION,
                "operation": PUBLIC_ANALYSIS_OPERATION,
                "source": {
                    "file_evidence_id": self.file_evidence_id,
                    "normalized_dependency_count": self.normalized_dependency_count,
                    "public_request_id": self.public_request_id,
                    "snapshot_id": self.snapshot_id,
                    "source_execution_id": self.source_execution_id,
                    "source_execution_sha256": self.source_execution_sha256,
                    "unsupported_normalization_count": (
                        self.unsupported_normalization_count
                    ),
                    "unsupported_package_count": self.unsupported_package_count,
                },
            }
        )

    @property
    def request_sha256(self) -> str:
        """Return a deterministic identity for the exact planner projection."""
        return sha256(self.canonical_json).hexdigest()

    @property
    def request_id(self) -> str:
        """Return a versioned content-addressed planner-request identifier."""
        return (
            f"{PUBLIC_SEMANTIC_PLANNING_CONTRACT_VERSION}@sha256:"
            f"{self.request_sha256}"
        )


@dataclass(frozen=True, slots=True)
class PublicSemanticPlanProposal:
    """Untrusted planner proposal after structural parsing but before policy admission."""

    planning_request_sha256: str
    evidence_needs: tuple[EvidenceNeed, ...]

    def __post_init__(self) -> None:
        """Reuse Phase 8 routing-request validation for proposed evidence-need syntax."""
        _validate_sha256(
            self.planning_request_sha256,
            field="planning_request_sha256",
        )
        routing_request = HybridRoutingRequest(evidence_needs=self.evidence_needs)
        object.__setattr__(self, "evidence_needs", routing_request.evidence_needs)

    @property
    def canonical_json(self) -> bytes:
        """Return the canonical structurally valid proposal representation."""
        return _canonical_json(
            {
                "contract_version": PUBLIC_SEMANTIC_PLANNING_CONTRACT_VERSION,
                "evidence_needs": [need.value for need in self.evidence_needs],
                "planning_request_sha256": self.planning_request_sha256,
            }
        )

    @property
    def proposal_sha256(self) -> str:
        """Return a content-addressed identity for the parsed proposal."""
        return sha256(self.canonical_json).hexdigest()

    @property
    def proposal_id(self) -> str:
        """Return a versioned content-addressed proposal identifier."""
        return (
            f"{PUBLIC_SEMANTIC_PLANNING_CONTRACT_VERSION}:proposal@sha256:"
            f"{self.proposal_sha256}"
        )


@dataclass(frozen=True, slots=True)
class PublicAnalysisAdmissionHandoff:
    """Deterministically admitted boundary before any downstream public analysis."""

    source_execution: PublicRepositoryEvidenceExecution
    planning_request: PublicSemanticPlanningRequest
    proposal: PublicSemanticPlanProposal
    route_decision: HybridRouteDecision

    def __post_init__(self) -> None:
        """Reject any planner, source, or routing drift before downstream authority exists."""
        if type(self.source_execution) is not PublicRepositoryEvidenceExecution:
            raise PublicAnalysisValidationError(
                "public handoff requires one verified repository evidence execution"
            )
        if type(self.planning_request) is not PublicSemanticPlanningRequest:
            raise PublicAnalysisValidationError(
                "public handoff requires one admitted semantic planning request"
            )
        if type(self.proposal) is not PublicSemanticPlanProposal:
            raise PublicAnalysisValidationError(
                "public handoff requires one parsed semantic plan proposal"
            )
        if type(self.route_decision) is not HybridRouteDecision:
            raise PublicAnalysisValidationError(
                "public handoff requires one deterministic hybrid route decision"
            )

        execution = self.source_execution
        request = self.planning_request
        inventory = execution.normalization_inventory
        if request.source_execution_id != execution.execution_id:
            raise PublicAnalysisValidationError(
                "planning request execution identity does not match source evidence"
            )
        if request.source_execution_sha256 != execution.evidence_sha256:
            raise PublicAnalysisValidationError(
                "planning request execution hash does not match source evidence"
            )
        if request.public_request_id != execution.request.request_id:
            raise PublicAnalysisValidationError(
                "planning request public request identity does not match source evidence"
            )
        if request.snapshot_id != execution.snapshot_id:
            raise PublicAnalysisValidationError(
                "planning request snapshot identity does not match source evidence"
            )
        if request.file_evidence_id != execution.file_evidence_id:
            raise PublicAnalysisValidationError(
                "planning request file evidence identity does not match source evidence"
            )
        if request.normalized_dependency_count != len(inventory.normalized_dependencies):
            raise PublicAnalysisValidationError(
                "planning request normalized dependency accounting drifted"
            )
        if request.unsupported_package_count != len(execution.parsed_lock.unsupported_packages):
            raise PublicAnalysisValidationError(
                "planning request unsupported package accounting drifted"
            )
        if request.unsupported_normalization_count != len(inventory.unsupported_normalization):
            raise PublicAnalysisValidationError(
                "planning request unsupported normalization accounting drifted"
            )

        if self.proposal.planning_request_sha256 != request.request_sha256:
            raise PublicAnalysisValidationError(
                "semantic plan proposal is not bound to the admitted planning request"
            )
        if self.proposal.evidence_needs != PUBLIC_ANALYSIS_V1_REQUIRED_EVIDENCE_NEEDS:
            raise PublicAnalysisValidationError(
                "public analysis v1 requires the complete deterministic evidence-need set"
            )

        decision = self.route_decision
        if decision.evidence_needs != self.proposal.evidence_needs:
            raise PublicAnalysisValidationError(
                "route decision evidence needs do not match the admitted proposal"
            )
        if decision.route is not HybridRoute.HYBRID:
            raise PublicAnalysisValidationError(
                "public analysis v1 admission requires the deterministic hybrid route"
            )
        if decision.completeness is not CompletenessSemantics.ALL_REQUIRED:
            raise PublicAnalysisValidationError(
                "public analysis v1 admission requires ALL_REQUIRED completeness"
            )
        if decision.required_evidence_classes != (
            EvidenceClass.STRUCTURED,
            EvidenceClass.SEMANTIC,
        ):
            raise PublicAnalysisValidationError(
                "public analysis v1 requires structured and semantic evidence classes"
            )

    @property
    def canonical_json(self) -> bytes:
        """Return bounded identities only; no repository content enters the handoff."""
        return _canonical_json(
            {
                "contract_version": PUBLIC_ANALYSIS_HANDOFF_CONTRACT_VERSION,
                "planning_request_id": self.planning_request.request_id,
                "proposal_id": self.proposal.proposal_id,
                "route_decision_id": self.route_decision.decision_id,
                "source_execution_id": self.source_execution.execution_id,
                "source_execution_sha256": self.source_execution.evidence_sha256,
            }
        )

    @property
    def handoff_sha256(self) -> str:
        """Return SHA-256 over the exact admitted handoff identities."""
        return sha256(self.canonical_json).hexdigest()

    @property
    def handoff_id(self) -> str:
        """Return a stable versioned content-addressed handoff identifier."""
        return (
            f"{PUBLIC_ANALYSIS_HANDOFF_CONTRACT_VERSION}@sha256:"
            f"{self.handoff_sha256}"
        )


__all__ = [
    "MAX_PUBLIC_SEMANTIC_PLANNING_REQUEST_BYTES",
    "PUBLIC_ANALYSIS_HANDOFF_CONTRACT_VERSION",
    "PUBLIC_ANALYSIS_OPERATION",
    "PUBLIC_ANALYSIS_V1_REQUIRED_EVIDENCE_NEEDS",
    "PUBLIC_SEMANTIC_PLANNING_CONTRACT_VERSION",
    "PublicAnalysisAdmissionHandoff",
    "PublicSemanticPlanProposal",
    "PublicSemanticPlanningRequest",
]
