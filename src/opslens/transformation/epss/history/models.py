"""Models for exact historical EPSS Bronze evidence."""

from dataclasses import dataclass
from datetime import date

from opslens.ingestion.epss.domain.history import EpssModelEra


@dataclass(frozen=True, slots=True)
class HistoricalEpssBronzeObjectPayloadV1:
    """Represent exact bytes read from one explicit S3 object version."""

    key: str
    version_id: str
    raw_bytes: bytes

    def __post_init__(self) -> None:
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
