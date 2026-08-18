"""Unit tests for CISA KEV Silver runtime orchestration."""

from datetime import UTC, date, datetime
from types import MappingProxyType

import pytest

from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.transformation.kev.adapters.inbound.s3_event import (
    KevBronzeObjectReference,
)
from opslens.transformation.kev.adapters.outbound.s3_bronze import (
    KevBronzeObject,
)
from opslens.transformation.kev.application.runtime_models import (
    KevSilverRepositoryWriteStatus,
    KevSilverSourceEvidence,
    KevSilverTransformationResult,
)
from opslens.transformation.kev.runtime import (
    KevSilverObjectProcessor,
)

BUCKET = "opslens-dev-data-487757851499-us-east-1"

KEY = "bronze/kev/snapshot_date=2026-08-17/known_exploited_vulnerabilities.json"

SHA256 = "a" * 64


def _reference() -> KevBronzeObjectReference:
    """Build one validated-style KEV Bronze event reference."""
    return KevBronzeObjectReference(
        bucket=BUCKET,
        key=KEY,
        version_id="version-123",
        etag="bronze-etag",
        size_bytes=2,
        snapshot_date=date(2026, 8, 17),
        event_name="ObjectCreated:Put",
        sequencer="001",
    )


def _snapshot() -> KevCatalogSnapshot:
    """Build one semantically verified-style KEV snapshot."""
    return KevCatalogSnapshot(
        raw_bytes=b"{}",
        catalog_version="2026.08.14",
        date_released=datetime(
            2026,
            8,
            14,
            16,
            34,
            49,
            tzinfo=UTC,
        ),
        retrieved_at=datetime(
            2026,
            8,
            17,
            3,
            52,
            3,
            tzinfo=UTC,
        ),
        sha256=SHA256,
        record_count=1,
    )


class FakeBronzeReader:
    """Return one configured transport-verified Bronze object."""

    def __init__(
        self,
        bronze: KevBronzeObject,
    ) -> None:
        """Initialize the fake reader."""
        self._bronze = bronze
        self.references: list[KevBronzeObjectReference] = []

    def get(
        self,
        reference: KevBronzeObjectReference,
    ) -> KevBronzeObject:
        """Capture the reference and return configured Bronze evidence."""
        self.references.append(reference)
        return self._bronze


class FakeProvenanceVerifier:
    """Return one configured semantically verified snapshot."""

    def __init__(
        self,
        snapshot: KevCatalogSnapshot,
    ) -> None:
        """Initialize the fake verifier."""
        self._snapshot = snapshot
        self.objects: list[KevBronzeObject] = []

    def verify(
        self,
        bronze: KevBronzeObject,
    ) -> KevCatalogSnapshot:
        """Capture Bronze evidence and return the configured snapshot."""
        self.objects.append(bronze)
        return self._snapshot


class FakeTransformationService:
    """Capture verified application evidence and return one result."""

    def __init__(self) -> None:
        """Initialize the fake transformation service."""
        self.evidence: list[KevSilverSourceEvidence] = []

    def transform(
        self,
        evidence: KevSilverSourceEvidence,
    ) -> KevSilverTransformationResult:
        """Capture evidence and return a deterministic result."""
        self.evidence.append(evidence)

        return KevSilverTransformationResult(
            bronze_key=evidence.bronze_key,
            bronze_version_id=evidence.bronze_version_id,
            silver_key=("silver/kev/snapshot_date=2026-08-17/part-00000.parquet"),
            snapshot_date="2026-08-17",
            row_count=1,
            size_bytes=100,
            schema_version=1,
            source_sha256=evidence.snapshot.sha256,
            write_status=KevSilverRepositoryWriteStatus.CREATED,
        )


class RaisingBronzeReader:
    """Raise one configured runtime failure."""

    def get(
        self,
        reference: KevBronzeObjectReference,
    ) -> KevBronzeObject:
        """Raise instead of reading Bronze evidence."""
        del reference
        raise RuntimeError("bronze read failure")


def _bronze(
    reference: KevBronzeObjectReference,
) -> KevBronzeObject:
    """Build one transport-verified Bronze object."""
    return KevBronzeObject(
        reference=reference,
        raw_bytes=b"{}",
        metadata=MappingProxyType(
            {
                "source": "cisa-kev",
            }
        ),
        version_id=reference.version_id,
        etag=reference.etag,
        content_length=2,
    )


def test_processes_reference_through_verified_application_boundary() -> None:
    """Preserve exact Bronze lineage through runtime orchestration."""
    reference = _reference()
    bronze = _bronze(reference)
    snapshot = _snapshot()

    reader = FakeBronzeReader(bronze)
    verifier = FakeProvenanceVerifier(snapshot)
    service = FakeTransformationService()

    processor = KevSilverObjectProcessor(
        bronze_reader=reader,
        provenance_verifier=verifier,
        transformation_service=service,
    )

    result = processor.process(reference)

    assert reader.references == [reference]
    assert verifier.objects == [bronze]

    assert len(service.evidence) == 1

    evidence = service.evidence[0]

    assert evidence.snapshot is snapshot
    assert evidence.bronze_key == KEY
    assert evidence.bronze_version_id == "version-123"
    assert evidence.bronze_etag == "bronze-etag"

    assert result.bronze_key == KEY
    assert result.bronze_version_id == "version-123"
    assert result.write_status is KevSilverRepositoryWriteStatus.CREATED


def test_propagates_runtime_failure_without_swallowing_it() -> None:
    """Allow the outer Lambda invocation to observe runtime failures."""
    reference = _reference()

    processor = KevSilverObjectProcessor(
        bronze_reader=RaisingBronzeReader(),
        provenance_verifier=FakeProvenanceVerifier(_snapshot()),
        transformation_service=FakeTransformationService(),
    )

    with pytest.raises(
        RuntimeError,
        match="bronze read failure",
    ):
        processor.process(reference)
