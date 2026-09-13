"""Deterministic final result contract for one representative public analysis."""

from dataclasses import dataclass
from hashlib import sha256

from opslens.hybrid_retrieval.domain.synthesis import (
    HybridSynthesisRequest,
    HybridSynthesisResult,
)
from opslens.public_analysis.domain.errors import PublicAnalysisValidationError
from opslens.public_analysis.domain.semantic_planning import PublicAnalysisAdmissionHandoff
from opslens.shared.evidence import canonical_json

PUBLIC_ANALYSIS_PRODUCT_RESULT_CONTRACT_VERSION = "public-analysis-product-result:v1"
PUBLIC_ANALYSIS_SYNTHESIS_QUESTION = (
    "Explain the admitted vulnerability facts, risk priority, and remediation guidance "
    "for this repository."
)


def _canonical_json(payload: object) -> bytes:
    """Serialize one stable public-product response payload."""
    return canonical_json(payload)


@dataclass(frozen=True, slots=True)
class PublicAnalysisProductResult:
    """Bind one admitted hybrid answer to the exact public-analysis handoff authority."""

    handoff: PublicAnalysisAdmissionHandoff
    synthesis_request: HybridSynthesisRequest
    synthesis_result: HybridSynthesisResult

    def __post_init__(self) -> None:
        """Reject cross-request, cross-route, or arbitrary-question result laundering."""
        if type(self.handoff) is not PublicAnalysisAdmissionHandoff:
            raise PublicAnalysisValidationError(
                "public product result requires one admitted public-analysis handoff"
            )
        if type(self.synthesis_request) is not HybridSynthesisRequest:
            raise PublicAnalysisValidationError(
                "public product result requires one admitted hybrid synthesis request"
            )
        if type(self.synthesis_result) is not HybridSynthesisResult:
            raise PublicAnalysisValidationError(
                "public product result requires one admitted hybrid synthesis result"
            )
        if self.synthesis_request.question != PUBLIC_ANALYSIS_SYNTHESIS_QUESTION:
            raise PublicAnalysisValidationError(
                "public product result requires the fixed public-analysis synthesis question"
            )
        if (
            self.synthesis_request.envelope.authority_decision.decision_id
            != self.handoff.route_decision.decision_id
        ):
            raise PublicAnalysisValidationError(
                "public product synthesis authority must match the admitted public route"
            )
        if self.synthesis_result.request_sha256 != self.synthesis_request.request_sha256:
            raise PublicAnalysisValidationError(
                "public product synthesis result must match the exact admitted request"
            )

    @property
    def canonical_json(self) -> bytes:
        """Return the bounded public response with evidence handles and no retrieved chunk text."""
        source = self.handoff.source_execution
        snapshot = source.snapshot_resolution.snapshot
        target = source.request.target
        request = self.synthesis_request
        result = self.synthesis_result

        structured_facts = [fact.to_prompt_payload() for fact in request.structured_facts]
        semantic_citations = [
            {
                "canonical_uri": citation.canonical_uri,
                "chunk_content_sha256": citation.chunk_content_sha256,
                "chunk_id": citation.chunk_id,
                "citation_id": citation.citation_id,
                "document_content_sha256": citation.document_content_sha256,
                "document_id": citation.document_id,
                "evidence_id": citation.evidence_id,
                "rank": citation.rank,
                "section_path": list(citation.section_path),
                "source_id": citation.source_id,
                "source_type": citation.source_type,
                "title": citation.title,
            }
            for citation in request.semantic_citations
        ]
        claims = [
            {
                "claim_index": claim.claim_index,
                "semantic_citation_ids": list(claim.semantic_citation_ids),
                "structured_fact_ids": list(claim.structured_fact_ids),
                "text": claim.text,
            }
            for claim in result.claims
        ]
        payload: dict[str, object] = {
            "contract_version": PUBLIC_ANALYSIS_PRODUCT_RESULT_CONTRACT_VERSION,
            "evidence": {
                "envelope_id": request.envelope.envelope_id,
                "semantic_citations": semantic_citations,
                "structured_facts": structured_facts,
            },
            "handoff_id": self.handoff.handoff_id,
            "repository": {
                "commit_sha": snapshot.commit_sha,
                "name": target.name,
                "owner": target.owner,
                "snapshot_id": snapshot.snapshot_id,
            },
            "request_id": source.request.request_id,
            "route_decision_id": self.handoff.route_decision.decision_id,
            "source_execution_id": source.execution_id,
            "synthesis": {
                "claims": claims,
                "decision": result.decision.value,
                "result_sha256": result.result_sha256,
            },
            "synthesis_request_sha256": request.request_sha256,
        }
        return _canonical_json(payload)

    @property
    def result_sha256(self) -> str:
        """Return the content address of the exact admitted public-product response."""
        return sha256(self.canonical_json).hexdigest()

    @property
    def result_id(self) -> str:
        """Return one versioned content-addressed public-product identifier."""
        return (
            f"{PUBLIC_ANALYSIS_PRODUCT_RESULT_CONTRACT_VERSION}@sha256:"
            f"{self.result_sha256}"
        )

    @property
    def serialized_size_bytes(self) -> int:
        """Return exact UTF-8 bytes for the current response projection."""
        return len(self.canonical_json)


__all__ = [
    "PUBLIC_ANALYSIS_PRODUCT_RESULT_CONTRACT_VERSION",
    "PUBLIC_ANALYSIS_SYNTHESIS_QUESTION",
    "PublicAnalysisProductResult",
]
