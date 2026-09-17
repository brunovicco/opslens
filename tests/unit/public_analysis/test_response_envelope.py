"""Tests for the request-time response envelope.

Two properties carry this module. The first is reproducibility: the same repository at
the same commit against the same index must produce the same bytes, including when that
index was rebuilt from identical content in between — which is why the index's
`built_at` is reported and not digested.

```text
when the index was built != which index answered
```

The second is that coverage travels with the verdict. Findings and "what was not
evaluated" come out of the same object, so a consumer cannot take one without the other.

The envelope is assembled over the real authority and the offline index store, not over
mocks, so the identities in the digest are ones the production path actually computes.
"""

import base64
import gzip
import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

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
from opslens.public_analysis.application import (
    admit_public_analysis_request,
    build_public_repository_evidence,
)
from opslens.public_analysis.application.response_envelope import (
    PUBLIC_ANALYSIS_ENVELOPE_CONTRACT_VERSION,
    build_public_analysis_envelope,
)
from opslens.public_analysis.application.threat_evidence_authority import (
    PublicThreatEvidenceRequest,
    build_public_threat_evidence_scope,
)
from opslens.public_analysis.domain import (
    PublicAnalysisValidationError,
    PublicRepositoryEvidenceExecution,
)
from opslens.repository_intelligence.domain import compute_git_blob_sha1
from opslens.risk_policy.domain import RiskEvidenceCompleteness

_REPOSITORY_ID = 1_333_092_779
_COMMIT_SHA = "3f75a4fc2bd22589df0a5ffe98a8442fda81c8d3"
_TREE_SHA = "01ac6fe03f1db867ef29c6652311ee43b1f63afb"
_ADVISORY_DIGEST = "6872a46115d1775d1eac3f5ba734e73ec98a9f78487d178e38e13163c69d7dbf"
_ENTRY_DIGEST = "f086757888580ceef4a1f94c58aacb2c28ae445a18fecdac07c6561ff0519f6d"
_GHSA_ID = "GHSA-fq2j-3j99-rx65"
_CVE_ID = "CVE-2026-1234"
_WATERMARKS = (
    SourceWatermark(
        source="ghsa", observed_through="2026-09-16T18:56:22Z", record_count=35584
    ),
)


def _lock(version: str = "2.31.0") -> bytes:
    """Build one uv.lock holding requests at that version."""
    return (
        b"version = 1\nrevision = 3\nrequires-python = \">=3.13\"\n"
        b"[[package]]\n"
        b'name = "Requests"\n'
        + f'version = "{version}"\n'.encode()
        + b'source = { registry = "https://pypi.org/simple" }\n'
    )


@dataclass(slots=True)
class _Source:
    """One canned GitHub source."""

    content: bytes = field(default_factory=_lock)

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


def _execution(version: str = "2.31.0") -> PublicRepositoryEvidenceExecution:
    """Build admitted repository evidence for a lock at that version."""
    request = admit_public_analysis_request(
        b'{"repository_url":"https://github.com/brunovicco/opslens","requested_ref":null}'
    ).request
    return build_public_repository_evidence(request, _Source(content=_lock(version)))


def _row() -> ProjectedGhsaIndexRow:
    """Build the one advisory row the fixture index holds."""
    return ProjectedGhsaIndexRow(
        package_name_canonical="requests",
        observed_advisory_version_id=f"{_GHSA_ID}@sha256:{_ADVISORY_DIGEST}",
        source_advisory_sha256=_ADVISORY_DIGEST,
        source_entry_sha256=_ENTRY_DIGEST,
        ghsa_id=_GHSA_ID,
        github_cve_id=_CVE_ID,
        github_identifiers=(),
        vulnerability_entry_id="ghsa-entry:v1:test",
        source_index=0,
        ecosystem_original="pip",
        package_name_original="Requests",
        vulnerable_range_original="<2.32.0",
        first_patched_version_original="2.32.0",
    )


def _kev() -> KevCatalogSnapshot:
    """Build one complete KEV snapshot naming the CVE."""
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
    """Build one complete EPSS snapshot scoring the CVE."""
    text = (
        "#model_version:v2026.06.15,score_date:2026-09-03T12:00:00Z\n"
        "cve,epss,percentile\n"
        f"{_CVE_ID},0.42,0.88\n"
    )
    return EpssSnapshotParser().parse(gzip.compress(text.encode(), mtime=0))


def _authority(built_at: datetime) -> CorrelationIndexThreatEvidenceAuthority:
    """Compose the real authority over an offline index built at that instant."""
    store = InMemoryCorrelationIndexStore(
        built_at=built_at, ghsa=[_row()], nvd=(), watermarks=_WATERMARKS
    )
    return CorrelationIndexThreatEvidenceAuthority(
        store=store, snapshots=ThreatSnapshotSet(kev=_kev(), epss=_epss())
    )


