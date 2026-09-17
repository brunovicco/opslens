"""Tests for the first threat authority that reads real data at request time.

The cases worth having are the ones where a wrong answer looks like a right one. An
authority that returns no advisories is indistinguishable, to everything downstream,
from a repository with none — so the tests that matter are the ones proving the
authority refuses to reach that state by accident.

```text
empty key space != no advisories
the index that answered != the index that is live now
```
"""

import gzip
import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import cast

import pytest

from opslens.correlation_index.adapters.dynamodb_index_store import (
    DynamoDbCorrelationIndexStore,
)
from opslens.correlation_index.application.index_reading import IndexReadError
from opslens.correlation_index.application.item_serialization import (
    ghsa_item,
    pointer_document,
)
from opslens.correlation_index.config import CorrelationIndexCatalog
from opslens.correlation_index.domain.index_contract import (
    ProjectedGhsaIndexRow,
    ProjectedSourceIdentifier,
    SourceWatermark,
    build_manifest,
)
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.epss.domain.parser import EpssSnapshotParser
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.public_analysis.adapters.correlation_index_threat_authority import (
    CorrelationIndexAuthorityError,
    CorrelationIndexThreatEvidenceAuthority,
    ThreatSnapshotSet,
)
from opslens.public_analysis.application.threat_evidence_authority import (
    PublicThreatDependencyScope,
    PublicThreatEvidenceRequest,
    PublicThreatEvidenceScope,
)
from opslens.public_analysis.domain import PublicAnalysisValidationError

_ADVISORY_DIGEST = "6872a46115d1775d1eac3f5ba734e73ec98a9f78487d178e38e13163c69d7dbf"
_ENTRY_DIGEST = "f086757888580ceef4a1f94c58aacb2c28ae445a18fecdac07c6561ff0519f6d"
_GHSA_ID = "GHSA-fq2j-3j99-rx65"
_CVE_ID = "CVE-2026-1234"
_BUILT_AT = datetime(2026, 9, 17, 3, 40, 55, tzinfo=UTC)


def _row(
    package: str = "requests", entry: str = "entry-0", index: int = 0
) -> ProjectedGhsaIndexRow:
    """Build one GHSA index row for a package."""
    return ProjectedGhsaIndexRow(
        package_name_canonical=package,
        observed_advisory_version_id=f"{_GHSA_ID}@sha256:{_ADVISORY_DIGEST}",
        source_advisory_sha256=_ADVISORY_DIGEST,
        source_entry_sha256=_ENTRY_DIGEST,
        ghsa_id=_GHSA_ID,
        github_cve_id=_CVE_ID,
        github_identifiers=(
            ProjectedSourceIdentifier(identifier_type="GHSA", value=_GHSA_ID),
        ),
        vulnerability_entry_id=entry,
        source_index=index,
        ecosystem_original="pip",
        package_name_original=package,
        vulnerable_range_original="< 2.32.0",
        first_patched_version_original="2.32.0",
    )


