"""Application models for EPSS snapshot ingestion."""

from dataclasses import dataclass
from enum import StrEnum

from opslens.ingestion.epss.domain.models import EpssSnapshot


class RepositoryWriteStatus(StrEnum):
    """Represent the outcome of a conditional Bronze repository write."""

    CREATED = "created"
    ALREADY_EXISTS = "already_exists"


@dataclass(frozen=True, slots=True)
class RepositoryWriteResult:
    """Represent the result returned by a Bronze repository adapter."""

    status: RepositoryWriteStatus
    version_id: str | None = None
    etag: str | None = None


@dataclass(frozen=True, slots=True)
class EpssIngestionResult:
    """Represent the externally visible result of an EPSS ingestion."""

    status: RepositoryWriteStatus
    s3_key: str
    snapshot: EpssSnapshot
    version_id: str | None = None
    etag: str | None = None

    def to_dict(self) -> dict[str, str | int | None]:
        """Serialize the ingestion result into a Lambda-friendly structure."""
        return {
            "status": self.status.value,
            "snapshot_date": self.snapshot.snapshot_date,
            "score_timestamp": self.snapshot.score_timestamp.isoformat(),
            "model_version": self.snapshot.model_version,
            "sha256": self.snapshot.sha256,
            "row_count": self.snapshot.row_count,
            "payload_size_bytes": self.snapshot.payload_size_bytes,
            "s3_key": self.s3_key,
            "version_id": self.version_id,
            "etag": self.etag,
        }
