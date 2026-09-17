"""Tests for the single-dependency path.

Two things carry this module. The grammar is one operator wide on purpose, because a
range has no single answer to "is this affected" and accepting one would mean picking a
version on the caller's behalf. And the answer is a different type from the repository
answer, because the warrant behind it is different.

```text
observed evidence != asserted evidence
unsupported != not affected
```
"""

import gzip
import hashlib
import json
from datetime import UTC, datetime

import pytest

from opslens.correlation.domain.pypi_ranges import CorrelationResult
from opslens.correlation_index.adapters.in_memory_index_store import (
    InMemoryCorrelationIndexStore,
)
from opslens.correlation_index.domain.index_contract import (
    ProjectedGhsaIndexRow,
    SourceWatermark,
)
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.epss.domain.parser import EpssSnapshotParser
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.public_analysis.adapters.correlation_index_threat_authority import (
    CorrelationIndexThreatEvidenceAuthority,
    ThreatSnapshotSet,
)
from opslens.public_analysis.application.dependency_analysis import (
    PUBLIC_DEPENDENCY_ENVELOPE_CONTRACT_VERSION,
    analyze_public_dependency,
    build_dependency_evidence_request,
    build_dependency_threat_scope,
)
from opslens.public_analysis.domain import PublicAnalysisValidationError
from opslens.public_analysis.domain.dependency_request import (
    MAX_DEPENDENCY_SPECIFIER_LENGTH,
    admit_public_dependency_request,
)

_ADVISORY_DIGEST = "6872a46115d1775d1eac3f5ba734e73ec98a9f78487d178e38e13163c69d7dbf"
_ENTRY_DIGEST = "f086757888580ceef4a1f94c58aacb2c28ae445a18fecdac07c6561ff0519f6d"
_GHSA_ID = "GHSA-fq2j-3j99-rx65"
_CVE_ID = "CVE-2026-1234"
_BUILT_AT = datetime(2026, 9, 17, 10, 11, 11, tzinfo=UTC)
_WATERMARKS = (
    SourceWatermark(
        source="ghsa", observed_through="2026-09-16T18:56:22Z", record_count=35584
    ),
)


def _row(
    package: str = "requests",
    vulnerable_range: str = "<2.32.0",
    entry: str = "ghsa-entry:v1:test",
    advisory: str = _GHSA_ID,
    digest: str = _ADVISORY_DIGEST,
) -> ProjectedGhsaIndexRow:
    """Build one advisory row for the fixture index."""
    return ProjectedGhsaIndexRow(
        package_name_canonical=package,
        observed_advisory_version_id=f"{advisory}@sha256:{digest}",
        source_advisory_sha256=digest,
        source_entry_sha256=_ENTRY_DIGEST,
        ghsa_id=advisory,
        github_cve_id=_CVE_ID,
        github_identifiers=(),
        vulnerability_entry_id=entry,
        source_index=0,
        ecosystem_original="pip",
        package_name_original=package,
        vulnerable_range_original=vulnerable_range,
        first_patched_version_original=None,
    )


def _kev() -> KevCatalogSnapshot:
    """Build one complete KEV snapshot."""
    document: dict[str, object] = {
        "title": "CISA Known Exploited Vulnerabilities Catalog",
        "catalogVersion": "2026.09.03",
        "dateReleased": "2026-09-03T12:00:00Z",
        "count": 1,
        "vulnerabilities": [
            {
                "cveID": _CVE_ID,
                "vendorProject": "Example",
                "product": "Example",
                "vulnerabilityName": "Example",
                "dateAdded": "2026-09-01",
                "shortDescription": "Example",
                "requiredAction": "Apply updates.",
                "dueDate": "2026-09-22",
                "knownRansomwareCampaignUse": "Unknown",
                "notes": "https://example.com/advisory",
                "cwes": ["CWE-79"],
            }
        ],
    }
    payload = json.dumps(document, separators=(",", ":")).encode()
    return KevCatalogSnapshot(
        raw_bytes=payload,
        catalog_version="2026.09.03",
        date_released=datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
        retrieved_at=datetime(2026, 9, 3, 12, 30, tzinfo=UTC),
        sha256=hashlib.sha256(payload).hexdigest(),
        record_count=1,
    )


