"""Deterministic COMPLETE manifest for GHSA Bronze source attempts."""

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar

from opslens.ingestion.ghsa.application.attempt import (
    GhsaAttemptIdFactory,
)
from opslens.ingestion.ghsa.application.key_factory import (
    GhsaBronzeKeyFactory,
)
from opslens.ingestion.ghsa.application.models import (
    GhsaBronzeWriteResult,
)
from opslens.ingestion.ghsa.domain.api_page import (
    GhsaAdvisoryPagination,
)
from opslens.ingestion.ghsa.domain.sync import (
    GhsaSyncMode,
    GhsaSyncWindow,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GHSA_PATTERN = re.compile(r"^GHSA(?:-[23456789cfghjmpqrvwx]{4}){3}$")


@dataclass(frozen=True, slots=True)
class GhsaStoredPage:
    """Describe one exact persisted GitHub advisory response page."""

    page_ordinal: int
    key: str
    version_id: str
    size_bytes: int
    sha256: str
    item_count: int
    request_url: str
    next_url: str | None
    first_ghsa_id: str | None
    last_ghsa_id: str | None

    def __post_init__(self) -> None:
        """Validate immutable page provenance."""
        if type(self.page_ordinal) is not int or self.page_ordinal < 1:
            raise ValueError("GHSA stored page ordinal must be a positive integer.")

        if not self.key.strip():
            raise ValueError("GHSA stored page key cannot be empty.")

        if not self.version_id.strip():
            raise ValueError("GHSA stored page version_id cannot be empty.")

        if not self.request_url.strip():
            raise ValueError("GHSA stored page request_url cannot be empty.")

        if type(self.size_bytes) is not int or self.size_bytes <= 0:
            raise ValueError("GHSA stored page size_bytes must be positive.")

        if _SHA256_PATTERN.fullmatch(self.sha256) is None:
            raise ValueError("GHSA stored page SHA-256 must be lowercase hexadecimal.")

        if type(self.item_count) is not int or self.item_count < 0:
            raise ValueError("GHSA stored page item_count must be non-negative.")

        if self.item_count == 0:
            if self.first_ghsa_id is not None or self.last_ghsa_id is not None:
                raise ValueError("Empty GHSA stored pages cannot carry advisory boundary IDs.")
        else:
            if self.first_ghsa_id is None or self.last_ghsa_id is None:
                raise ValueError("Non-empty GHSA stored pages require advisory boundary IDs.")

            if _GHSA_PATTERN.fullmatch(self.first_ghsa_id) is None:
                raise ValueError("GHSA stored page first_ghsa_id is invalid.")

            if _GHSA_PATTERN.fullmatch(self.last_ghsa_id) is None:
                raise ValueError("GHSA stored page last_ghsa_id is invalid.")


@dataclass(frozen=True, slots=True)
class GhsaCompleteManifest:
    """Represent COMPLETE Bronze evidence for one exact GHSA source attempt."""

    MANIFEST_VERSION: ClassVar[str] = "1"
    COMPLETION_STATUS: ClassVar[str] = "complete"
    SOURCE: ClassVar[str] = "github-ghsa"
    SOURCE_INTERFACE: ClassVar[str] = "global-security-advisories-rest"

    mode: GhsaSyncMode
    sync_id: str
    attempt_id: str
    window_start_at: datetime
    window_end_at: datetime
    total_items: int
    total_bytes: int
    pages: tuple[GhsaStoredPage, ...]

    def __post_init__(self) -> None:
        """Validate complete attempt inventory and totals."""
        if _SHA256_PATTERN.fullmatch(self.sync_id) is None:
            raise ValueError("GHSA manifest sync_id must be a lowercase SHA-256 digest.")

        if _SHA256_PATTERN.fullmatch(self.attempt_id) is None:
            raise ValueError("GHSA manifest attempt_id must be a lowercase SHA-256 digest.")

        self._require_utc(self.window_start_at, "window_start_at")
        self._require_utc(self.window_end_at, "window_end_at")

        if self.window_start_at >= self.window_end_at:
            raise ValueError("GHSA manifest window_start_at must be before window_end_at.")

        if type(self.total_items) is not int or self.total_items < 0:
            raise ValueError("GHSA manifest total_items must be non-negative.")

        if type(self.total_bytes) is not int or self.total_bytes <= 0:
            raise ValueError("GHSA manifest total_bytes must be positive.")

        if not self.pages:
            raise ValueError("GHSA COMPLETE manifest requires at least one stored page.")

        expected_ordinals = tuple(range(1, len(self.pages) + 1))
        actual_ordinals = tuple(page.page_ordinal for page in self.pages)

        if actual_ordinals != expected_ordinals:
            raise ValueError("GHSA manifest page ordinals must be contiguous from one.")

        page_keys = tuple(page.key for page in self.pages)
        request_urls = tuple(page.request_url for page in self.pages)

        if len(page_keys) != len(set(page_keys)):
            raise ValueError("GHSA manifest page keys must be unique.")

        if len(request_urls) != len(set(request_urls)):
            raise ValueError("GHSA manifest request URLs must be unique.")

        if sum(page.item_count for page in self.pages) != self.total_items:
            raise ValueError("GHSA manifest page item counts do not match total_items.")

        if sum(page.size_bytes for page in self.pages) != self.total_bytes:
            raise ValueError("GHSA manifest page sizes do not match total_bytes.")

        if self.total_items == 0 and (
            len(self.pages) != 1 or self.pages[0].item_count != 0
        ):
            raise ValueError("An empty GHSA attempt must contain exactly one empty page.")

    @property
    def page_count(self) -> int:
        """Return the number of persisted response pages."""
        return len(self.pages)

    @property
    def canonical_window_start_at(self) -> str:
        """Return the source-query lower boundary."""
        return self.window_start_at.astimezone(UTC).isoformat(timespec="seconds")

    @property
    def canonical_window_end_at(self) -> str:
        """Return the source-query upper boundary."""
        return self.window_end_at.astimezone(UTC).isoformat(timespec="seconds")

    @staticmethod
    def _require_utc(value: datetime, field_name: str) -> None:
        """Require an aware UTC timestamp."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"GHSA manifest {field_name} must be timezone-aware.")

        offset = value.utcoffset()

        if offset is None or offset.total_seconds() != 0:
            raise ValueError(f"GHSA manifest {field_name} must be normalized to UTC.")

        if value.microsecond != 0:
            raise ValueError(f"GHSA manifest {field_name} must use whole-second precision.")


class GhsaCompleteManifestFactory:
    """Bind validated pagination to exact persisted S3 page versions."""

    def __init__(
        self,
        *,
        attempt_factory: GhsaAttemptIdFactory,
        key_factory: GhsaBronzeKeyFactory,
    ) -> None:
        """Initialize deterministic identity and key dependencies."""
        self._attempt_factory = attempt_factory
        self._key_factory = key_factory

    def build(
        self,
        *,
        window: GhsaSyncWindow,
        pagination: GhsaAdvisoryPagination,
        page_writes: tuple[GhsaBronzeWriteResult, ...],
    ) -> GhsaCompleteManifest:
        """Build COMPLETE evidence only after every exact page is persisted."""
        if pagination.window.sync_id != window.sync_id:
            raise ValueError("GHSA manifest pagination does not match the requested sync window.")

        if len(page_writes) != len(pagination.pages):
            raise ValueError("GHSA page persistence results do not match the page inventory.")

        attempt_id = self._attempt_factory.build(
            window=window,
            pagination=pagination,
        )
        stored_pages: list[GhsaStoredPage] = []

        for ordinal, (page, write) in enumerate(
            zip(pagination.pages, page_writes, strict=True),
            start=1,
        ):
            expected_key = self._key_factory.build_page_key(
                window=window,
                attempt_id=attempt_id,
                page_ordinal=ordinal,
            )

            if write.key != expected_key:
                raise ValueError(
                    "GHSA persisted page key does not match the deterministic Bronze layout."
                )

            stored_pages.append(
                GhsaStoredPage(
                    page_ordinal=ordinal,
                    key=write.key,
                    version_id=write.version_id,
                    size_bytes=page.size_bytes,
                    sha256=page.sha256,
                    item_count=page.item_count,
                    request_url=page.request_url,
                    next_url=page.next_url,
                    first_ghsa_id=page.ghsa_ids[0] if page.ghsa_ids else None,
                    last_ghsa_id=page.ghsa_ids[-1] if page.ghsa_ids else None,
                )
            )

        return GhsaCompleteManifest(
            mode=window.mode,
            sync_id=window.sync_id,
            attempt_id=attempt_id,
            window_start_at=window.start_at,
            window_end_at=window.end_at,
            total_items=pagination.total_items,
            total_bytes=pagination.total_bytes,
            pages=tuple(stored_pages),
        )


class GhsaCompleteManifestSerializer:
    """Serialize GHSA COMPLETE evidence deterministically."""

    def serialize(self, manifest: GhsaCompleteManifest) -> bytes:
        """Return canonical UTF-8 JSON bytes without credentials or runtime metadata."""
        page_documents: list[dict[str, object]] = [
            {
                "first_ghsa_id": page.first_ghsa_id,
                "item_count": page.item_count,
                "key": page.key,
                "last_ghsa_id": page.last_ghsa_id,
                "next_url": page.next_url,
                "page_ordinal": page.page_ordinal,
                "request_url": page.request_url,
                "sha256": page.sha256,
                "size_bytes": page.size_bytes,
                "version_id": page.version_id,
            }
            for page in manifest.pages
        ]

        document: dict[str, object] = {
            "advisory_type": GhsaSyncWindow.ADVISORY_TYPE,
            "api_version": GhsaSyncWindow.API_VERSION,
            "attempt_id": manifest.attempt_id,
            "completion_status": manifest.COMPLETION_STATUS,
            "manifest_version": manifest.MANIFEST_VERSION,
            "mode": manifest.mode.value,
            "page_count": manifest.page_count,
            "pages": page_documents,
            "source": manifest.SOURCE,
            "source_interface": manifest.SOURCE_INTERFACE,
            "sync_id": manifest.sync_id,
            "total_bytes": manifest.total_bytes,
            "total_items": manifest.total_items,
            "window_end_at": manifest.canonical_window_end_at,
            "window_start_at": manifest.canonical_window_start_at,
        }

        text = json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )

        return f"{text}\n".encode()