def _manifest(rows: Sequence[ProjectedGhsaIndexRow]):
    """Describe a build of exactly those rows."""
    return build_manifest(
        built_at=_BUILT_AT,
        ghsa_rows=rows,
        nvd_rows=(),
        watermarks=(
            SourceWatermark(
                source="ghsa", observed_through="2026-09-16T18:56:22Z", record_count=35584
            ),
        ),
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


def _snapshots() -> ThreatSnapshotSet:
    """Build the set a worker holds."""
    return ThreatSnapshotSet(kev=_kev(), epss=_epss())


def _request(*packages: str) -> PublicThreatEvidenceRequest:
    """Build one bounded request scoped to those packages."""
    return PublicThreatEvidenceRequest(
        scope=PublicThreatEvidenceScope(
            source_execution_id="public-repository-evidence:v1@sha256:" + ("e" * 64),
            source_evidence_sha256="e" * 64,
            dependencies=tuple(
                PublicThreatDependencyScope(
                    package_name=name,
                    version="1.0.0",
                    purl=f"pkg:pypi/{name}@1.0.0",
                    source_record_indexes=(position,),
                )
                for position, name in enumerate(sorted(packages))
            ),
        )
    )


class _Body:
    """The streaming body an S3 get returns."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        """Return the whole object."""
        return self._payload


class _Objects:
    """Serve canned objects by key."""

    def __init__(self, objects: Mapping[str, bytes]) -> None:
        self._objects = dict(objects)
        self.keys: list[str] = []

    def get_object(self, *, Bucket: str, Key: str) -> Mapping[str, object]:
        """Return the canned object for that key."""
        del Bucket
        self.keys.append(Key)
        if Key not in self._objects:
            raise RuntimeError("NoSuchKey")
        return {"Body": _Body(self._objects[Key])}


class _Table:
    """Return canned items by partition key, one page each."""

    def __init__(self, by_partition: Mapping[str, Sequence[Mapping[str, object]]]) -> None:
        self._by_partition = dict(by_partition)
        self.partitions: list[str] = []

    def query(self, **kwargs: object) -> Mapping[str, object]:
        """Return the single page for that partition."""
        values = kwargs["ExpressionAttributeValues"]
        assert isinstance(values, dict)
        bound = cast(Mapping[str, str], values)
        partition = bound[":pk"]
        self.partitions.append(partition)
        return {"Items": list(self._by_partition.get(partition, ()))}

    def get_item(self, **kwargs: object) -> Mapping[str, object]:
        """Not used by this authority."""
        del kwargs
        return {}


class _Resource:
    """Hand out one table per name."""

    def __init__(self, ghsa: _Table) -> None:
        self._ghsa = ghsa

    def Table(self, name: str) -> _Table:
        """Return the GHSA table; the authority touches no other."""
        assert name == "index-ghsa"
        return self._ghsa


def _catalog() -> CorrelationIndexCatalog:
    """Build one catalog naming test stores."""
    return CorrelationIndexCatalog(
        ghsa_table="index-ghsa",
        nvd_table="index-nvd",
        evidence_bucket="opslens-test-data",
    )


def _authority(
    rows: Sequence[ProjectedGhsaIndexRow],
    *,
    manifest_rows: Sequence[ProjectedGhsaIndexRow] | None = None,
    stored_rows: Sequence[ProjectedGhsaIndexRow] | None = None,
) -> tuple[CorrelationIndexThreatEvidenceAuthority, _Objects, _Table]:
    """Compose the authority over an index built from `rows`.

    Args:
        rows: The rows the manifest and the tables both describe by default.
        manifest_rows: Rows the manifest describes, when it must disagree with the store.
        stored_rows: Rows the tables hold, when they must disagree with the manifest.

    Returns:
        The authority, the object store, and the GHSA table.
    """
    described = list(manifest_rows if manifest_rows is not None else rows)
    held = list(stored_rows if stored_rows is not None else rows)
    manifest = _manifest(described)
    index_id = manifest.index_id
    catalog = _catalog()

    objects = _Objects(
        {
            catalog.pointer_key: json.dumps(
                pointer_document(index_id, manifest.built_at)
            ).encode(),
            catalog.manifest_key(index_id): json.dumps(manifest.stored_document).encode(),
        }
    )
    generation = index_id.partition("@sha256:")[2][:16]
    by_partition: dict[str, list[Mapping[str, object]]] = {}
    for row in held:
        key = f"{generation}#{row.package_name_canonical}"
        by_partition.setdefault(key, []).append(
            ghsa_item(row, index_id=index_id, expires_at=1)
        )
    table = _Table(by_partition)

    store = DynamoDbCorrelationIndexStore(
        pointer_client=objects,
        tables=_Resource(table),
        catalog=catalog,
    )
    authority = CorrelationIndexThreatEvidenceAuthority(
        store=store, snapshots=_snapshots()
    )
    return authority, objects, table


class TestSnapshotSet:
    """The snapshots a worker holds are values, not a cache."""

    def test_two_complete_snapshots_are_accepted(self) -> None:
        """The happy case."""
        assert _snapshots().kev.record_count == 1

    def test_an_untyped_kev_snapshot_is_refused(self) -> None:
        """A worker composed with the wrong object must fail at start, not per request."""
        with pytest.raises(PublicAnalysisValidationError, match="KEV"):
            ThreatSnapshotSet(kev=object(), epss=_epss())  # pyright: ignore[reportArgumentType]

    def test_an_untyped_epss_snapshot_is_refused(self) -> None:
        """The same, for the other half."""
        with pytest.raises(PublicAnalysisValidationError, match="EPSS"):
            ThreatSnapshotSet(kev=_kev(), epss=object())  # pyright: ignore[reportArgumentType]


class TestLoad:
    """What the port returns, and what it refuses to return."""

    def test_it_returns_scoped_evidence(self) -> None:
        """The happy case: one package, one advisory occurrence."""
        rows = [_row("requests")]
        authority, _, table = _authority(rows)
        evidence = authority.load(_request("requests"))
        assert len(evidence.ghsa_vulnerabilities) == 1
        assert evidence.ghsa_vulnerabilities[0].ghsa_id == _GHSA_ID
        assert table.partitions == [
            f"{_manifest(rows).index_id.partition('@sha256:')[2][:16]}#requests"
        ]

    def test_it_queries_every_scoped_package_once(self) -> None:
        """The scope deduplicates names; the authority must not query more than those."""
        rows = [_row("requests"), _row("urllib3", entry="entry-1", index=1)]
        authority, _, table = _authority(rows)
        evidence = authority.load(_request("requests", "urllib3"))
        assert len(evidence.ghsa_vulnerabilities) == 2
        assert len(table.partitions) == 2

    def test_a_scoped_package_with_no_rows_contributes_nothing(self) -> None:
        """A clean package is an empty partition, not a failure."""
        authority, _, _ = _authority([_row("requests")])
        evidence = authority.load(_request("requests", "urllib3"))
        assert len(evidence.ghsa_vulnerabilities) == 1

    def test_it_returns_no_nvd_records(self) -> None:
        """ADR 0089: the index holds the CVE digest, not the body the type requires."""
        authority, _, _ = _authority([_row("requests")])
        assert authority.load(_request("requests")).nvd_records == ()

    def test_it_binds_the_evidence_to_the_request(self) -> None:
        """The port's own binding check must pass without the caller re-asserting it."""
        request = _request("requests")
        authority, _, _ = _authority([_row("requests")])
        assert authority.load(request).request == request

    def test_it_carries_the_worker_snapshots_through(self) -> None:
        """The authority loads no snapshots of its own."""
        snapshots = _snapshots()
        rows = [_row("requests")]
        authority, _, _ = _authority(rows)
        evidence = authority.load(_request("requests"))
        assert evidence.kev_snapshot.sha256 == snapshots.kev.sha256
        assert evidence.epss_snapshot.sha256 == snapshots.epss.sha256


class TestIndexCertification:
    """An authority that cannot certify its index must not answer from it."""

    def test_an_index_with_no_rows_is_refused(self) -> None:
        """A generation whose rows expired answers everything with nothing."""
        authority, _, _ = _authority([], manifest_rows=[], stored_rows=[])
        with pytest.raises(CorrelationIndexAuthorityError, match="no GHSA rows"):
            authority.load(_request("requests"))

    def test_a_manifest_describing_another_build_is_refused(self) -> None:
        """A leftover manifest would state counts belonging to an index nobody read."""
        catalog = _catalog()
        real = _manifest([_row("requests")])
        other = _manifest([_row("urllib3"), _row("requests", entry="entry-9", index=9)])
        objects = _Objects(
            {
                catalog.pointer_key: json.dumps(
                    pointer_document(real.index_id, real.built_at)
                ).encode(),
                catalog.manifest_key(real.index_id): json.dumps(
                    other.stored_document
                ).encode(),
            }
        )
        store = DynamoDbCorrelationIndexStore(
            pointer_client=objects, tables=_Resource(_Table({})), catalog=catalog
        )
        authority = CorrelationIndexThreatEvidenceAuthority(
            store=store, snapshots=_snapshots()
        )
        with pytest.raises(IndexReadError, match="different identity"):
            authority.load(_request("requests"))

    def test_the_manifest_is_read_before_any_query(self) -> None:
        """Certifying after querying would answer from an index and then check it."""
        authority, objects, table = _authority([_row("requests")])
        authority.load(_request("requests"))
        assert objects.keys[0].endswith("current.json")
        assert "manifests/" in objects.keys[1]
        assert len(table.partitions) == 1


class TestProvenance:
    """A response that cannot name the index that answered cannot state its age."""

    def test_it_carries_the_generation_it_read(self) -> None:
        """Not the one that is live when the response is written."""
        rows = [_row("requests")]
        expected = _manifest(rows)
        authority, _, _ = _authority(rows)
        loaded = authority.load_with_provenance(_request("requests"))
        assert loaded.live.index_id == expected.index_id
        assert loaded.manifest.ghsa_row_count == 1
        assert loaded.manifest.built_at == expected.built_at

    def test_load_returns_exactly_what_provenance_wraps(self) -> None:
        """The port and the envelope must not see two different loads."""
        authority, _, _ = _authority([_row("requests")])
        request = _request("requests")
        assert authority.load(request) == authority.load_with_provenance(request).evidence
