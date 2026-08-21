"""Application service orchestrating NVD incremental Bronze ingestion."""

from opslens.ingestion.nvd.application.incremental_key_factory import (
    NvdIncrementalKeyFactory,
)
from opslens.ingestion.nvd.application.incremental_manifest import (
    NvdIncrementalManifestFactory,
    NvdIncrementalManifestSerializer,
)
from opslens.ingestion.nvd.application.incremental_models import (
    NvdIncrementalIngestionResult,
)
from opslens.ingestion.nvd.application.incremental_ports import (
    NvdCveApiSource,
    NvdIncrementalBronzeRepository,
)
from opslens.ingestion.nvd.application.models import (
    NvdBronzeWriteResult,
)
from opslens.ingestion.nvd.application.watermark import (
    NvdWatermarkCandidateFactory,
)
from opslens.ingestion.nvd.domain.api_page import (
    NvdCveApiPage,
    NvdCveApiPageParser,
    NvdCveApiPagination,
)
from opslens.ingestion.nvd.domain.errors import (
    InvalidNvdCveApiPaginationError,
)
from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)


class IngestNvdIncrementalWindow:
    """Orchestrate one deterministic NVD CVE API Bronze update run."""

    def __init__(
        self,
        *,
        source: NvdCveApiSource,
        repository: NvdIncrementalBronzeRepository,
        page_parser: NvdCveApiPageParser,
        key_factory: NvdIncrementalKeyFactory,
        manifest_factory: NvdIncrementalManifestFactory,
        manifest_serializer: NvdIncrementalManifestSerializer,
        candidate_factory: NvdWatermarkCandidateFactory,
    ) -> None:
        """Initialize the use case through explicit dependency injection."""
        self._source = source
        self._repository = repository
        self._page_parser = page_parser
        self._key_factory = key_factory
        self._manifest_factory = manifest_factory
        self._manifest_serializer = manifest_serializer
        self._candidate_factory = candidate_factory

    def execute(
        self,
        *,
        window: NvdIncrementalWindow,
    ) -> NvdIncrementalIngestionResult:
        """Fetch, validate, persist, and complete one incremental Bronze run.

        All source pages are fetched and the complete pagination contract is
        validated before any Bronze object is written. The completion manifest
        is persisted only after every page has been created or verified.

        The returned watermark candidate is advisory state only. This service
        does not advance the authoritative committed watermark.

        Args:
            window: Deterministic closed NVD last-modified query window.

        Returns:
            Exact persistence and Bronze-completion evidence.
        """
        pagination = self._fetch_complete_pagination(window=window)

        page_keys: list[str] = []
        page_writes: list[NvdBronzeWriteResult] = []

        for page in pagination.pages:
            page_key = self._key_factory.build_page_key(
                window=window,
                start_index=page.start_index,
            )

            page_write = self._repository.create_page(
                page=page,
                window=window,
                object_key=page_key,
            )

            page_keys.append(page_key)
            page_writes.append(page_write)

        manifest = self._manifest_factory.build(
            window=window,
            pagination=pagination,
            page_writes=tuple(page_writes),
            key_factory=self._key_factory,
        )

        manifest_payload = self._manifest_serializer.serialize(manifest)

        manifest_key = self._key_factory.build_manifest_key(window=window)

        manifest_write = self._repository.create_manifest(
            manifest=manifest,
            payload=manifest_payload,
            object_key=manifest_key,
        )

        candidate = self._candidate_factory.build(
            window=window,
            manifest=manifest,
            manifest_payload=manifest_payload,
            manifest_key=manifest_key,
            manifest_write=manifest_write,
            key_factory=self._key_factory,
        )

        return NvdIncrementalIngestionResult(
            update_id=window.update_id,
            window_start_at=window.start_at,
            window_end_at=window.end_at,
            total_results=pagination.total_results,
            page_keys=tuple(page_keys),
            page_writes=tuple(page_writes),
            manifest_key=manifest_key,
            manifest_write=manifest_write,
            candidate=candidate,
        )

    def _fetch_complete_pagination(
        self,
        *,
        window: NvdIncrementalWindow,
    ) -> NvdCveApiPagination:
        """Fetch all pages and validate the complete source sequence."""
        pages: list[NvdCveApiPage] = []
        requested_start_index = 0
        expected_total_results: int | None = None

        while True:
            payload = self._source.fetch_page(
                window=window,
                start_index=requested_start_index,
            )

            page = self._page_parser.parse(payload)

            if page.start_index != requested_start_index:
                raise InvalidNvdCveApiPaginationError(
                    "NVD CVE API response startIndex does not match the requested page offset."
                )

            if expected_total_results is None:
                expected_total_results = page.total_results
            elif page.total_results != expected_total_results:
                raise InvalidNvdCveApiPaginationError(
                    "NVD CVE API totalResults changed between pages."
                )

            pages.append(page)

            if page.total_results == 0 or page.is_final_page:
                break

            requested_start_index = page.next_start_index

        return NvdCveApiPagination(pages=tuple(pages))
