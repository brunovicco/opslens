"""An index held in memory, so the offline path runs the real authority.

The demo and the offline tests must work with no network and no AWS. The tempting way to
get that is a second authority returning canned evidence, and it is the wrong way: the
certification the real authority performs would then run only in production, which is
exactly where nobody watches it fail.

So this is a store, not an authority. It builds a real manifest from the rows it holds,
derives its identity the same way the projector does, serializes each row with the same
`ghsa_item` the projector writes, and decodes it back through the same `ghsa_rows` the
request path reads. Every rule the live path enforces is enforced here, over bytes that
took the same shape.

```text
a fixture that bypasses the logic != a fixture of the logic
canned evidence != a canned index
```

Two things it does not imitate, and says so rather than pretending. It never fails: no
throttling, no unreachable store, no cursor that stops advancing — those belong to the
store the DynamoDB adapter talks to, and its own tests cover them. And it holds one page
per partition, because paging is the adapter's concern and this store has no page.
"""

from collections.abc import Mapping, Sequence
from datetime import datetime

from opslens.correlation_index.application.index_reading import (
    LiveIndexGeneration,
    ghsa_rows,
    manifest_from_document,
    nvd_rows,
    read_pointer,
)
from opslens.correlation_index.application.item_serialization import (
    ghsa_item,
    nvd_item,
    pointer_document,
)
from opslens.correlation_index.domain.index_contract import (
    CorrelationIndexManifest,
    ProjectedGhsaIndexRow,
    ProjectedNvdIndexRow,
    SourceWatermark,
    build_manifest,
)

# The fixture index does not expire. A TTL is a property of the store that holds the
# items, and holding one here would make offline runs depend on the clock.
_NO_EXPIRY = 0


class InMemoryCorrelationIndexStore:
    """Serve one generation of an index built from rows given at construction."""

    def __init__(
        self,
        *,
        built_at: datetime,
        ghsa: Sequence[ProjectedGhsaIndexRow],
        nvd: Sequence[ProjectedNvdIndexRow] = (),
        watermarks: Sequence[SourceWatermark],
    ) -> None:
        """Build one complete generation and the pointer naming it.

        Args:
            built_at: When this fixture index is to claim it was built.
            ghsa: The GHSA rows the index holds.
            nvd: The CVE spine rows the index holds.
            watermarks: One watermark per contributing source.

        Raises:
            CorrelationIndexContractError: If the rows cannot describe a build.
        """
        manifest = build_manifest(
            built_at=built_at, ghsa_rows=ghsa, nvd_rows=nvd, watermarks=watermarks
        )
        self._manifest_payload = manifest.canonical_payload
        self._index_id = manifest.index_id
        self._pointer = pointer_document(self._index_id, manifest.built_at)

        self._ghsa: dict[str, list[Mapping[str, object]]] = {}
        for row in ghsa:
            self._ghsa.setdefault(row.package_name_canonical, []).append(
                ghsa_item(row, index_id=self._index_id, expires_at=_NO_EXPIRY)
            )
        self._nvd: dict[str, Mapping[str, object]] = {
            row.cve_id: nvd_item(row, index_id=self._index_id, expires_at=_NO_EXPIRY)
            for row in nvd
        }

    @property
    def index_id(self) -> str:
        """Return the identity this fixture index carries."""
        return self._index_id

    def resolve_live_generation(self) -> LiveIndexGeneration:
        """Resolve the generation through the same pointer rules the live path uses.

        Returns:
            The generation this fixture serves.

        Raises:
            IndexReadError: If the pointer is inconsistent, which would be a defect here.
        """
        return read_pointer(self._pointer)

    def read_manifest(self, live: LiveIndexGeneration) -> CorrelationIndexManifest:
        """Return the manifest, certified against the identity the pointer names.

        Args:
            live: The generation this request resolved.

        Returns:
            The typed manifest.

        Raises:
            IndexReadError: If the manifest describes another build.
        """
        return manifest_from_document(self._manifest_payload, live=live)

    def ghsa_for_package(
        self, package_name_canonical: str, *, live: LiveIndexGeneration
    ) -> tuple[ProjectedGhsaIndexRow, ...]:
        """Return every advisory occurrence held for one package.

        Args:
            package_name_canonical: The canonical name the request asks about.
            live: The generation this request resolved.

        Returns:
            The rows, in insertion order.

        Raises:
            IndexReadError: If an item crosses generations or cannot be decoded.
        """
        return ghsa_rows(self._ghsa.get(package_name_canonical, []), live=live)

    def nvd_for_cve(
        self, cve_id: str, *, live: LiveIndexGeneration
    ) -> ProjectedNvdIndexRow | None:
        """Return the CVE spine row, or `None` when this index holds none for it.

        Args:
            cve_id: The CVE identifier.
            live: The generation this request resolved.

        Returns:
            The row, or `None`.

        Raises:
            IndexReadError: If the item crosses generations or cannot be decoded.
        """
        item = self._nvd.get(cve_id)
        if item is None:
            return None
        return nvd_rows([item], live=live)[0]


__all__ = ["InMemoryCorrelationIndexStore"]
