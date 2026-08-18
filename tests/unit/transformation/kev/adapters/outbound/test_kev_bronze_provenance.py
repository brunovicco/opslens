"""Unit tests for CISA KEV Bronze semantic provenance verification."""

import hashlib
import json
from datetime import date
from types import MappingProxyType

import pytest

from opslens.ingestion.kev.domain.parser import KevCatalogParser
from opslens.transformation.kev.adapters.inbound.s3_event import (
    KevBronzeObjectReference,
)
from opslens.transformation.kev.adapters.outbound.bronze_provenance import (
    KevBronzeProvenanceError,
    KevBronzeProvenanceVerifier,
)
from opslens.transformation.kev.adapters.outbound.s3_bronze import (
    KevBronzeObject,
)

BUCKET = "opslens-dev-data-487757851499-us-east-1"

KEY = "bronze/kev/snapshot_date=2026-08-17/known_exploited_vulnerabilities.json"

RETRIEVED_AT = "2026-08-17T03:52:03.692159Z"
DATE_RELEASED = "2026-08-14T16:34:49.039100Z"


def _payload(
    *,
    catalog_version: str = "2026.08.14",
    date_released: str = DATE_RELEASED,
    count: int = 1,
) -> bytes:
    """Build one minimum-contract CISA KEV JSON document."""
    document = {
        "catalogVersion": catalog_version,
        "dateReleased": date_released,
        "count": count,
        "vulnerabilities": [{} for _ in range(count)],
    }

    return json.dumps(
        document,
        separators=(",", ":"),
    ).encode("utf-8")


def _metadata(
    payload: bytes,
) -> dict[str, str]:
    """Build canonical KEV Bronze provenance metadata."""
    return {
        "source": "cisa-kev",
        "catalog_version": "2026.08.14",
        "date_released": DATE_RELEASED,
        "retrieved_at": RETRIEVED_AT,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "record_count": "1",
    }


def _bronze(
    *,
    payload: bytes | None = None,
    metadata: dict[str, str] | None = None,
    snapshot_date: date = date(2026, 8, 17),
    content_length: int | None = None,
) -> KevBronzeObject:
    """Build transport-verified-style Bronze evidence."""
    source_payload = payload or _payload()

    source_metadata = _metadata(source_payload) if metadata is None else metadata

    reference = KevBronzeObjectReference(
        bucket=BUCKET,
        key=KEY,
        version_id="version-123",
        etag="abc123",
        size_bytes=len(source_payload),
        snapshot_date=snapshot_date,
        event_name="ObjectCreated:Put",
        sequencer="001",
    )

    return KevBronzeObject(
        reference=reference,
        raw_bytes=source_payload,
        metadata=MappingProxyType(source_metadata),
        version_id="version-123",
        etag="abc123",
        content_length=(len(source_payload) if content_length is None else content_length),
    )


def _verifier() -> KevBronzeProvenanceVerifier:
    """Build the production provenance verifier."""
    return KevBronzeProvenanceVerifier(
        parser=KevCatalogParser(),
    )


def test_verifies_complete_bronze_provenance() -> None:
    """Reconstruct a KEV snapshot when all evidence agrees."""
    bronze = _bronze()

    snapshot = _verifier().verify(bronze)

    assert snapshot.catalog_version == "2026.08.14"
    assert snapshot.record_count == 1
    assert snapshot.snapshot_date == "2026-08-17"
    assert snapshot.sha256 == bronze.metadata["sha256"]


@pytest.mark.parametrize(
    "field_name",
    [
        "source",
        "catalog_version",
        "date_released",
        "retrieved_at",
        "sha256",
        "record_count",
    ],
)
def test_rejects_missing_required_metadata(
    field_name: str,
) -> None:
    """Fail closed when required provenance metadata is absent."""
    payload = _payload()
    metadata = _metadata(payload)
    del metadata[field_name]

    with pytest.raises(
        KevBronzeProvenanceError,
        match="missing required fields",
    ):
        _verifier().verify(
            _bronze(
                payload=payload,
                metadata=metadata,
            )
        )


def test_rejects_wrong_source() -> None:
    """Require metadata to identify the CISA KEV source."""
    payload = _payload()
    metadata = _metadata(payload)
    metadata["source"] = "unexpected-source"

    with pytest.raises(
        KevBronzeProvenanceError,
        match="metadata source",
    ):
        _verifier().verify(
            _bronze(
                payload=payload,
                metadata=metadata,
            )
        )


