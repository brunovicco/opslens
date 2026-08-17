"""Application models for CISA KEV catalog ingestion."""

from dataclasses import dataclass
from enum import StrEnum

from opslens.ingestion.kev.domain.models import KevCatalogSnapshot


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
class KevIngestionResult:
    """Represent the externally visible result of a KEV ingestion."""

    status: RepositoryWriteStatus
    s3_key: str
    snapshot: KevCatalogSnapshot
    version_id: str | None = None
    etag: str | None = None

    def to_dict(self) -> dict[str, str | int | None]:
        """Serialize the ingestion result into a Lambda-friendly structure."""
        return {
            "status": self.status.value,
            "snapshot_date": self.snapshot.snapshot_date,
            "catalog_version": self.snapshot.catalog_version,
            "date_released": self.snapshot.date_released.isoformat(),
            "retrieved_at": self.snapshot.retrieved_at.isoformat(),
            "sha256": self.snapshot.sha256,
            "record_count": self.snapshot.record_count,
            "payload_size_bytes": self.snapshot.payload_size_bytes,
            "s3_key": self.s3_key,
            "version_id": self.version_id,
            "etag": self.etag,
        }
