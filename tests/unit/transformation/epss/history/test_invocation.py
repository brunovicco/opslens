"""Tests for strict explicit historical EPSS invocation composition."""

import hashlib
from datetime import date

import pytest

from opslens.ingestion.epss.domain.history import EpssModelEra
from opslens.transformation.epss.history.completion import (
    HistoricalEpssCompletionArtifactV1,
    HistoricalEpssCompletionManifestFactoryV1,
    HistoricalEpssCompletionPersistenceResultV1,
    HistoricalEpssCompletionReplayStatus,
    HistoricalEpssCompletionStoredObjectV1,
)
from opslens.transformation.epss.history.invocation import (
    ExecuteHistoricalEpssInvocationV1,
    HistoricalEpssInvocationParserV1,
)
from opslens.transformation.epss.history.models import (
    HistoricalEpssBronzeEvidenceV1,
    HistoricalEpssBronzeManifestV1,
    HistoricalEpssBronzeObjectPayloadV1,
    HistoricalEpssSilverArtifactV1,
    HistoricalEpssSilverPersistenceResultV1,
    HistoricalEpssSilverReplayStatus,
    HistoricalEpssSilverStoredObjectV1,
)
from opslens.transformation.epss.history.preparation import HistoricalEpssPreparedSilverV1

COMMIT = "a" * 40
SNAPSHOT_DATE = date(2021, 4, 14)
MANIFEST_KEY = (
    "bronze/epss-history/schema_version=1/"
    f"archive_commit={COMMIT}/snapshot_date=2021-04-14/manifest.json"
)
EVENT = {
    "schema_version": "1",
    "bronze_manifest_key": MANIFEST_KEY,
    "bronze_manifest_version_id": "manifest-version",
}


def _bronze() -> HistoricalEpssBronzeEvidenceV1:
    """Build exact Bronze evidence matching the invocation coordinate."""
    source = b"source"
    source_key = MANIFEST_KEY.removesuffix("manifest.json") + "epss_scores.csv.gz"
    manifest = HistoricalEpssBronzeManifestV1(
        snapshot_date=SNAPSHOT_DATE,
        archive_repository="empiricalsec/epss_scores",
        archive_commit=COMMIT,
        archive_path="2021/epss_scores-2021-04-14.csv.gz",
        archive_git_blob_sha1="b" * 40,
        model_era=EpssModelEra.V1,
        source_metadata_present=False,
        source_object_key=source_key,
        source_object_version_id="source-version",
        source_sha256=hashlib.sha256(source).hexdigest(),
        compressed_size_bytes=len(source),
        manifest_key=MANIFEST_KEY,
        manifest_version_id="manifest-version",
    )
    return HistoricalEpssBronzeEvidenceV1(
        manifest=manifest,
        source=HistoricalEpssBronzeObjectPayloadV1(
            key=source_key,
            version_id="source-version",
            raw_bytes=source,
        ),
    )


class FakeBronzeReader:
    """Return exact Bronze evidence and record ordering."""

    def __init__(self, calls: list[str]) -> None:
        """Initialize call-order capture."""
        self.calls = calls

    def execute(
        self,
        *,
        manifest_key: str,
        manifest_version_id: str,
    ) -> HistoricalEpssBronzeEvidenceV1:
        """Return matching Bronze evidence."""
        assert manifest_key == MANIFEST_KEY
        assert manifest_version_id == "manifest-version"
        self.calls.append("bronze")
        return _bronze()


class FakePreparer:
    """Prepare deterministic Silver bytes and record ordering."""

    def __init__(self, calls: list[str]) -> None:
        """Initialize call-order capture."""
        self.calls = calls

    def execute(
        self,
        evidence: HistoricalEpssBronzeEvidenceV1,
    ) -> HistoricalEpssPreparedSilverV1:
        """Return deterministic prepared Silver."""
        assert evidence.manifest.snapshot_date == SNAPSHOT_DATE
        self.calls.append("prepare")
        return HistoricalEpssPreparedSilverV1(
            key="silver/epss/snapshot_date=2021-04-14/part-00000.parquet",
            artifact=HistoricalEpssSilverArtifactV1(
                parquet_bytes=b"PAR1deterministic",
                row_count=2,
                schema_version=2,
            ),
        )


