"""Read the live correlation index out of S3 and DynamoDB, one generation per request.

This adapter does three things and refuses to do a fourth. It resolves the pointer,
follows every query cursor to its end, and hands the raw items to `index_reading`, which
owns every rule about what a valid read looks like. It decides nothing about validity
itself, so there is one place to change when a rule changes.

Two choices here are worth stating because neither is obvious and both cost something.

**Reads are strongly consistent.** The projector writes every row and then the pointer,
so a pointer can only become visible after the rows exist. That ordering protects
nothing against a replica: an eventually-consistent read taken just after a pointer flip
can miss rows that are written but not yet propagated, and a missing advisory reads as a
clean package.

```text
written != readable everywhere
```

A strongly consistent read doubles the capacity a page costs — the measured page is
128.5 units eventually consistent, so 257 strongly consistent — which is a fraction of a
cent at this size. Gate 21 may revisit that when it sizes the request budget; it should
revisit it as a cost decision, not discover it as a default.

**Every query paginates to exhaustion.** There is no page cap here. The live index puts
973 items in a page and one package carries 1,323, so a single-page read is wrong today,
not hypothetically. A guard fails the read if the store stops making progress rather
than looping forever.

The fourth thing: there is no batched NVD read. `batch_get_item` returns
`UnprocessedKeys`, which is the same partial-response trap in a different shape and
deserves its own treatment when Gate 20.4 actually needs many CVEs at once. A single
point lookup is what exists, because that is what is used.
"""

import json
from collections.abc import Mapping, Sequence
from typing import Final, Protocol, cast

from opslens.correlation_index.application.index_reading import (
    IndexQueryPage,
    IndexReadError,
    LiveIndexGeneration,
    collect_pages,
    ghsa_rows,
    nvd_rows,
    read_pointer,
)
from opslens.correlation_index.config import CorrelationIndexCatalog
from opslens.correlation_index.domain.index_contract import (
    CorrelationIndexContractError,
    ProjectedGhsaIndexRow,
    ProjectedNvdIndexRow,
)

# A package cannot legitimately need more pages than this. At the measured 973 items per
# page the bound allows well over 100,000 rows for one package, against a measured
# maximum of 1,323, so reaching it means the store stopped making progress rather than
# that the answer is large.
_MAX_PAGES: Final = 128


class IndexStoreError(RuntimeError):
    """Raised when the index store cannot be read at all, as opposed to read wrongly."""


class PointerObjectBody(Protocol):
    """The streaming body an S3 get returns."""

    def read(self) -> bytes:
        """Return the whole object."""
        ...


class PointerObjectClient(Protocol):
    """Only the read this adapter needs."""

    def get_object(self, *, Bucket: str, Key: str) -> Mapping[str, object]:
        """Return one object."""
        ...


class IndexTable(Protocol):
    """Only the reads this adapter needs from one index table."""

    def query(self, **kwargs: object) -> Mapping[str, object]:
        """Return one page of a partition."""
        ...

    def get_item(self, **kwargs: object) -> Mapping[str, object]:
        """Return one item, or a response carrying none."""
        ...


class DynamoResource(Protocol):
    """Only the table lookup this adapter needs."""

    def Table(self, name: str) -> IndexTable:
        """Return one table by name."""
        ...


