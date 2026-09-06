"""Typed contracts for provider-independent hybrid evidence routing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import cast

from opslens.hybrid_retrieval.domain.errors import HybridRetrievalValidationError

HYBRID_ROUTING_CONTRACT_VERSION = "hybrid-routing:v1"


class EvidenceNeed(StrEnum):
    """Evidence needs deliberately recognized by the Phase 8 Gate 8.1 contract."""

    VULNERABILITY_FACTS = "vulnerability_facts"
    RISK_PRIORITY = "risk_priority"
    REMEDIATION_GUIDANCE = "remediation_guidance"
    RUNTIME_EXPOSURE = "runtime_exposure"


class EvidenceClass(StrEnum):
    """Authority-preserving evidence classes available to the hybrid router."""

    STRUCTURED = "structured"
    SEMANTIC = "semantic"


class HybridRoute(StrEnum):
    """Deterministic route outcomes frozen for the initial hybrid surface."""

    STRUCTURED = "structured"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    UNSUPPORTED = "unsupported"


class CompletenessSemantics(StrEnum):
    """How downstream execution must interpret required evidence classes."""

    ALL_REQUIRED = "all_required"
    NOT_APPLICABLE = "not_applicable"


class RouteReason(StrEnum):
    """Stable reason codes explaining one deterministic route decision."""

    STRUCTURED_EVIDENCE_REQUIRED = "structured_evidence_required"
    SEMANTIC_EVIDENCE_REQUIRED = "semantic_evidence_required"
    ALL_REQUIRED_HYBRID_EVIDENCE = "all_required_hybrid_evidence"
    RUNTIME_EXPOSURE_AUTHORITY_UNAVAILABLE = "runtime_exposure_authority_unavailable"


STRUCTURED_EVIDENCE_NEEDS = frozenset(
    {
        EvidenceNeed.VULNERABILITY_FACTS,
        EvidenceNeed.RISK_PRIORITY,
    }
)
SEMANTIC_EVIDENCE_NEEDS = frozenset({EvidenceNeed.REMEDIATION_GUIDANCE})
UNSUPPORTED_EVIDENCE_NEEDS = frozenset({EvidenceNeed.RUNTIME_EXPOSURE})

_EVIDENCE_CLASS_ORDER = {
    EvidenceClass.STRUCTURED: 0,
    EvidenceClass.SEMANTIC: 1,
}


def _canonical_sha256(payload: object) -> str:
    """Hash one canonical JSON payload with stable ordering and separators."""
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def _normalize_evidence_needs(value: object) -> tuple[EvidenceNeed, ...]:
    """Validate and canonically order a non-empty tuple of unique evidence needs."""
    if not isinstance(value, tuple):
        raise HybridRetrievalValidationError("evidence_needs must be a tuple.")
    raw_values = cast(tuple[object, ...], value)
    if not raw_values:
        raise HybridRetrievalValidationError("evidence_needs cannot be empty.")
    if any(not isinstance(item, EvidenceNeed) for item in raw_values):
        raise HybridRetrievalValidationError(
            "evidence_needs must contain only recognized EvidenceNeed values."
        )
    typed_values = cast(tuple[EvidenceNeed, ...], raw_values)
    if len(set(typed_values)) != len(typed_values):
        raise HybridRetrievalValidationError("evidence_needs cannot contain duplicates.")
    return tuple(sorted(typed_values, key=lambda item: item.value))


def _normalize_required_evidence_classes(value: object) -> tuple[EvidenceClass, ...]:
    """Validate and canonically order unique required evidence classes."""
    if not isinstance(value, tuple):
        raise HybridRetrievalValidationError("required_evidence_classes must be a tuple.")
    raw_values = cast(tuple[object, ...], value)
    if any(not isinstance(item, EvidenceClass) for item in raw_values):
        raise HybridRetrievalValidationError(
            "required_evidence_classes must contain only EvidenceClass values."
        )
    typed_values = cast(tuple[EvidenceClass, ...], raw_values)
    if len(set(typed_values)) != len(typed_values):
        raise HybridRetrievalValidationError(
            "required_evidence_classes cannot contain duplicates."
        )
    return tuple(sorted(typed_values, key=_EVIDENCE_CLASS_ORDER.__getitem__))


@dataclass(frozen=True, slots=True)
class HybridRoutingRequest:
    """Validated evidence-needs proposal presented to deterministic routing authority."""

    evidence_needs: tuple[EvidenceNeed, ...]

    def __post_init__(self) -> None:
        """Reject unknown/empty/duplicate semantics and freeze canonical ordering."""
        object.__setattr__(
            self,
            "evidence_needs",
            _normalize_evidence_needs(self.evidence_needs),
        )

    @property
    def request_sha256(self) -> str:
        """Return a content-addressed identity independent of caller-supplied ordering."""
        return _canonical_sha256(
            {
                "contract_version": HYBRID_ROUTING_CONTRACT_VERSION,
                "evidence_needs": [need.value for need in self.evidence_needs],
            }
        )


@dataclass(frozen=True, slots=True)
class HybridRouteDecision:
    """Deterministic route decision with explicit authority and completeness semantics."""

    route: HybridRoute
    evidence_needs: tuple[EvidenceNeed, ...]
    required_evidence_classes: tuple[EvidenceClass, ...]
    completeness: CompletenessSemantics
    reason: RouteReason

    def __post_init__(self) -> None:
        """Reject internally inconsistent route/authority combinations."""
        if not isinstance(self.route, HybridRoute):
            raise HybridRetrievalValidationError("route must be a HybridRoute value.")
        if not isinstance(self.completeness, CompletenessSemantics):
            raise HybridRetrievalValidationError(
                "completeness must be a CompletenessSemantics value."
            )
        if not isinstance(self.reason, RouteReason):
            raise HybridRetrievalValidationError("reason must be a RouteReason value.")

        normalized_needs = _normalize_evidence_needs(self.evidence_needs)
        normalized_classes = _normalize_required_evidence_classes(
            self.required_evidence_classes
        )
        object.__setattr__(self, "evidence_needs", normalized_needs)
        object.__setattr__(self, "required_evidence_classes", normalized_classes)

        need_set = frozenset(normalized_needs)
        has_runtime_exposure = bool(need_set & UNSUPPORTED_EVIDENCE_NEEDS)
        if self.route is HybridRoute.UNSUPPORTED:
            if not has_runtime_exposure:
                raise HybridRetrievalValidationError(
                    "unsupported v1 decisions must identify the known runtime-exposure boundary."
                )
            if normalized_classes:
                raise HybridRetrievalValidationError(
                    "unsupported decisions cannot authorize downstream evidence execution."
                )
            if self.completeness is not CompletenessSemantics.NOT_APPLICABLE:
                raise HybridRetrievalValidationError(
                    "unsupported decisions must use NOT_APPLICABLE completeness."
                )
            if self.reason is not RouteReason.RUNTIME_EXPOSURE_AUTHORITY_UNAVAILABLE:
                raise HybridRetrievalValidationError(
                    "unsupported runtime-exposure decisions require the frozen reason code."
                )
            return

        if has_runtime_exposure:
            raise HybridRetrievalValidationError(
                "runtime exposure cannot participate in a supported Phase 8 v1 route."
            )
        if self.completeness is not CompletenessSemantics.ALL_REQUIRED:
            raise HybridRetrievalValidationError(
                "supported Phase 8 v1 routes must use ALL_REQUIRED completeness."
            )

        structured_needs = need_set & STRUCTURED_EVIDENCE_NEEDS
        semantic_needs = need_set & SEMANTIC_EVIDENCE_NEEDS
        classified_needs = structured_needs | semantic_needs
        if classified_needs != need_set:
            raise HybridRetrievalValidationError(
                "supported route contains evidence needs without a v1 authority mapping."
            )

        expected_classes: tuple[EvidenceClass, ...]
        expected_reason: RouteReason
        if self.route is HybridRoute.STRUCTURED:
            if not structured_needs or semantic_needs:
                raise HybridRetrievalValidationError(
                    "structured routes may contain only structured evidence needs."
                )
            expected_classes = (EvidenceClass.STRUCTURED,)
            expected_reason = RouteReason.STRUCTURED_EVIDENCE_REQUIRED
        elif self.route is HybridRoute.SEMANTIC:
            if not semantic_needs or structured_needs:
                raise HybridRetrievalValidationError(
                    "semantic routes may contain only semantic evidence needs."
                )
            expected_classes = (EvidenceClass.SEMANTIC,)
            expected_reason = RouteReason.SEMANTIC_EVIDENCE_REQUIRED
        elif self.route is HybridRoute.HYBRID:
            if not structured_needs or not semantic_needs:
                raise HybridRetrievalValidationError(
                    "hybrid routes require both structured and semantic evidence needs."
                )
            expected_classes = (EvidenceClass.STRUCTURED, EvidenceClass.SEMANTIC)
            expected_reason = RouteReason.ALL_REQUIRED_HYBRID_EVIDENCE
        else:
            raise HybridRetrievalValidationError("route semantics are not recognized by v1.")

        if normalized_classes != expected_classes:
            raise HybridRetrievalValidationError(
                "required evidence classes do not match the selected route."
            )
        if self.reason is not expected_reason:
            raise HybridRetrievalValidationError(
                "route reason does not match the selected route."
            )

    @property
    def identity_sha256(self) -> str:
        """Return a stable content hash over the complete routing authority decision."""
        return _canonical_sha256(
            {
                "completeness": self.completeness.value,
                "contract_version": HYBRID_ROUTING_CONTRACT_VERSION,
                "evidence_needs": [need.value for need in self.evidence_needs],
                "reason": self.reason.value,
                "required_evidence_classes": [
                    evidence_class.value
                    for evidence_class in self.required_evidence_classes
                ],
                "route": self.route.value,
            }
        )

    @property
    def decision_id(self) -> str:
        """Return a versioned content-addressed identifier for audit/evaluation use."""
        return f"{HYBRID_ROUTING_CONTRACT_VERSION}:{self.identity_sha256}"
