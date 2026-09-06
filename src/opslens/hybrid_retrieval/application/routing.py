"""Deterministic application policy for Phase 8 hybrid evidence routing."""

from __future__ import annotations

from opslens.hybrid_retrieval.domain.errors import HybridRetrievalValidationError
from opslens.hybrid_retrieval.domain.models import (
    SEMANTIC_EVIDENCE_NEEDS,
    STRUCTURED_EVIDENCE_NEEDS,
    UNSUPPORTED_EVIDENCE_NEEDS,
    CompletenessSemantics,
    EvidenceClass,
    HybridRoute,
    HybridRouteDecision,
    HybridRoutingRequest,
    RouteReason,
)


def _admit_routing_request(value: object) -> HybridRoutingRequest:
    """Reject runtime values that bypass the typed routing-request admission contract."""
    if not isinstance(value, HybridRoutingRequest):
        raise HybridRetrievalValidationError(
            "request must be an admitted HybridRoutingRequest."
        )
    return value


def route_evidence_request(request: HybridRoutingRequest) -> HybridRouteDecision:
    """Return the only route authorized by the frozen v1 evidence-needs policy."""
    admitted_request = _admit_routing_request(request)
    needs = frozenset(admitted_request.evidence_needs)
    if needs & UNSUPPORTED_EVIDENCE_NEEDS:
        return HybridRouteDecision(
            route=HybridRoute.UNSUPPORTED,
            evidence_needs=admitted_request.evidence_needs,
            required_evidence_classes=(),
            completeness=CompletenessSemantics.NOT_APPLICABLE,
            reason=RouteReason.RUNTIME_EXPOSURE_AUTHORITY_UNAVAILABLE,
        )

    structured_needs = needs & STRUCTURED_EVIDENCE_NEEDS
    semantic_needs = needs & SEMANTIC_EVIDENCE_NEEDS
    classified_needs = structured_needs | semantic_needs
    if classified_needs != needs:
        raise HybridRetrievalValidationError(
            "request contains evidence needs without an authorized v1 policy mapping."
        )

    if structured_needs and semantic_needs:
        return HybridRouteDecision(
            route=HybridRoute.HYBRID,
            evidence_needs=admitted_request.evidence_needs,
            required_evidence_classes=(EvidenceClass.STRUCTURED, EvidenceClass.SEMANTIC),
            completeness=CompletenessSemantics.ALL_REQUIRED,
            reason=RouteReason.ALL_REQUIRED_HYBRID_EVIDENCE,
        )
    if structured_needs:
        return HybridRouteDecision(
            route=HybridRoute.STRUCTURED,
            evidence_needs=admitted_request.evidence_needs,
            required_evidence_classes=(EvidenceClass.STRUCTURED,),
            completeness=CompletenessSemantics.ALL_REQUIRED,
            reason=RouteReason.STRUCTURED_EVIDENCE_REQUIRED,
        )
    if semantic_needs:
        return HybridRouteDecision(
            route=HybridRoute.SEMANTIC,
            evidence_needs=admitted_request.evidence_needs,
            required_evidence_classes=(EvidenceClass.SEMANTIC,),
            completeness=CompletenessSemantics.ALL_REQUIRED,
            reason=RouteReason.SEMANTIC_EVIDENCE_REQUIRED,
        )

    raise HybridRetrievalValidationError("request has no authorized v1 route.")
