"""Application models for NVD Bootstrap Bronze persistence."""

from dataclasses import dataclass
from enum import StrEnum


class NvdBronzeWriteStatus(StrEnum):
    """Represent the outcome of an immutable NVD Bronze write."""

    CREATED = "created"
    ALREADY_EXISTS = "already_exists"


@dataclass(frozen=True, slots=True)
class NvdBronzeWriteResult:
    """Represent one verified NVD Bronze persistence result.

    Attributes:
        status: Conditional-write outcome.
        version_id: Exact S3 VersionId of the persisted object.
        etag: Optional S3 ETag retained as operational metadata only.
    """

    status: NvdBronzeWriteStatus
    version_id: str
    etag: str | None = None

    def __post_init__(self) -> None:
        """Require exact S3 object-version evidence."""
        if not self.version_id:
            raise ValueError("NVD Bronze write result requires an S3 VersionId.")


@dataclass(frozen=True, slots=True)
class NvdBootstrapIngestionResult:
    """Represent the externally visible result of one NVD bootstrap run.

    Attributes:
        feed_year: NVD yearly feed processed by the run.
        feed_revision: Deterministic immutable source revision.
        source_sha256: NVD SHA-256 of the uncompressed JSON source.
        feed_key: Bronze key containing the exact gzip source artifact.
        meta_key: Bronze key containing the exact META artifact.
        manifest_key: Bronze key containing COMPLETE evidence.
        feed_write: Verified persistence result for the gzip artifact.
        meta_write: Verified persistence result for the META artifact.
        manifest_write: Verified persistence result for the manifest.
    """

    feed_year: int
    feed_revision: str
    source_sha256: str
    feed_key: str
    meta_key: str
    manifest_key: str
    feed_write: NvdBronzeWriteResult
    meta_write: NvdBronzeWriteResult
    manifest_write: NvdBronzeWriteResult
