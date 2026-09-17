"""Tests for correlation over loaded evidence, and for the accounting beside it.

The verdict is the easy half. The half that decides whether a response is honest is the
accounting, because four of the five ways a dependency ends up without an answer look
identical from outside: an empty list of findings.

```text
no finding != nothing to find
unsupported != not affected
```

So most of these tests are about a count being non-zero in the right slot, not about a
finding being produced.
"""

import base64
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from opslens.correlation.adapters.ghsa import GhsaPyPIVulnerabilityEvidence
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.public_analysis.application import (
    admit_public_analysis_request,
    build_public_repository_evidence,
)
from opslens.public_analysis.application.correlation_execution import (
    PublicCorrelationCoverage,
    correlate_public_repository,
)
from opslens.public_analysis.application.threat_evidence_authority import (
    PublicRepositoryThreatEvidence,
    PublicThreatEvidenceRequest,
    build_public_threat_evidence_scope,
)
from opslens.public_analysis.domain import (
    PublicAnalysisValidationError,
    PublicRepositoryEvidenceExecution,
)
from opslens.repository_intelligence.domain import compute_git_blob_sha1

_REPOSITORY_ID = 1_333_092_779
_COMMIT_SHA = "3f75a4fc2bd22589df0a5ffe98a8442fda81c8d3"
_TREE_SHA = "01ac6fe03f1db867ef29c6652311ee43b1f63afb"


def _request():
    """Admit the one request these tests use."""
    return admit_public_analysis_request(
        b'{"repository_url":"https://github.com/brunovicco/opslens","requested_ref":null}'
    ).request


def _lock(*records: tuple[str, str]) -> bytes:
    """Build one uv.lock carrying the given (name, version) records."""
    body = b"version = 1\nrevision = 3\nrequires-python = \">=3.13\"\n"
    for name, version in records:
        body += (
            b"[[package]]\n"
            + f'name = "{name}"\n'.encode()
            + f'version = "{version}"\n'.encode()
            + b'source = { registry = "https://pypi.org/simple" }\n'
        )
    return body


@dataclass(slots=True)
class _Source:
    """One canned GitHub source."""

    content: bytes = field(default_factory=lambda: _lock(("Requests", "2.31.0")))

    def get_repository(self, owner: str, name: str) -> dict[str, object]:
        """Return the canned repository."""
        assert (owner, name) == ("brunovicco", "opslens")
        return {
            "id": _REPOSITORY_ID,
            "name": "opslens",
            "full_name": "brunovicco/opslens",
            "private": False,
            "visibility": "public",
            "default_branch": "main",
            "owner": {"login": "brunovicco"},
        }

    def get_commit(self, owner: str, name: str, ref: str) -> dict[str, object]:
        """Return the canned commit."""
        assert (owner, name, ref) == ("brunovicco", "opslens", "main")
        return {"sha": _COMMIT_SHA, "commit": {"tree": {"sha": _TREE_SHA}}}

    def get_uv_lock(self, owner: str, name: str, commit_sha: str) -> dict[str, object]:
        """Return the canned lock payload."""
        assert (owner, name, commit_sha) == ("brunovicco", "opslens", _COMMIT_SHA)
        return {
            "type": "file",
            "path": "uv.lock",
            "name": "uv.lock",
            "encoding": "base64",
            "size": len(self.content),
            "sha": compute_git_blob_sha1(self.content),
            "content": base64.encodebytes(self.content).decode("ascii"),
        }


def _execution(*records: tuple[str, str]) -> PublicRepositoryEvidenceExecution:
    """Build admitted repository evidence for a lock carrying those records."""
    return build_public_repository_evidence(
        _request(), _Source(content=_lock(*records or (("Requests", "2.31.0"),)))
    )


def _ghsa(
    *,
    package_name: str = "Requests",
    vulnerable_range: str = "<2.32.0",
    entry: str = "ghsa-entry:v1:test",
    advisory: str = "GHSA-aaaa-bbbb-cccc",
    digest: str = "a" * 64,
) -> GhsaPyPIVulnerabilityEvidence:
    """Build one GHSA occurrence."""
    return GhsaPyPIVulnerabilityEvidence(
        observed_advisory_version_id=f"{advisory}@sha256:{digest}",
        source_advisory_sha256=digest,
        ghsa_id=advisory,
        github_cve_id=None,
        github_identifiers=(),
        vulnerability_entry_id=entry,
        source_index=0,
        source_entry_sha256="b" * 64,
        ecosystem_original="pip",
        package_name_original=package_name,
        vulnerable_range_original=vulnerable_range,
        first_patched_version_original=None,
    )


def _kev() -> KevCatalogSnapshot:
    """Build one complete KEV snapshot."""
    return KevCatalogSnapshot(
        raw_bytes=b"{}",
        catalog_version="2026.09.12",
        date_released=datetime(2026, 9, 12, tzinfo=UTC),
        retrieved_at=datetime(2026, 9, 12, 12, tzinfo=UTC),
        sha256="c" * 64,
        record_count=1,
    )


def _epss() -> EpssSnapshot:
    """Build one complete EPSS snapshot."""
    return EpssSnapshot(
        raw_bytes=b"epss",
        model_version="v2026.06.15",
        score_timestamp=datetime(2026, 9, 12, tzinfo=UTC),
        sha256="d" * 64,
        row_count=1,
    )


def _evidence(
    execution: PublicRepositoryEvidenceExecution, *ghsa: GhsaPyPIVulnerabilityEvidence
) -> PublicRepositoryThreatEvidence:
    """Load threat evidence for that execution, the way Gate 20.2 returns it."""
    scope = build_public_threat_evidence_scope(execution)
    return PublicRepositoryThreatEvidence(
        request=PublicThreatEvidenceRequest(scope=scope),
        ghsa_vulnerabilities=tuple(ghsa),
        nvd_records=(),
        kev_snapshot=_kev(),
        epss_snapshot=_epss(),
    )


