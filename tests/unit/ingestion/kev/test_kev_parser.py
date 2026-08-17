"""Unit tests for the CISA KEV catalog parser."""

import hashlib
import json
from datetime import UTC, datetime, timedelta, timezone

import pytest

from opslens.ingestion.kev.domain.errors import InvalidKevCatalogError
from opslens.ingestion.kev.domain.parser import KevCatalogParser


def build_valid_catalog() -> bytes:
    """Build a deterministic minimal CISA KEV catalog."""
    document = {
        "title": "CISA Catalog of Known Exploited Vulnerabilities",
        "catalogVersion": "2026.08.16",
        "dateReleased": "2026-08-16T20:15:00.0000Z",
        "count": 2,
        "vulnerabilities": [
            {"cveID": "CVE-2026-0001"},
            {"cveID": "CVE-2026-0002"},
        ],
    }

    return json.dumps(document, separators=(",", ":")).encode("utf-8")


def test_parse_valid_catalog() -> None:
    """Parse metadata, observation date, count, and digest."""
    payload = build_valid_catalog()
    retrieved_at = datetime(2026, 8, 17, 2, 15, tzinfo=UTC)

    snapshot = KevCatalogParser().parse(
        payload=payload,
        retrieved_at=retrieved_at,
    )

    assert snapshot.catalog_version == "2026.08.16"
    assert snapshot.snapshot_date == "2026-08-17"
    assert snapshot.record_count == 2
    assert snapshot.payload_size_bytes == len(payload)
    assert snapshot.sha256 == hashlib.sha256(payload).hexdigest()
    assert snapshot.raw_bytes == payload


def test_snapshot_date_is_normalized_to_utc() -> None:
    """Derive snapshot_date from UTC rather than caller-local calendar date."""
    payload = build_valid_catalog()
    brazil_time = timezone(timedelta(hours=-3))

    retrieved_at = datetime(
        2026,
        8,
        16,
        23,
        30,
        tzinfo=brazil_time,
    )

    snapshot = KevCatalogParser().parse(
        payload=payload,
        retrieved_at=retrieved_at,
    )

    assert snapshot.snapshot_date == "2026-08-17"


def test_reject_invalid_json() -> None:
    """Reject source artifacts that are not valid JSON."""
    with pytest.raises(
        InvalidKevCatalogError,
        match="valid JSON",
    ):
        KevCatalogParser().parse(
            payload=b"{not-json",
            retrieved_at=datetime.now(UTC),
        )


def test_reject_missing_required_top_level_field() -> None:
    """Reject catalogs missing the minimum Bronze source contract."""
    vulnerabilities: list[object] = []

    document: dict[str, object] = {
        "catalogVersion": "2026.08.16",
        "dateReleased": "2026-08-16T20:15:00Z",
        "vulnerabilities": vulnerabilities,
    }

    with pytest.raises(
        InvalidKevCatalogError,
        match="count",
    ):
        KevCatalogParser().parse(
            payload=json.dumps(document).encode(),
            retrieved_at=datetime.now(UTC),
        )


def test_reject_count_mismatch() -> None:
    """Reject catalogs whose declared count differs from the array size."""
    document = {
        "catalogVersion": "2026.08.16",
        "dateReleased": "2026-08-16T20:15:00Z",
        "count": 2,
        "vulnerabilities": [{"cveID": "CVE-2026-0001"}],
    }

    with pytest.raises(
        InvalidKevCatalogError,
        match="does not match",
    ):
        KevCatalogParser().parse(
            payload=json.dumps(document).encode(),
            retrieved_at=datetime.now(UTC),
        )
