"""Domain surface for OpsLens hybrid retrieval authority and evidence."""

from opslens.hybrid_retrieval.domain.errors import HybridRetrievalValidationError
from opslens.hybrid_retrieval.domain.evidence import (
    HYBRID_EVIDENCE_CONTRACT_VERSION,
    EvidenceClassProvenance,
    HybridEvidenceEnvelope,
    SemanticEvidenceChunk,
    StructuredEvidenceAuthority,
    StructuredEvidenceField,
    StructuredEvidenceRow,
    StructuredScalar,
)
from opslens.hybrid_retrieval.domain.models import (
    HYBRID_ROUTING_CONTRACT_VERSION,
    CompletenessSemantics,
    EvidenceClass,
    EvidenceNeed,
    HybridRoute,
    HybridRouteDecision,
    HybridRoutingRequest,
    RouteReason,
)

__all__ = [
    "HYBRID_EVIDENCE_CONTRACT_VERSION",
    "HYBRID_ROUTING_CONTRACT_VERSION",
    "CompletenessSemantics",
    "EvidenceClass",
    "EvidenceClassProvenance",
    "EvidenceNeed",
    "HybridEvidenceEnvelope",
    "HybridRetrievalValidationError",
    "HybridRoute",
    "HybridRouteDecision",
    "HybridRoutingRequest",
    "RouteReason",
    "SemanticEvidenceChunk",
    "StructuredEvidenceAuthority",
    "StructuredEvidenceField",
    "StructuredEvidenceRow",
    "StructuredScalar",
]