def test_rejects_source_sha256_mismatch() -> None:
    """Recalculate SHA-256 and compare it with Bronze provenance."""
    payload = _payload()
    metadata = _metadata(payload)
    metadata["sha256"] = "a" * 64

    with pytest.raises(
        KevBronzeProvenanceError,
        match="sha256 does not match",
    ):
        _verifier().verify(
            _bronze(
                payload=payload,
                metadata=metadata,
            )
        )


@pytest.mark.parametrize(
    "sha256",
    [
        "",
        "abc",
        "A" * 64,
        "g" * 64,
    ],
)
def test_rejects_invalid_sha256_metadata(
    sha256: str,
) -> None:
    """Require the canonical lowercase SHA-256 metadata form."""
    payload = _payload()
    metadata = _metadata(payload)
    metadata["sha256"] = sha256

    with pytest.raises(
        KevBronzeProvenanceError,
        match="sha256",
    ):
        _verifier().verify(
            _bronze(
                payload=payload,
                metadata=metadata,
            )
        )


def test_rejects_catalog_version_mismatch() -> None:
    """Fail when metadata describes a different catalog version."""
    payload = _payload()
    metadata = _metadata(payload)
    metadata["catalog_version"] = "different-version"

    with pytest.raises(
        KevBronzeProvenanceError,
        match="catalog_version",
    ):
        _verifier().verify(
            _bronze(
                payload=payload,
                metadata=metadata,
            )
        )


def test_rejects_date_released_mismatch() -> None:
    """Fail when metadata dateReleased disagrees with source bytes."""
    payload = _payload()
    metadata = _metadata(payload)
    metadata["date_released"] = "2026-08-13T00:00:00Z"

    with pytest.raises(
        KevBronzeProvenanceError,
        match="date_released",
    ):
        _verifier().verify(
            _bronze(
                payload=payload,
                metadata=metadata,
            )
        )


def test_rejects_record_count_mismatch() -> None:
    """Fail when metadata count disagrees with the source catalog."""
    payload = _payload()
    metadata = _metadata(payload)
    metadata["record_count"] = "2"

    with pytest.raises(
        KevBronzeProvenanceError,
        match="record_count",
    ):
        _verifier().verify(
            _bronze(
                payload=payload,
                metadata=metadata,
            )
        )


@pytest.mark.parametrize(
    "record_count",
    [
        "0",
        "01",
        "-1",
        "abc",
        " 1",
    ],
)
def test_rejects_noncanonical_record_count(
    record_count: str,
) -> None:
    """Require canonical positive decimal record-count metadata."""
    payload = _payload()
    metadata = _metadata(payload)
    metadata["record_count"] = record_count

    with pytest.raises(
        KevBronzeProvenanceError,
        match="record_count",
    ):
        _verifier().verify(
            _bronze(
                payload=payload,
                metadata=metadata,
            )
        )


@pytest.mark.parametrize(
    "retrieved_at",
    [
        "not-a-timestamp",
        "2026-08-17T03:52:03",
        " 2026-08-17T03:52:03Z",
    ],
)
def test_rejects_invalid_retrieved_at(
    retrieved_at: str,
) -> None:
    """Require normalized timezone-aware retrieval metadata."""
    payload = _payload()
    metadata = _metadata(payload)
    metadata["retrieved_at"] = retrieved_at

    with pytest.raises(
        KevBronzeProvenanceError,
        match="retrieved_at",
    ):
        _verifier().verify(
            _bronze(
                payload=payload,
                metadata=metadata,
            )
        )


def test_rejects_snapshot_partition_mismatch() -> None:
    """Require the partition date to equal UTC retrieved_at date."""
    with pytest.raises(
        KevBronzeProvenanceError,
        match="snapshot_date",
    ):
        _verifier().verify(
            _bronze(
                snapshot_date=date(2026, 8, 18),
            )
        )


def test_rejects_verified_content_length_mismatch() -> None:
    """Defensively preserve the transport-verified payload size invariant."""
    payload = _payload()

    with pytest.raises(
        KevBronzeProvenanceError,
        match="ContentLength",
    ):
        _verifier().verify(
            _bronze(
                payload=payload,
                content_length=len(payload) + 1,
            )
        )


def test_allows_additive_metadata() -> None:
    """Ignore future metadata that does not alter required provenance."""
    payload = _payload()
    metadata = _metadata(payload)
    metadata["future_field"] = "future-value"

    snapshot = _verifier().verify(
        _bronze(
            payload=payload,
            metadata=metadata,
        )
    )

    assert snapshot.record_count == 1
