"""The response one public request produces, and everything needed to trust it.

Gate 20.4. A verdict on its own is not an answer: "no known vulnerabilities" is only
true of a particular repository, at a particular commit, against a particular index,
as of a particular moment, for the sources that index actually covers. Every one of those
qualifiers has been a place this system could quietly lie, and each has a field here.

**The envelope is content-addressed over what it answered from, not over when.** The
index identity is in the digest; the index's `built_at` is reported and excluded, exactly
as ADR 0088's correction excluded it from the index identity. Two requests for the same
commit against the same index must produce the same bytes even when the index was rebuilt
from identical content in between.

```text
what is stored != what is digested
when the index was built != which index answered
```

**Coverage sits beside the verdict, never behind it.** `PublicCorrelationCoverage`
counts the five distinct ways a dependency ends up without an answer, four of which look
identical from outside. The envelope carries the counts and a single `is_complete`, so a
consumer cannot read the findings without also being handed what was not evaluated.

```text
no finding != nothing to find
```

**The Risk Policy score is reported with its own completeness, and today that is always
partial.** CVSS reaches the policy only through NVD enrichment, and ADR 0089 leaves NVD
uncovered, so every evaluation comes back with `cvss_unavailable`, contributes zero
points for that factor, and sets `review_required`. That is the policy working as
designed rather than degrading: it was built to say when its evidence is incomplete, and
the evidence is incomplete.

```text
a score != a complete assessment
```

The consequence is worth stating plainly rather than leaving in a field: with NVD
uncovered, **every** finding this endpoint scores is a partial evaluation requiring
review, and the score ranks findings against each other without measuring severity.

This module assembles. It loads nothing, queries nothing, and decides no applicability.
"""

from dataclasses import dataclass

from opslens.correlation_index.domain.index_contract import SourceWatermark
from opslens.public_analysis.adapters.correlation_index_threat_authority import (
    IndexBackedThreatEvidence,
)
from opslens.public_analysis.application.correlation_execution import (
    PublicCorrelationCoverage,
    correlate_public_repository,
)
from opslens.public_analysis.application.threat_evidence_authority import (
    PublicThreatEvidenceProvenance,
)
from opslens.public_analysis.domain import (
    PublicAnalysisValidationError,
    PublicRepositoryEvidenceExecution,
)
from opslens.repository_intelligence.application import (
    build_repository_analysis_result,
    enrich_repository_findings_with_epss,
    enrich_repository_findings_with_kev,
    enrich_repository_findings_with_nvd,
)
from opslens.repository_intelligence.domain import RepositoryAnalysisResult
from opslens.risk_policy.application.prioritization import prioritize_repository_analysis
from opslens.risk_policy.domain import (
    RiskEvidenceCompleteness,
    RiskPrioritizationResult,
)
from opslens.shared.evidence import canonical_json, evidence_id

PUBLIC_ANALYSIS_ENVELOPE_CONTRACT_VERSION = "public-analysis-envelope:v1"


@dataclass(frozen=True, slots=True)
class AnsweringIndex:
    """The index generation that answered one request.

    `built_at` is carried and deliberately kept out of the envelope identity. Two builds
    of identical content share an index identity and differ in `built_at` (ADR 0088,
    Correction), so digesting it would make the same answer from the same index produce
    different bytes.

    Attributes:
        index_id: The content-addressed identity of the generation that was read.
        built_at: When that generation was built. Provenance, not identity.
        ghsa_row_count: Rows that generation holds.
        distinct_package_count: Packages it covers.
        watermarks: How fresh each contributing source was when it was built.
    """

    index_id: str
    built_at: str
    ghsa_row_count: int
    distinct_package_count: int
    watermarks: tuple[SourceWatermark, ...]

    @property
    def identity_payload(self) -> dict[str, object]:
        """Project the part of this that the envelope identity depends on."""
        return {
            "index_id": self.index_id,
            "watermarks": [
                {
                    "observed_through": item.observed_through,
                    "record_count": item.record_count,
                    "source": item.source,
                }
                for item in self.watermarks
            ],
        }

    @property
    def reported_payload(self) -> dict[str, object]:
        """Project everything a consumer is told, identity and provenance together."""
        return {
            **self.identity_payload,
            "built_at": self.built_at,
            "distinct_package_count": self.distinct_package_count,
            "ghsa_row_count": self.ghsa_row_count,
        }


