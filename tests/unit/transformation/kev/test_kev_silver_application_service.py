"""Unit tests for CISA KEV Silver application orchestration."""

import json
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import BinaryIO

import pytest

from opslens.ingestion.kev.domain.parser import KevCatalogParser
from opslens.transformation.kev.application.key_factory import (
    KevSilverKeyFactory,
)
from opslens.transformation.kev.application.models import (
    KevSilverWriteResult,
)
from opslens.transformation.kev.application.runtime_models import (
    KevSilverRepositoryWriteStatus,
    KevSilverSourceEvidence,
)
from opslens.transformation.kev.application.service import (
    KevSilverTransformationError,
    KevSilverTransformationService,
)
from opslens.transformation.kev.domain.models import SilverKevRecord
from opslens.transformation.kev.domain.transformer import (
    KevSilverTransformer,
)


class FakeRecordWriter:
    """Serialize records into a deterministic in-memory test artifact."""

    def __init__(
        self,
        *,
        row_count_override: int | None = None,
    ) -> None:
        """Initialize the fake writer."""
        self.records: tuple[SilverKevRecord, ...] = ()
        self._row_count_override = row_count_override

    def write(
        self,
        records: Iterable[SilverKevRecord],
        destination: BinaryIO,
    ) -> KevSilverWriteResult:
        """Capture records and emit one deterministic fake artifact."""
        self.records = tuple(records)

        payload = b"PARQUET"
        destination.write(payload)

        row_count = (
            len(self.records) if self._row_count_override is None else self._row_count_override
        )

        return KevSilverWriteResult(
            row_count=row_count,
            size_bytes=len(payload),
            schema_version=1,
        )


class FakeSilverRepository:
    """Capture an immutable Silver artifact persistence request."""

    def __init__(
        self,
        status: KevSilverRepositoryWriteStatus,
    ) -> None:
        """Initialize the fake repository."""
        self._status = status
        self.key: str | None = None
        self.artifact: bytes | None = None
        self.metadata: dict[str, str] | None = None
        self.calls = 0

    def put_if_absent(
        self,
        *,
        key: str,
        artifact: BinaryIO,
        metadata: Mapping[str, str],
    ) -> KevSilverRepositoryWriteStatus:
        """Capture the request and return the configured status."""
        self.calls += 1
        self.key = key
        self.artifact = artifact.read()
        self.metadata = dict(metadata)

        return self._status


def _source_payload() -> bytes:
    """Build a minimum complete KEV catalog for Silver transformation."""
    document = {
        "catalogVersion": "2026.08.14",
        "dateReleased": "2026-08-14T16:34:49.039100Z",
        "count": 1,
        "vulnerabilities": [
            {
                "cveID": "CVE-2026-12345",
                "vendorProject": "Example Vendor",
                "product": "Example Product",
                "vulnerabilityName": "Example vulnerability",
                "dateAdded": "2026-08-14",
                "shortDescription": "Example description.",
                "requiredAction": "Apply vendor remediation.",
                "dueDate": "2026-09-04",
                "knownRansomwareCampaignUse": "Unknown",
                "notes": "Example notes.",
                "cwes": ["CWE-79"],
            }
        ],
    }

    return json.dumps(
        document,
        separators=(",", ":"),
    ).encode("utf-8")


def _evidence() -> KevSilverSourceEvidence:
    """Build semantically verified-style Bronze application evidence."""
    snapshot = KevCatalogParser().parse(
        payload=_source_payload(),
        retrieved_at=datetime(
            2026,
            8,
            17,
            3,
            52,
            3,
            692159,
            tzinfo=UTC,
        ),
    )

    return KevSilverSourceEvidence(
        snapshot=snapshot,
        bronze_key=("bronze/kev/snapshot_date=2026-08-17/known_exploited_vulnerabilities.json"),
        bronze_version_id="version-123",
        bronze_etag="abc123",
    )


@pytest.mark.parametrize(
    "status",
    [
        KevSilverRepositoryWriteStatus.CREATED,
        KevSilverRepositoryWriteStatus.ALREADY_EXISTS,
    ],
)
def test_transforms_verified_evidence_and_preserves_idempotent_status(
    status: KevSilverRepositoryWriteStatus,
) -> None:
    """Produce deterministic Silver output for create and replay outcomes."""
    writer = FakeRecordWriter()
    repository = FakeSilverRepository(status)

    service = KevSilverTransformationService(
        transformer=KevSilverTransformer(),
        record_writer=writer,
        silver_repository=repository,
        key_factory=KevSilverKeyFactory(),
    )

    result = service.transform(_evidence())

    assert result.silver_key == ("silver/kev/snapshot_date=2026-08-17/part-00000.parquet")
    assert result.snapshot_date == "2026-08-17"
    assert result.row_count == 1
    assert result.size_bytes == len(b"PARQUET")
    assert result.schema_version == 1
    assert result.write_status is status

    assert len(writer.records) == 1
    assert writer.records[0].cve == "CVE-2026-12345"

    assert repository.artifact == b"PARQUET"
    assert repository.metadata is not None

    assert repository.metadata["source"] == "cisa-kev"
    assert repository.metadata["catalog_version"] == "2026.08.14"
    assert repository.metadata["row_count"] == "1"
    assert repository.metadata["schema_version"] == "1"
    assert repository.metadata["bronze_version_id"] == "version-123"
    assert repository.metadata["bronze_etag"] == "abc123"
    assert repository.metadata["source_sha256"] == result.source_sha256


def test_rejects_serialized_row_count_disagreement() -> None:
    """Fail before persistence if Silver row count differs from Bronze."""
    writer = FakeRecordWriter(
        row_count_override=2,
    )
    repository = FakeSilverRepository(KevSilverRepositoryWriteStatus.CREATED)

    service = KevSilverTransformationService(
        transformer=KevSilverTransformer(),
        record_writer=writer,
        silver_repository=repository,
        key_factory=KevSilverKeyFactory(),
    )

    with pytest.raises(
        KevSilverTransformationError,
        match="row count",
    ):
        service.transform(_evidence())

    assert repository.calls == 0


def test_builds_deterministic_silver_key() -> None:
    """Build the canonical Hive-style KEV Silver partition key."""
    key = KevSilverKeyFactory().build(_evidence().snapshot.retrieved_at.date())

    assert key == ("silver/kev/snapshot_date=2026-08-17/part-00000.parquet")


@pytest.mark.parametrize(
    "prefix",
    [
        "",
        "/silver/kev",
        "silver/kev/",
    ],
)
def test_rejects_invalid_silver_prefix(
    prefix: str,
) -> None:
    """Reject ambiguous Silver key prefixes."""
    with pytest.raises(ValueError):
        KevSilverKeyFactory(prefix=prefix)
