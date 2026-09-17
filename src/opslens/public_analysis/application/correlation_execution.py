"""Run correlation over loaded evidence, and account for everything it could not decide.

Gate 20.3 adds no correlation logic. `build_repository_pypi_vulnerability_scan` already
joins normalized lock records to GHSA occurrences and reuses the Phase 3 applicability
truth. What this module adds is the accounting, because a verdict is only honest
alongside the things it did not cover.

There are **five** distinct ways a dependency can end up without an answer, and they mean
different things. Collapsing them into one "unsupported" number is how a response ends up
implying coverage it does not have.

```text
1  unidentified lock record     the lock named something with no PyPI identity at all
2  unsupported advisory join    an advisory the index holds but whose package cannot be keyed
3  unsupported assessment       a candidate pair evaluated, and the range could not decide
4  no advisory in the index     the package is clean, as far as this index knows
5  NVD not covered              ADR 0089: the index holds no CVE body, for any package
```

Only the fourth is good news, and only the fourth looks like the others from the outside.
A package with no advisories and a package whose advisory could not be keyed produce the
same empty list of findings; the first is a clean package, the second is a gap.

```text
no finding != nothing to find
unsupported != not affected
```

So `PublicCorrelationCoverage` counts all five separately and proves the arithmetic it
can: every assessment is exactly one of affected, not-affected or unsupported, and every
source record in the lock is accounted for once across identified and unidentified. Those
are the same accounting rules ADR 0085 established for Silver admission, applied to the
request path.

This module runs no query and loads nothing. It takes admitted evidence and returns what
correlation made of it.
"""

from dataclasses import dataclass

from opslens.correlation.domain.pypi_ranges import CorrelationResult
from opslens.public_analysis.application.threat_evidence_authority import (
    PublicRepositoryThreatEvidence,
)
from opslens.public_analysis.domain import (
    PublicAnalysisValidationError,
    PublicRepositoryEvidenceExecution,
)
from opslens.public_analysis.domain.request_bounds import (
    PUBLIC_REQUEST_BOUNDS,
    PublicRequestBounds,
)
from opslens.repository_intelligence.application.vulnerability_findings import (
    build_repository_pypi_vulnerability_scan,
)
from opslens.repository_intelligence.domain.vulnerability_findings import (
    RepositoryVulnerabilityScanEvidence,
)


@dataclass(frozen=True, slots=True)
class PublicCorrelationCoverage:
    """Everything one correlation pass did not decide, counted by why.

    Attributes:
        identified_dependency_count: Distinct dependencies correlation could evaluate.
        unidentified_record_count: Lock records with no PyPI identity (kind 1).
        unsupported_join_count: Index advisories that could not be keyed (kind 2).
        affected_count: Assessments that decided the dependency is affected.
        not_affected_count: Assessments that decided it is not.
        unsupported_assessment_count: Assessments that could not decide (kind 3).
        dependencies_without_advisories: Scoped dependencies the index held nothing for
            (kind 4) — the only one of the five that is good news.
        nvd_covered: Whether typed NVD records were available at all (kind 5).
    """

    identified_dependency_count: int
    unidentified_record_count: int
    unsupported_join_count: int
    affected_count: int
    not_affected_count: int
    unsupported_assessment_count: int
    dependencies_without_advisories: int
    nvd_covered: bool

    def __post_init__(self) -> None:
        """Reject coverage that cannot describe a real pass.

        Raises:
            PublicAnalysisValidationError: If any count is negative.
        """
        for field, value in (
            ("identified_dependency_count", self.identified_dependency_count),
            ("unidentified_record_count", self.unidentified_record_count),
            ("unsupported_join_count", self.unsupported_join_count),
            ("affected_count", self.affected_count),
            ("not_affected_count", self.not_affected_count),
            ("unsupported_assessment_count", self.unsupported_assessment_count),
            ("dependencies_without_advisories", self.dependencies_without_advisories),
        ):
            if type(value) is not int or value < 0:
                raise PublicAnalysisValidationError(
                    f"correlation coverage {field} must be a non-negative integer"
                )

    @property
    def assessment_count(self) -> int:
        """Return every candidate pair evaluated, decided or not."""
        return (
            self.affected_count
            + self.not_affected_count
            + self.unsupported_assessment_count
        )

    @property
    def is_complete(self) -> bool:
        """Return whether every dependency and every advisory could be evaluated.

        False does not mean the verdict is wrong. It means the verdict describes less
        than the repository, and a response that does not say so is overstating itself.
        """
        return (
            self.unidentified_record_count == 0
            and self.unsupported_join_count == 0
            and self.unsupported_assessment_count == 0
        )


