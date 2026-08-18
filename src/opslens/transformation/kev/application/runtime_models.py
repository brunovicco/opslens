"""Application models for the CISA KEV Silver runtime flow."""

from dataclasses import dataclass
from enum import StrEnum

from opslens.ingestion.kev.domain.models import KevCatalogSnapshot


class KevSilverRepositoryWriteStatus(StrEnum):
    """Describe the idempotent outcome of a KEV Silver artifact write."""

    CREATED = "created"
    ALREADY_EXISTS = "already_exists"


@dataclass(frozen=True, slots=True)
class KevSilverSourceEvidence:
    """Represent verified Bronze evidence supplied to Silver transformation.

    Attributes:
        snapshot: Semantically verified CISA KEV catalog snapshot.
        bronze_key: Canonical Bronze S3 object key.
        bronze_version_id: Exact immutable S3 object version.
        bronze_etag: Normalized ETag associated with that object version.
    """

    snapshot: KevCatalogSnapshot
    bronze_key: str
    bronze_version_id: str
    bronze_etag: str

    def __post_init__(self) -> None:
        """Validate application-boundary evidence identifiers."""
        if not self.bronze_key.strip():
            raise ValueError("KEV Bronze key cannot be empty.")

        if not self.bronze_version_id.strip():
            raise ValueError("KEV Bronze VersionId cannot be empty.")

        if not self.bronze_etag.strip():
            raise ValueError("KEV Bronze ETag cannot be empty.")


@dataclass(frozen=True, slots=True)
class KevSilverTransformationResult:
    """Describe one deterministic KEV Bronze-to-Silver transformation."""

    bronze_key: str
    bronze_version_id: str
    silver_key: str
    snapshot_date: str
    row_count: int
    size_bytes: int
    schema_version: int
    source_sha256: str
    write_status: KevSilverRepositoryWriteStatus

    def __post_init__(self) -> None:
        """Validate transformation-result invariants."""
        if not self.bronze_key:
            raise ValueError("KEV transformation Bronze key cannot be empty.")

        if not self.bronze_version_id:
            raise ValueError("KEV transformation Bronze VersionId cannot be empty.")

        if not self.silver_key:
            raise ValueError("KEV transformation Silver key cannot be empty.")

        if self.row_count <= 0:
            raise ValueError("KEV transformation row count must be positive.")

        if self.size_bytes <= 0:
            raise ValueError("KEV transformation artifact size must be positive.")

        if self.schema_version <= 0:
            raise ValueError("KEV transformation schema version must be positive.")

        if len(self.source_sha256) != 64:
            raise ValueError("KEV transformation source SHA-256 must contain 64 characters.")
