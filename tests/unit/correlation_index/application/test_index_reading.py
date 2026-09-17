"""Tests for reading the live index back.

Every case here is a way a read can be wrong while raising nothing, which is the only
kind of wrong that reaches a caller as an answer. The three shapes:

- a query that stopped at a page boundary and reported what it had;
- an answer assembled from two generations because the pointer moved mid-request;
- a pointer that addresses a key space nothing ever wrote.

The round-trip test is the load-bearing one: it serializes a row with the same function
the projector uses and reads it back with the same function the request path uses. A
round trip that loses a field is how an index stops answering without failing.

```text
truncated page != complete answer
empty key space != no advisories
```
"""

from decimal import Decimal

import pytest

from opslens.correlation_index.application.index_reading import (
    IndexQueryPage,
    IndexReadError,
    LiveIndexGeneration,
    collect_pages,
    ghsa_rows,
    nvd_rows,
    read_pointer,
)
from opslens.correlation_index.application.item_serialization import (
    ghsa_item,
    nvd_item,
    pointer_document,
)
from opslens.correlation_index.domain.index_contract import (
    ProjectedGhsaIndexRow,
    ProjectedNvdIndexRow,
    ProjectedSourceIdentifier,
)

_ADVISORY_DIGEST = "6872a46115d1775d1eac3f5ba734e73ec98a9f78487d178e38e13163c69d7dbf"
_ENTRY_DIGEST = "f086757888580ceef4a1f94c58aacb2c28ae445a18fecdac07c6561ff0519f6d"
_CVE_DIGEST = "3e8f5bff0551f7533a34c40a9a944832e9a01d258049d908e179b24da872431c"
_MANIFEST_DIGEST = "ee5826ced8931fb4e41a6728052d6b4905a3773832ba45cf71e4b47463cf0423"
_OTHER_DIGEST = "1111111111111111e41a6728052d6b4905a3773832ba45cf71e4b47463cf0423"
_GHSA_ID = "GHSA-fq2j-3j99-rx65"
_INDEX_ID = f"opslens-correlation-index:v2@sha256:{_MANIFEST_DIGEST}"
_OTHER_INDEX_ID = f"opslens-correlation-index:v2@sha256:{_OTHER_DIGEST}"
_BUILT_AT = "2026-09-17T03:40:55Z"
_EXPIRES_AT = 1790826055


def _live() -> LiveIndexGeneration:
    """Resolve the generation the way a request does, from a real pointer."""
    return read_pointer(pointer_document(_INDEX_ID, _BUILT_AT))