class FakeSilverPersistence:
    """Persist deterministic Silver and record ordering."""

    def __init__(self, calls: list[str]) -> None:
        """Initialize call-order capture."""
        self.calls = calls

    def execute(
        self,
        *,
        key: str,
        artifact: HistoricalEpssSilverArtifactV1,
    ) -> HistoricalEpssSilverPersistenceResultV1:
        """Return exact persisted Silver evidence."""
        self.calls.append("silver")
        return HistoricalEpssSilverPersistenceResultV1(
            stored_object=HistoricalEpssSilverStoredObjectV1(
                key=key,
                version_id="silver-version",
                parquet_sha256=artifact.parquet_sha256,
                size_bytes=artifact.size_bytes,
                row_count=artifact.row_count,
                schema_version=artifact.schema_version,
            ),
            replay_status=HistoricalEpssSilverReplayStatus.CREATED,
        )


class FakeCompletionFactory:
    """Build deterministic completion evidence and record ordering."""

    def __init__(self, calls: list[str]) -> None:
        """Initialize call-order capture and deterministic factory."""
        self.calls = calls
        self.delegate = HistoricalEpssCompletionManifestFactoryV1()

    def build(
        self,
        *,
        bronze: HistoricalEpssBronzeEvidenceV1,
        silver: HistoricalEpssSilverPersistenceResultV1,
    ) -> HistoricalEpssCompletionArtifactV1:
        """Build exact completion bytes."""
        self.calls.append("completion_build")
        return self.delegate.build(bronze=bronze, silver=silver)


class FakeCompletionPersistence:
    """Persist completion last and record ordering."""

    def __init__(self, calls: list[str]) -> None:
        """Initialize call-order capture."""
        self.calls = calls

    def execute(
        self,
        artifact: HistoricalEpssCompletionArtifactV1,
    ) -> HistoricalEpssCompletionPersistenceResultV1:
        """Return exact completion persistence evidence."""
        self.calls.append("completion_write")
        return HistoricalEpssCompletionPersistenceResultV1(
            stored_object=HistoricalEpssCompletionStoredObjectV1(
                key=artifact.key,
                version_id="completion-version",
                sha256=artifact.sha256,
                size_bytes=artifact.size_bytes,
            ),
            replay_status=HistoricalEpssCompletionReplayStatus.CREATED,
        )


def _service(
    calls: list[str],
    *,
    forward_date: date = date(2026, 8, 15),
) -> ExecuteHistoricalEpssInvocationV1:
    """Build explicit invocation composition with deterministic fakes."""
    return ExecuteHistoricalEpssInvocationV1(
        parser=HistoricalEpssInvocationParserV1(approved_archive_commit=COMMIT),
        bronze_reader=FakeBronzeReader(calls),
        silver_preparer=FakePreparer(calls),
        silver_persistence=FakeSilverPersistence(calls),
        completion_factory=FakeCompletionFactory(calls),
        completion_persistence=FakeCompletionPersistence(calls),
        first_forward_snapshot_date=forward_date,
    )


def test_parser_rejects_extra_authority_field_and_wrong_commit() -> None:
    """Keep explicit invocation surface exact and pinned to one archive revision."""
    parser = HistoricalEpssInvocationParserV1(approved_archive_commit=COMMIT)

    with pytest.raises(ValueError, match="extra"):
        parser.parse({**EVENT, "unexpected": "value"})

    with pytest.raises(ValueError, match="approved pinned revision"):
        parser.parse(
            {
                **EVENT,
                "bronze_manifest_key": MANIFEST_KEY.replace(COMMIT, "b" * 40),
            }
        )


def test_completion_is_persisted_strictly_last() -> None:
    """Prove C5 ordering from exact Bronze evidence through completion write."""
    calls: list[str] = []

    result = _service(calls).execute(EVENT)

    assert calls == ["bronze", "prepare", "silver", "completion_build", "completion_write"]
    assert result.snapshot_date == SNAPSHOT_DATE
    assert result.silver.stored_object.version_id == "silver-version"
    assert result.completion.stored_object.version_id == "completion-version"


def test_forward_authority_boundary_fails_before_any_read_or_write() -> None:
    """Reject historical bootstrap overlap before touching exact Bronze evidence."""
    calls: list[str] = []
    service = _service(calls, forward_date=SNAPSHOT_DATE)

    with pytest.raises(ValueError, match="forward-authority"):
        service.execute(EVENT)

    assert calls == []
