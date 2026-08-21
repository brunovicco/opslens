"""Deterministic COMPLETE manifest for NVD incremental Bronze runs."""

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar

from opslens.ingestion.nvd.application.incremental_key_factory import (
    NvdIncrementalKeyFactory,
)
from opslens.ingestion.nvd.application.models import (
    NvdBronzeWriteResult,
)
from opslens.ingestion.nvd.domain.api_page import (
    NvdCveApiPagination,
)
from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class NvdIncrementalStoredPage:
    """Describe one exact persisted NVD CVE API page.

    Attributes:
        key: Deterministic Bronze object key.
        version_id: Exact S3 VersionId of the persisted response.
        size_bytes: Exact response byte count.
        sha256: SHA-256 over the exact stored response bytes.
        start_index: Zero-based API pagination offset.
        results_per_page: Number of CVEs returned in this page.
        total_results: Query total declared by NVD.
        source_timestamp: NVD response timestamp preserved as supplied.
    """

    key: str
    version_id: str
    size_bytes: int
    sha256: str
    start_index: int
    results_per_page: int
    total_results: int
    source_timestamp: str

    def __post_init__(self) -> None:
        """Validate immutable page provenance."""
        if not self.key:
            raise ValueError("NVD incremental page key cannot be empty.")

        if not self.version_id:
            raise ValueError("NVD incremental page VersionId cannot be empty.")

        if self.size_bytes <= 0:
            raise ValueError("NVD incremental page size must be positive.")

        if not _SHA256_PATTERN.fullmatch(self.sha256):
            raise ValueError(
                "NVD incremental page SHA-256 must contain exactly "
                "64 lowercase hexadecimal characters."
            )

        if type(self.start_index) is not int or self.start_index < 0:
            raise ValueError("NVD incremental page start index must be a non-negative integer.")

        if type(self.results_per_page) is not int or self.results_per_page < 0:
            raise ValueError("NVD incremental resultsPerPage must be a non-negative integer.")

        if type(self.total_results) is not int or self.total_results < 0:
            raise ValueError("NVD incremental totalResults must be a non-negative integer.")

        if not self.source_timestamp:
            raise ValueError("NVD incremental source timestamp cannot be empty.")


@dataclass(frozen=True, slots=True)
class NvdIncrementalManifest:
    """Represent COMPLETE Bronze evidence for one incremental window."""

    MANIFEST_VERSION: ClassVar[str] = "1"
    COMPLETION_STATUS: ClassVar[str] = "complete"
    SOURCE: ClassVar[str] = "nvd-cve"
    SOURCE_INTERFACE: ClassVar[str] = "cve-api-2.0"
    SOURCE_FORMAT: ClassVar[str] = "NVD_CVE"
    SOURCE_VERSION: ClassVar[str] = "2.0"

    update_id: str
    window_start_at: datetime
    window_end_at: datetime
    total_results: int
    pages: tuple[NvdIncrementalStoredPage, ...]

    def __post_init__(self) -> None:
        """Validate COMPLETE incremental-run evidence."""
        if not _SHA256_PATTERN.fullmatch(self.update_id):
            raise ValueError(
                "NVD incremental update id must contain exactly "
                "64 lowercase hexadecimal characters."
            )

        if self.window_start_at.tzinfo is None or self.window_start_at.utcoffset() is None:
            raise ValueError("NVD incremental manifest start timestamp must be timezone-aware.")

        if self.window_end_at.tzinfo is None or self.window_end_at.utcoffset() is None:
            raise ValueError("NVD incremental manifest end timestamp must be timezone-aware.")

        if self.window_start_at >= self.window_end_at:
            raise ValueError(
                "NVD incremental manifest start timestamp must be before end timestamp."
            )

        if type(self.total_results) is not int or self.total_results < 0:
            raise ValueError(
                "NVD incremental manifest totalResults must be a non-negative integer."
            )

        if not self.pages:
            raise ValueError(
                "NVD incremental COMPLETE manifest requires at least one response page."
            )

        expected_start_index = 0

        for page in self.pages:
            if page.total_results != self.total_results:
                raise ValueError(
                    "NVD incremental manifest page totalResults does not match run totalResults."
                )

            if page.start_index != expected_start_index:
                raise ValueError("NVD incremental manifest pages are not contiguous.")

            if self.total_results > 0 and page.results_per_page == 0:
                raise ValueError("NVD incremental non-empty run cannot contain an empty page.")

            expected_start_index += page.results_per_page

        if expected_start_index != self.total_results:
            raise ValueError("NVD incremental manifest page inventory does not reach totalResults.")

        if self.total_results == 0:
            if len(self.pages) != 1:
                raise ValueError(
                    "NVD incremental empty result must contain exactly one response page."
                )

            page = self.pages[0]

            if page.start_index != 0 or page.results_per_page != 0:
                raise ValueError("NVD incremental empty result page is invalid.")

    @property
    def page_count(self) -> int:
        """Return the number of exact response objects in the run."""
        return len(self.pages)

    @property
    def canonical_window_start_at(self) -> str:
        """Return the canonical UTC lower boundary."""
        return self._format_utc(self.window_start_at)

    @property
    def canonical_window_end_at(self) -> str:
        """Return the canonical UTC upper boundary."""
        return self._format_utc(self.window_end_at)

    @staticmethod
    def _format_utc(value: datetime) -> str:
        """Format one timezone-aware timestamp as canonical UTC."""
        timespec = "microseconds" if value.microsecond else "seconds"

        return value.astimezone(UTC).isoformat(timespec=timespec).replace("+00:00", "Z")


