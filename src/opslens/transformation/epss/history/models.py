"""Models for exact historical EPSS evidence and Silver persistence."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from hashlib import sha256

from opslens.ingestion.epss.domain.history import EpssModelEra


@dataclass(frozen=True, slots=True)
class HistoricalEpssBronzeObjectPayloadV1:
    """Represent exact bytes read from one explicit S3 object version."""

    key: str
    version_id: str
    raw_bytes: bytes

    def __post_init__(self) -> None:
        """Validate the exact immutable object coordinate and payload."""
        if not self.key.strip():
            raise ValueError("Historical EPSS Bronze object key cannot be empty.")
        if not self.version_id.strip():
            raise ValueError("Historical EPSS Bronze VersionId cannot be empty.")
        if not self.raw_bytes:
            raise ValueError("Historical EPSS Bronze object bytes cannot be empty.")


@dataclass(frozen=True, slots=True)
class HistoricalEpssBronzeManifestV1:
    """Represent validated immutable historical EPSS Bronze manifest evidence."""

    snapshot_date: date
    archive_repository: str
    archive_commit: str
    archive_path: str
    archive_git_blob_sha1: str
    model_era: EpssModelEra
    source_metadata_present: bool
    source_object_key: str
    source_object_version_id: str
    source_sha256: str
    compressed_size_bytes: int
    manifest_key: str
    manifest_version_id: str


@dataclass(frozen=True, slots=True)
class HistoricalEpssBronzeEvidenceV1:
    """Bind one exact manifest version to its exact source object version."""

    manifest: HistoricalEpssBronzeManifestV1
    source: HistoricalEpssBronzeObjectPayloadV1


@dataclass(frozen=True, slots=True)
class HistoricalEpssSilverArtifactV1:
    """Represent deterministic Parquet bytes prepared for historical Silver."""

    parquet_bytes: bytes
    row_count: int
    schema_version: int

    def __post_init__(self) -> None:
        """Validate the deterministic Silver artifact envelope."""
        if not self.parquet_bytes:
            raise ValueError("Historical EPSS Silver Parquet bytes cannot be empty.")
        if self.row_count <= 0:
            raise ValueError("Historical EPSS Silver row_count must be positive.")
        if self.schema_version <= 0:
            raise ValueError("Historical EPSS Silver schema_version must be positive.")

    @property
    def size_bytes(self) -> int:
        """Return the exact serialized artifact size."""
        return len(self.parquet_bytes)

    @property
    def parquet_sha256(self) -> str:
        """Return the exact SHA-256 identity of the Parquet bytes."""
        return sha256(self.parquet_bytes).hexdigest()


@dataclass(frozen=True, slots=True)
class HistoricalEpssSilverStoredObjectV1:
    """Represent exact persisted historical Silver object evidence."""

    key: str
    version_id: str
    parquet_sha256: str
    size_bytes: int
    row_count: int
    schema_version: int

    def __post_init__(self) -> None:
        """Validate exact persisted Silver evidence."""
        if not self.key.strip():
            raise ValueError("Historical EPSS Silver object key cannot be empty.")
        if not self.version_id.strip():
            raise ValueError("Historical EPSS Silver VersionId cannot be empty.")
        if len(self.parquet_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.parquet_sha256
        ):
            raise ValueError("Historical EPSS Silver SHA-256 must be lowercase hexadecimal.")
        if self.size_bytes <= 0:
            raise ValueError("Historical EPSS Silver size_bytes must be positive.")
        if self.row_count <= 0:
            raise ValueError("Historical EPSS Silver row_count must be positive.")
        if self.schema_version <= 0:
            raise ValueError("Historical EPSS Silver schema_version must be positive.")


class HistoricalEpssSilverReplayStatus(StrEnum):
    """Describe how deterministic historical Silver persistence completed."""

    CREATED = "created"
    REPLAY_VERIFIED = "replay_verified"


@dataclass(frozen=True, slots=True)
class HistoricalEpssSilverPersistenceResultV1:
    """Bind exact persisted Silver evidence to its replay outcome."""

    stored_object: HistoricalEpssSilverStoredObjectV1
    replay_status: HistoricalEpssSilverReplayStatus
