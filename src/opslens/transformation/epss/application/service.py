"""Application service for transforming EPSS Bronze snapshots into Silver."""

from datetime import UTC
from io import BytesIO

from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.epss.domain.parser import EpssSnapshotParser
from opslens.transformation.epss.application.key_factory import (
    EpssSilverKeyFactory,
)
from opslens.transformation.epss.application.models import (
    EpssSilverTransformationResult,
    SilverWriteResult,
)
from opslens.transformation.epss.application.ports import (
    BronzeEpssSnapshotRepository,
    SilverEpssArtifactRepository,
    SilverEpssRecordWriter,
)
from opslens.transformation.epss.domain.transformer import EpssSilverTransformer


class EpssSilverTransformationService:
    """Transform one immutable EPSS Bronze artifact into Silver Parquet."""

    def __init__(
        self,
        *,
        bronze_repository: BronzeEpssSnapshotRepository,
        parser: EpssSnapshotParser,
        transformer: EpssSilverTransformer,
        record_writer: SilverEpssRecordWriter,
        silver_repository: SilverEpssArtifactRepository,
        key_factory: EpssSilverKeyFactory,
    ) -> None:
        """Initialize the transformation service with explicit dependencies.

        Args:
            bronze_repository: Source repository for immutable Bronze artifacts.
            parser: Validator and parser for FIRST EPSS source snapshots.
            transformer: Bronze-to-Silver domain transformer.
            record_writer: Physical Silver record serializer.
            silver_repository: Destination repository for Silver artifacts.
            key_factory: Deterministic Silver object-key factory.
        """
        self._bronze_repository = bronze_repository
        self._parser = parser
        self._transformer = transformer
        self._record_writer = record_writer
        self._silver_repository = silver_repository
        self._key_factory = key_factory

    def transform(
        self,
        bronze_key: str,
    ) -> EpssSilverTransformationResult:
        """Transform one Bronze object into an immutable Silver artifact.

        Args:
            bronze_key: Canonical Bronze object key.

        Returns:
            Deterministic transformation result including the Silver location
            and idempotent repository-write outcome.
        """
        normalized_bronze_key = bronze_key.strip()

        if not normalized_bronze_key:
            raise ValueError("Bronze object key cannot be empty.")

        payload = self._bronze_repository.get(normalized_bronze_key)
        snapshot = self._parser.parse(payload)

        silver_key = self._key_factory.build(snapshot.score_timestamp.date())

        with BytesIO() as artifact:
            write_result = self._record_writer.write(
                records=self._transformer.iter_records(snapshot),
                destination=artifact,
            )

            artifact.seek(0)

            repository_status = self._silver_repository.put_if_absent(
                key=silver_key,
                artifact=artifact,
                metadata=self._build_metadata(
                    snapshot=snapshot,
                    write_result=write_result,
                ),
            )

        return EpssSilverTransformationResult(
            bronze_key=normalized_bronze_key,
            silver_key=silver_key,
            snapshot_date=snapshot.score_timestamp.date(),
            row_count=write_result.row_count,
            size_bytes=write_result.size_bytes,
            schema_version=write_result.schema_version,
            source_sha256=snapshot.sha256,
            write_status=repository_status,
        )

    @staticmethod
    def _build_metadata(
        *,
        snapshot: EpssSnapshot,
        write_result: SilverWriteResult,
    ) -> dict[str, str]:
        """Build immutable provenance metadata for the Silver artifact."""
        score_timestamp = (
            snapshot.score_timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z")
        )

        return {
            "source": EpssSilverTransformer.SOURCE,
            "model_version": snapshot.model_version,
            "score_timestamp": score_timestamp,
            "source_sha256": snapshot.sha256,
            "schema_version": str(write_result.schema_version),
            "row_count": str(write_result.row_count),
        }
