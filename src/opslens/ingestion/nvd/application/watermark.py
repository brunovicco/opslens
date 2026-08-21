"""Deterministic watermark-candidate contract for NVD incremental ingestion."""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar

from opslens.ingestion.nvd.application.incremental_key_factory import (
    NvdIncrementalKeyFactory,
)
from opslens.ingestion.nvd.application.incremental_manifest import (
    NvdIncrementalManifest,
)
from opslens.ingestion.nvd.application.models import (
    NvdBronzeWriteResult,
)
from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _canonical_utc(value: datetime) -> str:
    """Serialize one timezone-aware timestamp deterministically."""
    timespec = "microseconds" if value.microsecond else "seconds"

    return value.astimezone(UTC).isoformat(timespec=timespec).replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class NvdWatermarkCandidate:
    """Represent one Bronze-complete boundary awaiting Silver completion.

    A candidate is not an authoritative watermark.

    It proves only that one exact incremental Bronze run completed and binds
    the proposed next boundary to the exact immutable COMPLETE manifest.

    Attributes:
        update_id: Deterministic logical incremental-run identity.
        window_start_at: Current committed boundary used for the run.
        window_end_at: Proposed next committed boundary.
        bronze_manifest_key: Deterministic COMPLETE manifest key.
        bronze_manifest_version_id: Exact S3 VersionId of the manifest.
        bronze_manifest_sha256: SHA-256 of the exact manifest bytes.
        total_results: Number of CVE observations declared by the run.
        page_count: Number of persisted API response pages.
    """

    CANDIDATE_VERSION: ClassVar[str] = "1"
    SOURCE: ClassVar[str] = "nvd-cve"
    SOURCE_INTERFACE: ClassVar[str] = "cve-api-2.0"
    STATE: ClassVar[str] = "bronze_complete"

    update_id: str
    window_start_at: datetime
    window_end_at: datetime
    bronze_manifest_key: str
    bronze_manifest_version_id: str
    bronze_manifest_sha256: str
    total_results: int
    page_count: int

    def __post_init__(self) -> None:
        """Validate candidate provenance and normalize boundaries to UTC."""
        if not _SHA256_PATTERN.fullmatch(self.update_id):
            raise ValueError(
                "NVD watermark candidate update id must contain exactly "
                "64 lowercase hexadecimal characters."
            )

        if self.window_start_at.tzinfo is None or self.window_start_at.utcoffset() is None:
            raise ValueError("NVD watermark candidate start timestamp must be timezone-aware.")

        if self.window_end_at.tzinfo is None or self.window_end_at.utcoffset() is None:
            raise ValueError("NVD watermark candidate end timestamp must be timezone-aware.")

        start_at = self.window_start_at.astimezone(UTC)
        end_at = self.window_end_at.astimezone(UTC)

        if start_at >= end_at:
            raise ValueError(
                "NVD watermark candidate start timestamp must be before end timestamp."
            )

        object.__setattr__(
            self,
            "window_start_at",
            start_at,
        )
        object.__setattr__(
            self,
            "window_end_at",
            end_at,
        )

        if not self.bronze_manifest_key:
            raise ValueError("NVD watermark candidate manifest key cannot be empty.")

        if not self.bronze_manifest_version_id:
            raise ValueError("NVD watermark candidate manifest VersionId cannot be empty.")

        if not _SHA256_PATTERN.fullmatch(self.bronze_manifest_sha256):
            raise ValueError(
                "NVD watermark candidate manifest SHA-256 must contain "
                "exactly 64 lowercase hexadecimal characters."
            )

        if type(self.total_results) is not int or self.total_results < 0:
            raise ValueError("NVD watermark candidate totalResults must be a non-negative integer.")

        if type(self.page_count) is not int or self.page_count <= 0:
            raise ValueError("NVD watermark candidate page count must be a positive integer.")

    @property
    def canonical_window_start_at(self) -> str:
        """Return canonical UTC lower boundary."""
        return _canonical_utc(self.window_start_at)

    @property
    def canonical_window_end_at(self) -> str:
        """Return canonical UTC proposed watermark boundary."""
        return _canonical_utc(self.window_end_at)


