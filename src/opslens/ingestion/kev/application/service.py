"""Application service orchestrating CISA KEV Bronze ingestion."""

from opslens.ingestion.kev.application.key_factory import KevBronzeKeyFactory
from opslens.ingestion.kev.application.models import KevIngestionResult
from opslens.ingestion.kev.application.ports import (
    BronzeCatalogRepository,
    Clock,
    KevCatalogSource,
)
from opslens.ingestion.kev.domain.parser import KevCatalogParser


class IngestKevCatalog:
    """Orchestrate deterministic ingestion of the current CISA KEV catalog."""

    def __init__(
        self,
        source: KevCatalogSource,
        repository: BronzeCatalogRepository,
        parser: KevCatalogParser,
        key_factory: KevBronzeKeyFactory,
        clock: Clock,
    ) -> None:
        """Initialize the use case through explicit dependency injection."""
        self._source = source
        self._repository = repository
        self._parser = parser
        self._key_factory = key_factory
        self._clock = clock

    def execute(self) -> KevIngestionResult:
        """Fetch, validate, identify, and conditionally persist CISA KEV data."""
        payload = self._source.fetch()
        retrieved_at = self._clock.now()

        snapshot = self._parser.parse(
            payload=payload,
            retrieved_at=retrieved_at,
        )

        object_key = self._key_factory.build(snapshot)

        write_result = self._repository.create_if_absent(
            snapshot=snapshot,
            object_key=object_key,
        )

        return KevIngestionResult(
            status=write_result.status,
            s3_key=object_key,
            snapshot=snapshot,
            version_id=write_result.version_id,
            etag=write_result.etag,
        )
