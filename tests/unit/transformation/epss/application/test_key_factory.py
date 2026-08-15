"""Unit tests for the EPSS Silver key factory."""

from datetime import date

import pytest

from opslens.transformation.epss.application.key_factory import (
    EpssSilverKeyFactory,
)


def test_builds_canonical_partitioned_silver_key() -> None:
    """Build a deterministic Hive-style EPSS Silver object key."""
    factory = EpssSilverKeyFactory()

    key = factory.build(date(2026, 8, 15))

    assert key == ("silver/epss/snapshot_date=2026-08-15/part-00000.parquet")


def test_supports_explicit_prefix() -> None:
    """Build a key beneath an explicitly configured Silver prefix."""
    factory = EpssSilverKeyFactory(prefix="analytics/epss")

    assert factory.build(date(2026, 8, 15)) == (
        "analytics/epss/snapshot_date=2026-08-15/part-00000.parquet"
    )


@pytest.mark.parametrize(
    "prefix",
    [
        "",
        "/",
        "/silver/epss",
        "silver/epss/",
    ],
)
def test_rejects_invalid_prefix(prefix: str) -> None:
    """Reject empty or non-canonical Silver prefixes."""
    with pytest.raises(ValueError, match="prefix"):
        EpssSilverKeyFactory(prefix=prefix)
