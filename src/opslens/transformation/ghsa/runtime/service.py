"""Application orchestration for exact GHSA Bronze-to-Silver preparation."""

from typing import Protocol

from opslens.ingestion.ghsa.application.attempt import (
    GhsaAttemptIdFactory,
)
from opslens.ingestion.ghsa.application.manifest import (
    GhsaStoredPage,
)
from opslens.ingestion.ghsa.domain.api_page import (
    GhsaAdvisoryApiPage,
    GhsaAdvisoryApiPageParser,
    GhsaAdvisoryPagination,
)
from opslens.ingestion.ghsa.domain.sync import (
    GhsaSyncWindow,
)
from opslens.transformation.ghsa.runtime.manifest_processor import (
    GhsaAuthorizedBronzeManifestV1,
    GhsaBronzeManifestProcessorV1,
)
from opslens.transformation.ghsa.runtime.materializer import (
    GhsaSilverMaterializationV1,
    GhsaSilverMaterializerV1,
)
from opslens.transformation.ghsa.runtime.object_payload import (
    GhsaBronzeObjectPayloadV1,
)
from opslens.transformation.ghsa.runtime.page_processor import (
    GhsaBronzePageProcessorV1,
    GhsaVerifiedBronzePageV1,
)
from opslens.transformation.ghsa.runtime.record_processor import (
    GhsaSilverOccurrenceRecordV1,
    GhsaSilverRecordProcessorV1,
)


class GhsaBronzeObjectReader(Protocol):
    """Define exact immutable Bronze object reads required by Silver."""

    def get(
        self,
        *,
        key: str,
        version_id: str,
    ) -> GhsaBronzeObjectPayloadV1:
        """Read one exact object version."""
        ...


