"""Unit tests for the deterministic Phase 8 Gate 8.1 routing policy."""

from __future__ import annotations

from typing import cast

import pytest

from opslens.hybrid_retrieval.application import route_evidence_request
from opslens.hybrid_retrieval.domain import (
    CompletenessSemantics,
    EvidenceClass,
    EvidenceNeed,
    HybridRetrievalValidationError,
    HybridRoute,
    HybridRoutingRequest,
    RouteReason,
)


@pytest.mark.parametrize(
    "needs",
    [
        (EvidenceNeed.VULNERABILITY_FACTS,),
        (EvidenceNeed.RISK_PRIORITY,),
        (EvidenceNeed.VULNERABILITY_FACTS, EvidenceNeed.RISK_PRIORITY),
    ],
)
def test_structured_needs_route_only_to_structured_authority(
    needs: tuple[EvidenceNeed, ...],
) -> None:
    """Vulnerability and risk truth must remain on deterministic structured authority."""
    decision = route_evidence_request(HybridRoutingRequest(evidence_needs=needs))

    assert decision.route is HybridRoute.STRUCTURED
    assert decision.required_evidence_classes == (EvidenceClass.STRUCTURED,)
    assert decision.completeness is CompletenessSemantics.ALL_REQUIRED
    assert decision.reason is RouteReason.STRUCTURED_EVIDENCE_REQUIRED


def test_remediation_guidance_routes_only_to_semantic_evidence() -> None:
    """Explanatory remediation guidance may use bounded semantic retrieval evidence."""
    decision = route_evidence_request(
        HybridRoutingRequest(evidence_needs=(EvidenceNeed.REMEDIATION_GUIDANCE,))
    )

    assert decision.route is HybridRoute.SEMANTIC
    assert decision.required_evidence_classes == (EvidenceClass.SEMANTIC,)
    assert decision.completeness is CompletenessSemantics.ALL_REQUIRED
    assert decision.reason is RouteReason.SEMANTIC_EVIDENCE_REQUIRED


def test_true_hybrid_route_requires_both_evidence_classes() -> None:
    """A combined structured/remediation request must require both evidence authorities."""
    decision = route_evidence_request(
        HybridRoutingRequest(
            evidence_needs=(
                EvidenceNeed.REMEDIATION_GUIDANCE,
                EvidenceNeed.VULNERABILITY_FACTS,
            )
        )
    )

    assert decision.route is HybridRoute.HYBRID
    assert decision.required_evidence_classes == (
        EvidenceClass.STRUCTURED,
        EvidenceClass.SEMANTIC,
    )
    assert decision.completeness is CompletenessSemantics.ALL_REQUIRED
    assert decision.reason is RouteReason.ALL_REQUIRED_HYBRID_EVIDENCE


def test_runtime_exposure_fails_closed_as_unsupported() -> None:
    """Repository evidence must not be promoted into runtime-exposure authority."""
    decision = route_evidence_request(
        HybridRoutingRequest(evidence_needs=(EvidenceNeed.RUNTIME_EXPOSURE,))
    )

    assert decision.route is HybridRoute.UNSUPPORTED
    assert decision.required_evidence_classes == ()
    assert decision.completeness is CompletenessSemantics.NOT_APPLICABLE
    assert decision.reason is RouteReason.RUNTIME_EXPOSURE_AUTHORITY_UNAVAILABLE


def test_runtime_exposure_mixed_with_semantic_need_remains_unsupported() -> None:
    """One unavailable required authority must prevent partial semantic execution."""
    decision = route_evidence_request(
        HybridRoutingRequest(
            evidence_needs=(
                EvidenceNeed.REMEDIATION_GUIDANCE,
                EvidenceNeed.RUNTIME_EXPOSURE,
            )
        )
    )

    assert decision.route is HybridRoute.UNSUPPORTED
    assert decision.required_evidence_classes == ()


def test_route_identity_is_canonical_across_need_ordering() -> None:
    """Equivalent proposals must produce the same content-addressed authority decision."""
    first = route_evidence_request(
        HybridRoutingRequest(
            evidence_needs=(
                EvidenceNeed.RISK_PRIORITY,
                EvidenceNeed.REMEDIATION_GUIDANCE,
            )
        )
    )
    second = route_evidence_request(
        HybridRoutingRequest(
            evidence_needs=(
                EvidenceNeed.REMEDIATION_GUIDANCE,
                EvidenceNeed.RISK_PRIORITY,
            )
        )
    )

    assert first == second
    assert first.identity_sha256 == second.identity_sha256
    assert first.decision_id == second.decision_id
    assert first.decision_id.startswith("hybrid-routing:v1:")


def test_invalid_request_object_fails_closed_before_routing() -> None:
    """Routing authority must reject values that bypass the typed admission contract."""
    invalid_request = cast(HybridRoutingRequest, object())

    with pytest.raises(HybridRetrievalValidationError, match="admitted HybridRoutingRequest"):
        route_evidence_request(invalid_request)