def _ghsa_row(**overrides: object) -> ProjectedGhsaIndexRow:
    """Build one fully populated GHSA row."""
    fields: dict[str, object] = {
        "package_name_canonical": "tensorflow",
        "observed_advisory_version_id": f"{_GHSA_ID}@sha256:{_ADVISORY_DIGEST}",
        "source_advisory_sha256": _ADVISORY_DIGEST,
        "source_entry_sha256": _ENTRY_DIGEST,
        "ghsa_id": _GHSA_ID,
        "github_cve_id": "CVE-2026-1234",
        "github_identifiers": (
            ProjectedSourceIdentifier(identifier_type="GHSA", value=_GHSA_ID),
            ProjectedSourceIdentifier(identifier_type="CVE", value="CVE-2026-1234"),
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


def _nvd_row() -> ProjectedNvdIndexRow:
    """Build one valid NVD row."""
    return ProjectedNvdIndexRow(
        cve_id="CVE-2026-1234",
        observed_cve_version_id=f"CVE-2026-1234@sha256:{_CVE_DIGEST}",
        source_cve_sha256=_CVE_DIGEST,
        source_identifier="cve@mitre.org",
        published_at="2026-01-02T03:04:05Z",
        last_modified_at="2026-02-03T04:05:06Z",
        vuln_status="Analyzed",
    )


class TestPointer:
    """The pointer decides which key space a request addresses."""

    def test_a_real_pointer_resolves(self) -> None:
        """The document the projector writes is the document a request reads."""
        live = _live()
        assert live.index_id == _INDEX_ID
        assert live.generation == _MANIFEST_DIGEST[:16]
        assert live.built_at == _BUILT_AT

    def test_a_generation_contradicting_its_identity_is_refused(self) -> None:
        """The dangerous case: reads go to a key space that build never wrote.

        Nothing is there, the query succeeds, and the caller is told the package has no
        known vulnerabilities.
        """
        with pytest.raises(IndexReadError, match="never wrote"):
            read_pointer(
                {
                    "built_at": _BUILT_AT,
                    "generation": _OTHER_DIGEST[:16],
                    "index_id": _INDEX_ID,
                }
            )

    def test_an_identity_that_is_not_content_addressed_is_refused(self) -> None:
        """A generation cannot be derived from an identity carrying no digest."""
        with pytest.raises(IndexReadError):
            read_pointer(
                {
                    "built_at": _BUILT_AT,
                    "generation": _MANIFEST_DIGEST[:16],
                    "index_id": "opslens-correlation-index:v1",
                }
            )

    @pytest.mark.parametrize("missing", ["built_at", "generation", "index_id"])
    def test_a_pointer_missing_any_field_is_refused(self, missing: str) -> None:
        """A partially written pointer must not resolve to a partial read."""
        document = dict(pointer_document(_INDEX_ID, _BUILT_AT))
        del document[missing]
        with pytest.raises(IndexReadError, match=missing):
            read_pointer(document)

    def test_the_keys_it_builds_carry_the_generation(self) -> None:
        """A request keys by generation, never by package alone."""
        live = _live()
        assert live.ghsa_key("tensorflow") == f"{_MANIFEST_DIGEST[:16]}#tensorflow"
        assert live.nvd_key("CVE-2026-1234") == f"{_MANIFEST_DIGEST[:16]}#CVE-2026-1234"


class TestPageCollection:
    """The live index puts 973 items in a page and one package carries 1,323."""

    def test_a_single_final_page_collects(self) -> None:
        """The ordinary case: one page, no cursor."""
        page = IndexQueryPage(items=({"a": 1},), last_evaluated_key=None)
        assert collect_pages([page]) == ({"a": 1},)

    def test_an_empty_result_is_one_empty_page(self) -> None:
        """Absence is a page that came back empty, not the absence of a query."""
        page = IndexQueryPage(items=(), last_evaluated_key=None)
        assert collect_pages([page]) == ()

    def test_pages_are_concatenated_in_order(self) -> None:
        """Sort-key order is the answer's order; reassembly must not disturb it."""
        pages = [
            IndexQueryPage(items=({"n": 1}, {"n": 2}), last_evaluated_key={"pk": "x"}),
            IndexQueryPage(items=({"n": 3},), last_evaluated_key=None),
        ]
        assert [item["n"] for item in collect_pages(pages)] == [1, 2, 3]

    def test_a_sequence_ending_with_a_cursor_is_refused(self) -> None:
        """This is exactly what one unpaginated query against tensorflow returns."""
        pages = [IndexQueryPage(items=({"n": 1},), last_evaluated_key={"pk": "x"})]
        with pytest.raises(IndexReadError, match="truncated page"):
            collect_pages(pages)

    def test_a_page_after_the_last_is_refused(self) -> None:
        """A store that says it is done and then returns more is not being followed."""
        pages = [
            IndexQueryPage(items=({"n": 1},), last_evaluated_key=None),
            IndexQueryPage(items=({"n": 2},), last_evaluated_key=None),
        ]
        with pytest.raises(IndexReadError, match="after the store said"):
            collect_pages(pages)

    def test_no_pages_at_all_is_refused(self) -> None:
        """A loop that never ran is not an empty result."""
        with pytest.raises(IndexReadError, match="no pages at all"):
            collect_pages([])


class TestGhsaRoundTrip:
    """Serialize with what the projector uses, read with what the request path uses."""

    def test_every_field_survives(self) -> None:
        """A round trip that loses a field is how an index stops answering."""
        row = _ghsa_row()
        item = ghsa_item(row, index_id=_INDEX_ID, expires_at=_EXPIRES_AT)
        assert ghsa_rows([item], live=_live()) == (row,)

    def test_a_sparse_advisory_survives(self) -> None:
        """Null is a source that carried nothing, not a malformed row (ADR 0085)."""
        row = _ghsa_row(
            github_cve_id=None,
            github_identifiers=(),
            first_patched_version_original=None,
        )
        item = ghsa_item(row, index_id=_INDEX_ID, expires_at=_EXPIRES_AT)
        assert ghsa_rows([item], live=_live()) == (row,)

    def test_a_decimal_source_index_is_read_as_an_integer(self) -> None:
        """DynamoDB hands numbers back as Decimal through the resource API."""
        item = dict(ghsa_item(_ghsa_row(source_index=7), index_id=_INDEX_ID, expires_at=1))
        item["source_index"] = Decimal("7")
        assert ghsa_rows([item], live=_live())[0].source_index == 7

    def test_a_fractional_source_index_is_refused(self) -> None:
        """An index between two entries names no entry."""
        item = dict(ghsa_item(_ghsa_row(), index_id=_INDEX_ID, expires_at=1))
        item["source_index"] = Decimal("0.5")
        with pytest.raises(IndexReadError, match="whole number"):
            ghsa_rows([item], live=_live())

    def test_an_item_from_another_generation_is_refused(self) -> None:
        """The pointer moved mid-request; one answer cannot mix two builds."""
        item = ghsa_item(_ghsa_row(), index_id=_OTHER_INDEX_ID, expires_at=_EXPIRES_AT)
        with pytest.raises(IndexReadError, match="different index generation"):
            ghsa_rows([item], live=_live())

    def test_an_item_carrying_no_identity_is_refused(self) -> None:
        """An item written by something other than the projector is not readable."""
        item = dict(ghsa_item(_ghsa_row(), index_id=_INDEX_ID, expires_at=1))
        del item["index_id"]
        with pytest.raises(IndexReadError, match="different index generation"):
            ghsa_rows([item], live=_live())

    def test_a_missing_nullable_attribute_is_refused(self) -> None:
        """Stored null and absent attribute are different facts."""
        item = dict(ghsa_item(_ghsa_row(), index_id=_INDEX_ID, expires_at=1))
        del item["first_patched_version_original"]
        with pytest.raises(IndexReadError, match="missing attribute"):
            ghsa_rows([item], live=_live())

    def test_identifier_order_survives(self) -> None:
        """GitHub emits identifiers in an order; reordering rewrites the source."""
        item = ghsa_item(_ghsa_row(), index_id=_INDEX_ID, expires_at=_EXPIRES_AT)
        rebuilt = ghsa_rows([item], live=_live())[0]
        assert [entry.identifier_type for entry in rebuilt.github_identifiers] == [
            "GHSA",
            "CVE",
        ]

    def test_a_malformed_identifier_entry_is_refused(self) -> None:
        """A list of the wrong shape must not decode into a shorter list."""
        item = dict(ghsa_item(_ghsa_row(), index_id=_INDEX_ID, expires_at=1))
        item["github_identifiers"] = ["GHSA-not-a-mapping"]
        with pytest.raises(IndexReadError, match="not a mapping"):
            ghsa_rows([item], live=_live())


class TestNvdRoundTrip:
    """The CVE spine decodes even though it cannot become a typed NVD record."""

    def test_every_field_survives(self) -> None:
        """What the index does hold has to come back exactly."""
        row = _nvd_row()
        item = nvd_item(row, index_id=_INDEX_ID, expires_at=_EXPIRES_AT)
        assert nvd_rows([item], live=_live()) == (row,)

    def test_an_item_from_another_generation_is_refused(self) -> None:
        """The same generation rule, on the same reasoning."""
        item = nvd_item(_nvd_row(), index_id=_OTHER_INDEX_ID, expires_at=_EXPIRES_AT)
        with pytest.raises(IndexReadError, match="different index generation"):
            nvd_rows([item], live=_live())
