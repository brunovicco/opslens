"""Storage contract for the authoritative NVD incremental watermark."""

import re
from dataclasses import dataclass
from typing import Protocol

from opslens.ingestion.nvd.application.authoritative_watermark import (
    NvdAuthoritativeWatermarkV1,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class NvdAuthoritativeWatermarkStoreError(RuntimeError):
    """Base error for authoritative-watermark persistence."""


class NvdAuthoritativeWatermarkNotFoundError(
    NvdAuthoritativeWatermarkStoreError
):
    """Raised when no authoritative watermark currently exists."""


class NvdAuthoritativeWatermarkAlreadyExistsError(
    NvdAuthoritativeWatermarkStoreError
):
    """Raised when conditional initialization loses a race."""


class NvdAuthoritativeWatermarkPreconditionFailedError(
    NvdAuthoritativeWatermarkStoreError
):
    """Raised when CAS observes a different current ETag."""


class NvdAuthoritativeWatermarkConflictError(
    NvdAuthoritativeWatermarkStoreError
):
    """Raised for an S3 conditional-request concurrency conflict."""


class NvdAuthoritativeWatermarkEvidenceError(
    NvdAuthoritativeWatermarkStoreError
):
    """Raised when persisted watermark evidence is invalid."""


@dataclass(frozen=True, slots=True)
class NvdPersistedAuthoritativeWatermarkV1:
    """Bind logical watermark state to exact S3 persistence identity."""

    watermark: NvdAuthoritativeWatermarkV1
    version_id: str
    etag: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        """Validate persisted-state coordinates."""
        if not self.version_id.strip():
            raise ValueError(
                "Authoritative NVD watermark VersionId cannot be empty."
            )

        if not self.etag.strip():
            raise ValueError(
                "Authoritative NVD watermark ETag cannot be empty."
            )

        if _SHA256_PATTERN.fullmatch(self.sha256) is None:
            raise ValueError(
                "Authoritative NVD watermark SHA-256 must contain "
                "exactly 64 lowercase hexadecimal characters."
            )

        if type(self.size_bytes) is not int or self.size_bytes <= 0:
            raise ValueError(
                "Authoritative NVD watermark size must be positive."
            )


class NvdAuthoritativeWatermarkStoreV1(Protocol):
    """Define storage operations allowed for authoritative state."""

    def load(
        self,
    ) -> NvdPersistedAuthoritativeWatermarkV1:
        """Load the current authoritative watermark."""
        ...

    def initialize(
        self,
        *,
        watermark: NvdAuthoritativeWatermarkV1,
    ) -> NvdPersistedAuthoritativeWatermarkV1:
        """Create initial state only when no current state exists."""
        ...

    def compare_and_swap(
        self,
        *,
        watermark: NvdAuthoritativeWatermarkV1,
        expected_etag: str,
    ) -> NvdPersistedAuthoritativeWatermarkV1:
        """Replace state only when the current ETag still matches."""
        ...
