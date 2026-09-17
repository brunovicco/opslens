"""Answer one asserted dependency from the index, without any repository machinery.

Gate 21.4's cheap shape. A repository request costs a GitHub snapshot, a lock read, a
parse, an inventory and a correlation pass. This costs one pointer read, one manifest
read and one partition query.

What it deliberately does not reuse is the repository envelope. That envelope answers
about evidence OpsLens observed and pinned; this one answers about a pair of strings the
caller supplied. Nothing here checks that the version exists on PyPI, that anything
installs it, or that the caller has the package they believe they have.

```text
observed evidence != asserted evidence
a sound verdict != a verified subject
```

The verdict itself is the same quality: the advisories the index holds for that name,
evaluated against that version by the same applicability function the repository path
uses. Only the warrant differs, and the answer says so by being a different type.

The same index certification applies — the authority refuses to answer from a generation
it cannot certify — so an empty answer here means the package is clean, not that the
index is.

```text
empty key space != no advisories
```

This module assembles. It queries nothing directly and decides no applicability.
"""

from dataclasses import dataclass
from typing import Final

from opslens.correlation.adapters.ghsa import (
    GhsaPyPICorrelationDecision,
    evaluate_ghsa_pypi_vulnerability,
)
from opslens.correlation.domain.pypi_ranges import CorrelationResult
from opslens.correlation_index.domain.index_contract import SourceWatermark
from opslens.public_analysis.adapters.correlation_index_threat_authority import (
    IndexBackedThreatEvidence,
)
from opslens.public_analysis.application.response_envelope import AnsweringIndex
from opslens.public_analysis.application.threat_evidence_authority import (
    PublicThreatDependencyScope,
    PublicThreatEvidenceProvenance,
    PublicThreatEvidenceRequest,
    PublicThreatEvidenceScope,
)
from opslens.public_analysis.domain import PublicAnalysisValidationError
from opslens.public_analysis.domain.dependency_request import PublicDependencyRequest
from opslens.shared.evidence import canonical_json, evidence_id

PUBLIC_DEPENDENCY_ENVELOPE_CONTRACT_VERSION: Final = "public-dependency-envelope:v1"

_PYPI_ECOSYSTEM: Final = "pip"


def build_dependency_threat_scope(
    request: PublicDependencyRequest,
) -> PublicThreatEvidenceScope:
    """Derive the threat scope for one asserted dependency.

    The scope type carries `source_execution_id` and `source_evidence_sha256` because a
    repository scope is derived from admitted repository evidence. Here the evidence is
    the caller's own assertion, so the request's content-addressed identity fills both:
    it is exactly as verifiable as what it describes, which is the point.

    Args:
        request: The admitted dependency.

    Returns:
        A scope naming exactly that one dependency, with nothing unidentified.

    Raises:
        PublicAnalysisValidationError: If the scope cannot be built.
    """
    return PublicThreatEvidenceScope(
        source_execution_id=request.request_id,
        source_evidence_sha256=request.request_id.partition("@sha256:")[2],
        dependencies=(
            PublicThreatDependencyScope(
                package_name=request.package_name_canonical,
                version=request.version_canonical,
                purl=request.purl,
                source_record_indexes=(0,),
            ),
        ),
        unidentified=(),
    )


def build_dependency_evidence_request(
    request: PublicDependencyRequest,
) -> PublicThreatEvidenceRequest:
    """Build the authority request for one asserted dependency.

    Args:
        request: The admitted dependency.

    Returns:
        The bounded authority request.
    """
    return PublicThreatEvidenceRequest(scope=build_dependency_threat_scope(request))