@dataclass(frozen=True, slots=True)
class PublicAnalysisEnvelope:
    """One complete answer: the verdict, its ranking, and what it does not cover.

    Attributes:
        execution: The admitted repository evidence the answer is about.
        analysis: The final analysis, findings included.
        prioritization: Risk Policy v1 over those findings.
        coverage: What correlation could not decide, counted by why.
        answering_index: The index generation that answered.
        threat_provenance: Exact source identities and snapshot digests used.
    """

    execution: PublicRepositoryEvidenceExecution
    analysis: RepositoryAnalysisResult
    prioritization: RiskPrioritizationResult
    coverage: PublicCorrelationCoverage
    answering_index: AnsweringIndex
    threat_provenance: PublicThreatEvidenceProvenance

    @property
    def partial_evaluation_count(self) -> int:
        """Return how many scored findings the Risk Policy considers incomplete.

        With NVD uncovered this equals the number of findings, because CVSS reaches the
        policy only through NVD enrichment. A consumer reading a score without this
        number is reading a ranking as if it were a severity.
        """
        return sum(
            1
            for evaluation in self.prioritization.evaluations
            if evaluation.evidence_completeness is RiskEvidenceCompleteness.PARTIAL
        )

    @property
    def is_complete(self) -> bool:
        """Return whether every dependency, advisory and score was fully evaluated."""
        return self.coverage.is_complete and self.partial_evaluation_count == 0

    @property
    def canonical_payload(self) -> dict[str, object]:
        """Project the payload the envelope identity is taken over.

        Built from the identities the underlying evidence already computes rather than
        by re-serializing it, so a change anywhere in the chain moves this digest without
        this module needing to know what changed.
        """
        return {
            "analysis_id": self.analysis.analysis_id,
            "answering_index": self.answering_index.identity_payload,
            "contract_version": PUBLIC_ANALYSIS_ENVELOPE_CONTRACT_VERSION,
            "coverage": {
                "affected": self.coverage.affected_count,
                "dependencies_without_advisories": (
                    self.coverage.dependencies_without_advisories
                ),
                "identified_dependencies": self.coverage.identified_dependency_count,
                "not_affected": self.coverage.not_affected_count,
                "nvd_covered": self.coverage.nvd_covered,
                "partial_evaluations": self.partial_evaluation_count,
                "unidentified_records": self.coverage.unidentified_record_count,
                "unsupported_advisory_joins": self.coverage.unsupported_join_count,
                "unsupported_assessments": self.coverage.unsupported_assessment_count,
            },
            "prioritization_policy_version": self.prioritization.policy.version,
            "source_execution_id": self.execution.execution_id,
            "threat_provenance": {
                "epss_sha256": self.threat_provenance.epss_sha256,
                "epss_snapshot_date": self.threat_provenance.epss_snapshot_date,
                "ghsa_observed_advisory_version_ids": list(
                    self.threat_provenance.ghsa_observed_advisory_version_ids
                ),
                "kev_sha256": self.threat_provenance.kev_sha256,
                "kev_snapshot_date": self.threat_provenance.kev_snapshot_date,
                "nvd_observed_cve_version_ids": list(
                    self.threat_provenance.nvd_observed_cve_version_ids
                ),
            },
        }

    @property
    def canonical_json(self) -> bytes:
        """Return the exact bytes the envelope identity is taken over."""
        return canonical_json(self.canonical_payload)

    @property
    def envelope_id(self) -> str:
        """Return one content-addressed identity for this answer."""
        return evidence_id(
            PUBLIC_ANALYSIS_ENVELOPE_CONTRACT_VERSION, self.canonical_payload
        )


def build_public_analysis_envelope(
    execution: PublicRepositoryEvidenceExecution,
    loaded: IndexBackedThreatEvidence,
) -> PublicAnalysisEnvelope:
    """Assemble one answer from admitted repository evidence and one index read.

    Args:
        execution: Admitted deterministic repository evidence.
        loaded: Threat evidence, plus the index generation that produced it.

    Returns:
        The complete envelope.

    Raises:
        PublicAnalysisValidationError: If the evidence was not loaded for this execution.
    """
    if type(loaded) is not IndexBackedThreatEvidence:
        raise PublicAnalysisValidationError(
            "public analysis envelope requires evidence carrying the index that answered"
        )

    evidence = loaded.evidence
    outcome = correlate_public_repository(execution, evidence)

    nvd = enrich_repository_findings_with_nvd(
        outcome.scan, evidence.ghsa_vulnerabilities, evidence.nvd_records
    )
    kev = enrich_repository_findings_with_kev(nvd, evidence.kev_snapshot)
    epss = enrich_repository_findings_with_epss(kev, evidence.epss_snapshot)
    analysis = build_repository_analysis_result(epss)

    manifest = loaded.manifest
    return PublicAnalysisEnvelope(
        execution=execution,
        analysis=analysis,
        prioritization=prioritize_repository_analysis(analysis),
        coverage=outcome.coverage,
        answering_index=AnsweringIndex(
            index_id=loaded.live.index_id,
            built_at=manifest.built_at,
            ghsa_row_count=manifest.ghsa_row_count,
            distinct_package_count=manifest.distinct_package_count,
            watermarks=manifest.watermarks,
        ),
        threat_provenance=evidence.provenance,
    )


__all__ = [
    "PUBLIC_ANALYSIS_ENVELOPE_CONTRACT_VERSION",
    "AnsweringIndex",
    "PublicAnalysisEnvelope",
    "build_public_analysis_envelope",
]
