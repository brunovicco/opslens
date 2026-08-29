"""Prepare one-row authoritative GHSA Silver content artifacts."""

from dataclasses import dataclass

from opslens.transformation.ghsa.completion.key_factory import GhsaSilverKeyFactoryV1
from opslens.transformation.ghsa.runtime.materializer import GhsaSilverMaterializationV1
from opslens.transformation.ghsa.runtime.record_processor import GhsaSilverOccurrenceRecordV1
from opslens.transformation.ghsa.serialization.models import GhsaSilverParquetArtifactV1
from opslens.transformation.ghsa.serialization.parquet import GhsaSilverParquetSerializerV1


@dataclass(frozen=True, slots=True)
class GhsaSilverPreparedContentObjectV1:
    """Represent one authoritative one-row Silver object before persistence."""

    key: str
    binding: GhsaSilverOccurrenceRecordV1
    parquet_artifact: GhsaSilverParquetArtifactV1

    def __post_init__(self) -> None:
        """Validate the one-content-version physical grain."""
        if not self.key.strip():
            raise ValueError("GHSA Silver prepared content key cannot be empty.")

        if self.parquet_artifact.row_count != 1:
            raise ValueError(
                "GHSA Silver prepared content Parquet must contain exactly one row."
            )

    @property
    def observed_advisory_version_id(self) -> str:
        """Return the exact advisory content-version identity."""
        return self.binding.observed_advisory_version_id

    @property
    def ghsa_id(self) -> str:
        """Return the logical GitHub advisory identity."""
        return self.binding.occurrence.ghsa_id

    @property
    def source_advisory_sha256(self) -> str:
        """Return the canonical source advisory SHA-256."""
        return self.binding.occurrence.observed_version.source_advisory_sha256


class GhsaSilverContentPreparerV1:
    """Prepare immutable one-row Silver artifacts from logical materialization."""

    def __init__(
        self,
        *,
        key_factory: GhsaSilverKeyFactoryV1,
        parquet_serializer: GhsaSilverParquetSerializerV1,
    ) -> None:
        """Initialize deterministic physical-content dependencies."""
        self._key_factory = key_factory
        self._parquet_serializer = parquet_serializer

    def prepare(
        self,
        materialization: GhsaSilverMaterializationV1,
    ) -> tuple[GhsaSilverPreparedContentObjectV1, ...]:
        """Prepare one deterministic Parquet object per content version."""
        return tuple(
            self._prepare_binding(binding) for binding in materialization.bindings
        )

    def _prepare_binding(
        self,
        binding: GhsaSilverOccurrenceRecordV1,
    ) -> GhsaSilverPreparedContentObjectV1:
        """Serialize exactly one advisory content version."""
        observed_version = binding.occurrence.observed_version
        parquet_artifact = self._parquet_serializer.serialize((binding.record,))

        return GhsaSilverPreparedContentObjectV1(
            key=self._key_factory.build_content_object_key(observed_version),
            binding=binding,
            parquet_artifact=parquet_artifact,
        )
