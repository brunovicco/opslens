"""Persist NVD Silver COMPLETE only after deterministic preparation."""

from opslens.transformation.nvd.application.errors import (
    NvdSilverCompletionAlreadyExistsError,
)
from opslens.transformation.nvd.application.persistence_models import (
    NvdSilverStoredCompletionV1,
)
from opslens.transformation.nvd.application.ports import (
    NvdSilverCompletionReplayVerifier,
    NvdSilverCompletionRepository,
)
from opslens.transformation.nvd.completion.manifest import (
    NvdSilverCompletionArtifactV1,
)


class NvdSilverCompletionPersistenceServiceV1:
    """Create or exactly reconcile the final Silver COMPLETE manifest."""

    def __init__(
        self,
        *,
        repository: NvdSilverCompletionRepository,
        replay_verifier: NvdSilverCompletionReplayVerifier,
    ) -> None:
        """Initialize COMPLETE persistence dependencies."""
        self._repository = repository
        self._replay_verifier = replay_verifier

    def persist(
        self,
        artifact: NvdSilverCompletionArtifactV1,
    ) -> NvdSilverStoredCompletionV1:
        """Persist COMPLETE or prove an exact previously persisted replay."""
        try:
            stored = self._repository.put_if_absent(
                artifact=artifact,
            )
        except NvdSilverCompletionAlreadyExistsError:
            stored = self._replay_verifier.verify_current(
                artifact=artifact,
            )

        if stored.key != artifact.manifest_key:
            raise ValueError("Persisted NVD Silver COMPLETE key does not match artifact.")

        if stored.sha256 != artifact.manifest_sha256:
            raise ValueError("Persisted NVD Silver COMPLETE SHA-256 does not match artifact.")

        if stored.size_bytes != len(artifact.manifest_bytes):
            raise ValueError("Persisted NVD Silver COMPLETE size does not match artifact.")

        return stored
