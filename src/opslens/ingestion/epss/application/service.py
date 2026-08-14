"""Application service orchestrating EPSS Bronze ingestion."""

from opslens.ingestion.epss.application.key_factory import EpssBronzeKeyFactory
from opslens.ingestion.epss.application.models import EpssIngestionResult
from opslens.ingestion.epss.application.ports import (
    BronzeSnapshotRepository,
    EpssSnapshotSource,
)
from opslens.ingestion.epss.domain.parser import EpssSnapshotParser


class IngestEpssSnapshot:
    """Orchestrate deterministic ingestion of the current EPSS snapshot."""

    def __init__(
        self,
        source: EpssSnapshotSource,
        repository: BronzeSnapshotRepository,
        parser: EpssSnapshotParser,
        key_factory: EpssBronzeKeyFactory,
    ) -> None:
        """Initialize the use case through explicit dependency injection."""
        self._source = source
        self._repository = repository
        self._parser = parser
        self._key_factory = key_factory

    def execute(self) -> EpssIngestionResult:
        """Fetch, validate, identify, and conditionally persist EPSS data."""
        payload = self._source.fetch()

        snapshot = self._parser.parse(payload)
        object_key = self._key_factory.build(snapshot)

        write_result = self._repository.create_if_absent(
            snapshot=snapshot,
            object_key=object_key,
        )

        return EpssIngestionResult(
            status=write_result.status,
            s3_key=object_key,
            snapshot=snapshot,
            version_id=write_result.version_id,
            etag=write_result.etag,
        )
