"""Application ports for NVD Silver infrastructure boundaries."""

from typing import Protocol

from opslens.transformation.nvd.application.persistence_models import (
    NvdSilverStoredCompletionV1,
)
from opslens.transformation.nvd.completion.manifest import (
    NvdSilverCompletionArtifactV1,
    NvdSilverStoredObjectV1,
)
from opslens.transformation.nvd.provenance.models import (
    NvdBronzeObjectPayloadV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverParquetArtifactV1,
)


class NvdBronzeObjectVersionReader(Protocol):
    """Read one exact immutable NVD Bronze object version."""

    def get(
        self,
        *,
        key: str,
        version_id: str,
    ) -> NvdBronzeObjectPayloadV1:
        """Return exact bytes for one key and VersionId."""
        ...


class NvdSilverParquetRepository(Protocol):
    """Persist one deterministic NVD Silver Parquet artifact."""

    def put_if_absent(
        self,
        *,
        key: str,
        artifact: NvdSilverParquetArtifactV1,
    ) -> NvdSilverStoredObjectV1:
        """Create one immutable Silver object and return exact persisted evidence."""
        ...


class NvdSilverParquetReplayVerifier(Protocol):
    """Verify an existing deterministic Silver Parquet object exactly."""

    def verify_current(
        self,
        *,
        key: str,
        artifact: NvdSilverParquetArtifactV1,
    ) -> NvdSilverStoredObjectV1:
        """Return exact persisted evidence only when current S3 bytes match."""
        ...


class NvdSilverCompletionRepository(Protocol):
    """Persist one deterministic NVD Silver COMPLETE manifest."""

    def put_if_absent(
        self,
        *,
        artifact: NvdSilverCompletionArtifactV1,
    ) -> NvdSilverStoredCompletionV1:
        """Create COMPLETE and return its exact persisted version evidence."""
        ...


class NvdSilverCompletionReplayVerifier(Protocol):
    """Verify one pre-existing COMPLETE manifest exactly."""

    def verify_current(
        self,
        *,
        artifact: NvdSilverCompletionArtifactV1,
    ) -> NvdSilverStoredCompletionV1:
        """Return persisted evidence only when exact manifest bytes match."""
        ...
