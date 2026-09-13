"""Deterministic non-public result admission for the Gate 19.2 representative workload."""

from dataclasses import dataclass
from hashlib import sha256

from opslens.hybrid_retrieval.domain import (
    HybridEvidenceEnvelope,
    HybridSynthesisRequest,
    HybridSynthesisResult,
)
from opslens.public_analysis.domain.errors import PublicAnalysisValidationError
from opslens.public_analysis.domain.semantic_planning import PublicAnalysisAdmissionHandoff
from opslens.repository_intelligence.domain import RepositoryAnalysisResult
from opslens.risk_policy.domain import RiskPrioritizationResult
from opslens.shared.evidence import canonical_json

REPRESENTATIVE_PUBLIC_RESULT_CONTRACT_VERSION = "representative-public-analysis-result:v1"
MAX_REPRESENTATIVE_RESULT_FINDINGS = 8


def _canonical_json(value: object) -> bytes:
    """Serialize the bounded representative result with stable identity."""
    return canonical_json(value)


@dataclass(frozen=True, slots=True)
class RepresentativePublicAnalysisResult:
    """Admit one complete measured-path result without creating public transport authority."""

    handoff: PublicAnalysisAdmissionHandoff
    analysis: RepositoryAnalysisResult
    prioritization: RiskPrioritizationResult
    envelope: HybridEvidenceEnvelope
    synthesis_request: HybridSynthesisRequest
    synthesis_result: HybridSynthesisResult

    def __post_init__(self) -> None:
        """Reject source, evidence, risk, or synthesis drift before serialization."""
        if type(self.handoff) is not PublicAnalysisAdmissionHandoff:
            raise PublicAnalysisValidationError("result requires an admitted public handoff")
        if type(self.analysis) is not RepositoryAnalysisResult:
            raise PublicAnalysisValidationError("result requires RepositoryAnalysisResult")
        if type(self.prioritization) is not RiskPrioritizationResult:
            raise PublicAnalysisValidationError("result requires RiskPrioritizationResult")
        if type(self.envelope) is not HybridEvidenceEnvelope:
            raise PublicAnalysisValidationError("result requires HybridEvidenceEnvelope")
        if type(self.synthesis_request) is not HybridSynthesisRequest:
            raise PublicAnalysisValidationError("result requires HybridSynthesisRequest")
        if type(self.synthesis_result) is not HybridSynthesisResult:
            raise PublicAnalysisValidationError("result requires HybridSynthesisResult")

        source_execution = self.handoff.source_execution
        if self.analysis.snapshot_id != source_execution.snapshot_id:
            raise PublicAnalysisValidationError(
                "result analysis must use the exact immutable handoff snapshot"
            )
        if self.analysis.file_evidence_id != source_execution.file_evidence_id:
            raise PublicAnalysisValidationError(
                "result analysis must use the exact handoff dependency evidence"
            )
        if (
            self.prioritization.source_analysis_id != self.analysis.analysis_id
            or self.prioritization.source_analysis_sha256 != self.analysis.evidence_sha256
        ):
            raise PublicAnalysisValidationError(
                "result prioritization must use the exact admitted repository analysis"
            )
        if not self.prioritization.ranked_findings:
            raise PublicAnalysisValidationError(
                "representative measured result requires at least one affected finding"
            )
        if self.envelope.authority_decision != self.handoff.route_decision:
            raise PublicAnalysisValidationError(
                "result evidence envelope must use the exact public route decision"
            )
        if self.synthesis_request.envelope != self.envelope:
            raise PublicAnalysisValidationError(
                "result synthesis request must use the exact admitted evidence envelope"
            )
        if self.synthesis_result.request_sha256 != self.synthesis_request.request_sha256:
            raise PublicAnalysisValidationError(
                "result synthesis output must reference the exact synthesis request"
            )

        analysis_ids = {finding.analysis_finding_id for finding in self.analysis.findings}
        for ranked in self.prioritization.ranked_findings:
            if ranked.evaluation.source.analysis_finding_id not in analysis_ids:
                raise PublicAnalysisValidationError(
                    "result prioritization contains a finding outside repository analysis"
                )

    @property
    def canonical_json(self) -> bytes:
        """Return the bounded response candidate used for exact byte measurement."""
        findings_by_id = {
            finding.analysis_finding_id: finding for finding in self.analysis.findings
        }
        findings: list[object] = []
        for ranked in self.prioritization.ranked_findings[:MAX_REPRESENTATIVE_RESULT_FINDINGS]:
            evaluation = ranked.evaluation
            finding = findings_by_id[evaluation.source.analysis_finding_id]
            findings.append(
                {
                    "analysis_finding_id": finding.analysis_finding_id,
                    "cve_id": finding.cve_id,
                    "fixed_version": finding.fixed_version,
                    "ghsa_id": finding.ghsa_id,
                    "installed_version": finding.installed_version,
                    "priority_score": evaluation.priority_score,
                    "priority_tier": evaluation.priority_tier.value,
                    "purl": finding.purl,
                    "rank": ranked.rank,
                    "review_required": evaluation.review_required,
                }
            )

        semantic_citations = [
            {
                "canonical_uri": citation.canonical_uri,
                "citation_id": citation.citation_id,
                "document_id": citation.document_id,
                "evidence_id": citation.evidence_id,
                "source_id": citation.source_id,
                "title": citation.title,
            }
            for citation in self.synthesis_request.semantic_citations
        ]
        claims = [
            {
                "claim_index": claim.claim_index,
                "semantic_citation_ids": list(claim.semantic_citation_ids),
                "structured_fact_ids": list(claim.structured_fact_ids),
                "text": claim.text,
            }
            for claim in self.synthesis_result.claims
        ]
        snapshot = self.analysis.repository_snapshot
        return _canonical_json(
            {
                "accounting": {
                    "returned_findings": len(findings),
                    "total_affected_findings": self.analysis.finding_count,
                },
                "contract_version": REPRESENTATIVE_PUBLIC_RESULT_CONTRACT_VERSION,
                "evidence": {
                    "analysis_id": self.analysis.analysis_id,
                    "hybrid_envelope_id": self.envelope.envelope_id,
                    "prioritization_id": self.prioritization.prioritization_id,
                    "semantic_citations": semantic_citations,
                    "structured_evidence_ids": [
                        item.evidence_id for item in self.envelope.structured_evidence
                    ],
                    "synthesis_result_sha256": self.synthesis_result.result_sha256,
                },
                "explanation": {
                    "claims": claims,
                    "decision": self.synthesis_result.decision.value,
                },
                "findings": findings,
                "handoff_id": self.handoff.handoff_id,
                "outcome": "completed",
                "repository": {
                    "commit_sha": snapshot.commit_sha,
                    "full_name": snapshot.repository.full_name,
                    "provider": snapshot.repository.provider.value,
                    "snapshot_id": snapshot.snapshot_id,
                },
                "request_id": self.handoff.source_execution.request.request_id,
                "workload_id": "public-analysis-workload:v1",
            }
        )

    @property
    def result_sha256(self) -> str:
        """Return content identity for the exact serialized representative result."""
        return sha256(self.canonical_json).hexdigest()

    def serialize(self) -> bytes:
        """Implement the measurement harness admitted-result serializer port."""
        return self.canonical_json


__all__ = [
    "MAX_REPRESENTATIVE_RESULT_FINDINGS",
    "REPRESENTATIVE_PUBLIC_RESULT_CONTRACT_VERSION",
    "RepresentativePublicAnalysisResult",
]
