"""Application orchestration for CISA KEV Bronze-to-Silver transformation."""

from datetime import UTC, date, datetime
from io import BytesIO

from opslens.transformation.kev.application.key_factory import (
    KevSilverKeyFactory,
)
from opslens.transformation.kev.application.ports import (
    SilverKevArtifactRepository,
    SilverKevRecordWriter,
)
from opslens.transformation.kev.application.runtime_models import (
    KevSilverSourceEvidence,
    KevSilverTransformationResult,
)
from opslens.transformation.kev.domain.transformer import (
    KevSilverTransformer,
)


class KevSilverTransformationError(RuntimeError):
    """Raised when deterministic Silver transformation invariants fail."""


class KevSilverTransformationService:
    """Transform verified CISA KEV evidence into immutable Silver Parquet."""

    def __init__(
        self,
        *,
        transformer: KevSilverTransformer,
        record_writer: SilverKevRecordWriter,
        silver_repository: SilverKevArtifactRepository,
        key_factory: KevSilverKeyFactory,
    ) -> None:
        """Initialize the application service with explicit dependencies.

        Args:
            transformer: Deterministic KEV domain transformer.
            record_writer: Physical Silver serializer.
            silver_repository: Immutable Silver artifact repository.
            key_factory: Deterministic Silver S3 key factory.
        """
        self._transformer = transformer
        self._record_writer = record_writer
        self._silver_repository = silver_repository
        self._key_factory = key_factory

    def transform(
        self,
        evidence: KevSilverSourceEvidence,
    ) -> KevSilverTransformationResult:
        """Transform verified Bronze evidence into one Silver artifact.

        Args:
            evidence: Semantically and transport-verified Bronze evidence.

        Returns:
            Deterministic transformation and persistence result.

        Raises:
            KevSilverTransformationError: If the serialized row count differs
                from the verified Bronze catalog count.
        """
        snapshot = evidence.snapshot
        snapshot_date = date.fromisoformat(snapshot.snapshot_date)

        silver_key = self._key_factory.build(snapshot_date)

        with BytesIO() as artifact:
            write_result = self._record_writer.write(
                records=self._transformer.iter_records(snapshot),
                destination=artifact,
            )

            if write_result.row_count != snapshot.record_count:
                raise KevSilverTransformationError(
                    "KEV Silver serialized row count does not match "
                    "the verified Bronze record count."
                )

            artifact.seek(0)

            write_status = self._silver_repository.put_if_absent(
                key=silver_key,
                artifact=artifact,
                metadata=self._build_metadata(
                    evidence=evidence,
                    schema_version=write_result.schema_version,
                    row_count=write_result.row_count,
                ),
            )

        return KevSilverTransformationResult(
            bronze_key=evidence.bronze_key,
            bronze_version_id=evidence.bronze_version_id,
            silver_key=silver_key,
            snapshot_date=snapshot.snapshot_date,
            row_count=write_result.row_count,
            size_bytes=write_result.size_bytes,
            schema_version=write_result.schema_version,
            source_sha256=snapshot.sha256,
            write_status=write_status,
        )

    @classmethod
    def _build_metadata(
        cls,
        *,
        evidence: KevSilverSourceEvidence,
        schema_version: int,
        row_count: int,
    ) -> dict[str, str]:
        """Build immutable provenance metadata for a Silver artifact."""
        snapshot = evidence.snapshot

        return {
            "source": KevSilverTransformer.SOURCE,
            "catalog_version": snapshot.catalog_version,
            "date_released": cls._format_utc(snapshot.date_released),
            "retrieved_at": cls._format_utc(snapshot.retrieved_at),
            "source_sha256": snapshot.sha256,
            "schema_version": str(schema_version),
            "row_count": str(row_count),
            "bronze_version_id": evidence.bronze_version_id,
            "bronze_etag": evidence.bronze_etag,
        }

    @staticmethod
    def _format_utc(
        value: datetime,
    ) -> str:
        """Format one timezone-aware timestamp as canonical UTC."""
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
