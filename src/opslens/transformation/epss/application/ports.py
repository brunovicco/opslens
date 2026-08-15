"""Application ports for EPSS Silver serialization."""

from collections.abc import Iterable
from typing import BinaryIO, Protocol

from opslens.transformation.epss.application.models import SilverWriteResult
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
