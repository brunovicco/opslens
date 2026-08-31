"""Application orchestration for exact historical EPSS Silver persistence."""

from typing import Protocol

from opslens.transformation.epss.history.models import (
    HistoricalEpssSilverArtifactV1,
    HistoricalEpssSilverPersistenceResultV1,
    HistoricalEpssSilverReplayStatus,
    HistoricalEpssSilverStoredObjectV1,
)


class HistoricalEpssSilverAlreadyExistsError(RuntimeError):
    """Signal that deterministic Silver content exists and must be verified."""


class HistoricalEpssSilverRepository(Protocol):
    """Persist one deterministic historical EPSS Silver object."""

    def put_if_absent(
        self,
        *,
        key: str,
        artifact: HistoricalEpssSilverArtifactV1,
    ) -> HistoricalEpssSilverStoredObjectV1:
        """Create one Silver object or require replay verification."""
        ...


class HistoricalEpssSilverReplayVerifier(Protocol):
    """Verify one existing deterministic historical EPSS Silver object."""

    def verify_current(
        self,
        *,
        key: str,
        artifact: HistoricalEpssSilverArtifactV1,
    ) -> HistoricalEpssSilverStoredObjectV1:
        """Verify current-key persistence against exact prepared bytes."""
        ...


class PersistHistoricalEpssSilver:
    """Persist or reconcile one deterministic historical EPSS Silver artifact."""

    def __init__(
        self,
        *,
        repository: HistoricalEpssSilverRepository,
        replay_verifier: HistoricalEpssSilverReplayVerifier,
    ) -> None:
        """Initialize exact persistence dependencies."""
        self._repository = repository
        self._replay_verifier = replay_verifier

    def execute(
        self,
        *,
        key: str,
        artifact: HistoricalEpssSilverArtifactV1,
    ) -> HistoricalEpssSilverPersistenceResultV1:
        """Persist exact bytes or verify that the existing current version matches."""
        normalized_key = key.strip()

        if not normalized_key:
            raise ValueError("Historical EPSS Silver persistence key cannot be empty.")

        try:
            stored_object = self._repository.put_if_absent(
                key=normalized_key,
                artifact=artifact,
            )
            replay_status = HistoricalEpssSilverReplayStatus.CREATED
        except HistoricalEpssSilverAlreadyExistsError:
            stored_object = self._replay_verifier.verify_current(
                key=normalized_key,
                artifact=artifact,
            )
            replay_status = HistoricalEpssSilverReplayStatus.REPLAY_VERIFIED

        self._validate_stored_object(
            key=normalized_key,
            artifact=artifact,
            stored_object=stored_object,
        )

        return HistoricalEpssSilverPersistenceResultV1(
            stored_object=stored_object,
            replay_status=replay_status,
        )

    @staticmethod
    def _validate_stored_object(
        *,
        key: str,
        artifact: HistoricalEpssSilverArtifactV1,
        stored_object: HistoricalEpssSilverStoredObjectV1,
    ) -> None:
        """Require persisted evidence to match the prepared deterministic artifact."""
        if stored_object.key != key:
            raise ValueError(
                "Historical EPSS Silver stored key does not match the deterministic key."
            )
        if stored_object.parquet_sha256 != artifact.parquet_sha256:
            raise ValueError(
                "Historical EPSS Silver stored SHA-256 does not match the prepared artifact."
            )
        if stored_object.size_bytes != artifact.size_bytes:
            raise ValueError(
                "Historical EPSS Silver stored size does not match the prepared artifact."
            )
        if stored_object.row_count != artifact.row_count:
            raise ValueError(
                "Historical EPSS Silver stored row_count does not match the prepared artifact."
            )
        if stored_object.schema_version != artifact.schema_version:
            raise ValueError(
                "Historical EPSS Silver stored schema_version does not match the prepared artifact."
            )