class TestVerdict:
    """The easy half, asserted so the accounting tests have something to stand on."""

    def test_a_vulnerable_version_is_affected(self) -> None:
        """2.31.0 against <2.32.0."""
        execution = _execution(("Requests", "2.31.0"))
        outcome = correlate_public_repository(execution, _evidence(execution, _ghsa()))
        assert outcome.coverage.affected_count == 1
        assert len(outcome.scan.findings) == 1

    def test_a_patched_version_is_not_affected(self) -> None:
        """2.32.0 against <2.32.0."""
        execution = _execution(("Requests", "2.32.0"))
        outcome = correlate_public_repository(execution, _evidence(execution, _ghsa()))
        assert outcome.coverage.affected_count == 0
        assert outcome.coverage.not_affected_count == 1
        assert outcome.scan.findings == ()


class TestCoverage:
    """Four of the five ways to have no finding, and only one of them is good news."""

    def test_a_clean_package_is_counted_as_having_no_advisories(self) -> None:
        """The good one: the index held nothing for this package."""
        execution = _execution(("Requests", "2.31.0"))
        outcome = correlate_public_repository(execution, _evidence(execution))
        assert outcome.coverage.dependencies_without_advisories == 1
        assert outcome.coverage.assessment_count == 0
        assert outcome.coverage.is_complete

    def test_an_unidentified_lock_record_is_counted_not_dropped(self) -> None:
        """A record with no PyPI identity at all; ADR 0084 carries it in the scope."""
        execution = _execution(("Requests", "2.31.0"), ("brokenpkg", "definitely-not-pep440"))
        outcome = correlate_public_repository(execution, _evidence(execution, _ghsa()))
        assert outcome.coverage.unidentified_record_count == 1
        assert not outcome.coverage.is_complete

    def test_an_unsupported_assessment_is_counted_and_is_not_not_affected(self) -> None:
        """The dangerous collapse: an undecidable range reported as a clean dependency."""
        execution = _execution(("Requests", "2.31.0"))
        evidence = _evidence(execution, _ghsa(vulnerable_range="definitely not a range"))
        outcome = correlate_public_repository(execution, evidence)
        assert outcome.coverage.unsupported_assessment_count == 1
        assert outcome.coverage.not_affected_count == 0
        assert outcome.coverage.affected_count == 0
        assert not outcome.coverage.is_complete

    def test_nvd_is_reported_as_not_covered(self) -> None:
        """ADR 0089. Silence here would read as no CVE having a record."""
        execution = _execution(("Requests", "2.31.0"))
        outcome = correlate_public_repository(execution, _evidence(execution, _ghsa()))
        assert outcome.coverage.nvd_covered is False

    def test_every_assessment_lands_in_exactly_one_bucket(self) -> None:
        """The ADR 0085 accounting rule, applied to the request path."""
        execution = _execution(("Requests", "2.31.0"))
        evidence = _evidence(
            execution,
            _ghsa(),
            _ghsa(
                vulnerable_range="definitely not a range",
                entry="ghsa-entry:v1:other",
                advisory="GHSA-dddd-eeee-ffff",
                digest="e" * 64,
            ),
        )
        outcome = correlate_public_repository(execution, evidence)
        assert outcome.coverage.assessment_count == len(outcome.scan.assessments)
        assert outcome.coverage.assessment_count == 2


class TestBinding:
    """Evidence loaded for another repository must not produce a verdict for this one."""

    def test_evidence_from_another_execution_is_refused(self) -> None:
        """The authority binds evidence to a request; this binds it to the execution."""
        execution = _execution(("Requests", "2.31.0"))
        other = _execution(("Requests", "2.32.0"))
        with pytest.raises(PublicAnalysisValidationError, match="another execution"):
            correlate_public_repository(execution, _evidence(other, _ghsa()))

    def test_untyped_evidence_is_refused(self) -> None:
        """A verdict cannot be built from something that was never admitted."""
        execution = _execution(("Requests", "2.31.0"))
        with pytest.raises(PublicAnalysisValidationError, match="typed admitted"):
            correlate_public_repository(execution, object())  # pyright: ignore[reportArgumentType]


class TestCoverageType:
    """The counts describe a real pass or they describe nothing."""

    def test_a_negative_count_is_refused(self) -> None:
        """A count that cannot have happened cannot describe coverage."""
        with pytest.raises(PublicAnalysisValidationError, match="non-negative"):
            PublicCorrelationCoverage(
                identified_dependency_count=-1,
                unidentified_record_count=0,
                unsupported_join_count=0,
                affected_count=0,
                not_affected_count=0,
                unsupported_assessment_count=0,
                dependencies_without_advisories=0,
                nvd_covered=False,
            )

    def test_completeness_needs_all_three_gaps_empty(self) -> None:
        """Any one of them non-zero means the verdict describes less than the repository."""
        def coverage(**gaps: int) -> PublicCorrelationCoverage:
            """Build one coverage whose named gaps are non-zero."""
            return PublicCorrelationCoverage(
                identified_dependency_count=1,
                unidentified_record_count=gaps.get("unidentified_record_count", 0),
                unsupported_join_count=gaps.get("unsupported_join_count", 0),
                affected_count=0,
                not_affected_count=1,
                unsupported_assessment_count=gaps.get(
                    "unsupported_assessment_count", 0
                ),
                dependencies_without_advisories=0,
                nvd_covered=False,
            )

        assert coverage().is_complete
        for gap in (
            "unidentified_record_count",
            "unsupported_join_count",
            "unsupported_assessment_count",
        ):
            assert not coverage(**{gap: 1}).is_complete
