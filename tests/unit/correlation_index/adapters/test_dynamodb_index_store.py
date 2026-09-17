"""Tests for the physical read of the live index.

The adapter's whole job is to follow cursors and hand raw items to `index_reading`. So
the cases that matter are the ones where following cursors goes wrong: a store that
stops making progress, a store that returns a shape nothing expected, and a pointer that
cannot be turned into a generation.

The consistency choice is asserted rather than assumed. An eventually-consistent read
taken just after a pointer flip can miss rows that are written but not propagated, and a
missing advisory reads as a clean package — so every read here sets `ConsistentRead`,
and a test fails if that is ever quietly dropped.

```text
written != readable everywhere
```
"""

import json
from collections.abc import Mapping, Sequence

import pytest

from opslens.correlation_index.adapters.dynamodb_index_store import (
    DynamoDbCorrelationIndexStore,
    IndexStoreError,
)
from opslens.correlation_index.application.index_reading import IndexReadError
from opslens.correlation_index.application.item_serialization import (
    ghsa_item,
    nvd_item,
    pointer_document,
)
from opslens.correlation_index.config import CorrelationIndexCatalog
from opslens.correlation_index.domain.index_contract import (
    ProjectedGhsaIndexRow,
    ProjectedNvdIndexRow,
    ProjectedSourceIdentifier,
)

_ADVISORY_DIGEST = "6872a46115d1775d1eac3f5ba734e73ec98a9f78487d178e38e13163c69d7dbf"
_ENTRY_DIGEST = "f086757888580ceef4a1f94c58aacb2c28ae445a18fecdac07c6561ff0519f6d"
_CVE_DIGEST = "3e8f5bff0551f7533a34c40a9a944832e9a01d258049d908e179b24da872431c"
_MANIFEST_DIGEST = "ee5826ced8931fb4e41a6728052d6b4905a3773832ba45cf71e4b47463cf0423"
_GHSA_ID = "GHSA-fq2j-3j99-rx65"
_INDEX_ID = f"opslens-correlation-index:v2@sha256:{_MANIFEST_DIGEST}"
_GENERATION = _MANIFEST_DIGEST[:16]
_BUILT_AT = "2026-09-17T03:40:55Z"


