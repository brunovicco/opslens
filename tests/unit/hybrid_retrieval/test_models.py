"""Unit tests for the provider-independent Gate 8.1 domain contract."""

from __future__ import annotations

from typing import cast

import pytest

from opslens.hybrid_retrieval.domain import (
    CompletenessSemantics,
    EvidenceClass,
    EvidenceNeed,
    HybridRetrievalValidationError,
    HybridRoute,
    HybridRouteDecision,
    HybridRoutingRequest,
    RouteReason,
)


def test_routing_request_canonicalizes_order_and_identity() -> None:
    """Caller ordering must not change the canonical request identity."""
    first = HybridRoutingRequest(
        evidence_needs=(EvidenceNeed.RISK_PRIORITY, EvidenceNeed.VULNERABILITY_FACTS)
    )
    second = HybridRoutingRequest(
        evidence_needs=(EvidenceNeed.VULNERABILITY_FACTS, EvidenceNeed.RISK_PRIORITY)
    )

    assert first.evidence_needs == (
        EvidenceNeed.RISK_PRIORITY,
        EvidenceNeed.VULNERABILITY_FACTS,
    )
    assert first == second
    assert first.request_sha256 == second.request_sha256
    assert len(first.request_sha256) == 64


def test_routing_request_rejects_empty_evidence_needs() -> None:
    """A route proposal without an explicit evidence need must fail closed."""
    with pytest.raises(HybridRetrievalValidationError, match="cannot be empty"):
        HybridRoutingRequest(evidence_needs=())


def test_routing_request_rejects_duplicate_evidence_needs() -> None:
    """Duplicate needs are malformed input rather than silently deduplicated semantics."""
    with pytest.raises(HybridRetrievalValidationError, match="cannot contain duplicates"):
        HybridRoutingRequest(
            evidence_needs=(
                EvidenceNeed.VULNERABILITY_FACTS,
                EvidenceNeed.VULNERABILITY_FACTS,
            )
        )


def test_routing_request_rejects_unknown_runtime_value() -> None:
    """Unknown string semantics must not be coerced into a recognized evidence need."""
    unknown = cast(tuple[EvidenceNeed, ...], ("future_unknown_need",))

    with pytest.raises(HybridRetrievalValidationError, match="recognized EvidenceNeed"):
        HybridRoutingRequest(evidence_needs=unknown)


def test_route_decision_rejects_semantic_authority_laundering() -> None:
    """Structured truth cannot be relabeled as semantic evidence by constructing a result."""
    with pytest.raises(HybridRetrievalValidationError, match="semantic routes"):
        HybridRouteDecision(
            route=HybridRoute.SEMANTIC,
            evidence_needs=(EvidenceNeed.VULNERABILITY_FACTS,),
            required_evidence_classes=(EvidenceClass.SEMANTIC,),
            completeness=CompletenessSemantics.ALL_REQUIRED,
            reason=RouteReason.SEMANTIC_EVIDENCE_REQUIRED,
        )


def test_hybrid_route_requires_all_required_completeness() -> None:
    """The initial hybrid contract must not degrade to best-effort evidence semantics."""
    with pytest.raises(HybridRetrievalValidationError, match="ALL_REQUIRED"):
        HybridRouteDecision(
            route=HybridRoute.HYBRID,
            evidence_needs=(
                EvidenceNeed.VULNERABILITY_FACTS,
                EvidenceNeed.REMEDIATION_GUIDANCE,
            ),
            required_evidence_classes=(EvidenceClass.STRUCTURED, EvidenceClass.SEMANTIC),
            completeness=CompletenessSemantics.NOT_APPLICABLE,
            reason=RouteReason.ALL_REQUIRED_HYBRID_EVIDENCE,
        )


def test_unsupported_route_cannot_authorize_downstream_evidence() -> None:
    """Known out-of-authority semantics must stop before either downstream evidence path."""
    with pytest.raises(HybridRetrievalValidationError, match="cannot authorize"):
        HybridRouteDecision(
            route=HybridRoute.UNSUPPORTED,
            evidence_needs=(EvidenceNeed.RUNTIME_EXPOSURE,),
            required_evidence_classes=(EvidenceClass.STRUCTURED,),
            completeness=CompletenessSemantics.NOT_APPLICABLE,
            reason=RouteReason.RUNTIME_EXPOSURE_AUTHORITY_UNAVAILABLE,
        )
