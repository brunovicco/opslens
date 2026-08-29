"""Runtime orchestration for GHSA Bronze-to-Silver processing."""

from typing import Protocol

from opslens.transformation.ghsa.application.runtime_models import (
    GhsaSilverRuntimeRequestV1,
    GhsaSilverRuntimeResultV1,
)
from opslens.transformation.ghsa.completion.service import (
    GhsaSilverPersistenceResultV1,
)
from opslens.transformation.ghsa.runtime.materializer import (
    GhsaSilverMaterializationV1,
)


class GhsaSilverPreparationUseCase(Protocol):
    """Prepare logical Silver materialization from exact Bronze evidence."""

    def prepare(
        self,
        *,
        manifest_key: str,
        manifest_version_id: str,
    ) -> GhsaSilverMaterializationV1:
        """Prepare one exact Bronze attempt."""
        ...


class GhsaSilverPersistenceUseCase(Protocol):
    """Persist one logical materialization and publish COMPLETE last."""

    def persist(
        self,
        materialization: GhsaSilverMaterializationV1,
    ) -> GhsaSilverPersistenceResultV1:
        """Persist authoritative content and COMPLETE evidence."""
        ...


class GhsaSilverRuntimeProcessorV1:
    """Coordinate one exact GHSA Bronze-manifest-to-Silver flow."""

    def __init__(
        self,
        *,
        preparation_service: GhsaSilverPreparationUseCase,
        persistence_service: GhsaSilverPersistenceUseCase,
    ) -> None:
        """Initialize explicit application dependencies."""
        self._preparation_service = preparation_service
        self._persistence_service = persistence_service

    def process(
        self,
        request: GhsaSilverRuntimeRequestV1,
    ) -> GhsaSilverRuntimeResultV1:
        """Process one exact GHSA Bronze COMPLETE manifest coordinate."""
        materialization = self._preparation_service.prepare(
            manifest_key=request.manifest_key,
            manifest_version_id=request.manifest_version_id,
        )

        self._validate_materialization_binding(
            request=request,
            materialization=materialization,
        )

        persisted = self._persistence_service.persist(materialization)

        self._validate_persistence_binding(
            materialization=materialization,
            persisted=persisted,
        )

        context = materialization.context
        stored_complete = persisted.stored_completion

        return GhsaSilverRuntimeResultV1(
            sync_id=context.sync_id,
            attempt_id=context.attempt_id,
            bronze_manifest_key=context.manifest_key,
            bronze_manifest_version_id=context.manifest_version_id,
            logical_record_set_sha256=(
                materialization.logical_record_set_sha256
            ),
            silver_complete_key=stored_complete.key,
            silver_complete_version_id=stored_complete.version_id,
            silver_complete_sha256=stored_complete.sha256,
            row_count=materialization.record_count,
            content_object_count=len(persisted.stored_content_objects),
        )

    @staticmethod
    def _validate_materialization_binding(
        *,
        request: GhsaSilverRuntimeRequestV1,
        materialization: GhsaSilverMaterializationV1,
    ) -> None:
        """Require preparation to preserve the exact invocation coordinate."""
        context = materialization.context

        if context.manifest_key != request.manifest_key:
            raise ValueError(
                "Prepared GHSA Silver manifest key does not match runtime request."
            )

        if context.manifest_version_id != request.manifest_version_id:
            raise ValueError(
                "Prepared GHSA Silver manifest VersionId does not match "
                "runtime request."
            )

    @staticmethod
    def _validate_persistence_binding(
        *,
        materialization: GhsaSilverMaterializationV1,
        persisted: GhsaSilverPersistenceResultV1,
    ) -> None:
        """Require persistence result to remain bound to logical materialization."""
        if persisted.materialization != materialization:
            raise ValueError(
                "Persisted GHSA Silver materialization does not match preparation."
            )

        if persisted.record_count != materialization.record_count:
            raise ValueError(
                "Persisted GHSA Silver record count does not match preparation."
            )
