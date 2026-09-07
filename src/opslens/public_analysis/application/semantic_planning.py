"""Bounded semantic planning proposal boundary for the fixed public analysis operation."""

from __future__ import annotations

import json
from typing import Protocol, cast

from opslens.hybrid_retrieval.application import route_evidence_request
from opslens.hybrid_retrieval.domain import EvidenceNeed, HybridRoutingRequest
from opslens.hybrid_retrieval.domain.errors import HybridRetrievalValidationError
from opslens.public_analysis.domain import (
    PUBLIC_ANALYSIS_V1_REQUIRED_EVIDENCE_NEEDS,
    PublicAnalysisAdmissionHandoff,
    PublicAnalysisValidationError,
    PublicRepositoryEvidenceExecution,
    PublicSemanticPlanningRequest,
    PublicSemanticPlanProposal,
)

MAX_PUBLIC_SEMANTIC_PLAN_RESPONSE_BYTES = 1_024

_ALLOWED_PLAN_KEYS = frozenset({"planning_request_sha256", "evidence_needs"})
_REQUIRED_PLAN_KEYS = _ALLOWED_PLAN_KEYS


class PublicSemanticPlanAdmissionError(ValueError):
    """Raised when an untrusted semantic-plan proposal cannot enter public authority."""


class PublicSemanticPlanner(Protocol):
    """Content-free planner port; implementations receive only serialized bounded metadata."""

    def plan(self, request_json: bytes) -> bytes:
        """Return one untrusted semantic-plan JSON proposal."""
        ...


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate object keys before planner-output projection."""
    projected: dict[str, object] = {}
    for key, value in pairs:
        if key in projected:
            raise PublicSemanticPlanAdmissionError(
                "semantic plan JSON cannot contain duplicate object keys"
            )
        projected[key] = value
    return projected


def _decode_plan_object(raw_response: bytes) -> dict[str, object]:
    """Decode one small UTF-8 planner response with an exact top-level shape."""
    if type(raw_response) is not bytes:
        raise PublicSemanticPlanAdmissionError(
            "semantic planner response must be bytes"
        )
    if not raw_response:
        raise PublicSemanticPlanAdmissionError(
            "semantic planner response cannot be empty"
        )
    if len(raw_response) > MAX_PUBLIC_SEMANTIC_PLAN_RESPONSE_BYTES:
        raise PublicSemanticPlanAdmissionError(
            "semantic planner response exceeds the hard byte limit"
        )
    try:
        text = raw_response.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise PublicSemanticPlanAdmissionError(
            "semantic planner response must be valid UTF-8"
        ) from exc
    try:
        decoded: object = json.loads(text, object_pairs_hook=_unique_json_object)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise PublicSemanticPlanAdmissionError(
            "semantic planner response must contain valid bounded JSON"
        ) from exc
    if not isinstance(decoded, dict):
        raise PublicSemanticPlanAdmissionError(
            "semantic planner response must contain one object"
        )
    mapping = cast(dict[object, object], decoded)
    if any(not isinstance(key, str) for key in mapping):
        raise PublicSemanticPlanAdmissionError(
            "semantic planner object keys must be strings"
        )
    typed = cast(dict[str, object], mapping)
    keys = frozenset(typed)
    if keys != _REQUIRED_PLAN_KEYS:
        if not _REQUIRED_PLAN_KEYS.issubset(keys):
            raise PublicSemanticPlanAdmissionError(
                "semantic planner response is missing a required field"
            )
        if not keys.issubset(_ALLOWED_PLAN_KEYS):
            raise PublicSemanticPlanAdmissionError(
                "semantic planner response contains unknown fields"
            )
    return typed


def build_public_semantic_planning_request(
    execution: PublicRepositoryEvidenceExecution,
) -> PublicSemanticPlanningRequest:
    """Project verified repository evidence into content-free planning metadata."""
    if type(execution) is not PublicRepositoryEvidenceExecution:
        raise PublicAnalysisValidationError(
            "semantic planning requires one verified public repository evidence execution"
        )
    inventory = execution.normalization_inventory
    return PublicSemanticPlanningRequest(
        source_execution_id=execution.execution_id,
        source_execution_sha256=execution.evidence_sha256,
        public_request_id=execution.request.request_id,
        snapshot_id=execution.snapshot_id,
        file_evidence_id=execution.file_evidence_id,
        normalized_dependency_count=len(inventory.normalized_dependencies),
        unsupported_package_count=len(execution.parsed_lock.unsupported_packages),
        unsupported_normalization_count=len(inventory.unsupported_normalization),
    )


def parse_public_semantic_plan_proposal(
    raw_response: bytes,
    *,
    planning_request: PublicSemanticPlanningRequest,
) -> PublicSemanticPlanProposal:
    """Parse untrusted planner JSON without granting route or execution authority."""
    if type(planning_request) is not PublicSemanticPlanningRequest:
        raise PublicSemanticPlanAdmissionError(
            "proposal parsing requires one admitted semantic planning request"
        )
    mapping = _decode_plan_object(raw_response)

    request_sha256 = mapping["planning_request_sha256"]
    if type(request_sha256) is not str:
        raise PublicSemanticPlanAdmissionError(
            "planning_request_sha256 must be a string"
        )
    if request_sha256 != planning_request.request_sha256:
        raise PublicSemanticPlanAdmissionError(
            "semantic plan proposal does not target the current planning request"
        )

    evidence_needs_object = mapping["evidence_needs"]
    if not isinstance(evidence_needs_object, list):
        raise PublicSemanticPlanAdmissionError(
            "evidence_needs must be a JSON array"
        )
    raw_needs = cast(list[object], evidence_needs_object)
    if not raw_needs:
        raise PublicSemanticPlanAdmissionError(
            "evidence_needs cannot be empty"
        )
    if len(raw_needs) > len(EvidenceNeed):
        raise PublicSemanticPlanAdmissionError(
            "evidence_needs exceeds the recognized evidence-need catalog"
        )

    parsed_needs: list[EvidenceNeed] = []
    for value in raw_needs:
        if type(value) is not str:
            raise PublicSemanticPlanAdmissionError(
                "evidence_needs must contain only strings"
            )
        try:
            parsed_needs.append(EvidenceNeed(value))
        except ValueError as exc:
            raise PublicSemanticPlanAdmissionError(
                "semantic planner proposed an unknown evidence need"
            ) from exc

    try:
        return PublicSemanticPlanProposal(
            planning_request_sha256=request_sha256,
            evidence_needs=tuple(parsed_needs),
        )
    except (PublicAnalysisValidationError, HybridRetrievalValidationError) as exc:
        raise PublicSemanticPlanAdmissionError(
            "semantic planner proposal violates the typed evidence-need contract"
        ) from exc


def admit_public_semantic_plan(
    proposal: PublicSemanticPlanProposal,
    *,
    planning_request: PublicSemanticPlanningRequest,
    source_execution: PublicRepositoryEvidenceExecution,
) -> PublicAnalysisAdmissionHandoff:
    """Apply fixed v1 public policy, then delegate route authority to Phase 8."""
    if type(proposal) is not PublicSemanticPlanProposal:
        raise PublicSemanticPlanAdmissionError(
            "public semantic-plan admission requires one parsed proposal"
        )
    if type(planning_request) is not PublicSemanticPlanningRequest:
        raise PublicSemanticPlanAdmissionError(
            "public semantic-plan admission requires one planning request"
        )
    if type(source_execution) is not PublicRepositoryEvidenceExecution:
        raise PublicSemanticPlanAdmissionError(
            "public semantic-plan admission requires verified repository evidence"
        )
    if proposal.planning_request_sha256 != planning_request.request_sha256:
        raise PublicSemanticPlanAdmissionError(
            "semantic plan proposal is not bound to the current planning request"
        )
    if proposal.evidence_needs != PUBLIC_ANALYSIS_V1_REQUIRED_EVIDENCE_NEEDS:
        raise PublicSemanticPlanAdmissionError(
            "public analysis v1 requires vulnerability, risk, and remediation evidence"
        )

    route_decision = route_evidence_request(
        HybridRoutingRequest(evidence_needs=proposal.evidence_needs)
    )
    try:
        return PublicAnalysisAdmissionHandoff(
            source_execution=source_execution,
            planning_request=planning_request,
            proposal=proposal,
            route_decision=route_decision,
        )
    except PublicAnalysisValidationError as exc:
        raise PublicSemanticPlanAdmissionError(
            "semantic plan cannot be admitted against the verified source execution"
        ) from exc


def plan_public_analysis_handoff(
    execution: PublicRepositoryEvidenceExecution,
    planner: PublicSemanticPlanner,
) -> PublicAnalysisAdmissionHandoff:
    """Invoke one injected planner exactly once and fail closed before downstream work."""
    planning_request = build_public_semantic_planning_request(execution)
    raw_response = planner.plan(planning_request.canonical_json)
    proposal = parse_public_semantic_plan_proposal(
        raw_response,
        planning_request=planning_request,
    )
    return admit_public_semantic_plan(
        proposal,
        planning_request=planning_request,
        source_execution=execution,
    )


__all__ = [
    "MAX_PUBLIC_SEMANTIC_PLAN_RESPONSE_BYTES",
    "PublicSemanticPlanAdmissionError",
    "PublicSemanticPlanner",
    "admit_public_semantic_plan",
    "build_public_semantic_planning_request",
    "parse_public_semantic_plan_proposal",
    "plan_public_analysis_handoff",
]