def _envelope(
    version: str = "2.31.0",
    built_at: datetime = datetime(2026, 9, 17, 10, 11, 11, tzinfo=UTC),
):
    """Build one envelope end to end, through the real authority."""
    execution = _execution(version)
    request = PublicThreatEvidenceRequest(
        scope=build_public_threat_evidence_scope(execution)
    )
    loaded = _authority(built_at).load_with_provenance(request)
    return build_public_analysis_envelope(execution, loaded)


class TestVerdictAndCoverageTravelTogether:
    """A consumer must not be able to read one without the other."""

    def test_an_affected_dependency_produces_a_finding_and_its_coverage(self) -> None:
        """The whole chain, from lock to score."""
        envelope = _envelope()
        assert len(envelope.analysis.findings) == 1
        assert envelope.coverage.affected_count == 1
        assert envelope.coverage.is_complete

    def test_a_patched_dependency_produces_no_finding_and_says_why_not(self) -> None:
        """No finding here means evaluated and not affected, and the counts say so."""
        envelope = _envelope(version="2.32.0")
        assert envelope.analysis.findings == ()
        assert envelope.coverage.not_affected_count == 1
        assert envelope.coverage.dependencies_without_advisories == 0

    def test_nvd_is_declared_uncovered(self) -> None:
        """ADR 0089. The envelope states it rather than omitting the field."""
        envelope = _envelope()
        assert envelope.canonical_payload["coverage"]["nvd_covered"] is False  # pyright: ignore[reportIndexIssue]


class TestRiskScoreCarriesItsOwnCompleteness:
    """A ranking read as a severity is the failure this guards."""

    def test_every_scored_finding_is_partial_while_nvd_is_uncovered(self) -> None:
        """CVSS reaches the policy only through NVD enrichment."""
        envelope = _envelope()
        assert len(envelope.prioritization.evaluations) == 1
        evaluation = envelope.prioritization.evaluations[0]
        assert evaluation.evidence_completeness is RiskEvidenceCompleteness.PARTIAL
        assert evaluation.review_required is True
        assert evaluation.selected_cvss_base_score is None
        assert envelope.partial_evaluation_count == 1

    def test_the_envelope_is_not_complete_when_a_score_is_partial(self) -> None:
        """Coverage being complete is not enough for the answer to be."""
        envelope = _envelope()
        assert envelope.coverage.is_complete
        assert not envelope.is_complete


class TestReproducibility:
    """Same repository, same commit, same index, same bytes."""

    def test_two_builds_of_the_same_request_agree(self) -> None:
        """The property Gate 20.4 promises."""
        assert _envelope().envelope_id == _envelope().envelope_id

    def test_a_rebuilt_index_of_identical_content_does_not_move_the_answer(self) -> None:
        """The index `built_at` is reported and not digested.

        Under the pre-correction identity this could not even be expressed: every
        rebuild produced a new index identity. Now an idempotent rebuild must leave the
        answer byte-identical.

        ```text
        when the index was built != which index answered
        ```
        """
        early = _envelope(built_at=datetime(2026, 9, 17, 10, 11, 11, tzinfo=UTC))
        later = _envelope(built_at=datetime(2026, 9, 18, 4, 0, 0, tzinfo=UTC))
        assert early.answering_index.built_at != later.answering_index.built_at
        assert early.answering_index.index_id == later.answering_index.index_id
        assert early.envelope_id == later.envelope_id

    def test_built_at_is_reported_even_though_it_is_not_digested(self) -> None:
        """Excluding it from the identity must not mean hiding it."""
        envelope = _envelope()
        assert envelope.answering_index.built_at == "2026-09-17T10:11:11Z"
        assert "built_at" in envelope.answering_index.reported_payload
        assert "built_at" not in envelope.answering_index.identity_payload

    def test_a_different_commit_moves_the_identity(self) -> None:
        """A digest that does not move with the repository is not an identity."""
        assert _envelope().envelope_id != _envelope(version="2.32.0").envelope_id

    def test_the_identity_names_the_contract(self) -> None:
        """A consumer cites the contract, not only the digest."""
        assert _envelope().envelope_id.startswith(
            f"{PUBLIC_ANALYSIS_ENVELOPE_CONTRACT_VERSION}@sha256:"
        )


class TestBinding:
    """An answer assembled from another repository's evidence is not an answer."""

    def test_evidence_without_its_index_is_refused(self) -> None:
        """The envelope must be able to name what answered it."""
        execution = _execution()
        with pytest.raises(PublicAnalysisValidationError, match="index that answered"):
            build_public_analysis_envelope(execution, object())  # pyright: ignore[reportArgumentType]

    def test_evidence_loaded_for_another_execution_is_refused(self) -> None:
        """Delegated to correlation, asserted here so the envelope cannot bypass it."""
        execution = _execution("2.31.0")
        other = _execution("2.32.0")
        request = PublicThreatEvidenceRequest(
            scope=build_public_threat_evidence_scope(other)
        )
        loaded = _authority(
            datetime(2026, 9, 17, 10, 11, 11, tzinfo=UTC)
        ).load_with_provenance(request)
        with pytest.raises(PublicAnalysisValidationError, match="another execution"):
            build_public_analysis_envelope(execution, loaded)
