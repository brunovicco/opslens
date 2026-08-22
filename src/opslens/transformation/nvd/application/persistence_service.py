"""Application orchestration for persisted NVD Silver completion preparation."""

from opslens.transformation.nvd.application.errors import (
    NvdSilverParquetAlreadyExistsError,
)
from opslens.transformation.nvd.application.models import (
    NvdSilverPreparedBatchV1,
)
from opslens.transformation.nvd.application.ports import (
    NvdSilverParquetReplayVerifier,
    NvdSilverParquetRepository,
)
from opslens.transformation.nvd.completion.manifest import (
    NvdSilverCompletionArtifactV1,
    NvdSilverCompletionManifestFactoryV1,
    NvdSilverCompletionManifestSerializerV1,
    NvdSilverStoredObjectV1,
)


class NvdSilverPersistenceServiceV1:
    """Persist or reconcile Parquet before preparing Silver COMPLETE evidence."""

    def __init__(
        self,
        *,
        parquet_repository: NvdSilverParquetRepository,
        replay_verifier: NvdSilverParquetReplayVerifier,
        completion_factory: NvdSilverCompletionManifestFactoryV1,
        completion_serializer: NvdSilverCompletionManifestSerializerV1,
    ) -> None:
        """Initialize explicit persistence and completion dependencies."""
        self._parquet_repository = parquet_repository
        self._replay_verifier = replay_verifier
        self._completion_factory = completion_factory
        self._completion_serializer = completion_serializer

    def prepare_completion(
        self,
        prepared: NvdSilverPreparedBatchV1,
    ) -> NvdSilverCompletionArtifactV1:
        """Persist or reconcile Parquet and prepare deterministic COMPLETE bytes."""
        try:
            stored_object = self._parquet_repository.put_if_absent(
                key=prepared.keys.parquet_key,
                artifact=prepared.parquet_artifact,
            )
        except NvdSilverParquetAlreadyExistsError:
            stored_object = self._replay_verifier.verify_current(
                key=prepared.keys.parquet_key,
                artifact=prepared.parquet_artifact,
            )

        self._validate_stored_object(
            prepared=prepared,
            stored_object=stored_object,
        )

        manifest, keys = self._completion_factory.build(
            evidence=prepared.evidence,
            records=prepared.records,
            parquet_artifact=prepared.parquet_artifact,
            silver_object_version_id=stored_object.version_id,
        )

        if keys != prepared.keys:
            raise ValueError("NVD Silver completion keys do not match the prepared batch.")

        if manifest.silver_object != stored_object:
            raise ValueError(
                "NVD Silver completion manifest does not match "
                "the exact persisted Parquet evidence."
            )

        return self._completion_serializer.serialize(
            manifest=manifest,
            manifest_key=keys.manifest_key,
        )

    @staticmethod
    def _validate_stored_object(
        *,
        prepared: NvdSilverPreparedBatchV1,
        stored_object: NvdSilverStoredObjectV1,
    ) -> None:
        """Require persisted evidence to match the prepared deterministic artifact."""
        artifact = prepared.parquet_artifact

        if stored_object.key != prepared.keys.parquet_key:
            raise ValueError(
                "Persisted NVD Silver object key does not match the prepared Parquet key."
            )

        if stored_object.sha256 != artifact.parquet_sha256:
            raise ValueError(
                "Persisted NVD Silver object SHA-256 does not match the prepared artifact."
            )

        if stored_object.size_bytes != artifact.size_bytes:
            raise ValueError(
                "Persisted NVD Silver object size does not match the prepared artifact."
            )

        if stored_object.row_count != artifact.row_count:
            raise ValueError(
                "Persisted NVD Silver object row_count does not match the prepared artifact."
            )