class _Body:
    """The streaming body an S3 get returns."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        """Return the whole object."""
        return self._payload


class _PointerClient:
    """One canned pointer object, or one raised failure."""

    def __init__(self, payload: bytes | None = None, error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def get_object(self, *, Bucket: str, Key: str) -> Mapping[str, object]:
        """Return the canned object."""
        self.calls.append((Bucket, Key))
        if self.error is not None:
            raise self.error
        if self.payload is None:
            return {}
        return {"Body": _Body(self.payload)}


class _Table:
    """One table returning canned query pages and one canned item."""

    def __init__(
        self,
        pages: Sequence[Mapping[str, object]] = (),
        item: Mapping[str, object] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._pages = list(pages)
        self._item = item
        self._error = error
        self.query_calls: list[Mapping[str, object]] = []
        self.get_calls: list[Mapping[str, object]] = []

    def query(self, **kwargs: object) -> Mapping[str, object]:
        """Return the next canned page."""
        self.query_calls.append(kwargs)
        if self._error is not None:
            raise self._error
        if not self._pages:
            return {"Items": []}
        return self._pages.pop(0)

    def get_item(self, **kwargs: object) -> Mapping[str, object]:
        """Return the canned item."""
        self.get_calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return {} if self._item is None else {"Item": self._item}


class _Resource:
    """Hand out one table per name."""

    def __init__(self, **tables: _Table) -> None:
        self._tables = tables
        self.requested: list[str] = []

    def Table(self, name: str) -> _Table:
        """Return the table registered for that name."""
        self.requested.append(name)
        return self._tables[name]


def _catalog() -> CorrelationIndexCatalog:
    """Build one catalog naming test stores."""
    return CorrelationIndexCatalog(
        ghsa_table="index-ghsa",
        nvd_table="index-nvd",
        evidence_bucket="opslens-test-data",
    )


def _row(**overrides: object) -> ProjectedGhsaIndexRow:
    """Build one GHSA row."""
    fields: dict[str, object] = {
        "package_name_canonical": "tensorflow",
        "observed_advisory_version_id": f"{_GHSA_ID}@sha256:{_ADVISORY_DIGEST}",
        "source_advisory_sha256": _ADVISORY_DIGEST,
        "source_entry_sha256": _ENTRY_DIGEST,
        "ghsa_id": _GHSA_ID,
        "github_cve_id": "CVE-2026-1234",
        "github_identifiers": (
            ProjectedSourceIdentifier(identifier_type="GHSA", value=_GHSA_ID),
        ),
        "vulnerability_entry_id": "entry-0",
        "source_index": 0,
        "ecosystem_original": "pip",
        "package_name_original": "TensorFlow",
        "vulnerable_range_original": "< 2.11.1",
        "first_patched_version_original": "2.11.1",
    }
    fields.update(overrides)
    return ProjectedGhsaIndexRow(**fields)  # pyright: ignore[reportArgumentType]


def _nvd() -> ProjectedNvdIndexRow:
    """Build one NVD row."""
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
    pointer: _PointerClient | None = None,
    ghsa: _Table | None = None,
    nvd: _Table | None = None,
) -> DynamoDbCorrelationIndexStore:
    """Build the adapter over canned stores."""
    payload = json.dumps(pointer_document(_INDEX_ID, _BUILT_AT)).encode("utf-8")
    return DynamoDbCorrelationIndexStore(
        pointer_client=pointer or _PointerClient(payload),
        tables=_Resource(**{"index-ghsa": ghsa or _Table(), "index-nvd": nvd or _Table()}),
        catalog=_catalog(),
    )


class TestPointerResolution:
    """The pointer decides which key space every later read addresses."""

    def test_it_reads_the_catalogued_location(self) -> None:
        """A request must not discover the pointer; the catalog names it."""
        pointer = _PointerClient(
            json.dumps(pointer_document(_INDEX_ID, _BUILT_AT)).encode("utf-8")
        )
        live = _store(pointer=pointer).resolve_live_generation()
        assert pointer.calls == [("opslens-test-data", "index/correlation/current.json")]
        assert live.generation == _GENERATION

    def test_an_unreadable_pointer_fails_rather_than_defaulting(self) -> None:
        """There is no default generation; not knowing which one is not an answer."""
        pointer = _PointerClient(error=RuntimeError("NoSuchKey"))
        with pytest.raises(IndexStoreError, match="could not be read"):
            _store(pointer=pointer).resolve_live_generation()

    def test_a_pointer_that_is_not_json_fails(self) -> None:
        """Garbage must not decode into a partial generation."""
        with pytest.raises(IndexStoreError, match="valid UTF-8 JSON"):
            _store(pointer=_PointerClient(b"{not json")).resolve_live_generation()

    def test_a_pointer_that_is_not_an_object_fails(self) -> None:
        """A JSON array parses and carries no generation."""
        with pytest.raises(IndexStoreError, match="JSON object"):
            _store(pointer=_PointerClient(b"[]")).resolve_live_generation()

    def test_a_response_with_no_body_fails(self) -> None:
        """An empty response is not an empty pointer."""
        with pytest.raises(IndexStoreError, match="no body"):
            _store(pointer=_PointerClient()).resolve_live_generation()

    def test_an_inconsistent_pointer_is_refused_by_the_contract(self) -> None:
        """The adapter defers validity to index_reading rather than re-deciding it."""
        payload = json.dumps(
            {"built_at": _BUILT_AT, "generation": "0" * 16, "index_id": _INDEX_ID}
        ).encode("utf-8")
        with pytest.raises(IndexReadError):
            _store(pointer=_PointerClient(payload)).resolve_live_generation()


class TestGhsaQuery:
    """973 items fill a page and one package carries 1,323, so paging is the job."""

    def test_it_follows_every_cursor(self) -> None:
        """The case a single unpaginated query gets wrong on the live index."""
        first = _row(vulnerability_entry_id="entry-0", source_index=0)
        second = _row(vulnerability_entry_id="entry-1", source_index=1)
        table = _Table(
            pages=[
                {
                    "Items": [ghsa_item(first, index_id=_INDEX_ID, expires_at=1)],
                    "LastEvaluatedKey": {"pk": f"{_GENERATION}#tensorflow", "sk": "a"},
                },
                {"Items": [ghsa_item(second, index_id=_INDEX_ID, expires_at=1)]},
            ]
        )
        store = _store(ghsa=table)
        live = store.resolve_live_generation()
        assert store.ghsa_for_package("tensorflow", live=live) == (first, second)
        assert len(table.query_calls) == 2
        assert table.query_calls[1]["ExclusiveStartKey"] == {
            "pk": f"{_GENERATION}#tensorflow",
            "sk": "a",
        }

    def test_every_read_is_strongly_consistent(self) -> None:
        """Dropping this silently reintroduces the missing-advisory window."""
        table = _Table(pages=[{"Items": []}])
        store = _store(ghsa=table)
        live = store.resolve_live_generation()
        store.ghsa_for_package("tensorflow", live=live)
        assert table.query_calls[0]["ConsistentRead"] is True

    def test_it_keys_by_generation(self) -> None:
        """A query keyed by package alone would read every generation at once."""
        table = _Table(pages=[{"Items": []}])
        store = _store(ghsa=table)
        live = store.resolve_live_generation()
        store.ghsa_for_package("tensorflow", live=live)
        values = table.query_calls[0]["ExpressionAttributeValues"]
        assert values == {":pk": f"{_GENERATION}#tensorflow"}

    def test_an_empty_partition_is_an_empty_answer(self) -> None:
        """A package with no advisories reads as no rows, not as a failure."""
        store = _store(ghsa=_Table(pages=[{"Items": []}]))
        live = store.resolve_live_generation()
        assert store.ghsa_for_package("requests", live=live) == ()

    def test_a_repeated_cursor_fails_instead_of_looping(self) -> None:
        """A store that stops making progress must not spin a request forever."""
        cursor = {"pk": f"{_GENERATION}#tensorflow", "sk": "a"}
        table = _Table(
            pages=[
                {"Items": [], "LastEvaluatedKey": cursor},
                {"Items": [], "LastEvaluatedKey": cursor},
            ]
        )
        store = _store(ghsa=table)
        live = store.resolve_live_generation()
        with pytest.raises(IndexStoreError, match="not making progress"):
            store.ghsa_for_package("tensorflow", live=live)

    def test_a_response_without_items_fails(self) -> None:
        """A shape nothing expected must not decode as an empty partition."""
        store = _store(ghsa=_Table(pages=[{"Count": 0}]))
        live = store.resolve_live_generation()
        with pytest.raises(IndexStoreError, match="no item list"):
            store.ghsa_for_package("tensorflow", live=live)

    def test_a_query_failure_is_not_an_empty_answer(self) -> None:
        """The store being unreachable is not the package being clean."""
        store = _store(ghsa=_Table(error=RuntimeError("throttled")))
        live = store.resolve_live_generation()
        with pytest.raises(IndexStoreError, match="failed"):
            store.ghsa_for_package("tensorflow", live=live)


class TestNvdLookup:
    """One item per partition by construction, so this is a point lookup."""

    def test_it_returns_the_row(self) -> None:
        """The happy case."""
        row = _nvd()
        table = _Table(item=nvd_item(row, index_id=_INDEX_ID, expires_at=1))
        store = _store(nvd=table)
        live = store.resolve_live_generation()
        assert store.nvd_for_cve("CVE-2026-1234", live=live) == row
        assert table.get_calls[0]["ConsistentRead"] is True
        assert table.get_calls[0]["Key"] == {"pk": f"{_GENERATION}#CVE-2026-1234"}

    def test_a_missing_item_is_none_not_an_error(self) -> None:
        """Seven CVEs in ten are absent from the corpus; that is data, not a fault."""
        store = _store(nvd=_Table(item=None))
        live = store.resolve_live_generation()
        assert store.nvd_for_cve("CVE-2026-9999", live=live) is None

    def test_a_lookup_failure_is_not_an_absence(self) -> None:
        """An unreachable store must not be reported as a CVE nobody knows."""
        store = _store(nvd=_Table(error=RuntimeError("throttled")))
        live = store.resolve_live_generation()
        with pytest.raises(IndexStoreError, match="failed"):
            store.nvd_for_cve("CVE-2026-1234", live=live)
