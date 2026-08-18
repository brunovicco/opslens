"""Application ports for CISA KEV Silver serialization and persistence."""

from collections.abc import Iterable, Mapping
from typing import BinaryIO, Protocol

from opslens.transformation.kev.application.models import (
    KevSilverWriteResult,
)
from opslens.transformation.kev.application.runtime_models import (
    KevSilverRepositoryWriteStatus,
)
from opslens.transformation.kev.domain.models import SilverKevRecord


class SilverKevRecordWriter(Protocol):
    """Serialize normalized KEV records into one physical artifact."""

    def write(
        self,
        records: Iterable[SilverKevRecord],
        destination: BinaryIO,
    ) -> KevSilverWriteResult:
        """Serialize records into the supplied binary destination."""
        ...


class SilverKevArtifactRepository(Protocol):
    """Persist immutable KEV Silver artifacts."""

    def put_if_absent(
        self,
        *,
        key: str,
        artifact: BinaryIO,
        metadata: Mapping[str, str],
    ) -> KevSilverRepositoryWriteStatus:
        """Persist an artifact only when its deterministic key is absent."""
        ...
