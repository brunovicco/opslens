"""Bounded end-to-end runtime composition for GHSA Bronze ingestion."""

from collections import deque
from dataclasses import dataclass

from opslens.ingestion.ghsa.application.attempt import GhsaAttemptIdFactory
from opslens.ingestion.ghsa.application.key_factory import GhsaBronzeKeyFactory
from opslens.ingestion.ghsa.application.manifest import (
    GhsaCompleteManifestFactory,
    GhsaCompleteManifestSerializer,
)
from opslens.ingestion.ghsa.application.ports import (
    GhsaBronzeRepository,
    GhsaPageSource,
)
from opslens.ingestion.ghsa.application.subdivision import GhsaWindowSubdivisionPlanner
from opslens.ingestion.ghsa.domain.api_page import (
    GhsaAdvisoryApiPage,
    GhsaAdvisoryApiPageParser,
    GhsaAdvisoryPagination,
    GhsaRequestUrlPolicy,
)
from opslens.ingestion.ghsa.domain.sync import GhsaSyncWindow
from opslens.shared.observability.ports import OperationalTelemetry


class GhsaWindowCapacityExceededError(RuntimeError):
    """Raised when one logical GHSA window exceeds frozen Bronze attempt caps."""


class GhsaSubdivisionBudgetExceededError(RuntimeError):
    """Raised when deterministic subdivision would exceed the runtime leaf budget."""


@dataclass(frozen=True, slots=True)
class GhsaBronzeAttemptCompletion:
    """Expose exact COMPLETE evidence for one persisted leaf synchronization window."""

    sync_id: str
    attempt_id: str
    page_count: int
    total_items: int
    total_bytes: int
    manifest_key: str
    manifest_version_id: str

    def __post_init__(self) -> None:
        """Require usable COMPLETE evidence."""
        if not self.sync_id.strip():
            raise ValueError("GHSA completion sync_id cannot be empty.")

        if not self.attempt_id.strip():
            raise ValueError("GHSA completion attempt_id cannot be empty.")

        if type(self.page_count) is not int or self.page_count < 1:
            raise ValueError("GHSA completion page_count must be positive.")

        if type(self.total_items) is not int or self.total_items < 0:
            raise ValueError("GHSA completion total_items must be non-negative.")

        if type(self.total_bytes) is not int or self.total_bytes <= 0:
            raise ValueError("GHSA completion total_bytes must be positive.")

        if not self.manifest_key.strip():
            raise ValueError("GHSA completion manifest_key cannot be empty.")

        if not self.manifest_version_id.strip():
            raise ValueError("GHSA completion manifest_version_id cannot be empty.")


