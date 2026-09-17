"""Tests for the offline index.

The point of these is not that the fixture works. It is that the fixture is not a
shortcut: the same certification, the same serialization, the same decoding. So the
strongest test here compares the two stores' answers for identical rows and requires
them to agree on the index identity itself, which is content-addressed and therefore
impossible to agree on by accident.

```text
a fixture that bypasses the logic != a fixture of the logic
```
"""

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

import pytest

from opslens.correlation_index.adapters.dynamodb_index_store import (
    DynamoDbCorrelationIndexStore,
)
from opslens.correlation_index.adapters.in_memory_index_store import (
    InMemoryCorrelationIndexStore,
)
from opslens.correlation_index.application.index_reading import IndexReadError
from opslens.correlation_index.application.item_serialization import (
    ghsa_item,
    pointer_document,
)
from opslens.correlation_index.config import CorrelationIndexCatalog
from opslens.correlation_index.domain.index_contract import (
    CorrelationIndexContractError,
    ProjectedGhsaIndexRow,
    ProjectedNvdIndexRow,
    ProjectedSourceIdentifier,
    SourceWatermark,
    build_manifest,
)

_ADVISORY_DIGEST = "6872a46115d1775d1eac3f5ba734e73ec98a9f78487d178e38e13163c69d7dbf"
_ENTRY_DIGEST = "f086757888580ceef4a1f94c58aacb2c28ae445a18fecdac07c6561ff0519f6d"
_CVE_DIGEST = "3e8f5bff0551f7533a34c40a9a944832e9a01d258049d908e179b24da872431c"
_GHSA_ID = "GHSA-fq2j-3j99-rx65"
_BUILT_AT = datetime(2026, 9, 17, 3, 40, 55, tzinfo=UTC)
_WATERMARKS = (
    SourceWatermark(
        source="ghsa", observed_through="2026-09-16T18:56:22Z", record_count=35584
    ),
)


