"""The port the threat authority reads the index through.

It exists so the offline fixture can be the same authority over a different store,
rather than a second authority that behaves like the first. A fixture that reimplements
the logic it stands in for proves nothing about that logic: the certification the
authority performs — re-deriving the manifest identity, refusing an index with no rows,
holding one generation for the whole load — would run in production and be skipped in
every offline run, which is where it is easiest to break unnoticed.

```text
a fixture that bypasses the logic != a fixture of the logic
```

So there is one authority, one set of rules, and two stores.
"""

from typing import Protocol

from opslens.correlation_index.application.index_reading import LiveIndexGeneration
from opslens.correlation_index.domain.index_contract import (
    CorrelationIndexManifest,
    ProjectedGhsaIndexRow,
    ProjectedNvdIndexRow,
)


class CorrelationIndexStore(Protocol):
    """Read access to one live correlation index."""

    def resolve_live_generation(self) -> LiveIndexGeneration:
        """Return the generation a request addresses, resolved once and then held."""
        ...

    def read_manifest(self, live: LiveIndexGeneration) -> CorrelationIndexManifest:
        """Return that generation's manifest, certified against the identity it names."""
        ...

    def ghsa_for_package(
        self, package_name_canonical: str, *, live: LiveIndexGeneration
    ) -> tuple[ProjectedGhsaIndexRow, ...]:
        """Return every advisory occurrence held for one package in that generation."""
        ...

    def nvd_for_cve(
        self, cve_id: str, *, live: LiveIndexGeneration
    ) -> ProjectedNvdIndexRow | None:
        """Return the CVE spine row, or `None` when this index holds none for it."""
        ...


__all__ = ["CorrelationIndexStore"]
