"""Tests for what one public request is allowed to cost.

Every case here asserts a refusal, because the failure this guards is not a crash — it is
a request that quietly returns less than it should and reads as clean.

```text
a bound reached != a smaller answer
truncated input != smaller input
```

The bound set itself is also tested, because a bound that contradicts the platform it
assumes is worse than no bound: it promises a ceiling nothing enforces.
"""

import gzip
import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from opslens.correlation_index.adapters.in_memory_index_store import (
    InMemoryCorrelationIndexStore,
)
from opslens.correlation_index.application.index_reading import LiveIndexGeneration
from opslens.correlation_index.domain.index_contract import (
    CorrelationIndexManifest,
    ProjectedGhsaIndexRow,
    ProjectedNvdIndexRow,
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
    build_dependency_evidence_request,
)
from opslens.public_analysis.application.threat_evidence_authority import (
    PublicThreatDependencyScope,
    PublicThreatEvidenceRequest,
    PublicThreatEvidenceScope,
)
from opslens.public_analysis.domain import PublicAnalysisValidationError
from opslens.public_analysis.domain.dependency_request import (
    admit_public_dependency_request,
)
from opslens.public_analysis.domain.request_bounds import (
    FINDING_RESPONSE_BYTES,
    PUBLIC_REQUEST_BOUNDS,
    RESPONSE_BUDGET_BYTES,
    PublicRequestBoundError,
    PublicRequestBounds,
)

_ENTRY_DIGEST = "f086757888580ceef4a1f94c58aacb2c28ae445a18fecdac07c6561ff0519f6d"
_BUILT_AT = datetime(2026, 9, 17, 10, 11, 11, tzinfo=UTC)
_WATERMARKS = (
    SourceWatermark(
        source="ghsa", observed_through="2026-09-16T18:56:22Z", record_count=35584
    ),
)


def _advisory_id(index: int) -> str:
    """Return one syntactically valid GHSA id."""
    alphabet = "23456789cfghjmpqrvwx"
    digits: list[str] = []
    value = index
    for _ in range(12):
        digits.append(alphabet[value % len(alphabet)])
        value //= len(alphabet)
    body = "".join(digits)
    return f"GHSA-{body[0:4]}-{body[4:8]}-{body[8:12]}"


def _rows(package: str, count: int) -> list[ProjectedGhsaIndexRow]:
    """Build `count` advisory rows against one package."""
    rows: list[ProjectedGhsaIndexRow] = []
    for index in range(count):
        advisory = _advisory_id(index)
        digest = hashlib.sha256(advisory.encode()).hexdigest()
        rows.append(
            ProjectedGhsaIndexRow(
                package_name_canonical=package,
                observed_advisory_version_id=f"{advisory}@sha256:{digest}",
                source_advisory_sha256=digest,
                source_entry_sha256=_ENTRY_DIGEST,
                ghsa_id=advisory,
                github_cve_id=None,
                github_identifiers=(),
                vulnerability_entry_id=f"ghsa-entry:v1:{advisory}",
                source_index=0,
                ecosystem_original="pip",
                package_name_original=package,
                vulnerable_range_original="<99.0.0",
                first_patched_version_original=None,
            )
        )
    return rows


