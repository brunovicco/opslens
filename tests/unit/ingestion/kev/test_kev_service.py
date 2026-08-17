"""Unit tests for the CISA KEV ingestion application service."""

import json
from datetime import UTC, datetime

from opslens.ingestion.kev.application.key_factory import KevBronzeKeyFactory
from opslens.ingestion.kev.application.models import (
    RepositoryWriteResult,
    RepositoryWriteStatus,
)
from opslens.ingestion.kev.application.service import IngestKevCatalog
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.ingestion.kev.domain.parser import KevCatalogParser


class FakeCatalogSource:
    """In-memory CISA KEV source used to test application orchestration."""

    def __init__(self, payload: bytes) -> None:
        """Initialize the fake source with deterministic bytes."""
        self._payload = payload

    def fetch(self) -> bytes:
        """Return the configured in-memory CISA KEV artifact."""
        return self._payload


class FakeBronzeRepository:
    """In-memory Bronze repository that captures the requested write."""

    def __init__(self, status: RepositoryWriteStatus) -> None:
        """Initialize the repository with a deterministic write outcome."""
        self._status = status
        self.snapshot: KevCatalogSnapshot | None = None
        self.object_key: str | None = None

    def create_if_absent(
        self,
        snapshot: KevCatalogSnapshot,
        object_key: str,
    ) -> RepositoryWriteResult:
        """Capture the write request and return the configured outcome."""
        self.snapshot = snapshot
        self.object_key = object_key

        return RepositoryWriteResult(
            status=self._status,
            version_id=(
                "test-version"
                if self._status is RepositoryWriteStatus.CREATED
                else None
            ),
            etag=(
                '"test-etag"'
                if self._status is RepositoryWriteStatus.CREATED
                else None
            ),
        )


class FixedClock:
    """Return a deterministic timestamp for application tests."""

    def __init__(self, current_time: datetime) -> None:
        """Initialize the clock with a fixed timestamp."""
        self._current_time = current_time

    def now(self) -> datetime:
        """Return the configured timestamp."""
        return self._current_time


def build_catalog_payload() -> bytes:
    """Build a deterministic CISA KEV catalog for service tests."""
    document = {
        "catalogVersion": "2026.08.16",
        "dateReleased": "2026-08-16T20:15:00Z",
        "count": 1,
        "vulnerabilities": [
            {
                "cveID": "CVE-2026-0001",
            }
        ],
    }

    return json.dumps(
        document,
        separators=(",", ":"),
    ).encode("utf-8")


def test_ingestion_creates_deterministic_bronze_key() -> None:
    """Persist a valid catalog under its canonical partitioned Bronze key."""
    source = FakeCatalogSource(build_catalog_payload())
    repository = FakeBronzeRepository(RepositoryWriteStatus.CREATED)
    clock = FixedClock(
        datetime(
            2026,
            8,
            17,
            2,
            15,
            tzinfo=UTC,
        )
    )

    use_case = IngestKevCatalog(
        source=source,
        repository=repository,
        parser=KevCatalogParser(),
        key_factory=KevBronzeKeyFactory(),
        clock=clock,
    )

    result = use_case.execute()

    expected_key = (
        "bronze/kev/"
        "snapshot_date=2026-08-17/"
        "known_exploited_vulnerabilities.json"
    )

    assert result.status is RepositoryWriteStatus.CREATED
    assert result.s3_key == expected_key
    assert result.snapshot.snapshot_date == "2026-08-17"

    assert repository.object_key == expected_key
    assert repository.snapshot is not None
    assert repository.snapshot.raw_bytes == build_catalog_payload()

    assert result.version_id == "test-version"
    assert result.etag == '"test-etag"'


def test_ingestion_propagates_already_exists_result() -> None:
    """Treat an existing deterministic object as an idempotent outcome."""
    source = FakeCatalogSource(build_catalog_payload())
    repository = FakeBronzeRepository(
        RepositoryWriteStatus.ALREADY_EXISTS
    )
    clock = FixedClock(
        datetime(
            2026,
            8,
            17,
            2,
            15,
            tzinfo=UTC,
        )
    )

    use_case = IngestKevCatalog(
        source=source,
        repository=repository,
        parser=KevCatalogParser(),
        key_factory=KevBronzeKeyFactory(),
        clock=clock,
    )

    result = use_case.execute()

    assert result.status is RepositoryWriteStatus.ALREADY_EXISTS
    assert result.version_id is None
    assert result.etag is None


def test_ingestion_uses_clock_for_observation_date() -> None:
    """Derive the Bronze partition from the injected observation clock."""
    source = FakeCatalogSource(build_catalog_payload())
    repository = FakeBronzeRepository(RepositoryWriteStatus.CREATED)

    clock = FixedClock(
        datetime(
            2026,
            12,
            31,
            23,
            59,
            tzinfo=UTC,
        )
    )

    use_case = IngestKevCatalog(
        source=source,
        repository=repository,
        parser=KevCatalogParser(),
        key_factory=KevBronzeKeyFactory(),
        clock=clock,
    )

    result = use_case.execute()

    assert result.snapshot.snapshot_date == "2026-12-31"
    assert (
        result.s3_key
        == "bronze/kev/"
        "snapshot_date=2026-12-31/"
        "known_exploited_vulnerabilities.json"
    )
