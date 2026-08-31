"""Tests for historical EPSS completion evidence and persistence orchestration."""

import hashlib
import json
from datetime import date

import pytest

from opslens.ingestion.epss.domain.history import EpssModelEra
from opslens.transformation.epss.history.completion import (
    HistoricalEpssCompletionAlreadyExistsError,
    HistoricalEpssCompletionArtifactV1,
    HistoricalEpssCompletionManifestFactoryV1,
    HistoricalEpssCompletionReplayStatus,
    HistoricalEpssCompletionStoredObjectV1,
    PersistHistoricalEpssCompletion,
)
from opslens.transformation.epss.history.models import (
    HistoricalEpssBronzeEvidenceV1,
    HistoricalEpssBronzeManifestV1,
    HistoricalEpssBronzeObjectPayloadV1,
    HistoricalEpssSilverPersistenceResultV1,
    HistoricalEpssSilverReplayStatus,
    HistoricalEpssSilverStoredObjectV1,
)

SNAPSHOT_DATE = date(2021, 4, 14)
COMMIT = "a" * 40
SOURCE_BYTES = b"historical-source"
SOURCE_SHA = hashlib.sha256(SOURCE_BYTES).hexdigest()
SILVER_SHA = "c" * 64
SILVER_KEY = "silver/epss/snapshot_date=2021-04-14/part-00000.parquet"


def _bronze() -> HistoricalEpssBronzeEvidenceV1:
    """Build exact Bronze evidence for completion tests."""
    prefix = (
        "bronze/epss-history/schema_version=1/"
        f"archive_commit={COMMIT}/snapshot_date={SNAPSHOT_DATE.isoformat()}"
    )
    manifest = HistoricalEpssBronzeManifestV1(
        snapshot_date=SNAPSHOT_DATE,
        archive_repository="empiricalsec/epss_scores",
        archive_commit=COMMIT,
        archive_path="2021/epss_scores-2021-04-14.csv.gz",
        archive_git_blob_sha1="b" * 40,
        model_era=EpssModelEra.V1,
        source_metadata_present=False,
        source_object_key=f"{prefix}/epss_scores.csv.gz",
        source_object_version_id="source-version",
        source_sha256=SOURCE_SHA,
        compressed_size_bytes=len(SOURCE_BYTES),
        manifest_key=f"{prefix}/manifest.json",
        manifest_version_id="manifest-version",
    )
    return HistoricalEpssBronzeEvidenceV1(
        manifest=manifest,
        source=HistoricalEpssBronzeObjectPayloadV1(
            key=manifest.source_object_key,
            version_id=manifest.source_object_version_id,
            raw_bytes=SOURCE_BYTES,
        ),
    )


def _silver() -> HistoricalEpssSilverPersistenceResultV1:
    """Build exact persisted Silver evidence for completion tests."""
    return HistoricalEpssSilverPersistenceResultV1(
        stored_object=HistoricalEpssSilverStoredObjectV1(
            key=SILVER_KEY,
            version_id="silver-version",
            parquet_sha256=SILVER_SHA,
            size_bytes=1234,
            row_count=64_712,
            schema_version=2,
        ),
        replay_status=HistoricalEpssSilverReplayStatus.REPLAY_VERIFIED,
    )


def test_builds_canonical_completion_manifest_from_exact_evidence() -> None:
    """Bind exact Bronze and Silver coordinates into deterministic COMPLETE bytes."""
    artifact = HistoricalEpssCompletionManifestFactoryV1().build(
        bronze=_bronze(),
        silver=_silver(),
    )

    assert artifact.key == (
        "silver/epss-history/completions/schema_version=1/"
        f"archive_commit={COMMIT}/snapshot_date=2021-04-14/manifest.json"
    )
    document = json.loads(artifact.raw_bytes)
    assert document == {
        "archive_commit": COMMIT,
        "bronze_manifest_key": _bronze().manifest.manifest_key,
        "bronze_manifest_version_id": "manifest-version",
        "replay_status": "replay_verified",
        "row_count": 64_712,
        "schema_version": 1,
        "silver_key": SILVER_KEY,
        "silver_schema_version": 2,
        "silver_sha256": SILVER_SHA,
        "silver_version_id": "silver-version",
        "snapshot_date": "2021-04-14",
        "source_object_key": _bronze().manifest.source_object_key,
        "source_object_version_id": "source-version",
        "source_sha256": SOURCE_SHA,
    }
    assert artifact.sha256 == hashlib.sha256(artifact.raw_bytes).hexdigest()


def test_rejects_silver_key_outside_snapshot_coordinate() -> None:
    """Fail closed when Silver evidence does not belong to the Bronze date."""
    silver = HistoricalEpssSilverPersistenceResultV1(
        stored_object=HistoricalEpssSilverStoredObjectV1(
            key="silver/epss/snapshot_date=2021-04-15/part-00000.parquet",
            version_id="silver-version",
            parquet_sha256=SILVER_SHA,
            size_bytes=1234,
            row_count=1,
            schema_version=2,
        ),
        replay_status=HistoricalEpssSilverReplayStatus.CREATED,
    )

    with pytest.raises(ValueError, match="Silver key"):
        HistoricalEpssCompletionManifestFactoryV1().build(
            bronze=_bronze(),
            silver=silver,
        )


class FakeRepository:
    """Create completion or signal that exact replay verification is required."""

    def __init__(self, *, already_exists: bool = False) -> None:
        """Initialize deterministic repository behavior."""
        self.already_exists = already_exists

    def put_if_absent(
        self,
        *,
        artifact: HistoricalEpssCompletionArtifactV1,
    ) -> HistoricalEpssCompletionStoredObjectV1:
        """Return exact create evidence or force replay path."""
        if self.already_exists:
            raise HistoricalEpssCompletionAlreadyExistsError("exists")
        return HistoricalEpssCompletionStoredObjectV1(
            key=artifact.key,
            version_id="completion-created-version",
            sha256=artifact.sha256,
            size_bytes=artifact.size_bytes,
        )


class FakeReplayVerifier:
    """Return exact verified completion replay evidence."""

    def verify_current(
        self,
        *,
        artifact: HistoricalEpssCompletionArtifactV1,
    ) -> HistoricalEpssCompletionStoredObjectV1:
        """Return exact current-version evidence."""
        return HistoricalEpssCompletionStoredObjectV1(
            key=artifact.key,
            version_id="completion-replay-version",
            sha256=artifact.sha256,
            size_bytes=artifact.size_bytes,
        )


def test_completion_is_written_after_evidence_and_supports_verified_replay() -> None:
    """Treat existing completion as success only after verifier evidence."""
    artifact = HistoricalEpssCompletionManifestFactoryV1().build(
        bronze=_bronze(),
        silver=_silver(),
    )
    service = PersistHistoricalEpssCompletion(
        repository=FakeRepository(already_exists=True),
        replay_verifier=FakeReplayVerifier(),
    )

    result = service.execute(artifact)

    assert result.replay_status is HistoricalEpssCompletionReplayStatus.REPLAY_VERIFIED
    assert result.stored_object.version_id == "completion-replay-version"
