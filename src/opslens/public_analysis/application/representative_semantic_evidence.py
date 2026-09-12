"""Build bounded remediation retrieval for the representative public workload."""

from collections.abc import Callable
from dataclasses import dataclass

from opslens.hybrid_retrieval.application import project_semantic_retrieval_evidence
from opslens.hybrid_retrieval.domain import SemanticEvidenceChunk
from opslens.knowledge_retrieval.application.bedrock_retrieval import BedrockRetrieveResult
from opslens.knowledge_retrieval.domain import RetrievalRequest
from opslens.public_analysis.domain import ProviderResourceUsage
from opslens.repository_intelligence.domain import RepositoryAnalysisResult
from opslens.risk_policy.domain import RiskPrioritizationResult

REPRESENTATIVE_REMEDIATION_TOP_K = 5

type RepresentativeSemanticRetriever = Callable[[RetrievalRequest], BedrockRetrieveResult]


@dataclass(frozen=True, slots=True)
class RepresentativeSemanticEvidence:
    """Admitted semantic evidence plus exact provider counters for one representative run."""

    source_analysis_id: str
    source_prioritization_id: str
    request: RetrievalRequest
    retrieve_result: BedrockRetrieveResult
    semantic_chunks: tuple[SemanticEvidenceChunk, ...]
    usage: ProviderResourceUsage

    def __post_init__(self) -> None:
        """Reject request, source, projection, or accounting drift."""
        if self.retrieve_result.evidence.request != self.request:
            raise ValueError("semantic evidence must originate from the exact retrieval request")
        expected_chunks = project_semantic_retrieval_evidence(self.retrieve_result.evidence)
        if self.semantic_chunks != expected_chunks:
            raise ValueError("semantic chunks must preserve the exact admitted retrieval evidence")
        invocation = self.retrieve_result.invocation
        expected_usage = ProviderResourceUsage(
            bedrock_retrieve_count=1,
            bedrock_retrieve_client_elapsed_ms=invocation.client_elapsed_ms,
            retry_count=invocation.retry_attempts,
        )
        if self.usage != expected_usage:
            raise ValueError(
                "semantic provider usage must match exact retrieval invocation evidence"
            )


def build_representative_remediation_request(
    *,
    analysis: RepositoryAnalysisResult,
    prioritization: RiskPrioritizationResult,
) -> RetrievalRequest:
    """Build one deterministic remediation query for the highest-priority affected finding."""
    if type(analysis) is not RepositoryAnalysisResult:
        raise TypeError("analysis must be RepositoryAnalysisResult")
    if type(prioritization) is not RiskPrioritizationResult:
        raise TypeError("prioritization must be RiskPrioritizationResult")
    if (
        prioritization.source_analysis_id != analysis.analysis_id
        or prioritization.source_analysis_sha256 != analysis.evidence_sha256
    ):
        raise ValueError("risk prioritization must reference the exact repository analysis")
    if not prioritization.ranked_findings:
        raise ValueError("representative remediation retrieval requires an affected finding")

    evaluation = prioritization.ranked_findings[0].evaluation
    finding = next(
        (
            item
            for item in analysis.findings
            if item.analysis_finding_id == evaluation.source.analysis_finding_id
        ),
        None,
    )
    if finding is None or finding.evidence_sha256 != evaluation.source.source_evidence_sha256:
        raise ValueError("highest-priority risk finding must bind to exact repository evidence")

    vulnerability_id = finding.cve_id or finding.ghsa_id
    fixed_version = finding.fixed_version or "unavailable"
    query = (
        f"Remediation guidance for {vulnerability_id} affecting {finding.purl}; "
        f"first patched version evidence: {fixed_version}."
    )
    return RetrievalRequest(query=query, top_k=REPRESENTATIVE_REMEDIATION_TOP_K)


def retrieve_representative_semantic_evidence(
    *,
    analysis: RepositoryAnalysisResult,
    prioritization: RiskPrioritizationResult,
    retriever: RepresentativeSemanticRetriever,
) -> RepresentativeSemanticEvidence:
    """Invoke one injected bounded Bedrock retrieval and preserve its measured counters."""
    request = build_representative_remediation_request(
        analysis=analysis,
        prioritization=prioritization,
    )
    result = retriever(request)
    if type(result) is not BedrockRetrieveResult:
        raise TypeError("representative retriever must return BedrockRetrieveResult")
    semantic_chunks = project_semantic_retrieval_evidence(result.evidence)
    invocation = result.invocation
    usage = ProviderResourceUsage(
        bedrock_retrieve_count=1,
        bedrock_retrieve_client_elapsed_ms=invocation.client_elapsed_ms,
        retry_count=invocation.retry_attempts,
    )
    return RepresentativeSemanticEvidence(
        source_analysis_id=analysis.analysis_id,
        source_prioritization_id=prioritization.prioritization_id,
        request=request,
        retrieve_result=result,
        semantic_chunks=semantic_chunks,
        usage=usage,
    )


__all__ = [
    "REPRESENTATIVE_REMEDIATION_TOP_K",
    "RepresentativeSemanticEvidence",
    "RepresentativeSemanticRetriever",
    "build_representative_remediation_request",
    "retrieve_representative_semantic_evidence",
]