def _epss() -> EpssSnapshot:
    """Build one complete EPSS snapshot."""
    text = (
        "#model_version:v2026.06.15,score_date:2026-09-03T12:00:00Z\n"
        "cve,epss,percentile\n"
        f"{_CVE_ID},0.42,0.88\n"
    )
    return EpssSnapshotParser().parse(gzip.compress(text.encode(), mtime=0))


def _authority(
    *rows: ProjectedGhsaIndexRow, built_at: datetime = _BUILT_AT
) -> CorrelationIndexThreatEvidenceAuthority:
    """Compose the real authority over an offline index holding those rows."""
    store = InMemoryCorrelationIndexStore(
        built_at=built_at, ghsa=list(rows) or [_row()], nvd=(), watermarks=_WATERMARKS
    )
    return CorrelationIndexThreatEvidenceAuthority(
        store=store, snapshots=ThreatSnapshotSet(kev=_kev(), epss=_epss())
    )


def _answer(specifier: str, *rows: ProjectedGhsaIndexRow, built_at: datetime = _BUILT_AT):
    """Answer one specifier end to end, through the real authority."""
    request = admit_public_dependency_request(specifier)
    loaded = _authority(*rows, built_at=built_at).load_with_provenance(
        build_dependency_evidence_request(request)
    )
    return analyze_public_dependency(request, loaded)


class TestAdmission:
    """The grammar is one operator wide, and refuses rather than guesses."""

    def test_a_pair_is_admitted_and_canonicalized(self) -> None:
        """Both spellings are kept; only the canonical pair carries identity."""
        request = admit_public_dependency_request("Requests==2.31.0")
        assert request.package_name_original == "Requests"
        assert request.package_name_canonical == "requests"
        assert request.purl == "pkg:pypi/requests@2.31.0"
        assert request.request_id.startswith("public-dependency-request:v1@sha256:")

    def test_two_spellings_of_one_dependency_are_one_question(self) -> None:
        """A cache keyed on the spelling would answer the same question twice."""
        assert (
            admit_public_dependency_request("Requests==2.31.0").request_id
            == admit_public_dependency_request("requests==2.31.0").request_id
        )

    def test_a_different_version_is_a_different_question(self) -> None:
        """An identity that does not move with the version is not an identity."""
        assert (
            admit_public_dependency_request("requests==2.31.0").request_id
            != admit_public_dependency_request("requests==2.32.0").request_id
        )

    @pytest.mark.parametrize(
        "specifier",
        ["requests>=2.0", "requests", "requests==", "==2.31.0", "requests===2.31.0"],
    )
    def test_anything_but_one_equality_pair_is_refused(self, specifier: str) -> None:
        """A range has no single answer, and picking one would be answering for them."""
        with pytest.raises(PublicAnalysisValidationError):
            admit_public_dependency_request(specifier)

    def test_an_oversized_specifier_is_refused_before_parsing(self) -> None:
        """Reject, never truncate — the Phase 21 rule, at the cheapest possible point."""
        with pytest.raises(PublicAnalysisValidationError, match="exceeds"):
            admit_public_dependency_request("a" * (MAX_DEPENDENCY_SPECIFIER_LENGTH + 1))

    def test_a_name_with_no_pypi_identity_is_refused(self) -> None:
        """An unkeyable name would query a partition no advisory can occupy."""
        with pytest.raises(PublicAnalysisValidationError, match="not a PyPI identity"):
            admit_public_dependency_request("not/a/name==1.0.0")

    def test_a_version_with_no_pypi_identity_is_refused(self) -> None:
        """Applicability is decided on a normalized version or not at all."""
        with pytest.raises(PublicAnalysisValidationError, match="not a PyPI identity"):
            admit_public_dependency_request("requests==definitely-not-pep440")