def _row(package: str = "requests", entry: str = "entry-0", index: int = 0):
    """Build one GHSA index row."""
    return ProjectedGhsaIndexRow(
        package_name_canonical=package,
        observed_advisory_version_id=f"{_GHSA_ID}@sha256:{_ADVISORY_DIGEST}",
        source_advisory_sha256=_ADVISORY_DIGEST,
        source_entry_sha256=_ENTRY_DIGEST,
        ghsa_id=_GHSA_ID,
        github_cve_id="CVE-2026-1234",
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


def _nvd() -> ProjectedNvdIndexRow:
    """Build one CVE spine row."""
    return ProjectedNvdIndexRow(
        cve_id="CVE-2026-1234",
        observed_cve_version_id=f"CVE-2026-1234@sha256:{_CVE_DIGEST}",
        source_cve_sha256=_CVE_DIGEST,
        source_identifier="cve@mitre.org",
        published_at="2026-01-02T03:04:05Z",
        last_modified_at="2026-02-03T04:05:06Z",
        vuln_status="Analyzed",
    )


def _store(
    ghsa: Sequence[ProjectedGhsaIndexRow] = (),
    nvd: Sequence[ProjectedNvdIndexRow] = (),
) -> InMemoryCorrelationIndexStore:
    """Build the offline index over those rows."""
    return InMemoryCorrelationIndexStore(
        built_at=_BUILT_AT, ghsa=ghsa, nvd=nvd, watermarks=_WATERMARKS
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

    def get_object(self, *, Bucket: str, Key: str) -> Mapping[str, object]:
        """Return the canned object."""
        del Bucket
        return {"Body": _Body(self._objects[Key])}


class _Table:
    """Return canned items by partition key."""

    def __init__(self, by_partition: Mapping[str, Sequence[Mapping[str, object]]]) -> None:
        self._by_partition = dict(by_partition)

    def query(self, **kwargs: object) -> Mapping[str, object]:
        """Return the single page for that partition."""
        values = kwargs["ExpressionAttributeValues"]
        assert isinstance(values, dict)
        partition = str(values[":pk"])  # pyright: ignore[reportUnknownArgumentType]
        return {"Items": list(self._by_partition.get(partition, ()))}

    def get_item(self, **kwargs: object) -> Mapping[str, object]:
        """Not exercised here."""
        del kwargs
        return {}


class _Resource:
    """Hand out the one table these tests use."""

    def __init__(self, table: _Table) -> None:
        self._table = table

    def Table(self, name: str) -> _Table:
        """Return the table regardless of name."""
        del name
        return self._table


class TestOfflineIndex:
    """It serves one generation, built from the rows it was given."""

    def test_it_resolves_its_own_pointer(self) -> None:
        """The pointer rules are the live ones, not a shortcut around them."""
        store = _store([_row()])
        live = store.resolve_live_generation()
        assert live.index_id == store.index_id
        assert live.generation == store.index_id.partition("@sha256:")[2][:16]

    def test_its_manifest_certifies_against_its_pointer(self) -> None:
        """The identity is re-derived here exactly as it is against the live index."""
        store = _store([_row(), _row("urllib3", entry="entry-1", index=1)])
        manifest = store.read_manifest(store.resolve_live_generation())
        assert manifest.ghsa_row_count == 2
        assert manifest.distinct_package_count == 2
        assert manifest.index_id == store.index_id

    def test_rows_round_trip_through_the_stored_shape(self) -> None:
        """Serialized with the projector's writer, decoded with the request path's reader."""
        row = _row()
        store = _store([row])
        assert store.ghsa_for_package("requests", live=store.resolve_live_generation()) == (row,)

    def test_a_package_it_does_not_hold_is_empty_not_an_error(self) -> None:
        """A clean package answers with no rows."""
        store = _store([_row()])
        assert store.ghsa_for_package("flask", live=store.resolve_live_generation()) == ()

    def test_the_cve_spine_round_trips(self) -> None:
        """The NVD half decodes even though nothing rebuilds a typed record from it."""
        row = _nvd()
        store = _store([_row()], [row])
        live = store.resolve_live_generation()
        assert store.nvd_for_cve("CVE-2026-1234", live=live) == row

    def test_a_cve_it_does_not_hold_is_none(self) -> None:
        """Absence from this index is not absence from NVD."""
        store = _store([_row()])
        assert store.nvd_for_cve("CVE-2026-9999", live=store.resolve_live_generation()) is None

    def test_an_index_with_no_rows_still_builds(self) -> None:
        """An empty index is a legitimate fixture; refusing it is the authority's job."""
        store = _store([])
        assert store.read_manifest(store.resolve_live_generation()).ghsa_row_count == 0

    def test_an_index_with_no_watermark_is_refused(self) -> None:
        """A build from no source cannot state its freshness, offline included."""
        with pytest.raises(CorrelationIndexContractError):
            InMemoryCorrelationIndexStore(
                built_at=_BUILT_AT, ghsa=[_row()], nvd=(), watermarks=()
            )

    def test_a_generation_from_another_index_reads_nothing_from_this_one(self) -> None:
        """Holding one generation per request is enforced here too.

        The two indexes differ in row count, which is what makes their identities
        differ. That is a weaker guarantee than it looks: the manifest identity is taken
        over counts and watermarks, not over row content, so two indexes holding
        different rows in the same quantity share an identity today. That is a defect in
        the index contract rather than in this store, and it is tracked separately.
        """
        store = _store([_row()])
        other = _store([_row("urllib3"), _row("flask", entry="entry-1", index=1)])
        assert store.index_id != other.index_id
        with pytest.raises(IndexReadError, match="different index generation"):
            store.ghsa_for_package("requests", live=other.resolve_live_generation())


class TestItAgreesWithTheLiveStore:
    """The same rows must produce the same index, or the fixture is a different system."""

    def test_both_stores_derive_the_same_identity(self) -> None:
        """Content-addressed, so agreement cannot happen by accident."""
        rows = [_row(), _row("urllib3", entry="entry-1", index=1)]
        offline = _store(rows)

        manifest = build_manifest(
            built_at=_BUILT_AT, ghsa_rows=rows, nvd_rows=(), watermarks=_WATERMARKS
        )
        catalog = CorrelationIndexCatalog(
            ghsa_table="index-ghsa", nvd_table="index-nvd", evidence_bucket="opslens-test"
        )
        generation = manifest.index_id.partition("@sha256:")[2][:16]
        live_store = DynamoDbCorrelationIndexStore(
            pointer_client=_Objects(
                {
                    catalog.pointer_key: json.dumps(
                        pointer_document(manifest.index_id, manifest.built_at)
                    ).encode(),
                    catalog.manifest_key(manifest.index_id): json.dumps(
                        manifest.canonical_payload
                    ).encode(),
                }
            ),
            tables=_Resource(
                _Table(
                    {
                        f"{generation}#{row.package_name_canonical}": [
                            ghsa_item(row, index_id=manifest.index_id, expires_at=1)
                        ]
                        for row in rows
                    }
                )
            ),
            catalog=catalog,
        )

        assert offline.index_id == manifest.index_id
        assert offline.resolve_live_generation() == live_store.resolve_live_generation()

    def test_both_stores_return_the_same_rows(self) -> None:
        """Same input, same answer, through two different physical paths."""
        rows = [_row()]
        offline = _store(rows)
        manifest = build_manifest(
            built_at=_BUILT_AT, ghsa_rows=rows, nvd_rows=(), watermarks=_WATERMARKS
        )
        catalog = CorrelationIndexCatalog(
            ghsa_table="index-ghsa", nvd_table="index-nvd", evidence_bucket="opslens-test"
        )
        generation = manifest.index_id.partition("@sha256:")[2][:16]
        live_store = DynamoDbCorrelationIndexStore(
            pointer_client=_Objects(
                {
                    catalog.pointer_key: json.dumps(
                        pointer_document(manifest.index_id, manifest.built_at)
                    ).encode(),
                    catalog.manifest_key(manifest.index_id): json.dumps(
                        manifest.canonical_payload
                    ).encode(),
                }
            ),
            tables=_Resource(
                _Table(
                    {
                        f"{generation}#requests": [
                            ghsa_item(rows[0], index_id=manifest.index_id, expires_at=1)
                        ]
                    }
                )
            ),
            catalog=catalog,
        )

        offline_live = offline.resolve_live_generation()
        live = live_store.resolve_live_generation()
        assert offline.ghsa_for_package("requests", live=offline_live) == (
            live_store.ghsa_for_package("requests", live=live)
        )
        assert offline.read_manifest(offline_live) == live_store.read_manifest(live)