class GhsaSilverRuntimeServiceV1:
    """Prepare deterministic Silver materialization from exact Bronze evidence."""

    def __init__(
        self,
        *,
        object_reader: GhsaBronzeObjectReader,
        manifest_processor: GhsaBronzeManifestProcessorV1,
        source_page_parser: GhsaAdvisoryApiPageParser,
        attempt_id_factory: GhsaAttemptIdFactory,
        page_processor: GhsaBronzePageProcessorV1,
        record_processor: GhsaSilverRecordProcessorV1,
        materializer: GhsaSilverMaterializerV1,
    ) -> None:
        """Initialize explicit deterministic runtime dependencies."""
        self._object_reader = object_reader
        self._manifest_processor = manifest_processor
        self._source_page_parser = source_page_parser
        self._attempt_id_factory = attempt_id_factory
        self._page_processor = page_processor
        self._record_processor = record_processor
        self._materializer = materializer

    def prepare(
        self,
        *,
        manifest_key: str,
        manifest_version_id: str,
    ) -> GhsaSilverMaterializationV1:
        """Prepare Silver from one exact immutable Bronze COMPLETE manifest."""
        manifest_payload = self._read_exact(
            key=manifest_key,
            version_id=manifest_version_id,
        )

        authorized = self._manifest_processor.process(
            manifest_key=manifest_payload.key,
            manifest_version_id=manifest_payload.version_id,
            manifest_bytes=manifest_payload.raw_bytes,
        )

        window = self._window(authorized)

        source_pages: list[GhsaAdvisoryApiPage] = []
        verified_pages: list[GhsaVerifiedBronzePageV1] = []

        for stored_page, page_evidence in zip(
            authorized.manifest.pages,
            authorized.page_evidences,
            strict=True,
        ):
            page_payload = self._read_exact(
                key=page_evidence.page_key,
                version_id=page_evidence.page_version_id,
            )

            source_page = self._revalidate_source_page(
                window=window,
                stored_page=stored_page,
                page_payload=page_payload,
            )

            verified_page = self._page_processor.process(
                evidence=page_evidence,
                page_bytes=page_payload.raw_bytes,
            )

            if verified_page.item_count != stored_page.item_count:
                raise ValueError(
                    "GHSA persisted Bronze page item_count does not "
                    "match the COMPLETE manifest."
                )

            source_pages.append(source_page)
            verified_pages.append(verified_page)

        pagination = GhsaAdvisoryPagination(
            window=window,
            pages=tuple(source_pages),
        )

        recomputed_attempt_id = self._attempt_id_factory.build(
            window=window,
            pagination=pagination,
        )

        if recomputed_attempt_id != authorized.manifest.attempt_id:
            raise ValueError(
                "GHSA Bronze manifest attempt_id does not match "
                "the exact persisted page evidence."
            )

        bindings = self._compose_bindings(
            verified_pages=tuple(verified_pages),
        )

        if len(bindings) != authorized.manifest.total_items:
            raise ValueError(
                "GHSA Silver bound record count does not match "
                "the COMPLETE Bronze manifest total_items."
            )

        return self._materializer.materialize(
            context=authorized.attempt_context,
            bindings=bindings,
        )

    def _read_exact(
        self,
        *,
        key: str,
        version_id: str,
    ) -> GhsaBronzeObjectPayloadV1:
        """Require the reader to return exactly the requested coordinates."""
        payload = self._object_reader.get(
            key=key,
            version_id=version_id,
        )

        if payload.key != key:
            raise ValueError(
                "GHSA Bronze object reader returned a different object key."
            )

        if payload.version_id != version_id:
            raise ValueError(
                "GHSA Bronze object reader returned a different VersionId."
            )

        return payload

    def _revalidate_source_page(
        self,
        *,
        window: GhsaSyncWindow,
        stored_page: GhsaStoredPage,
        page_payload: GhsaBronzeObjectPayloadV1,
    ) -> GhsaAdvisoryApiPage:
        """Reapply the Bronze source-page contract to exact persisted bytes."""
        link_header = (
            None
            if stored_page.next_url is None
            else f'<{stored_page.next_url}>; rel="next"'
        )

        source_page = self._source_page_parser.parse(
            page_payload.raw_bytes,
            request_url=stored_page.request_url,
            link_header=link_header,
            window=window,
        )

        if source_page.sha256 != stored_page.sha256:
            raise ValueError(
                "GHSA persisted Bronze page SHA-256 does not "
                "match the COMPLETE manifest."
            )

        if source_page.size_bytes != stored_page.size_bytes:
            raise ValueError(
                "GHSA persisted Bronze page size does not "
                "match the COMPLETE manifest."
            )

        if source_page.item_count != stored_page.item_count:
            raise ValueError(
                "GHSA persisted Bronze source-page item_count does not "
                "match the COMPLETE manifest."
            )

        first_ghsa_id = (
            source_page.ghsa_ids[0]
            if source_page.ghsa_ids
            else None
        )
        last_ghsa_id = (
            source_page.ghsa_ids[-1]
            if source_page.ghsa_ids
            else None
        )

        if first_ghsa_id != stored_page.first_ghsa_id:
            raise ValueError(
                "GHSA persisted Bronze first_ghsa_id does not "
                "match the COMPLETE manifest."
            )

        if last_ghsa_id != stored_page.last_ghsa_id:
            raise ValueError(
                "GHSA persisted Bronze last_ghsa_id does not "
                "match the COMPLETE manifest."
            )

        return source_page

    def _compose_bindings(
        self,
        *,
        verified_pages: tuple[GhsaVerifiedBronzePageV1, ...],
    ) -> tuple[GhsaSilverOccurrenceRecordV1, ...]:
        """Normalize verified pages into one ordered Silver binding sequence."""
        bindings: list[GhsaSilverOccurrenceRecordV1] = []

        for verified_page in verified_pages:
            bindings.extend(
                self._record_processor.process_page(
                    verified_page
                )
            )

        return tuple(bindings)

    @staticmethod
    def _window(
        authorized: GhsaAuthorizedBronzeManifestV1,
    ) -> GhsaSyncWindow:
        """Rebuild the deterministic logical source window."""
        manifest = authorized.manifest

        return GhsaSyncWindow(
            mode=manifest.mode,
            start_at=manifest.window_start_at,
            end_at=manifest.window_end_at,
        )