class TestScope:
    """The scope says what the answer is warranted by."""

    def test_the_scope_names_exactly_one_dependency(self) -> None:
        """No repository machinery is involved and nothing is unidentified."""
        request = admit_public_dependency_request("requests==2.31.0")
        scope = build_dependency_threat_scope(request)
        assert scope.query_package_names == ("requests",)
        assert scope.unidentified == ()
        assert scope.source_execution_id == request.request_id


class TestVerdict:
    """The same applicability function the repository path uses."""

    def test_a_vulnerable_version_is_affected(self) -> None:
        """2.31.0 against <2.32.0."""
        envelope = _answer("requests==2.31.0")
        assert envelope.affected_count == 1
        assert envelope.decisions[0].result is CorrelationResult.AFFECTED
        assert envelope.is_complete

    def test_a_patched_version_is_not_affected(self) -> None:
        """2.32.0 against <2.32.0."""
        envelope = _answer("requests==2.32.0")
        assert envelope.affected_count == 0
        assert envelope.not_affected_count == 1

    def test_a_package_with_no_advisories_answers_empty(self) -> None:
        """Clean, because the index was certified before the query ran."""
        envelope = _answer("flask==3.0.0")
        assert envelope.decisions == ()
        assert envelope.affected_count == 0
        assert envelope.is_complete

    def test_an_undecidable_range_is_counted_not_folded_into_not_affected(self) -> None:
        """The collapse that would report a package clean without evaluating it."""
        envelope = _answer(
            "requests==2.31.0", _row(vulnerable_range="definitely not a range")
        )
        assert envelope.unsupported_count == 1
        assert envelope.not_affected_count == 0
        assert not envelope.is_complete


class TestAnswerIdentity:
    """Same question, same index, same bytes."""

    def test_two_answers_to_one_question_agree(self) -> None:
        """The property that makes a result cache possible in Gate 21.3."""
        assert _answer("requests==2.31.0").envelope_id == (
            _answer("requests==2.31.0").envelope_id
        )

    def test_a_rebuilt_index_of_identical_content_does_not_move_the_answer(self) -> None:
        """The index `built_at` is reported and not digested, as in the repository path."""
        early = _answer("requests==2.31.0", built_at=_BUILT_AT)
        later = _answer(
            "requests==2.31.0", built_at=datetime(2026, 9, 18, 4, 0, tzinfo=UTC)
        )
        assert early.answering_index.built_at != later.answering_index.built_at
        assert early.envelope_id == later.envelope_id

    def test_a_different_version_moves_the_answer(self) -> None:
        """Different question, different answer identity."""
        assert _answer("requests==2.31.0").envelope_id != (
            _answer("requests==2.32.0").envelope_id
        )

    def test_the_identity_names_the_contract(self) -> None:
        """A consumer cites the contract, not only the digest."""
        assert _answer("requests==2.31.0").envelope_id.startswith(
            f"{PUBLIC_DEPENDENCY_ENVELOPE_CONTRACT_VERSION}@sha256:"
        )


class TestBinding:
    """An answer assembled from another question's evidence is not an answer."""

    def test_evidence_loaded_for_another_dependency_is_refused(self) -> None:
        """Two dependencies, one load: the mismatch must fail rather than answer."""
        asked = admit_public_dependency_request("requests==2.31.0")
        other = admit_public_dependency_request("flask==3.0.0")
        loaded = _authority().load_with_provenance(
            build_dependency_evidence_request(other)
        )
        with pytest.raises(PublicAnalysisValidationError, match="another dependency"):
            analyze_public_dependency(asked, loaded)

    def test_evidence_without_its_index_is_refused(self) -> None:
        """The answer must be able to name what answered it."""
        request = admit_public_dependency_request("requests==2.31.0")
        with pytest.raises(PublicAnalysisValidationError, match="index that answered"):
            analyze_public_dependency(request, object())  # pyright: ignore[reportArgumentType]
