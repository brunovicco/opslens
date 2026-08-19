"""Unit tests for the NVD yearly-feed META parser."""

from datetime import timedelta

import pytest

from opslens.ingestion.nvd.domain.errors import InvalidNvdFeedMetaError
from opslens.ingestion.nvd.domain.meta_parser import NvdFeedMetaParser

REAL_META = b"""lastModifiedDate:2026-08-18T03:00:12-04:00
size:282112001
zipSize:23938309
gzSize:23938173
sha256:10FB32C20BD6187FE43FA047D74772256F5B37C18029B17C5379A1F4E18F5D4F
"""


def test_parse_real_nvd_meta_contract() -> None:
    """Parse the real NVD 2026 META values observed during Phase 2.3A."""
    result = NvdFeedMetaParser().parse(REAL_META)

    assert result.raw_bytes == REAL_META
    assert result.last_modified_at.isoformat() == ("2026-08-18T03:00:12-04:00")
    assert result.last_modified_at.utcoffset() == timedelta(hours=-4)
    assert result.uncompressed_size_bytes == 282112001
    assert result.zip_size_bytes == 23938309
    assert result.gzip_size_bytes == 23938173
    assert result.source_sha256 == (
        "10fb32c20bd6187fe43fa047d74772256f5b37c18029b17c5379a1f4e18f5d4f"
    )


def test_parse_tolerates_unknown_additive_meta_field() -> None:
    """Ignore additive fields while preserving the complete raw artifact."""
    payload = REAL_META + b"futureField:future-value\n"

    result = NvdFeedMetaParser().parse(payload)

    assert result.raw_bytes == payload


@pytest.mark.parametrize(
    "field",
    [
        "lastModifiedDate",
        "size",
        "zipSize",
        "gzSize",
        "sha256",
    ],
)
def test_parse_rejects_missing_required_field(field: str) -> None:
    """Reject META artifacts missing one required source field."""
    lines = [line for line in REAL_META.splitlines() if not line.startswith(f"{field}:".encode())]
    payload = b"\n".join(lines) + b"\n"

    with pytest.raises(
        InvalidNvdFeedMetaError,
        match="missing required fields",
    ):
        NvdFeedMetaParser().parse(payload)


def test_parse_rejects_duplicate_field() -> None:
    """Reject ambiguous META artifacts containing duplicate keys."""
    payload = REAL_META + b"size:282112001\n"

    with pytest.raises(
        InvalidNvdFeedMetaError,
        match="duplicate field: size",
    ):
        NvdFeedMetaParser().parse(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("size", "0"),
        ("zipSize", "-1"),
        ("gzSize", "not-an-integer"),
    ],
)
def test_parse_rejects_invalid_size(
    field: str,
    value: str,
) -> None:
    """Reject non-positive or non-integer META size values."""
    lines: list[str] = []

    for line in REAL_META.decode().splitlines():
        if line.startswith(f"{field}:"):
            lines.append(f"{field}:{value}")
        else:
            lines.append(line)

    payload = ("\n".join(lines) + "\n").encode()

    with pytest.raises(InvalidNvdFeedMetaError):
        NvdFeedMetaParser().parse(payload)


def test_parse_rejects_invalid_sha256() -> None:
    """Reject source digests that are not valid SHA-256 hexadecimal values."""
    payload = REAL_META.replace(
        b"10FB32C20BD6187FE43FA047D74772256F5B37C18029B17C5379A1F4E18F5D4F",
        b"not-a-sha256",
    )

    with pytest.raises(
        InvalidNvdFeedMetaError,
        match="64 hexadecimal characters",
    ):
        NvdFeedMetaParser().parse(payload)


def test_parse_rejects_timestamp_without_timezone() -> None:
    """Reject source timestamps without explicit timezone evidence."""
    payload = REAL_META.replace(
        b"2026-08-18T03:00:12-04:00",
        b"2026-08-18T03:00:12",
    )

    with pytest.raises(
        InvalidNvdFeedMetaError,
        match="timezone",
    ):
        NvdFeedMetaParser().parse(payload)


def test_parse_rejects_malformed_line() -> None:
    """Reject ambiguous META lines without a key-value separator."""
    payload = REAL_META + b"malformed-line\n"

    with pytest.raises(
        InvalidNvdFeedMetaError,
        match="key-value separator",
    ):
        NvdFeedMetaParser().parse(payload)


def test_parse_rejects_empty_payload() -> None:
    """Reject an empty NVD META artifact."""
    with pytest.raises(
        InvalidNvdFeedMetaError,
        match="payload is empty",
    ):
        NvdFeedMetaParser().parse(b"")
