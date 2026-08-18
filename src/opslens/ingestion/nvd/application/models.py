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
