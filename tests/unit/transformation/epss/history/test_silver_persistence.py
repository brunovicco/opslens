"""Unit tests for historical EPSS Silver persistence orchestration."""

from opslens.transformation.epss.history.models import (
    HistoricalEpssSilverArtifactV1,
    HistoricalEpssSilverReplayStatus,
    HistoricalEpssSilverStoredObjectV1,
)
from opslens.transformation.epss.history.persistence import (
    HistoricalEpssSilverAlreadyExistsError,
    PersistHistoricalEpssSilver,
)

KEY = "silver/epss/snapshot_date=2021-04-14/part-00000.parquet"
ARTIFACT = HistoricalEpssSilverArtifactV1(
    parquet_bytes=b"PAR1historical-epss",
    row_count=64_712,
    schema_version=2,
)


def _stored(*, key: str = KEY, version_id: str = "version-1") -> HistoricalEpssSilverStoredObjectV1:
    """Build exact stored evidence matching the deterministic test artifact."""
    return HistoricalEpssSilverStoredObjectV1(
        key=key,
        version_id=version_id,
        parquet_sha256=ARTIFACT.parquet_sha256,
        size_bytes=ARTIFACT.size_bytes,
        row_count=ARTIFACT.row_count,
        schema_version=ARTIFACT.schema_version,
    )


class FakeRepository:
    """Return configured create evidence or signal that replay is required."""

    def __init__(
        self,
        *,
        stored_object: HistoricalEpssSilverStoredObjectV1 | None = None,
        already_exists: bool = False,
    ) -> None:
        """Initialize deterministic fake repository behavior."""
        self.stored_object = stored_object or _stored()
        self.already_exists = already_exists
        self.calls = 0

    def put_if_absent(
        self,
        *,
        key: str,
        artifact: HistoricalEpssSilverArtifactV1,
    ) -> HistoricalEpssSilverStoredObjectV1:
        """Capture one create attempt."""
        self.calls += 1
        assert key == KEY
        assert artifact == ARTIFACT
        if self.already_exists:
            raise HistoricalEpssSilverAlreadyExistsError("replay required")
        return self.stored_object


class FakeReplayVerifier:
    """Return configured exact replay evidence."""

    def __init__(
        self,
        *,
        stored_object: HistoricalEpssSilverStoredObjectV1 | None = None,
    ) -> None:
        """Initialize deterministic fake replay evidence."""
        self.stored_object = stored_object or _stored(version_id="existing-version")
        self.calls = 0

    def verify_current(
        self,
        *,
        key: str,
        artifact: HistoricalEpssSilverArtifactV1,
    ) -> HistoricalEpssSilverStoredObjectV1:
        """Capture one replay verification."""
        self.calls += 1
        assert key == KEY
        assert artifact == ARTIFACT
        return self.stored_object


def test_returns_created_with_exact_new_version_evidence() -> None:
    """Keep successful create evidence without invoking replay verification."""
    repository = FakeRepository()
    replay = FakeReplayVerifier()
    service = PersistHistoricalEpssSilver(
        repository=repository,
        replay_verifier=replay,
    )

    result = service.execute(key=KEY, artifact=ARTIFACT)

    assert result.replay_status is HistoricalEpssSilverReplayStatus.CREATED
    assert result.stored_object.version_id == "version-1"
    assert repository.calls == 1
    assert replay.calls == 0


def test_precondition_failure_requires_exact_replay_verification() -> None:
    """Convert an already-existing key into success only after verifier evidence."""
    repository = FakeRepository(already_exists=True)
    replay = FakeReplayVerifier()
    service = PersistHistoricalEpssSilver(
        repository=repository,
        replay_verifier=replay,
    )

    result = service.execute(key=KEY, artifact=ARTIFACT)

    assert result.replay_status is HistoricalEpssSilverReplayStatus.REPLAY_VERIFIED
    assert result.stored_object.version_id == "existing-version"
    assert repository.calls == 1
    assert replay.calls == 1


def test_rejects_stored_evidence_for_different_key() -> None:
    """Fail closed when repository evidence does not match the deterministic key."""
    repository = FakeRepository(stored_object=_stored(key="silver/epss/wrong.parquet"))
    service = PersistHistoricalEpssSilver(
        repository=repository,
        replay_verifier=FakeReplayVerifier(),
    )

    try:
        service.execute(key=KEY, artifact=ARTIFACT)
    except ValueError as exc:
        assert "stored key" in str(exc)
    else:
        raise AssertionError("Expected stored-key evidence mismatch to fail closed.")


def test_rejects_empty_persistence_key() -> None:
    """Reject persistence without a deterministic Silver key."""
    service = PersistHistoricalEpssSilver(
        repository=FakeRepository(),
        replay_verifier=FakeReplayVerifier(),
    )

    try:
        service.execute(key="   ", artifact=ARTIFACT)
    except ValueError as exc:
        assert "key cannot be empty" in str(exc)
    else:
        raise AssertionError("Expected empty persistence key to fail.")