@dataclass(frozen=True, slots=True)
class PublicDependencyEnvelope:
    """One answer about one asserted dependency.

    Attributes:
        request: The dependency the caller asserted.
        decisions: One decision per advisory occurrence the index held, in index order.
        answering_index: The generation that answered.
        threat_provenance: Exact source identities and snapshot digests used.
    """

    request: PublicDependencyRequest
    decisions: tuple[GhsaPyPICorrelationDecision, ...]
    answering_index: AnsweringIndex
    threat_provenance: PublicThreatEvidenceProvenance

    @property
    def affected_count(self) -> int:
        """Return how many advisories apply to this version."""
        return sum(
            1
            for decision in self.decisions
            if decision.result is CorrelationResult.AFFECTED
        )

    @property
    def not_affected_count(self) -> int:
        """Return how many advisories were evaluated and do not apply."""
        return sum(
            1
            for decision in self.decisions
            if decision.result is CorrelationResult.NOT_AFFECTED
        )

    @property
    def unsupported_count(self) -> int:
        """Return how many advisories could not be decided.

        Counted rather than dropped, and never folded into not-affected: an advisory
        whose range this system cannot read is not an advisory that does not apply.

        ```text
        unsupported != not affected
        ```
        """
        return sum(
            1
            for decision in self.decisions
            if decision.result is CorrelationResult.UNSUPPORTED
        )

    @property
    def is_complete(self) -> bool:
        """Return whether every advisory the index held could be decided."""
        return self.unsupported_count == 0

    @property
    def canonical_payload(self) -> dict[str, object]:
        """Project the payload this answer's identity is taken over.

        The index identity is in; the index's `built_at` is not, for the reason ADR 0088
        gives: an idempotent rebuild must not move an answer.
        """
        return {
            "affected_advisories": sorted(
                {
                    decision.source.ghsa_id
                    for decision in self.decisions
                    if decision.result is CorrelationResult.AFFECTED
                }
            ),
            "answering_index": self.answering_index.identity_payload,
            "contract_version": PUBLIC_DEPENDENCY_ENVELOPE_CONTRACT_VERSION,
            "counts": {
                "affected": self.affected_count,
                "evaluated": len(self.decisions),
                "not_affected": self.not_affected_count,
                "unsupported": self.unsupported_count,
            },
            "observed_advisory_version_ids": sorted(
                {
                    decision.source.observed_advisory_version_id
                    for decision in self.decisions
                }
            ),
            "request_id": self.request.request_id,
            "threat_provenance": {
                "epss_sha256": self.threat_provenance.epss_sha256,
                "epss_snapshot_date": self.threat_provenance.epss_snapshot_date,
                "kev_sha256": self.threat_provenance.kev_sha256,
                "kev_snapshot_date": self.threat_provenance.kev_snapshot_date,
            },
        }

    @property
    def canonical_json(self) -> bytes:
        """Return the exact bytes this answer's identity is taken over."""
        return canonical_json(self.canonical_payload)

    @property
    def envelope_id(self) -> str:
        """Return one content-addressed identity for this answer."""
        return evidence_id(
            PUBLIC_DEPENDENCY_ENVELOPE_CONTRACT_VERSION, self.canonical_payload
        )


def analyze_public_dependency(
    request: PublicDependencyRequest,
    loaded: IndexBackedThreatEvidence,
) -> PublicDependencyEnvelope:
    """Evaluate one asserted dependency against the advisories the index holds.

    Args:
        request: The admitted dependency.
        loaded: Threat evidence, plus the index generation that produced it.

    Returns:
        The answer.

    Raises:
        PublicAnalysisValidationError: If the evidence was loaded for another question.
    """
    if type(loaded) is not IndexBackedThreatEvidence:
        raise PublicAnalysisValidationError(
            "dependency analysis requires evidence carrying the index that answered"
        )
    scope = loaded.evidence.request.scope
    if scope.source_execution_id != request.request_id:
        raise PublicAnalysisValidationError(
            "dependency analysis cannot use evidence loaded for another dependency"
        )

    decisions = tuple(
        evaluate_ghsa_pypi_vulnerability(
            source,
            installed_ecosystem=_PYPI_ECOSYSTEM,
            installed_package=request.package_name_original,
            installed_version=request.version_original,
            installed_purl=request.purl,
        )
        for source in loaded.evidence.ghsa_vulnerabilities
    )

    manifest = loaded.manifest
    return PublicDependencyEnvelope(
        request=request,
        decisions=decisions,
        answering_index=AnsweringIndex(
            index_id=loaded.live.index_id,
            built_at=manifest.built_at,
            ghsa_row_count=manifest.ghsa_row_count,
            distinct_package_count=manifest.distinct_package_count,
            watermarks=tuple[SourceWatermark, ...](manifest.watermarks),
        ),
        threat_provenance=loaded.evidence.provenance,
    )


__all__ = [
    "PUBLIC_DEPENDENCY_ENVELOPE_CONTRACT_VERSION",
    "PublicDependencyEnvelope",
    "analyze_public_dependency",
    "build_dependency_evidence_request",
    "build_dependency_threat_scope",
]
