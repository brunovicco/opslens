"""Models for exact NVD Bronze evidence used by Silver transformation."""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class NvdBronzeObjectRole(StrEnum):
    """Role of one exact object referenced by an NVD Bronze manifest."""

    FEED = "feed"
    META = "meta"
    PAGE = "page"


@dataclass(frozen=True, slots=True)
class NvdBronzeObjectPayloadV1:
    """Represent exact bytes fetched from one explicit S3 object version."""

    key: str
    version_id: str
    raw_bytes: bytes

    def __post_init__(self) -> None:
        """Validate the supplied exact-object coordinates."""
        if not self.key.strip():
            raise ValueError("NVD Bronze payload key cannot be empty.")

        if not self.version_id.strip():
            raise ValueError("NVD Bronze payload VersionId cannot be empty.")

        if not self.raw_bytes:
            raise ValueError("NVD Bronze payload bytes cannot be empty.")


@dataclass(frozen=True, slots=True)
class NvdBronzeObjectReferenceV1:
    """Represent one exact object reference proven by a Bronze manifest."""

    role: NvdBronzeObjectRole
    key: str
    version_id: str
    size_bytes: int
    sha256: str

    page_start: int | None
    source_timestamp: str | None

    def __post_init__(self) -> None:
        """Validate exact Bronze object-reference invariants."""
        if not self.key.strip():
            raise ValueError("NVD Bronze object key cannot be empty.")

        if not self.version_id.strip():
            raise ValueError("NVD Bronze object VersionId cannot be empty.")

        if type(self.size_bytes) is not int or self.size_bytes <= 0:
            raise ValueError("NVD Bronze object size_bytes must be positive.")

        if _SHA256_PATTERN.fullmatch(self.sha256) is None:
            raise ValueError("NVD Bronze object sha256 must be a lowercase SHA-256 digest.")

        if self.role is NvdBronzeObjectRole.PAGE:
            if type(self.page_start) is not int or self.page_start < 0:
                raise ValueError("NVD Bronze page requires non-negative page_start.")

            if self.source_timestamp is None or not self.source_timestamp.strip():
                raise ValueError("NVD Bronze page requires source_timestamp.")
        else:
            if self.page_start is not None:
                raise ValueError("Non-page NVD Bronze object cannot have page_start.")

            if self.source_timestamp is not None:
                raise ValueError("Non-page NVD Bronze object cannot have source_timestamp.")


@dataclass(frozen=True, slots=True)
class VerifiedNvdBronzeEvidenceV1:
    """Represent a fully verified COMPLETE NVD Bronze source batch."""

    source_kind: NvdSilverSourceKind
    source_batch_id: str

    manifest_key: str
    manifest_version_id: str
    manifest_sha256: str
    manifest_size_bytes: int

    objects: tuple[NvdBronzeObjectReferenceV1, ...]

    bootstrap_feed_year: int | None
    bootstrap_feed_revision: str | None
    bootstrap_source_observed_at: datetime | None

    incremental_update_id: str | None
    incremental_total_results: int | None
    incremental_window_start_at: datetime | None
    incremental_window_end_at: datetime | None

    def __post_init__(self) -> None:
        """Validate source-kind-specific verified evidence shape."""
        if not self.source_batch_id.strip():
            raise ValueError("Verified NVD Bronze source_batch_id cannot be empty.")

        if not self.manifest_key.strip():
            raise ValueError("Verified NVD Bronze manifest key cannot be empty.")

        if not self.manifest_version_id.strip():
            raise ValueError("Verified NVD Bronze manifest VersionId cannot be empty.")

        if _SHA256_PATTERN.fullmatch(self.manifest_sha256) is None:
            raise ValueError("Verified NVD Bronze manifest SHA-256 is invalid.")

        if type(self.manifest_size_bytes) is not int or self.manifest_size_bytes <= 0:
            raise ValueError("Verified NVD Bronze manifest size must be positive.")

        if not self.objects:
            raise ValueError("Verified NVD Bronze evidence requires objects.")

        keys = [item.key for item in self.objects]

        if len(keys) != len(set(keys)):
            raise ValueError("Verified NVD Bronze evidence contains duplicate keys.")

        if self.source_kind is NvdSilverSourceKind.BOOTSTRAP:
            self._validate_bootstrap()
        elif self.source_kind is NvdSilverSourceKind.INCREMENTAL:
            self._validate_incremental()
        else:
            raise ValueError("Unsupported verified NVD Bronze source kind.")

    def _validate_bootstrap(self) -> None:
        """Validate bootstrap-only evidence."""
        if type(self.bootstrap_feed_year) is not int:
            raise ValueError("Verified bootstrap evidence requires feed year.")

        if self.bootstrap_feed_revision is None or not self.bootstrap_feed_revision.strip():
            raise ValueError("Verified bootstrap evidence requires feed revision.")

        if self.bootstrap_source_observed_at is None:
            raise ValueError("Verified bootstrap evidence requires source timestamp.")

        if self.incremental_update_id is not None:
            raise ValueError("Bootstrap evidence cannot contain update_id.")

        if self.incremental_total_results is not None:
            raise ValueError("Bootstrap evidence cannot contain incremental total_results.")

        if self.incremental_window_start_at is not None:
            raise ValueError("Bootstrap evidence cannot contain incremental window.")

        if self.incremental_window_end_at is not None:
            raise ValueError("Bootstrap evidence cannot contain incremental window.")

        roles = tuple(item.role for item in self.objects)

        if roles != (
            NvdBronzeObjectRole.FEED,
            NvdBronzeObjectRole.META,
        ):
            raise ValueError("Verified bootstrap evidence requires feed then meta.")

    def _validate_incremental(self) -> None:
        """Validate incremental-only evidence."""
        if self.incremental_update_id is None or not self.incremental_update_id.strip():
            raise ValueError("Verified incremental evidence requires update_id.")

        if self.source_batch_id != self.incremental_update_id:
            raise ValueError("Incremental source_batch_id must equal update_id.")

        if type(self.incremental_total_results) is not int or self.incremental_total_results < 0:
            raise ValueError("Verified incremental evidence requires non-negative total_results.")

        if self.incremental_window_start_at is None:
            raise ValueError("Verified incremental evidence requires window start.")

        if self.incremental_window_end_at is None:
            raise ValueError("Verified incremental evidence requires window end.")

        if self.bootstrap_feed_year is not None:
            raise ValueError("Incremental evidence cannot contain feed year.")

        if self.bootstrap_feed_revision is not None:
            raise ValueError("Incremental evidence cannot contain feed revision.")

        if self.bootstrap_source_observed_at is not None:
            raise ValueError("Incremental evidence cannot contain bootstrap timestamp.")

        if any(item.role is not NvdBronzeObjectRole.PAGE for item in self.objects):
            raise ValueError("Incremental evidence may contain only page objects.")

    def object_by_key(
        self,
        key: str,
    ) -> NvdBronzeObjectReferenceV1:
        """Resolve one exact verified object by deterministic key."""
        matches = tuple(item for item in self.objects if item.key == key)

        if len(matches) != 1:
            raise ValueError(f"Verified NVD Bronze object {key!r} was not found.")

        return matches[0]
