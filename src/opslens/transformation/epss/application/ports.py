"""Application ports for EPSS Silver serialization."""

from collections.abc import Iterable, Mapping
from typing import BinaryIO, Protocol

from opslens.transformation.epss.application.models import (
    SilverRepositoryWriteStatus,
    SilverWriteResult,
)
from opslens.transformation.epss.domain.models import SilverEpssRecord


class SilverEpssRecordWriter(Protocol):
    """Serialize normalized EPSS records into a physical Silver artifact."""

    def write(
        self,
        records: Iterable[SilverEpssRecord],
        destination: BinaryIO,
    ) -> SilverWriteResult:
        """Serialize records into the supplied binary destination.

        Args:
            records: Normalized EPSS Silver records.
            destination: Writable binary destination.

        Returns:
            Metadata describing the serialized artifact.
        """
        ...


class BronzeEpssSnapshotRepository(Protocol):
    """Read immutable EPSS Bronze snapshot artifacts."""

    def get(self, key: str) -> bytes:
        """Read one Bronze source artifact.

        Args:
            key: Canonical Bronze object key.

        Returns:
            Immutable gzip-compressed EPSS source bytes.
        """
        ...


class SilverEpssArtifactRepository(Protocol):
    """Persist immutable EPSS Silver artifacts."""

    def put_if_absent(
        self,
        *,
        key: str,
        artifact: BinaryIO,
        metadata: Mapping[str, str],
    ) -> SilverRepositoryWriteStatus:
        """Persist one Silver artifact only when the key does not exist.

        Args:
            key: Canonical Silver object key.
            artifact: Binary artifact positioned at the beginning of the stream.
            metadata: Provenance metadata associated with the artifact.

        Returns:
            Whether the artifact was created or already existed.
        """
        ...
