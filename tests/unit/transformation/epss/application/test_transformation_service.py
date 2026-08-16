"""Unit tests for the EPSS Bronze-to-Silver application service."""

import gzip
import hashlib
from collections.abc import Iterable, Mapping
from typing import BinaryIO

import pytest

from opslens.ingestion.epss.domain.parser import EpssSnapshotParser
from opslens.transformation.epss.application.key_factory import (
    EpssSilverKeyFactory,
)
from opslens.transformation.epss.application.models import (
    SilverRepositoryWriteStatus,
    SilverWriteResult,
)
from opslens.transformation.epss.application.service import (
    EpssSilverTransformationService,
)
from opslens.transformation.epss.domain.models import SilverEpssRecord
from opslens.transformation.epss.domain.transformer import EpssSilverTransformer


class FakeBronzeRepository:
    """Return one deterministic Bronze payload."""

    def __init__(self, payload: bytes) -> None:
        """Initialize the fake repository."""
        self.payload = payload
        self.requested_key: str | None = None

    def get(self, key: str) -> bytes:
        """Return the configured Bronze payload."""
        self.requested_key = key
        return self.payload


class FakeRecordWriter:
    """Serialize records into a deterministic binary test artifact."""

    def __init__(self) -> None:
        """Initialize captured records."""
        self.records: list[SilverEpssRecord] = []

    def write(
        self,
        records: Iterable[SilverEpssRecord],
        destination: BinaryIO,
    ) -> SilverWriteResult:
        """Write deterministic bytes after consuming all Silver records."""
        self.records = list(records)

        payload = b"PAR1-deterministic-test-artifact"
        destination.write(payload)

        return SilverWriteResult(
            row_count=len(self.records),
            size_bytes=len(payload),
            schema_version=1,
        )


class FakeSilverRepository:
    """Capture one Silver artifact publication request."""

    def __init__(
        self,
        status: SilverRepositoryWriteStatus = SilverRepositoryWriteStatus.CREATED,
    ) -> None:
        """Initialize the fake repository."""
        self.status = status
        self.key: str | None = None
        self.payload: bytes | None = None
        self.metadata: Mapping[str, str] | None = None
        self.artifact_position: int | None = None

    def put_if_absent(
        self,
        *,
        key: str,
        artifact: BinaryIO,
        metadata: Mapping[str, str],
    ) -> SilverRepositoryWriteStatus:
        """Capture the artifact and return the configured status."""
        self.key = key
        self.artifact_position = artifact.tell()
        self.payload = artifact.read()
        self.metadata = dict(metadata)

        return self.status


def build_bronze_payload() -> bytes:
    """Build one deterministic valid FIRST EPSS Bronze payload."""
    content = (
        "#model_version:v2026.06.15,score_date:2026-08-15T12:02:44Z\n"
        "cve,epss,percentile\n"
        "CVE-2026-12345,0.812345,0.987654\n"
        "CVE-2026-67890,0.123456,0.456789\n"
    )

    return gzip.compress(
        content.encode("utf-8"),
        mtime=0,
    )


def test_transforms_bronze_and_publishes_silver_artifact() -> None:
    """Orchestrate the complete application-level transformation workflow."""
    payload = build_bronze_payload()
    bronze_repository = FakeBronzeRepository(payload)
    record_writer = FakeRecordWriter()
    silver_repository = FakeSilverRepository()

    service = EpssSilverTransformationService(
        bronze_repository=bronze_repository,
        parser=EpssSnapshotParser(),
        transformer=EpssSilverTransformer(),
        record_writer=record_writer,
        silver_repository=silver_repository,
        key_factory=EpssSilverKeyFactory(),
    )

    bronze_key = "bronze/epss/snapshot_date=2026-08-15/epss_scores.csv.gz"

    result = service.transform(bronze_key)

    assert bronze_repository.requested_key == bronze_key

    assert [record.cve for record in record_writer.records] == [
        "CVE-2026-12345",
        "CVE-2026-67890",
    ]

    assert silver_repository.key == ("silver/epss/snapshot_date=2026-08-15/part-00000.parquet")

    assert silver_repository.artifact_position == 0
    assert silver_repository.payload == b"PAR1-deterministic-test-artifact"

    assert result.bronze_key == bronze_key
    assert result.silver_key == silver_repository.key
    assert result.row_count == 2
    assert result.write_status is SilverRepositoryWriteStatus.CREATED

    expected_sha256 = hashlib.sha256(payload).hexdigest()

    assert result.source_sha256 == expected_sha256

    assert silver_repository.metadata == {
        "source": "first-epss",
        "model_version": "v2026.06.15",
        "score_timestamp": "2026-08-15T12:02:44Z",
        "source_sha256": expected_sha256,
        "schema_version": "1",
        "row_count": "2",
    }


def test_preserves_already_exists_repository_outcome() -> None:
    """Return an idempotent result when the Silver key already exists."""
    service = EpssSilverTransformationService(
        bronze_repository=FakeBronzeRepository(build_bronze_payload()),
        parser=EpssSnapshotParser(),
        transformer=EpssSilverTransformer(),
        record_writer=FakeRecordWriter(),
        silver_repository=FakeSilverRepository(SilverRepositoryWriteStatus.ALREADY_EXISTS),
        key_factory=EpssSilverKeyFactory(),
    )

    result = service.transform("bronze/epss/snapshot_date=2026-08-15/epss_scores.csv.gz")

    assert result.write_status is SilverRepositoryWriteStatus.ALREADY_EXISTS


def test_rejects_empty_bronze_key_before_repository_access() -> None:
    """Reject an empty Bronze key before invoking external storage."""
    bronze_repository = FakeBronzeRepository(build_bronze_payload())

    service = EpssSilverTransformationService(
        bronze_repository=bronze_repository,
        parser=EpssSnapshotParser(),
        transformer=EpssSilverTransformer(),
        record_writer=FakeRecordWriter(),
        silver_repository=FakeSilverRepository(),
        key_factory=EpssSilverKeyFactory(),
    )

    with pytest.raises(
        ValueError,
        match="Bronze object key cannot be empty",
    ):
        service.transform("   ")

    assert bronze_repository.requested_key is None