def _snapshots() -> ThreatSnapshotSet:
    """Build the snapshots a worker holds."""
    document: dict[str, object] = {
        "title": "CISA Known Exploited Vulnerabilities Catalog",
        "catalogVersion": "2026.09.03",
        "dateReleased": "2026-09-03T12:00:00Z",
        "count": 1,
        "vulnerabilities": [
            {
                "cveID": "CVE-1999-0001",
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
    kev = KevCatalogSnapshot(
        raw_bytes=payload,
        catalog_version="2026.09.03",
        date_released=datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
        retrieved_at=datetime(2026, 9, 3, 12, 30, tzinfo=UTC),
        sha256=hashlib.sha256(payload).hexdigest(),
        record_count=1,
    )
    text = (
        "#model_version:v2026.06.15,score_date:2026-09-03T12:00:00Z\n"
        "cve,epss,percentile\n"
        "CVE-1999-0001,0.42,0.88\n"
    )
    epss: EpssSnapshot = EpssSnapshotParser().parse(gzip.compress(text.encode(), mtime=0))
    return ThreatSnapshotSet(kev=kev, epss=epss)


def _authority(
    rows: list[ProjectedGhsaIndexRow], bounds: PublicRequestBounds
) -> CorrelationIndexThreatEvidenceAuthority:
    """Compose the real authority over an offline index, under those bounds."""
    store = InMemoryCorrelationIndexStore(
        built_at=_BUILT_AT, ghsa=rows, nvd=(), watermarks=_WATERMARKS
    )
    return CorrelationIndexThreatEvidenceAuthority(
        store=store, snapshots=_snapshots(), bounds=bounds
    )


class _CountingStore:
    """Wrap the offline store and count how many package queries it served."""

    def __init__(self, inner: InMemoryCorrelationIndexStore) -> None:
        self._inner = inner
        self.queries = 0

    def resolve_live_generation(self) -> LiveIndexGeneration:
        """Delegate."""
        return self._inner.resolve_live_generation()

    def read_manifest(self, live: LiveIndexGeneration) -> CorrelationIndexManifest:
        """Delegate."""
        return self._inner.read_manifest(live)

    def ghsa_for_package(
        self, package_name_canonical: str, *, live: LiveIndexGeneration
    ) -> tuple[ProjectedGhsaIndexRow, ...]:
        """Delegate, counting the query."""
        self.queries += 1
        return self._inner.ghsa_for_package(package_name_canonical, live=live)

    def nvd_for_cve(
        self, cve_id: str, *, live: LiveIndexGeneration
    ) -> ProjectedNvdIndexRow | None:
        """Delegate."""
        return self._inner.nvd_for_cve(cve_id, live=live)


class TestTheBoundSetItself:
    """A bound that contradicts its platform promises a ceiling nothing enforces."""

    def test_the_shipped_bounds_derive_from_the_measurement(self) -> None:
        """320 findings is RESPONSE_BUDGET / measured finding size, not a round number."""
        assert PUBLIC_REQUEST_BOUNDS.max_findings_emitted == (
            RESPONSE_BUDGET_BYTES // FINDING_RESPONSE_BYTES
        )
        assert PUBLIC_REQUEST_BOUNDS.max_findings_emitted == 320

    def test_the_shipped_bounds_leave_platform_headroom(self) -> None:
        """The platform ceiling must never be the thing that stops a request."""
        assert PUBLIC_REQUEST_BOUNDS.projected_response_bytes < (
            PUBLIC_REQUEST_BOUNDS.assumed_platform_response_bytes
        )
        assert PUBLIC_REQUEST_BOUNDS.platform_headroom > 5

    def test_the_read_bound_covers_the_heaviest_real_packages(self) -> None:
        """tensorflow, -gpu and -cpu carry 3,941 rows between them (ADR 0087)."""
        assert PUBLIC_REQUEST_BOUNDS.max_index_rows_read >= 3941

    def test_a_response_bound_above_the_platform_ceiling_is_refused(self) -> None:
        """Promising more than the platform allows is worse than promising nothing.

        The row bound is raised alongside it so the coherence check is not what fires:
        this asserts the platform check specifically.
        """
        with pytest.raises(PublicAnalysisValidationError, match="platform ceiling"):
            replace(
                PUBLIC_REQUEST_BOUNDS,
                max_findings_emitted=100_000,
                max_index_rows_read=100_000,
            )

    def test_emitting_more_than_can_be_read_is_refused(self) -> None:
        """A finding comes from a row; a bound set implying otherwise is incoherent."""
        with pytest.raises(PublicAnalysisValidationError, match="more findings than"):
            replace(PUBLIC_REQUEST_BOUNDS, max_index_rows_read=10)

    @pytest.mark.parametrize(
        "field",
        [
            "max_lock_bytes",
            "max_lock_package_records",
            "max_scoped_packages",
            "max_index_rows_read",
            "max_findings_emitted",
        ],
    )
    def test_a_non_positive_bound_is_refused(self, field: str) -> None:
        """A bound of zero refuses everything, which is not a bound but an outage."""
        with pytest.raises(PublicAnalysisValidationError, match="positive integer"):
            replace(PUBLIC_REQUEST_BOUNDS, **{field: 0})


class TestEachBoundRefusesWithAReason:
    """Every breach is machine-readable, because a caller has to know what to change."""

    def test_an_oversized_lock_is_refused(self) -> None:
        """Checked against the file, before anything is parsed."""
        with pytest.raises(PublicRequestBoundError) as raised:
            PUBLIC_REQUEST_BOUNDS.admit_lock_bytes(PUBLIC_REQUEST_BOUNDS.max_lock_bytes + 1)
        assert raised.value.reason_code == "lock_too_large"
        assert raised.value.limit == PUBLIC_REQUEST_BOUNDS.max_lock_bytes

    def test_too_many_lock_records_are_refused(self) -> None:
        """A lock that declares more than the parser will read."""
        with pytest.raises(PublicRequestBoundError) as raised:
            PUBLIC_REQUEST_BOUNDS.admit_lock_records(5_001)
        assert raised.value.reason_code == "lock_records_exceeded"

    def test_too_many_scoped_packages_are_refused(self) -> None:
        """A monorepo is a refusal, not a slow answer."""
        with pytest.raises(PublicRequestBoundError) as raised:
            PUBLIC_REQUEST_BOUNDS.admit_scoped_packages(1_001)
        assert raised.value.reason_code == "scoped_packages_exceeded"

    def test_too_many_rows_read_are_refused(self) -> None:
        """The capacity bound, separate from the response bound."""
        with pytest.raises(PublicRequestBoundError) as raised:
            PUBLIC_REQUEST_BOUNDS.admit_rows_read(5_001)
        assert raised.value.reason_code == "index_rows_exceeded"

    def test_too_many_findings_are_refused(self) -> None:
        """The response bound, separate from the capacity bound."""
        with pytest.raises(PublicRequestBoundError) as raised:
            PUBLIC_REQUEST_BOUNDS.admit_findings(321)
        assert raised.value.reason_code == "findings_exceeded"
        assert raised.value.observed == 321

    def test_a_request_exactly_at_a_bound_is_admitted(self) -> None:
        """A bound is a ceiling, not a target to stay under."""
        PUBLIC_REQUEST_BOUNDS.admit_findings(PUBLIC_REQUEST_BOUNDS.max_findings_emitted)
        PUBLIC_REQUEST_BOUNDS.admit_rows_read(PUBLIC_REQUEST_BOUNDS.max_index_rows_read)
        PUBLIC_REQUEST_BOUNDS.admit_scoped_packages(
            PUBLIC_REQUEST_BOUNDS.max_scoped_packages
        )


class TestTheAuthorityEnforcesTheReadBounds:
    """Where rows are actually read, refusal must happen instead of a short answer."""

    def test_reading_past_the_row_bound_refuses_rather_than_returning_what_fits(
        self,
    ) -> None:
        """The whole point: 3 rows under a bound of 2 is an error, not 2 rows."""
        bounds = replace(
            PUBLIC_REQUEST_BOUNDS, max_index_rows_read=2, max_findings_emitted=2
        )
        authority = _authority(_rows("requests", 3), bounds)
        request = build_dependency_evidence_request(
            admit_public_dependency_request("requests==1.0.0")
        )
        with pytest.raises(PublicRequestBoundError) as raised:
            authority.load(request)
        assert raised.value.reason_code == "index_rows_exceeded"
        assert raised.value.observed == 3

    def test_a_request_within_the_row_bound_is_answered_whole(self) -> None:
        """The same request under a bound that fits returns every row."""
        bounds = replace(
            PUBLIC_REQUEST_BOUNDS, max_index_rows_read=3, max_findings_emitted=3
        )
        authority = _authority(_rows("requests", 3), bounds)
        request = build_dependency_evidence_request(
            admit_public_dependency_request("requests==1.0.0")
        )
        assert len(authority.load(request).ghsa_vulnerabilities) == 3

    def test_the_package_bound_refuses_before_any_query_runs(self) -> None:
        """The cheapest point at which the request is already known to be too large.

        Asserted by counting queries rather than by trusting the ordering in the source:
        a bound checked after the queries would still raise, and would still have spent
        the capacity it exists to protect.
        """
        bounds = replace(PUBLIC_REQUEST_BOUNDS, max_scoped_packages=1)
        store = _CountingStore(
            InMemoryCorrelationIndexStore(
                built_at=_BUILT_AT,
                ghsa=_rows("requests", 1) + _rows("urllib3", 1),
                nvd=(),
                watermarks=_WATERMARKS,
            )
        )
        authority = CorrelationIndexThreatEvidenceAuthority(
            store=store, snapshots=_snapshots(), bounds=bounds
        )
        scope = PublicThreatEvidenceScope(
            source_execution_id="public-repository-evidence:v1@sha256:" + ("e" * 64),
            source_evidence_sha256="e" * 64,
            dependencies=(
                PublicThreatDependencyScope(
                    package_name="requests",
                    version="1.0.0",
                    purl="pkg:pypi/requests@1.0.0",
                    source_record_indexes=(0,),
                ),
                PublicThreatDependencyScope(
                    package_name="urllib3",
                    version="1.0.0",
                    purl="pkg:pypi/urllib3@1.0.0",
                    source_record_indexes=(1,),
                ),
            ),
        )
        with pytest.raises(PublicRequestBoundError) as raised:
            authority.load(PublicThreatEvidenceRequest(scope=scope))
        assert raised.value.reason_code == "scoped_packages_exceeded"
        assert store.queries == 0