@dataclass(frozen=True, slots=True)
class PublicCorrelationOutcome:
    """One correlation pass: what it found, and what it could not look at.

    Attributes:
        scan: The full bounded scan, including every assessment.
        coverage: The accounting a response must carry beside the verdict.
    """

    scan: RepositoryVulnerabilityScanEvidence
    coverage: PublicCorrelationCoverage


def correlate_public_repository(
    execution: PublicRepositoryEvidenceExecution,
    evidence: PublicRepositoryThreatEvidence,
    *,
    bounds: PublicRequestBounds = PUBLIC_REQUEST_BOUNDS,
) -> PublicCorrelationOutcome:
    """Correlate admitted lock evidence against admitted threat evidence.

    The scan is built from the execution's own normalization inventory rather than from
    the scope, because the inventory is what carries the unidentified half. Correlating
    from the scope alone would evaluate only what could be identified and report a
    verdict with no way to say what it skipped.

    The finding bound is applied after the scan rather than during it. A finding is only
    known to exist once its candidate pair has been evaluated, and evaluating is cheap
    next to emitting: the response is what the bound protects.

    ```text
    rows read != findings emitted != response bytes
    ```

    Args:
        execution: Admitted deterministic repository evidence.
        evidence: Threat evidence loaded for the scope derived from that execution.
        bounds: What one response is allowed to carry.

    Returns:
        The scan and its coverage.

    Raises:
        PublicAnalysisValidationError: If the evidence was not loaded for this execution.
        PublicRequestBoundError: If the response would carry too many findings.
        InvalidRepositoryVulnerabilityScanError: If the GHSA evidence is inconsistent.
        RepositoryVulnerabilityScanLimitError: If an internal bound is exceeded.
    """
    if type(execution) is not PublicRepositoryEvidenceExecution:
        raise PublicAnalysisValidationError(
            "public correlation requires admitted public repository evidence"
        )
    if type(evidence) is not PublicRepositoryThreatEvidence:
        raise PublicAnalysisValidationError(
            "public correlation requires typed admitted threat evidence"
        )
    scope = evidence.request.scope
    if scope.source_execution_id != execution.execution_id:
        raise PublicAnalysisValidationError(
            "public correlation cannot join threat evidence loaded for another execution"
        )

    inventory = execution.normalization_inventory
    scan = build_repository_pypi_vulnerability_scan(
        inventory, evidence.ghsa_vulnerabilities
    )
    bounds.admit_findings(len(scan.findings))

    tally = dict.fromkeys(CorrelationResult, 0)
    for assessment in scan.assessments:
        tally[assessment.result] += 1

    evaluated_packages = {
        assessment.dependency_name_canonical for assessment in scan.assessments
    }
    scoped_packages = set(scope.query_package_names)

    coverage = PublicCorrelationCoverage(
        identified_dependency_count=len(inventory.normalized_dependencies),
        unidentified_record_count=sum(
            len(item.source_record_indexes) for item in scope.unidentified
        ),
        unsupported_join_count=len(scan.unsupported_ghsa_join),
        affected_count=tally[CorrelationResult.AFFECTED],
        not_affected_count=tally[CorrelationResult.NOT_AFFECTED],
        unsupported_assessment_count=tally[CorrelationResult.UNSUPPORTED],
        dependencies_without_advisories=len(scoped_packages - evaluated_packages),
        nvd_covered=bool(evidence.nvd_records),
    )
    return PublicCorrelationOutcome(scan=scan, coverage=coverage)


__all__ = [
    "PublicCorrelationCoverage",
    "PublicCorrelationOutcome",
    "correlate_public_repository",
]
