"""Runtime orchestration for NVD Bronze-to-Silver processing."""

from typing import Protocol

from opslens.transformation.nvd.application.models import (
    NvdSilverPreparedBatchV1,
    NvdSilverTransformRequestV1,
)
from opslens.transformation.nvd.application.persistence_models import (
    NvdSilverStoredCompletionV1,
)
from opslens.transformation.nvd.application.runtime_models import (
    NvdSilverRuntimeRequestV1,
    NvdSilverRuntimeResultV1,
)
from opslens.transformation.nvd.completion.manifest import (
    NvdSilverCompletionArtifactV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)


class NvdSilverRuntimeRequestLoader(Protocol):
    """Load exact Bronze objects for one runtime manifest coordinate."""

    def load(
        self,
        *,
        source_kind: NvdSilverSourceKind,
        manifest_key: str,
        manifest_version_id: str,
    ) -> NvdSilverTransformRequestV1:
        """Load exact manifest and object-version payloads."""
        ...


class NvdSilverPrepareUseCase(Protocol):
    """Prepare deterministic NVD Silver output from exact Bronze bytes."""

    def prepare(
        self,
        request: NvdSilverTransformRequestV1,
    ) -> NvdSilverPreparedBatchV1:
        """Verify Bronze evidence and prepare deterministic Silver."""
        ...


class NvdSilverParquetPersistenceUseCase(Protocol):
    """Persist or reconcile Parquet and prepare COMPLETE evidence."""

    def prepare_completion(
        self,
        prepared: NvdSilverPreparedBatchV1,
    ) -> NvdSilverCompletionArtifactV1:
        """Return deterministic COMPLETE evidence after Parquet persistence."""
        ...


class NvdSilverCompletionPersistenceUseCase(Protocol):
    """Persist or exactly reconcile the final COMPLETE manifest."""

    def persist(
        self,
        artifact: NvdSilverCompletionArtifactV1,
    ) -> NvdSilverStoredCompletionV1:
        """Return exact persisted COMPLETE evidence."""
        ...