class GhsaBronzeRuntimeService:
    """Retrieve, verify, persist, and complete bounded GHSA Bronze windows."""

    DEFAULT_MAX_LEAF_WINDOWS = 64

    def __init__(
        self,
        *,
        source: GhsaPageSource,
        repository: GhsaBronzeRepository,
        parser: GhsaAdvisoryApiPageParser,
        attempt_factory: GhsaAttemptIdFactory,
        key_factory: GhsaBronzeKeyFactory,
        manifest_factory: GhsaCompleteManifestFactory,
        manifest_serializer: GhsaCompleteManifestSerializer,
        subdivision_planner: GhsaWindowSubdivisionPlanner,
        telemetry: OperationalTelemetry,
        max_leaf_windows: int = DEFAULT_MAX_LEAF_WINDOWS,
    ) -> None:
        """Initialize explicit deterministic runtime dependencies."""
        if type(max_leaf_windows) is not int or max_leaf_windows < 1:
            raise ValueError("GHSA runtime max_leaf_windows must be a positive integer.")

        self._source = source
        self._repository = repository
        self._parser = parser
        self._attempt_factory = attempt_factory
        self._key_factory = key_factory
        self._manifest_factory = manifest_factory
        self._manifest_serializer = manifest_serializer
        self._subdivision_planner = subdivision_planner
        self._telemetry = telemetry
        self._max_leaf_windows = max_leaf_windows

    def run(self, window: GhsaSyncWindow) -> tuple[GhsaBronzeAttemptCompletion, ...]:
        """Complete one root window, subdividing only on aggregate attempt capacity."""
        pending: deque[GhsaSyncWindow] = deque((window,))
        completions: list[GhsaBronzeAttemptCompletion] = []

        while pending:
            current = pending.popleft()

            try:
                pagination = self._fetch_complete_pagination(current)
            except GhsaWindowCapacityExceededError as exc:
                planned_leaf_count = len(completions) + len(pending) + 2

                if planned_leaf_count > self._max_leaf_windows:
                    raise GhsaSubdivisionBudgetExceededError(
                        "GHSA deterministic subdivision exceeded the configured leaf-window budget."
                    ) from exc

                left, right = self._subdivision_planner.split(current)
                self._telemetry.metric(
                    name="GhsaBronzeWindowSubdivision",
                    value=1.0,
                    unit="Count",
                )
                self._telemetry.info(
                    "Subdividing GHSA Bronze synchronization window",
                    fields={
                        "parent_sync_id": current.sync_id,
                        "left_sync_id": left.sync_id,
                        "right_sync_id": right.sync_id,
                    },
                )
                pending.appendleft(right)
                pending.appendleft(left)
                continue

            completion = self._persist_complete_attempt(
                window=current,
                pagination=pagination,
            )
            completions.append(completion)
            self._telemetry.metric(
                name="GhsaBronzeAttemptComplete",
                value=1.0,
                unit="Count",
            )
            self._telemetry.info(
                "Completed GHSA Bronze source attempt",
                fields={
                    "attempt_id": completion.attempt_id,
                    "page_count": completion.page_count,
                    "sync_id": completion.sync_id,
                    "total_items": completion.total_items,
                },
            )

        return tuple(completions)

    def _fetch_complete_pagination(
        self,
        window: GhsaSyncWindow,
    ) -> GhsaAdvisoryPagination:
        """Buffer one complete cursor chain before any attempt-keyed persistence occurs."""
        request_url = GhsaRequestUrlPolicy.build_initial(window)
        pages: list[GhsaAdvisoryApiPage] = []
        total_bytes = 0

        while True:
            fetched = self._source.fetch(
                request_url=request_url,
                window=window,
            )
            page = self._parser.parse(
                fetched.payload,
                request_url=request_url,
                link_header=fetched.link_header,
                window=window,
            )
            pages.append(page)
            total_bytes += page.size_bytes

            if total_bytes > GhsaAdvisoryPagination.MAX_TOTAL_BYTES:
                raise GhsaWindowCapacityExceededError(
                    "GHSA window exceeded the total Bronze payload-byte cap."
                )

            if page.next_url is None:
                break

            if len(pages) >= GhsaAdvisoryPagination.MAX_PAGES:
                raise GhsaWindowCapacityExceededError(
                    "GHSA window exceeded the Bronze cursor-page cap."
                )

            request_url = page.next_url

        return GhsaAdvisoryPagination(
            window=window,
            pages=tuple(pages),
        )

    def _persist_complete_attempt(
        self,
        *,
        window: GhsaSyncWindow,
        pagination: GhsaAdvisoryPagination,
    ) -> GhsaBronzeAttemptCompletion:
        """Persist exact pages first and publish COMPLETE only after all versions exist."""
        attempt_id = self._attempt_factory.build(
            window=window,
            pagination=pagination,
        )
        page_writes = []

        for ordinal, page in enumerate(pagination.pages, start=1):
            page_key = self._key_factory.build_page_key(
                window=window,
                attempt_id=attempt_id,
                page_ordinal=ordinal,
            )
            page_writes.append(
                self._repository.create_page(
                    page=page,
                    window=window,
                    object_key=page_key,
                )
            )

        manifest = self._manifest_factory.build(
            window=window,
            pagination=pagination,
            page_writes=tuple(page_writes),
        )
        manifest_payload = self._manifest_serializer.serialize(manifest)
        manifest_key = self._key_factory.build_manifest_key(
            window=window,
            attempt_id=attempt_id,
        )
        manifest_write = self._repository.create_manifest(
            manifest=manifest,
            payload=manifest_payload,
            object_key=manifest_key,
        )

        return GhsaBronzeAttemptCompletion(
            sync_id=window.sync_id,
            attempt_id=attempt_id,
            page_count=pagination.page_count,
            total_items=pagination.total_items,
            total_bytes=pagination.total_bytes,
            manifest_key=manifest_write.key,
            manifest_version_id=manifest_write.version_id,
        )
