"""Answer the threat-evidence port from the correlation index, and say what answered.

This is the first `PublicThreatEvidenceAuthority` that reads real data at request time.
It is deliberately narrow: three things it does, and two it refuses to do.

**It resolves the generation once.** The pointer is read at the start of a load and held
for that load. A build landing mid-request cannot make one answer out of two indexes,
and the generation is carried out with the evidence so the response can name what
answered it rather than what is live when the response is written.

```text
the index that answered != the index that is live now
```

**It refuses an index that cannot be certified.** A pointer to a generation whose rows
were never written, or have expired under the retirement TTL, answers every query with
nothing — and nothing reads as a clean repository. So the manifest is read and re-derives
its own content-addressed identity, and a manifest reporting no GHSA rows fails the load.
An empty answer from this authority means the packages are clean, not that the index is.

```text
empty key space != no advisories
```

**It returns no NVD records.** ADR 0089: `NvdCveCoreRecord` requires the complete
canonical CVE body, the index holds the digest, and the body exists nowhere per CVE. The
tuple is empty and the response envelope declares NVD as not covered. That declaration is
the load-bearing half, because absence was already the majority case — only 1,642 of the
5,685 CVEs the admitted advisories name are in the corpus at all.

```text
no NVD record stored != no NVD record exists
```

**It loads no snapshots of its own.** KEV and EPSS arrive already loaded and already
digest-verified, held in one frozen set built at worker start. That is what "once per
worker" means here, expressed as a value rather than a cache: a cache raises questions
about invalidation and staleness that a value built at composition time does not. The
snapshots do age over a warm worker's lifetime, and the provenance the evidence carries
states their dates, so the age is declared rather than hidden.

**It performs no correlation.** Gate 20.3 wires `evaluate_pypi_correlation` to what this
returns. This module loads evidence and nothing else.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from opslens.correlation.adapters.ghsa import GhsaPyPIVulnerabilityEvidence
from opslens.correlation_index.adapters.dynamodb_index_store import (
    DynamoDbCorrelationIndexStore,
)
from opslens.correlation_index.application.evidence_rebuild import rebuild_ghsa_evidence
from opslens.correlation_index.application.index_reading import LiveIndexGeneration
from opslens.correlation_index.domain.index_contract import CorrelationIndexManifest
from opslens.ingestion.epss.domain.history import HistoricalEpssSnapshot
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.public_analysis.application.threat_evidence_authority import (
    PublicRepositoryThreatEvidence,
    PublicThreatEvidenceRequest,
    SupportedEpssSnapshot,
)
from opslens.public_analysis.domain import PublicAnalysisValidationError


class CorrelationIndexAuthorityError(RuntimeError):
    """Raised when the index cannot be certified as an authority to answer from."""


@dataclass(frozen=True, slots=True)
class ThreatSnapshotSet:
    """The complete snapshots one worker holds for its lifetime.

    Built once at worker start from the exact readers, which verify their own digests.
    Held as a value rather than behind a cache: a value has no invalidation question, and
    its age is stated in the provenance every response carries.

    Attributes:
        kev: The complete KEV catalogue snapshot.
        epss: The complete EPSS snapshot.
    """

    kev: KevCatalogSnapshot
    epss: SupportedEpssSnapshot

    def __post_init__(self) -> None:
        """Reject a set that is not two complete typed snapshots.

        Raises:
            PublicAnalysisValidationError: If either snapshot is the wrong type.
        """
        if type(self.kev) is not KevCatalogSnapshot:
            raise PublicAnalysisValidationError(
                "worker threat snapshots require one complete typed KEV snapshot"
            )
        if type(self.epss) not in {EpssSnapshot, HistoricalEpssSnapshot}:
            raise PublicAnalysisValidationError(
                "worker threat snapshots require one complete supported EPSS snapshot"
            )


@dataclass(frozen=True, slots=True)
class IndexBackedThreatEvidence:
    """Evidence, plus the index that produced it.

    `PublicRepositoryThreatEvidence` has no room for the index identity, and the Gate
    20.4 envelope needs it: a response that cannot name the index that answered cannot
    state how old its answer is. So the port's return value is carried alongside the
    generation and manifest rather than inside them.

    Attributes:
        evidence: What the port returns.
        live: The generation this load resolved and read.
        manifest: That generation's certified manifest.
    """

    evidence: PublicRepositoryThreatEvidence
    live: LiveIndexGeneration
    manifest: CorrelationIndexManifest


class CorrelationIndexThreatEvidenceAuthority:
    """Load scoped GHSA evidence from the live correlation index."""

    def __init__(
        self,
        *,
        store: DynamoDbCorrelationIndexStore,
        snapshots: ThreatSnapshotSet,
    ) -> None:
        """Bind the index store and the worker's snapshots.

        Args:
            store: Read access to the live index.
            snapshots: The complete snapshots this worker holds.
        """
        self._store = store
        self._snapshots = snapshots

    def load(self, request: PublicThreatEvidenceRequest) -> PublicRepositoryThreatEvidence:
        """Return evidence bound to the exact request.

        Args:
            request: The bounded authority request.

        Returns:
            Evidence for exactly that request.

        Raises:
            CorrelationIndexAuthorityError: If the index cannot be certified.
            IndexStoreError: If the store cannot be read.
            IndexReadError: If a read is incomplete or crosses generations.
        """
        return self.load_with_provenance(request).evidence

    def load_with_provenance(
        self, request: PublicThreatEvidenceRequest
    ) -> IndexBackedThreatEvidence:
        """Load evidence and carry out the index identity that produced it.

        Args:
            request: The bounded authority request.

        Returns:
            The evidence, the generation read, and that generation's manifest.

        Raises:
            CorrelationIndexAuthorityError: If the index cannot be certified.
            IndexStoreError: If the store cannot be read.
            IndexReadError: If a read is incomplete or crosses generations.
        """
        live = self._store.resolve_live_generation()
        manifest = self._store.read_manifest(live)
        if manifest.ghsa_row_count == 0:
            raise CorrelationIndexAuthorityError(
                "the live index holds no GHSA rows; every query would answer nothing "
                "and nothing would read as a clean repository"
            )

        vulnerabilities = self._ghsa(request.scope.query_package_names, live=live)
        evidence = PublicRepositoryThreatEvidence(
            request=request,
            ghsa_vulnerabilities=vulnerabilities,
            nvd_records=(),
            kev_snapshot=self._snapshots.kev,
            epss_snapshot=self._snapshots.epss,
        )
        return IndexBackedThreatEvidence(evidence=evidence, live=live, manifest=manifest)

    def _ghsa(
        self, package_names: Sequence[str], *, live: LiveIndexGeneration
    ) -> tuple[GhsaPyPIVulnerabilityEvidence, ...]:
        """Query every scoped package and rebuild the typed evidence.

        One query per package. The index keys by package precisely so this is a bounded
        set of point queries rather than a scan, and the scope already deduplicates
        names. No bound on the total rows is applied here: Gate 21.1 sets that from a
        measured figure and must reject rather than trim.

        Args:
            package_names: The unique canonical names the scope asks about.
            live: The generation this load resolved.

        Returns:
            The rebuilt evidence, in package order then stored order.

        Raises:
            IndexStoreError: If the store cannot be read.
            IndexReadError: If a read is incomplete or crosses generations.
        """
        rebuilt: list[GhsaPyPIVulnerabilityEvidence] = []
        for name in package_names:
            for row in self._store.ghsa_for_package(name, live=live):
                rebuilt.append(rebuild_ghsa_evidence(row))
        return tuple(rebuilt)


__all__ = [
    "CorrelationIndexAuthorityError",
    "CorrelationIndexThreatEvidenceAuthority",
    "IndexBackedThreatEvidence",
    "ThreatSnapshotSet",
]