class NvdSilverRuntimeProcessor:
    """Coordinate one exact Bronze-manifest-to-Silver processing flow."""

    def __init__(
        self,
        *,
        request_loader: NvdSilverRuntimeRequestLoader,
        prepare_service: NvdSilverPrepareUseCase,
        parquet_persistence_service: NvdSilverParquetPersistenceUseCase,
        completion_persistence_service: NvdSilverCompletionPersistenceUseCase,
    ) -> None:
        """Initialize explicit runtime application dependencies."""
        self._request_loader = request_loader
        self._prepare_service = prepare_service
        self._parquet_persistence_service = parquet_persistence_service
        self._completion_persistence_service = completion_persistence_service

    def process(
        self,
        request: NvdSilverRuntimeRequestV1,
    ) -> NvdSilverRuntimeResultV1:
        """Process one exact NVD Bronze COMPLETE manifest coordinate."""
        transform_request = self._request_loader.load(
            source_kind=request.source_kind,
            manifest_key=request.manifest_key,
            manifest_version_id=request.manifest_version_id,
        )

        self._validate_loaded_request(
            runtime_request=request,
            transform_request=transform_request,
        )

        prepared = self._prepare_service.prepare(
            transform_request,
        )

        self._validate_prepared_binding(
            runtime_request=request,
            prepared=prepared,
        )

        completion = self._parquet_persistence_service.prepare_completion(prepared)

        self._validate_completion_binding(
            prepared=prepared,
            completion=completion,
        )

        stored_complete = self._completion_persistence_service.persist(completion)

        self._validate_stored_completion(
            completion=completion,
            stored=stored_complete,
        )

        silver_object = completion.manifest.silver_object

        return NvdSilverRuntimeResultV1(
            source_kind=prepared.evidence.source_kind,
            source_batch_id=prepared.evidence.source_batch_id,
            bronze_manifest_key=prepared.evidence.manifest_key,
            bronze_manifest_version_id=(prepared.evidence.manifest_version_id),
            bronze_manifest_sha256=(prepared.evidence.manifest_sha256),
            silver_parquet_key=silver_object.key,
            silver_parquet_version_id=silver_object.version_id,
            silver_parquet_sha256=silver_object.sha256,
            silver_complete_key=stored_complete.key,
            silver_complete_version_id=stored_complete.version_id,
            silver_complete_sha256=stored_complete.sha256,
            row_count=silver_object.row_count,
        )

    @staticmethod
    def _validate_loaded_request(
        *,
        runtime_request: NvdSilverRuntimeRequestV1,
        transform_request: NvdSilverTransformRequestV1,
    ) -> None:
        """Require the loader output to preserve the requested coordinate."""
        if transform_request.source_kind is not runtime_request.source_kind:
            raise ValueError("Loaded NVD Silver source_kind does not match the runtime request.")

        if transform_request.manifest_key != runtime_request.manifest_key:
            raise ValueError("Loaded NVD Silver manifest key does not match the runtime request.")

        if transform_request.manifest_version_id != runtime_request.manifest_version_id:
            raise ValueError(
                "Loaded NVD Silver manifest VersionId does not match the runtime request."
            )

    @staticmethod
    def _validate_prepared_binding(
        *,
        runtime_request: NvdSilverRuntimeRequestV1,
        prepared: NvdSilverPreparedBatchV1,
    ) -> None:
        """Require verified Bronze evidence to bind to the runtime coordinate."""
        evidence = prepared.evidence

        if evidence.source_kind is not runtime_request.source_kind:
            raise ValueError("Prepared NVD Silver source_kind does not match the runtime request.")

        if evidence.manifest_key != runtime_request.manifest_key:
            raise ValueError(
                "Prepared NVD Silver Bronze manifest key does not match the runtime request."
            )

        if evidence.manifest_version_id != runtime_request.manifest_version_id:
            raise ValueError(
                "Prepared NVD Silver Bronze manifest VersionId does not match the runtime request."
            )

    @staticmethod
    def _validate_completion_binding(
        *,
        prepared: NvdSilverPreparedBatchV1,
        completion: NvdSilverCompletionArtifactV1,
    ) -> None:
        """Require COMPLETE evidence to remain bound to the prepared batch."""
        manifest = completion.manifest

        if manifest.bronze_evidence != prepared.evidence:
            raise ValueError(
                "NVD Silver COMPLETE Bronze evidence does not match the prepared batch."
            )

        if completion.manifest_key != prepared.keys.manifest_key:
            raise ValueError("NVD Silver COMPLETE key does not match the prepared batch.")

        silver_object = manifest.silver_object

        if silver_object.key != prepared.keys.parquet_key:
            raise ValueError("NVD Silver COMPLETE Parquet key does not match the prepared batch.")

        if silver_object.sha256 != prepared.parquet_artifact.parquet_sha256:
            raise ValueError(
                "NVD Silver COMPLETE Parquet SHA-256 does not match the prepared artifact."
            )

        if silver_object.row_count != prepared.parquet_artifact.row_count:
            raise ValueError(
                "NVD Silver COMPLETE Parquet row_count does not match the prepared artifact."
            )

    @staticmethod
    def _validate_stored_completion(
        *,
        completion: NvdSilverCompletionArtifactV1,
        stored: NvdSilverStoredCompletionV1,
    ) -> None:
        """Require final persisted COMPLETE evidence to match exact bytes."""
        if stored.key != completion.manifest_key:
            raise ValueError(
                "Persisted NVD Silver COMPLETE key does not match the completion artifact."
            )

        if stored.sha256 != completion.manifest_sha256:
            raise ValueError(
                "Persisted NVD Silver COMPLETE SHA-256 does not match the completion artifact."
            )

        if stored.size_bytes != len(completion.manifest_bytes):
            raise ValueError(
                "Persisted NVD Silver COMPLETE size does not match the completion artifact."
            )
