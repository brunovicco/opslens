"""Application orchestration for immutable GHSA Silver persistence."""

from dataclasses import dataclass
from typing import Protocol

from opslens.transformation.ghsa.completion.manifest import (
    GhsaSilverCompletionArtifactV1,
    GhsaSilverCompletionManifestFactoryV1,
    GhsaSilverCompletionManifestSerializerV1,
)
from opslens.transformation.ghsa.completion.models import (
    GhsaSilverStoredCompletionV1,
    GhsaSilverStoredContentObjectV1,
)
from opslens.transformation.ghsa.completion.preparation import (
    GhsaSilverContentPreparerV1,
    GhsaSilverPreparedContentObjectV1,
)
from opslens.transformation.ghsa.runtime.materializer import (
    GhsaSilverMaterializationV1,
)


class GhsaSilverContentRepository(Protocol):
    """Define immutable persistence for one authoritative content object."""

    def put_if_absent(
        self,
        prepared: GhsaSilverPreparedContentObjectV1,
    ) -> GhsaSilverStoredContentObjectV1:
        """Create or exactly verify one deterministic content object."""
        ...


class GhsaSilverCompletionRepository(Protocol):
    """Define immutable persistence for one COMPLETE artifact."""

    def put_if_absent(
        self,
        artifact: GhsaSilverCompletionArtifactV1,
    ) -> GhsaSilverStoredCompletionV1:
        """Create or exactly verify one deterministic COMPLETE artifact."""
        ...


@dataclass(frozen=True, slots=True)
class GhsaSilverPersistenceResultV1:
    """Represent one fully persisted GHSA Silver Bronze-attempt result."""

    materialization: GhsaSilverMaterializationV1
    stored_content_objects: tuple[GhsaSilverStoredContentObjectV1, ...]
    completion_artifact: GhsaSilverCompletionArtifactV1
    stored_completion: GhsaSilverStoredCompletionV1

    def __post_init__(self) -> None:
        """Validate end-to-end persisted completion evidence."""
        if len(self.stored_content_objects) != self.materialization.record_count:
            raise ValueError(
                "GHSA Silver persistence content count does not match "
                "logical materialization."
            )

        manifest = self.completion_artifact.manifest

        if manifest.context != self.materialization.context:
            raise ValueError(
                "GHSA Silver persistence COMPLETE context does not match "
                "logical materialization."
            )

        if (
            manifest.logical_record_set_sha256
            != self.materialization.logical_record_set_sha256
        ):
            raise ValueError(
                "GHSA Silver persistence COMPLETE logical identity does not match."
            )

        if self.stored_completion.key != self.completion_artifact.key:
            raise ValueError(
                "GHSA Silver stored COMPLETE key does not match artifact."
            )

        if (
            self.stored_completion.sha256
            != self.completion_artifact.manifest_sha256
        ):
            raise ValueError(
                "GHSA Silver stored COMPLETE SHA-256 does not match artifact."
            )

        if (
            self.stored_completion.size_bytes
            != len(self.completion_artifact.manifest_bytes)
        ):
            raise ValueError(
                "GHSA Silver stored COMPLETE size does not match artifact."
            )

    @property
    def record_count(self) -> int:
        """Return the number of authoritative content versions completed."""
        return self.materialization.record_count


class GhsaSilverPersistenceServiceV1:
    """Persist content-addressed Silver rows before publishing COMPLETE."""

    def __init__(
        self,
        *,
        content_preparer: GhsaSilverContentPreparerV1,
        content_repository: GhsaSilverContentRepository,
        manifest_factory: GhsaSilverCompletionManifestFactoryV1,
        manifest_serializer: GhsaSilverCompletionManifestSerializerV1,
        completion_repository: GhsaSilverCompletionRepository,
    ) -> None:
        """Initialize explicit deterministic persistence dependencies."""
        self._content_preparer = content_preparer
        self._content_repository = content_repository
        self._manifest_factory = manifest_factory
        self._manifest_serializer = manifest_serializer
        self._completion_repository = completion_repository

    def persist(
        self,
        materialization: GhsaSilverMaterializationV1,
    ) -> GhsaSilverPersistenceResultV1:
        """Persist all content first and publish COMPLETE only after success."""
        prepared_objects = self._content_preparer.prepare(materialization)
        stored_objects = tuple(
            self._content_repository.put_if_absent(prepared)
            for prepared in prepared_objects
        )
        manifest = self._manifest_factory.build(
            materialization=materialization,
            stored_objects=stored_objects,
        )
        completion_artifact = self._manifest_serializer.serialize(manifest)
        stored_completion = self._completion_repository.put_if_absent(
            completion_artifact
        )

        return GhsaSilverPersistenceResultV1(
            materialization=materialization,
            stored_content_objects=stored_objects,
            completion_artifact=completion_artifact,
            stored_completion=stored_completion,
        )