class NvdIncrementalManifestFactory:
    """Build COMPLETE evidence from validated pages and S3 provenance."""

    def build(
        self,
        *,
        window: NvdIncrementalWindow,
        pagination: NvdCveApiPagination,
        page_writes: tuple[NvdBronzeWriteResult, ...],
        key_factory: NvdIncrementalKeyFactory,
    ) -> NvdIncrementalManifest:
        """Build one deterministic incremental COMPLETE manifest.

        Args:
            window: Deterministic logical update window.
            pagination: Fully validated source page sequence.
            page_writes: Exact S3 persistence results in page order.
            key_factory: Deterministic incremental Bronze key factory.

        Returns:
            Validated COMPLETE manifest.

        Raises:
            ValueError: If persisted page evidence is incomplete.
        """
        if len(page_writes) != len(pagination.pages):
            raise ValueError(
                "NVD incremental page persistence results do not "
                "match the validated page inventory."
            )

        stored_pages = tuple(
            NvdIncrementalStoredPage(
                key=key_factory.build_page_key(
                    window=window,
                    start_index=page.start_index,
                ),
                version_id=write.version_id,
                size_bytes=len(page.raw_bytes),
                sha256=page.sha256,
                start_index=page.start_index,
                results_per_page=page.results_per_page,
                total_results=page.total_results,
                source_timestamp=page.source_timestamp,
            )
            for page, write in zip(
                pagination.pages,
                page_writes,
                strict=True,
            )
        )

        return NvdIncrementalManifest(
            update_id=window.update_id,
            window_start_at=window.start_at,
            window_end_at=window.end_at,
            total_results=pagination.total_results,
            pages=stored_pages,
        )


class NvdIncrementalManifestSerializer:
    """Serialize incremental COMPLETE evidence deterministically."""

    def serialize(
        self,
        manifest: NvdIncrementalManifest,
    ) -> bytes:
        """Return canonical UTF-8 JSON bytes."""
        page_documents: list[dict[str, object]] = [
            {
                "key": page.key,
                "results_per_page": (page.results_per_page),
                "sha256": page.sha256,
                "size_bytes": page.size_bytes,
                "source_timestamp": (page.source_timestamp),
                "start_index": page.start_index,
                "total_results": page.total_results,
                "version_id": page.version_id,
            }
            for page in manifest.pages
        ]

        document: dict[str, object] = {
            "completion_status": (manifest.COMPLETION_STATUS),
            "manifest_version": (manifest.MANIFEST_VERSION),
            "page_count": manifest.page_count,
            "pages": page_documents,
            "source": manifest.SOURCE,
            "source_format": (manifest.SOURCE_FORMAT),
            "source_interface": (manifest.SOURCE_INTERFACE),
            "source_version": (manifest.SOURCE_VERSION),
            "total_results": (manifest.total_results),
            "update_id": manifest.update_id,
            "window_end_at": (manifest.canonical_window_end_at),
            "window_start_at": (manifest.canonical_window_start_at),
        }

        text = json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )

        return f"{text}\n".encode()
