"""Application service orchestrating NVD incremental Bronze ingestion."""

from opslens.ingestion.nvd.application.incremental_attempt import (
    NvdIncrementalAttemptIdFactory,
)
from opslens.ingestion.nvd.application.incremental_complete import (
    NvdIncrementalCanonicalManifestAlreadyExistsError,
    NvdPersistedIncrementalManifest,
)
from opslens.ingestion.nvd.application.incremental_key_factory import (
    NvdIncrementalKeyFactory,
)
from opslens.ingestion.nvd.application.incremental_manifest import (
    NvdIncrementalManifest,
    NvdIncrementalManifestFactory,
    NvdIncrementalManifestSerializer,
)
from opslens.ingestion.nvd.application.incremental_models import (
    NvdIncrementalIngestionResult,
)
from opslens.ingestion.nvd.application.incremental_ports import (
    NvdCveApiSource,
    NvdIncrementalBronzeRepository,
    NvdIncrementalCompleteManifestReader,
)
from opslens.ingestion.nvd.application.models import (
    NvdBronzeWriteResult,
    NvdBronzeWriteStatus,
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
    """Orchestrate one replay-safe NVD CVE API Bronze update run."""

    def __init__(
        self,
        *,
        source: NvdCveApiSource,
        repository: NvdIncrementalBronzeRepository,
        complete_reader: NvdIncrementalCompleteManifestReader,
        page_parser: NvdCveApiPageParser,
        attempt_id_factory: NvdIncrementalAttemptIdFactory,
        key_factory: NvdIncrementalKeyFactory,
        manifest_factory: NvdIncrementalManifestFactory,
        manifest_serializer: NvdIncrementalManifestSerializer,
        candidate_factory: NvdWatermarkCandidateFactory,
    ) -> None:
        """Initialize the use case through explicit dependency injection."""
        self._source = source
        self._repository = repository
        self._complete_reader = complete_reader
        self._page_parser = page_parser
        self._attempt_id_factory = attempt_id_factory
        self._key_factory = key_factory
        self._manifest_factory = manifest_factory
        self._manifest_serializer = manifest_serializer
        self._candidate_factory = candidate_factory

    def execute(
        self,
        *,
        window: NvdIncrementalWindow,
    ) -> NvdIncrementalIngestionResult:
        """Fetch, isolate, persist, and complete one incremental Bronze run.

        The logical ``update_id`` identifies only the requested time window.
        Exact source-response bytes define a physical ``attempt_id`` used to
        isolate page objects from repeated observations of the same window.

        All source pages are fetched and validated before persistence.

        The canonical COMPLETE manifest remains scoped only by ``update_id``.
        If another physical attempt already created that manifest, this attempt
        loads and returns the winning persisted COMPLETE evidence instead of
        comparing the winner with the losing attempt's bytes.

        The returned watermark candidate remains advisory state only.

        Args:
            window: Deterministic closed NVD last-modified query window.

        Returns:
            Exact winning Bronze-completion evidence.
        """
        pagination = self._fetch_complete_pagination(
            window=window
        )

        attempt_id = self._attempt_id_factory.build(
            window=window,
            pagination=pagination,
        )

        page_keys, page_writes = self._persist_attempt_pages(
            window=window,
            pagination=pagination,
            attempt_id=attempt_id,
        )

        manifest = self._manifest_factory.build(
            window=window,
            pagination=pagination,
            page_keys=page_keys,
            page_writes=page_writes,
        )

        manifest_payload = self._manifest_serializer.serialize(
            manifest
        )

        manifest_key = self._key_factory.build_manifest_key(
            window=window
        )

        try:
            manifest_write = self._repository.create_manifest(
                manifest=manifest,
                payload=manifest_payload,
                object_key=manifest_key,
            )
        except NvdIncrementalCanonicalManifestAlreadyExistsError:
            persisted = self._complete_reader.load_existing(
                window=window,
                object_key=manifest_key,
            )

            return self._result_from_existing_complete(
                window=window,
                manifest_key=manifest_key,
                persisted=persisted,
            )

        return self._build_result(
            window=window,
            manifest=manifest,
            manifest_payload=manifest_payload,
            manifest_key=manifest_key,
            manifest_write=manifest_write,
            page_keys=page_keys,
            page_writes=page_writes,
        )

    def _persist_attempt_pages(
        self,
        *,
        window: NvdIncrementalWindow,
        pagination: NvdCveApiPagination,
        attempt_id: str,
    ) -> tuple[
        tuple[str, ...],
        tuple[NvdBronzeWriteResult, ...],
    ]:
        """Persist exact pages below one physical-attempt identity."""
        page_keys: list[str] = []
        page_writes: list[NvdBronzeWriteResult] = []

        for page in pagination.pages:
            page_key = self._key_factory.build_attempt_page_key(
                window=window,
                attempt_id=attempt_id,
                start_index=page.start_index,
            )

            page_write = self._repository.create_page(
                page=page,
                window=window,
                object_key=page_key,
            )

            page_keys.append(
                page_key
            )
            page_writes.append(
                page_write
            )

        return (
            tuple(page_keys),
            tuple(page_writes),
        )

    def _result_from_existing_complete(
        self,
        *,
        window: NvdIncrementalWindow,
        manifest_key: str,
        persisted: NvdPersistedIncrementalManifest,
    ) -> NvdIncrementalIngestionResult:
        """Return the canonical winning COMPLETE instead of losing attempt data."""
        manifest = persisted.manifest

        page_keys = tuple(
            page.key
            for page in manifest.pages
        )

        page_writes = tuple(
            NvdBronzeWriteResult(
                status=NvdBronzeWriteStatus.ALREADY_EXISTS,
                version_id=page.version_id,
            )
            for page in manifest.pages
        )

        manifest_write = NvdBronzeWriteResult(
            status=NvdBronzeWriteStatus.ALREADY_EXISTS,
            version_id=persisted.version_id,
            etag=persisted.etag,
        )

        return self._build_result(
            window=window,
            manifest=manifest,
            manifest_payload=persisted.payload,
            manifest_key=manifest_key,
            manifest_write=manifest_write,
            page_keys=page_keys,
            page_writes=page_writes,
        )

    def _build_result(
        self,
        *,
        window: NvdIncrementalWindow,
        manifest: NvdIncrementalManifest,
        manifest_payload: bytes,
        manifest_key: str,
        manifest_write: NvdBronzeWriteResult,
        page_keys: tuple[str, ...],
        page_writes: tuple[NvdBronzeWriteResult, ...],
    ) -> NvdIncrementalIngestionResult:
        """Build exact externally visible evidence from the selected COMPLETE."""
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
            total_results=manifest.total_results,
            page_keys=page_keys,
            page_writes=page_writes,
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

            page = self._page_parser.parse(
                payload
            )

            if page.start_index != requested_start_index:
                raise InvalidNvdCveApiPaginationError(
                    "NVD CVE API response startIndex does not match "
                    "the requested page offset."
                )

            if expected_total_results is None:
                expected_total_results = page.total_results
            elif page.total_results != expected_total_results:
                raise InvalidNvdCveApiPaginationError(
                    "NVD CVE API totalResults changed between pages."
                )

            pages.append(
                page
            )

            if page.total_results == 0 or page.is_final_page:
                break

            requested_start_index = page.next_start_index

        return NvdCveApiPagination(
            pages=tuple(pages)
        )
