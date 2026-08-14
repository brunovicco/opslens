"""Unit tests for the EPSS ingestion application service."""

import gzip

from opslens.ingestion.epss.application.key_factory import EpssBronzeKeyFactory
from opslens.ingestion.epss.application.models import (
    RepositoryWriteResult,
    RepositoryWriteStatus,
)
from opslens.ingestion.epss.application.service import IngestEpssSnapshot
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.epss.domain.parser import EpssSnapshotParser


class FakeSnapshotSource:
    """In-memory EPSS source used to test application orchestration."""

    def __init__(self, payload: bytes) -> None:
        """Initialize the fake source with deterministic bytes."""
        self._payload = payload

    def fetch(self) -> bytes:
        """Return the configured in-memory EPSS artifact."""
        return self._payload


class FakeBronzeRepository:
    """In-memory Bronze repository that captures the requested write."""

    def __init__(self, status: RepositoryWriteStatus) -> None:
        """Initialize the repository with a deterministic write outcome."""
        self._status = status
        self.snapshot: EpssSnapshot | None = None
        self.object_key: str | None = None

    def create_if_absent(
        self,
        snapshot: EpssSnapshot,
        object_key: str,
    ) -> RepositoryWriteResult:
        """Capture the write request and return the configured outcome."""
        self.snapshot = snapshot
        self.object_key = object_key

        return RepositoryWriteResult(
            status=self._status,
            version_id="test-version" if self._status is RepositoryWriteStatus.CREATED else None,
            etag='"test-etag"' if self._status is RepositoryWriteStatus.CREATED else None,
        )


def build_snapshot_payload() -> bytes:
    """Build a deterministic EPSS source artifact for service tests."""
    content = (
        "#model_version:v2026.06.15,score_date:2026-08-14T12:00:27Z\n"
        "cve,epss,percentile\n"
        "CVE-1999-0001,0.03351,0.8762\n"
    )

    return gzip.compress(content.encode("utf-8"), mtime=0)


def test_ingestion_creates_deterministic_bronze_key() -> None:
    """Persist a valid snapshot under its canonical partitioned Bronze key."""
    source = FakeSnapshotSource(build_snapshot_payload())
    repository = FakeBronzeRepository(RepositoryWriteStatus.CREATED)

    use_case = IngestEpssSnapshot(
        source=source,
        repository=repository,
        parser=EpssSnapshotParser(),
        key_factory=EpssBronzeKeyFactory(),
    )

    result = use_case.execute()

    expected_key = "bronze/epss/snapshot_date=2026-08-14/epss_scores.csv.gz"

    assert result.status is RepositoryWriteStatus.CREATED
    assert result.s3_key == expected_key
    assert repository.object_key == expected_key
    assert repository.snapshot is not None
    assert repository.snapshot.snapshot_date == "2026-08-14"


def test_ingestion_propagates_already_exists_result() -> None:
    """Treat an existing deterministic object as an idempotent outcome."""
    source = FakeSnapshotSource(build_snapshot_payload())
    repository = FakeBronzeRepository(RepositoryWriteStatus.ALREADY_EXISTS)

    use_case = IngestEpssSnapshot(
        source=source,
        repository=repository,
        parser=EpssSnapshotParser(),
        key_factory=EpssBronzeKeyFactory(),
    )

    result = use_case.execute()

    assert result.status is RepositoryWriteStatus.ALREADY_EXISTS
    assert result.version_id is None
    assert result.etag is None