class NvdWatermarkCandidateFactory:
    """Build one candidate from exact COMPLETE Bronze evidence."""

    def build(
        self,
        *,
        window: NvdIncrementalWindow,
        manifest: NvdIncrementalManifest,
        manifest_payload: bytes,
        manifest_key: str,
        manifest_write: NvdBronzeWriteResult,
        key_factory: NvdIncrementalKeyFactory,
    ) -> NvdWatermarkCandidate:
        """Build a Bronze-complete candidate without advancing state.

        Args:
            window: Exact logical incremental query window.
            manifest: COMPLETE Bronze manifest for the window.
            manifest_payload: Canonical exact manifest bytes.
            manifest_key: Persisted deterministic manifest key.
            manifest_write: Exact manifest S3 persistence result.
            key_factory: Deterministic incremental key factory.

        Returns:
            Validated watermark candidate.

        Raises:
            ValueError: If manifest evidence does not belong to the window.
        """
        if not manifest_payload:
            raise ValueError("NVD watermark candidate requires manifest bytes.")

        if manifest.update_id != window.update_id:
            raise ValueError(
                "NVD watermark candidate manifest update id does not match the incremental window."
            )

        if manifest.window_start_at != window.start_at or manifest.window_end_at != window.end_at:
            raise ValueError(
                "NVD watermark candidate manifest boundaries do not match the incremental window."
            )

        expected_manifest_key = key_factory.build_manifest_key(window=window)

        if manifest_key != expected_manifest_key:
            raise ValueError(
                "NVD watermark candidate manifest key does not match the deterministic window key."
            )

        return NvdWatermarkCandidate(
            update_id=window.update_id,
            window_start_at=window.start_at,
            window_end_at=window.end_at,
            bronze_manifest_key=manifest_key,
            bronze_manifest_version_id=(manifest_write.version_id),
            bronze_manifest_sha256=(hashlib.sha256(manifest_payload).hexdigest()),
            total_results=(manifest.total_results),
            page_count=manifest.page_count,
        )


class NvdWatermarkCandidateSerializer:
    """Serialize Bronze-complete candidate evidence deterministically."""

    def serialize(
        self,
        candidate: NvdWatermarkCandidate,
    ) -> bytes:
        """Return canonical candidate JSON bytes."""
        document: dict[str, object] = {
            "bronze_manifest": {
                "key": (candidate.bronze_manifest_key),
                "sha256": (candidate.bronze_manifest_sha256),
                "version_id": (candidate.bronze_manifest_version_id),
            },
            "candidate_version": (candidate.CANDIDATE_VERSION),
            "page_count": (candidate.page_count),
            "source": candidate.SOURCE,
            "source_interface": (candidate.SOURCE_INTERFACE),
            "state": candidate.STATE,
            "total_results": (candidate.total_results),
            "update_id": candidate.update_id,
            "window_end_at": (candidate.canonical_window_end_at),
            "window_start_at": (candidate.canonical_window_start_at),
        }

        text = json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )

        return f"{text}\n".encode()


class NvdWatermarkTransitionValidator:
    """Validate continuity from committed state to one candidate."""

    def validate(
        self,
        *,
        committed_through_at: datetime,
        candidate: NvdWatermarkCandidate,
    ) -> None:
        """Require one exact gap-free next incremental candidate.

        This method validates only continuity. It does not commit or mutate
        authoritative watermark state.

        Args:
            committed_through_at: Current authoritative incremental boundary.
            candidate: Bronze-complete proposed next boundary.

        Raises:
            ValueError: If the transition would create a gap or overlap.
        """
        if committed_through_at.tzinfo is None or committed_through_at.utcoffset() is None:
            raise ValueError("NVD committed watermark timestamp must be timezone-aware.")

        committed = committed_through_at.astimezone(UTC)

        if candidate.window_start_at != committed:
            raise ValueError(
                "NVD watermark candidate does not start at the current committed boundary."
            )

        if candidate.window_end_at <= committed:
            raise ValueError(
                "NVD watermark candidate does not advance beyond the current committed boundary."
            )