class DynamoDbCorrelationIndexStore:
    """Read the live index, resolving its generation once per request."""

    def __init__(
        self,
        *,
        pointer_client: PointerObjectClient,
        tables: DynamoResource,
        catalog: CorrelationIndexCatalog,
    ) -> None:
        """Bind the physical stores without reading anything yet.

        Args:
            pointer_client: Reader for the pointer object.
            tables: Resource-level DynamoDB access.
            catalog: Where the index lives.
        """
        self._pointer_client = pointer_client
        self._tables = tables
        self._catalog = catalog

    def resolve_live_generation(self) -> LiveIndexGeneration:
        """Read the pointer and return the generation this request will address.

        A request resolves this once. Holding it is what stops a pointer landing
        mid-request from assembling one answer out of two builds.

        Returns:
            The live generation.

        Raises:
            IndexStoreError: If the pointer cannot be read or parsed.
            IndexReadError: If the pointer is malformed or internally inconsistent.
        """
        try:
            response = self._pointer_client.get_object(
                Bucket=self._catalog.evidence_bucket, Key=self._catalog.pointer_key
            )
        except Exception as exc:
            raise IndexStoreError(
                f"index pointer {self._catalog.pointer_key} could not be read: {exc}"
            ) from exc

        body = response.get("Body")
        if body is None:
            raise IndexStoreError("index pointer response carried no body")
        payload = cast(PointerObjectBody, body).read()

        try:
            document = cast(object, json.loads(payload.decode("utf-8")))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise IndexStoreError("index pointer is not valid UTF-8 JSON") from exc
        if not isinstance(document, dict):
            raise IndexStoreError("index pointer is not a JSON object")

        return read_pointer(cast(Mapping[str, object], document))

    def ghsa_for_package(
        self, package_name_canonical: str, *, live: LiveIndexGeneration
    ) -> tuple[ProjectedGhsaIndexRow, ...]:
        """Return every advisory occurrence the index holds for one package.

        Args:
            package_name_canonical: The canonical name, as the request path produces it.
            live: The generation this request resolved.

        Returns:
            The rows, in sort-key order.

        Raises:
            IndexStoreError: If the store cannot be queried or stops making progress.
            IndexReadError: If the read is incomplete or crosses generations.
            CorrelationIndexContractError: If the name cannot be keyed.
        """
        table = self._tables.Table(self._catalog.ghsa_table)
        partition = live.ghsa_key(package_name_canonical)
        pages = self._pages(table, partition=partition)
        return ghsa_rows(collect_pages(pages), live=live)

    def nvd_for_cve(
        self, cve_id: str, *, live: LiveIndexGeneration
    ) -> ProjectedNvdIndexRow | None:
        """Return the CVE spine row for one CVE, or `None` when the index holds none.

        `None` means this index has no NVD record for that CVE, which is not the same as
        NVD having none: only 1,642 of the 5,685 CVEs the admitted advisories name are
        present in the corpus at all (ADR 0087, Correction). The caller must declare that
        rather than report an absence.

        ```text
        no NVD record stored != no NVD record exists
        ```

        Args:
            cve_id: The CVE identifier.
            live: The generation this request resolved.

        Returns:
            The row, or `None`.

        Raises:
            IndexStoreError: If the store cannot be read.
            IndexReadError: If the item crosses generations or cannot be decoded.
            CorrelationIndexContractError: If the identifier cannot be keyed.
        """
        table = self._tables.Table(self._catalog.nvd_table)
        try:
            response = table.get_item(
                Key={"pk": live.nvd_key(cve_id)}, ConsistentRead=True
            )
        except CorrelationIndexContractError:
            raise
        except Exception as exc:
            raise IndexStoreError(f"index NVD lookup for {cve_id} failed: {exc}") from exc

        item = response.get("Item")
        if item is None:
            return None
        decoded = nvd_rows([cast(Mapping[str, object], item)], live=live)
        return decoded[0]

    def _pages(self, table: IndexTable, *, partition: str) -> list[IndexQueryPage]:
        """Follow every cursor a partition query returns, to its end.

        Args:
            table: The table to query.
            partition: The partition key value.

        Returns:
            The pages, in the order the store returned them.

        Raises:
            IndexStoreError: If the query fails or stops making progress.
        """
        pages: list[IndexQueryPage] = []
        cursor: Mapping[str, object] | None = None
        seen_cursors: list[Mapping[str, object]] = []

        while True:
            arguments: dict[str, object] = {
                "KeyConditionExpression": "pk = :pk",
                "ExpressionAttributeValues": {":pk": partition},
                "ConsistentRead": True,
            }
            if cursor is not None:
                arguments["ExclusiveStartKey"] = cursor

            try:
                response = table.query(**arguments)
            except Exception as exc:
                raise IndexStoreError(f"index query for {partition} failed: {exc}") from exc

            items = response.get("Items")
            if not isinstance(items, (list, tuple)):
                raise IndexStoreError(f"index query for {partition} returned no item list")
            next_cursor = response.get("LastEvaluatedKey")
            pages.append(
                IndexQueryPage(
                    items=tuple(
                        cast(Mapping[str, object], item)
                        for item in cast(Sequence[object], items)
                    ),
                    last_evaluated_key=(
                        cast(Mapping[str, object], next_cursor)
                        if next_cursor is not None
                        else None
                    ),
                )
            )
            if next_cursor is None:
                return pages

            cursor = cast(Mapping[str, object], next_cursor)
            if cursor in seen_cursors:
                raise IndexStoreError(
                    f"index query for {partition} returned a cursor it already returned; "
                    "the store is not making progress"
                )
            seen_cursors.append(cursor)
            if len(pages) >= _MAX_PAGES:
                raise IndexStoreError(
                    f"index query for {partition} exceeded {_MAX_PAGES} pages; "
                    "a partition this large means the store stopped making progress"
                )


__all__ = [
    "DynamoDbCorrelationIndexStore",
    "DynamoResource",
    "IndexReadError",
    "IndexStoreError",
    "IndexTable",
    "PointerObjectClient",
]
