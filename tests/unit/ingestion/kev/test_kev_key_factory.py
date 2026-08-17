"""Unit tests for deterministic CISA KEV Bronze object keys."""

from datetime import UTC, datetime

import pytest

from opslens.ingestion.kev.application.key_factory import KevBronzeKeyFactory
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot


def build_snapshot() -> KevCatalogSnapshot:
    """Build a deterministic KEV snapshot for key tests."""
    return KevCatalogSnapshot(
        raw_bytes=b'{"test":true}',
        catalog_version="2026.08.16",
        date_released=datetime(2026, 8, 16, 20, 15, tzinfo=UTC),
        retrieved_at=datetime(2026, 8, 17, 2, 15, tzinfo=UTC),
        sha256="a" * 64,
        record_count=1,
    )


def test_build_default_partitioned_key() -> None:
    """Build the canonical default KEV Bronze key."""
    key = KevBronzeKeyFactory().build(build_snapshot())

    assert (
        key
        == "bronze/kev/"
        "snapshot_date=2026-08-17/"
        "known_exploited_vulnerabilities.json"
    )


def test_normalize_custom_prefix() -> None:
    """Normalize surrounding separators from a configured prefix."""
    key = KevBronzeKeyFactory(
        prefix="/custom/kev/",
    ).build(build_snapshot())

    assert (
        key
        == "custom/kev/"
        "snapshot_date=2026-08-17/"
        "known_exploited_vulnerabilities.json"
    )


def test_reject_empty_prefix() -> None:
    """Reject a Bronze prefix containing no usable path."""
    with pytest.raises(
        ValueError,
        match="prefix cannot be empty",
    ):
        KevBronzeKeyFactory(prefix="///")
