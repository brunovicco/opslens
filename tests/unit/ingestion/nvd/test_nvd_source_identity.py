"""Unit tests for deterministic NVD bootstrap source identity."""

import pytest

from opslens.ingestion.nvd.domain.meta_parser import NvdFeedMetaParser
from opslens.ingestion.nvd.domain.source_identity import (
    NvdBootstrapSourceIdentity,
)

SOURCE_SHA256 = "10fb32c20bd6187fe43fa047d74772256f5b37c18029b17c5379a1f4e18f5d4f"


def _meta(timestamp: str, sha256: str = SOURCE_SHA256):
    """Build valid NVD META evidence for identity tests."""
    payload = (
        f"lastModifiedDate:{timestamp}\n"
        "size:282112001\n"
        "zipSize:23938309\n"
        "gzSize:23938173\n"
        f"sha256:{sha256}\n"
    ).encode()

    return NvdFeedMetaParser().parse(payload)


def test_identity_builds_expected_real_feed_revision() -> None:
    """Build the deterministic revision for the real Phase 2.3A META."""
    identity = NvdBootstrapSourceIdentity(
        feed_year=2026,
        meta=_meta("2026-08-18T03:00:12-04:00"),
    )

    assert identity.feed_revision == (
        "20260818T070012Z-10fb32c20bd6187fe43fa047d74772256f5b37c18029b17c5379a1f4e18f5d4f"
    )


def test_identity_normalizes_equivalent_timezone_instants() -> None:
    """Use the source instant rather than its timezone representation."""
    first = NvdBootstrapSourceIdentity(
        feed_year=2026,
        meta=_meta("2026-08-18T03:00:12-04:00"),
    )
    second = NvdBootstrapSourceIdentity(
        feed_year=2026,
        meta=_meta("2026-08-18T07:00:12Z"),
    )

    assert first.feed_revision == second.feed_revision


def test_identity_preserves_fractional_seconds() -> None:
    """Retain source timestamp precision when NVD supplies microseconds."""
    identity = NvdBootstrapSourceIdentity(
        feed_year=2026,
        meta=_meta("2026-08-18T07:00:12.123456Z"),
    )

    assert identity.feed_revision.startswith("20260818T070012.123456Z-")


def test_identity_changes_when_source_sha_changes() -> None:
    """Distinguish different source content at the same revision instant."""
    first = NvdBootstrapSourceIdentity(
        feed_year=2026,
        meta=_meta(
            "2026-08-18T07:00:12Z",
            sha256="1" * 64,
        ),
    )
    second = NvdBootstrapSourceIdentity(
        feed_year=2026,
        meta=_meta(
            "2026-08-18T07:00:12Z",
            sha256="2" * 64,
        ),
    )

    assert first.feed_revision != second.feed_revision


@pytest.mark.parametrize(
    "feed_year",
    [
        999,
        10000,
    ],
)
def test_identity_rejects_non_four_digit_feed_year(
    feed_year: int,
) -> None:
    """Reject feed identifiers outside the four-digit year contract."""
    with pytest.raises(
        ValueError,
        match="exactly four digits",
    ):
        NvdBootstrapSourceIdentity(
            feed_year=feed_year,
            meta=_meta("2026-08-18T07:00:12Z"),
        )


def test_identity_rejects_boolean_feed_year() -> None:
    """Reject booleans even though bool is an int subclass in Python."""
    with pytest.raises(
        ValueError,
        match="must be an integer",
    ):
        NvdBootstrapSourceIdentity(
            feed_year=True,
            meta=_meta("2026-08-18T07:00:12Z"),
        )
